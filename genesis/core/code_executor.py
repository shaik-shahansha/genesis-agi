"""Code Execution Engine - execute generated code through a sandbox provider.

SECURITY (ADR-0005): this module does **not** spawn processes itself. All
untrusted execution goes through ``SandboxProvider``, which supplies environment
scrubbing, resource limits, timeouts, bounded output and artifact control.

Removed deliberately (see docs/v3/SECURITY_BASELINE.md):

* ``_ensure_dependencies_installed`` - ran ``pip install`` on package names
  regex-extracted from model output (SEC-04). A missing import is now an ordinary
  ``ImportError`` inside the sandbox. Declare capabilities with a pre-baked image
  instead; the container installs the ``tools`` extra at build time.
* ``_docker_available`` - probed for Docker but never used it. Provider selection
  is now explicit via ``genesis.sandbox.factory``.

The public surface is unchanged: ``CodeExecutionEngine(mind).execute_code(...)``
returns the same ``ExecutionResult`` shape as before.
"""

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from genesis.core.code_parser import CodeParser
from genesis.sandbox.base import (
    CapabilityUnavailableError,
    SandboxError,
    SandboxPolicy,
    SandboxSpec,
    SandboxUnavailableError,
)
from genesis.sandbox.factory import get_sandbox_provider

if TYPE_CHECKING:
    from genesis.core.mind import Mind


@dataclass
class ExecutionResult:
    """Result of code execution.

    The shape is preserved for backward compatibility. ``sandbox`` carries the
    provenance an ``ActionReceipt`` needs: which provider ran the code and what
    it actually enforced.
    """

    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    error: Optional[str] = None
    sandbox: Optional[dict] = None


class CodeExecutionEngine:
    """Execute code safely through the configured sandbox provider."""

    def __init__(self, mind: "Mind"):
        """Initialize code executor."""
        self.mind = mind
        self.max_output_size = 100_000  # 100KB max output

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 60,
        files: Optional[List[Path]] = None,
    ) -> ExecutionResult:
        """
        Execute code with isolation.

        Args:
            code: Source code to execute (may contain markdown code blocks)
            language: Programming language (only python supported)
            timeout: Max execution time in seconds
            files: Uploaded files to make available

        Returns:
            ExecutionResult with stdout/stderr
        """
        # PARSE CODE BLOCKS: Extract from markdown if present
        # LLMs often wrap code in ```python ... ```
        if CodeParser.has_code_blocks(code):
            extracted = CodeParser.extract_python_code(code)
            if extracted:
                self.mind.logger.action(
                    "code_execution",
                    f"Extracted code from markdown blocks ({len(code)} -> {len(extracted)} bytes)",
                )
                code = extracted

        # Clean code artifacts
        code = CodeParser.clean_code(code)

        if language != "python":
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Language '{language}' not supported yet",
                return_code=-1,
                execution_time=0.0,
                error=f"Unsupported language: {language}",
            )

        return await self._execute_in_sandbox(code, timeout, files)

    async def _execute_in_sandbox(
        self,
        code: str,
        timeout: int,
        files: Optional[List[Path]],
    ) -> ExecutionResult:
        """Run code in the configured sandbox and collect declared artifacts."""
        from genesis.config import get_settings

        settings = get_settings()
        output_dir = settings.data_dir / "outputs" / self.mind.identity.gmid
        output_dir.mkdir(parents=True, exist_ok=True)

        # Clamp the caller's timeout into the policy's supported range rather
        # than trusting it: an unbounded timeout would defeat the sandbox.
        bounded_timeout = max(1, min(int(timeout), 3600))
        policy = SandboxPolicy(
            wall_timeout_s=bounded_timeout,
            cpu_seconds=bounded_timeout,
            max_output_bytes=self.max_output_size,
        )

        provider = get_sandbox_provider()
        capabilities = provider.capabilities() if hasattr(provider, "capabilities") else {}
        provider_name = getattr(provider, "name", "unknown")

        self.mind.logger.action(
            "sandbox_execution",
            f"provider={provider_name} timeout={bounded_timeout}s "
            f"network={policy.network_enabled}",
        )

        handle = None
        try:
            handle = await provider.create(
                SandboxSpec(
                    language="python",
                    policy=policy,
                    files=list(files or []),
                    label=f"{self.mind.identity.gmid}:code_execution",
                )
            )

            result = await provider.execute(handle, code, policy=policy)

            # Export only what the sandbox reports as produced, then copy into
            # the Mind's permanent output directory with de-duplicating names.
            generated_files: list[str] = []
            try:
                produced = await provider.list_artifacts(handle)
                artifacts = await provider.download(handle, produced)
                for artifact in artifacts:
                    source = artifact.host_path
                    if source is None or not Path(source).is_file():
                        continue
                    dest = self._get_unique_filename(output_dir, artifact.name)
                    shutil.copy2(source, dest)
                    generated_files.append(str(dest))
                    print(f"[CODE EXEC] Saved: {artifact.name} -> {dest}")
            except SandboxError as exc:
                # Artifact collection is best-effort; the execution result stands.
                self.mind.logger.warning(f"Artifact export failed: {exc}")

            stdout = result.stdout
            if generated_files:
                import json

                file_info = json.dumps({"generated_files": generated_files})
                stdout = stdout + f"\n__GENERATED_FILES__:{file_info}"

            sandbox_meta = {
                "provider": provider_name,
                "capabilities": capabilities,
                "exit_reason": result.exit_reason,
                "timed_out": result.timed_out,
                "output_truncated": result.output_truncated,
                "artifacts": generated_files,
            }

            return ExecutionResult(
                success=result.success,
                stdout=stdout,
                stderr=result.stderr,
                return_code=result.return_code,
                execution_time=result.execution_time,
                error=result.error,
                sandbox=sandbox_meta,
            )

        except SandboxUnavailableError as exc:
            # Never fall back to an unsandboxed execution.
            self.mind.logger.error(f"Sandbox unavailable: {exc}")
            return self._failure(f"Sandbox unavailable: {exc}", provider_name)
        except CapabilityUnavailableError as exc:
            return self._failure(str(exc), provider_name)
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            self.mind.logger.error(f"Sandbox execution error: {exc}")
            return self._failure(str(exc), provider_name)
        finally:
            if handle is not None:
                try:
                    await provider.terminate(handle)
                except Exception as exc:  # noqa: BLE001
                    self.mind.logger.warning(f"Sandbox cleanup failed: {exc}")

    @staticmethod
    def _failure(message: str, provider_name: str) -> ExecutionResult:
        """Build a failed result that still records which provider was used."""
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=message,
            return_code=-1,
            execution_time=0.0,
            error=message,
            sandbox={"provider": provider_name},
        )

    def _get_unique_filename(self, directory: Path, filename: str) -> Path:
        """
        Get unique filename by adding version number if file exists.

        ``filename`` comes from the sandbox, which already restricts it to a bare
        name inside the sandbox directory. Containment is still asserted here so
        this helper is safe if reused elsewhere.

        Examples:
            document.docx -> document.docx (if doesn't exist)
            document.docx -> document_v2.docx (if exists)
            document.docx -> document_v3.docx (if v2 exists)
        """
        from genesis.core.paths import UnsafePathError, safe_child

        directory = Path(directory)
        try:
            base_path = safe_child(directory, filename)
        except UnsafePathError as exc:
            raise SandboxError(
                f"Refusing unsafe artifact name '{filename}': {exc}"
            ) from exc

        # If file doesn't exist, use original name
        if not base_path.exists():
            return base_path

        # Extract name and extension
        stem = base_path.stem  # filename without extension
        suffix = base_path.suffix  # .docx, .pptx, etc.

        # Find next available version number
        version = 2
        while True:
            versioned_name = f"{stem}_v{version}{suffix}"
            versioned_path = directory / versioned_name
            if not versioned_path.exists():
                print(f"[CODE EXEC] File exists, using versioned name: {versioned_name}")
                return versioned_path
            version += 1

            # Safety: max 100 versions
            if version > 100:
                # Use timestamp as fallback
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamped_name = f"{stem}_{timestamp}{suffix}"
                return directory / timestamped_name

    def _extract_dependencies_from_code(self, code: str) -> List[str]:
        """Extract import statements from code, for capability diagnostics.

        Retained for reporting only. Nothing is installed as a result: this is
        used to build a helpful message when the sandbox image lacks a library.
        """
        import re

        dependencies = []

        # Map of import names to package names
        package_map = {
            'pptx': 'python-pptx',
            'docx': 'python-docx',
            'openpyxl': 'openpyxl',
            'PIL': 'pillow',
            'cv2': 'opencv-python',
            'bs4': 'beautifulsoup4',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'matplotlib': 'matplotlib',
            'seaborn': 'seaborn',
            'requests': 'requests',
            'PyPDF2': 'PyPDF2',
            'pdfplumber': 'pdfplumber',
        }

        # Find import statements
        import_pattern = r'^(?:from|import)\s+(\w+)'
        for line in code.split('\n'):
            match = re.match(import_pattern, line.strip())
            if match:
                module = match.group(1)
                # Map to package name if needed
                package = package_map.get(module, module)
                if package not in [
                    'json', 'sys', 'os', 'pathlib', 'datetime',
                    'time', 're', 'asyncio', 'typing',
                ]:
                    dependencies.append(package)

        return list(set(dependencies))

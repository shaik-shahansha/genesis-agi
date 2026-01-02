"""
Code Execution Engine - Safely execute generated code.

Runs code in isolated subprocess with resource limits.
Future: Docker support for maximum isolation.
"""

import asyncio
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from genesis.core.code_parser import CodeParser

if TYPE_CHECKING:
    from genesis.core.mind import Mind


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    error: Optional[str] = None


class CodeExecutionEngine:
    """
    Execute code safely in isolated environment.
    
    Security layers:
    1. Subprocess with timeout
    2. Resource limits (future)
    3. Output truncation
    4. No network access by default (future)
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize code executor."""
        self.mind = mind
        self.max_output_size = 100_000  # 100KB max output
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 60,
        files: Optional[List[Path]] = None
    ) -> ExecutionResult:
        """
        Execute code with isolation.
        
        Args:
            code: Source code to execute (may contain markdown code blocks)
            language: Programming language (only python supported now)
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
                    f"Extracted code from markdown blocks ({len(code)} -> {len(extracted)} bytes)"
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
                error=f"Unsupported language: {language}"
            )
        
        # For now, use subprocess (Docker support later)
        return await self._execute_in_subprocess(code, timeout, files)
    
    async def _execute_in_subprocess(
        self,
        code: str,
        timeout: int,
        files: Optional[List[Path]]
    ) -> ExecutionResult:
        """
        Execute Python code in subprocess.
        
        Creates temporary directory with code and files.
        """
        print(f"[CODE EXEC] Starting subprocess execution, timeout: {timeout}s")
        print(f"[CODE EXEC] Code length: {len(code)} bytes")
        
        start_time = time.time()
        
        # Create output directory for this Mind if it doesn't exist
        from genesis.config import get_settings
        settings = get_settings()
        output_dir = settings.data_dir / "outputs" / self.mind.identity.gmid
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            print(f"[CODE EXEC] Temp directory: {tmpdir}")
            print(f"[CODE EXEC] Output directory: {output_dir}")
            
            # Write code to file
            code_file = tmpdir / "script.py"
            code_file.write_text(code, encoding='utf-8')
            print(f"[CODE EXEC] Code written to: {code_file}")
            
            # Copy uploaded files to tmpdir
            if files:
                print(f"[CODE EXEC] Copying {len(files)} uploaded files")
                for file_path in files:
                    try:
                        import shutil
                        shutil.copy2(file_path, tmpdir / file_path.name)
                        print(f"[CODE EXEC] Copied: {file_path.name}")
                    except Exception as e:
                        self.mind.logger.warning(f"Could not copy file {file_path}: {e}")
            
            # Build command
            # Use python from current environment
            python_cmd = "python"  # Will use system Python
            
            # Auto-install dependencies if needed
            dependencies = self._extract_dependencies_from_code(code)
            if dependencies:
                print(f"[CODE EXEC] Found dependencies: {dependencies}")
                await self._ensure_dependencies_installed(dependencies, tmpdir)
            
            cmd = [python_cmd, str(code_file)]
            print(f"[CODE EXEC] Command: {' '.join(cmd)}")
            
            try:
                # Execute with timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(tmpdir)
                )
                
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                    
                    stdout = stdout_bytes.decode('utf-8', errors='replace')
                    stderr = stderr_bytes.decode('utf-8', errors='replace')
                    
                    # Log execution results
                    print(f"[CODE EXEC] Process return code: {process.returncode}")
                    print(f"[CODE EXEC] Stdout length: {len(stdout)} bytes")
                    print(f"[CODE EXEC] Stderr length: {len(stderr)} bytes")
                    
                    if stderr:
                        print(f"[CODE EXEC] STDERR:\n{stderr[:500]}")
                    if stdout:
                        print(f"[CODE EXEC] STDOUT:\n{stdout[:500]}")
                    
                    # Copy any generated files to permanent output directory
                    print(f"[CODE EXEC] Checking for generated files...")
                    generated_files = []
                    for file in tmpdir.iterdir():
                        if file.name != "script.py" and file.is_file():
                            # Copy to output directory with smart versioning
                            import shutil
                            dest = self._get_unique_filename(output_dir, file.name)
                            shutil.copy2(file, dest)
                            generated_files.append(str(dest))
                            print(f"[CODE EXEC] Saved: {file.name} -> {dest}")
                    
                    # Add file paths to stdout as JSON (so orchestrator can parse)
                    if generated_files:
                        import json
                        file_info = json.dumps({"generated_files": generated_files})
                        stdout = stdout + f"\n__GENERATED_FILES__:{file_info}"
                    
                    # Truncate output if too large
                    if len(stdout) > self.max_output_size:
                        stdout = stdout[:self.max_output_size] + "\n[OUTPUT TRUNCATED]"
                    if len(stderr) > self.max_output_size:
                        stderr = stderr[:self.max_output_size] + "\n[OUTPUT TRUNCATED]"
                    
                    execution_time = time.time() - start_time
                    
                    return ExecutionResult(
                        success=process.returncode == 0,
                        stdout=stdout,
                        stderr=stderr,
                        return_code=process.returncode,
                        execution_time=execution_time
                    )
                    
                except asyncio.TimeoutError:
                    # Kill process
                    process.kill()
                    await process.wait()
                    
                    return ExecutionResult(
                        success=False,
                        stdout="",
                        stderr="",
                        return_code=-1,
                        execution_time=timeout,
                        error=f"Execution timeout exceeded ({timeout}s)"
                    )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=str(e),
                    return_code=-1,
                    execution_time=execution_time,
                    error=str(e)
                )
    
    def _get_unique_filename(self, directory: Path, filename: str) -> Path:
        """
        Get unique filename by adding version number if file exists.
        
        Examples:
            document.docx -> document.docx (if doesn't exist)
            document.docx -> document_v2.docx (if exists)
            document.docx -> document_v3.docx (if v2 exists)
        
        Args:
            directory: Directory where file will be saved
            filename: Original filename
            
        Returns:
            Path with unique filename
        """
        base_path = directory / filename
        
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
        """Extract import statements from code to identify dependencies."""
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
            'pdfplumber': 'pdfplumber'
        }
        
        # Find import statements
        import_pattern = r'^(?:from|import)\s+(\w+)'
        for line in code.split('\n'):
            match = re.match(import_pattern, line.strip())
            if match:
                module = match.group(1)
                # Map to package name if needed
                package = package_map.get(module, module)
                if package not in ['json', 'sys', 'os', 'pathlib', 'datetime', 'time', 're', 'asyncio', 'typing']:
                    dependencies.append(package)
        
        return list(set(dependencies))
    
    async def _ensure_dependencies_installed(self, dependencies: List[str], tmpdir: Path):
        """Auto-install missing dependencies."""
        import subprocess
        
        for package in dependencies:
            try:
                print(f"[CODE EXEC] Checking if {package} is installed...")
                # Try importing to check if installed
                check_cmd = ['python', '-c', f'import {package.replace("-", "_").split("[")[0]}']
                result = subprocess.run(check_cmd, capture_output=True, timeout=5)
                
                if result.returncode != 0:
                    print(f"[CODE EXEC] Installing {package}...")
                    install_cmd = ['python', '-m', 'pip', 'install', '-q', package]
                    install_result = subprocess.run(install_cmd, capture_output=True, timeout=60)
                    
                    if install_result.returncode == 0:
                        print(f"[CODE EXEC] ✓ Installed {package}")
                    else:
                        print(f"[CODE EXEC] ✗ Failed to install {package}: {install_result.stderr.decode()}")
                else:
                    print(f"[CODE EXEC] ✓ {package} already installed")
                    
            except Exception as e:
                print(f"[CODE EXEC] Warning: Could not check/install {package}: {e}")
    
    def _docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

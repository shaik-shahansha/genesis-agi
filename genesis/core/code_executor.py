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
            code: Source code to execute
            language: Programming language (only python supported now)
            timeout: Max execution time in seconds
            files: Uploaded files to make available
            
        Returns:
            ExecutionResult with stdout/stderr
        """
        
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
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Write code to file
            code_file = tmpdir / "script.py"
            code_file.write_text(code, encoding='utf-8')
            
            # Copy uploaded files to tmpdir
            if files:
                for file_path in files:
                    try:
                        import shutil
                        shutil.copy2(file_path, tmpdir / file_path.name)
                    except Exception as e:
                        self.mind.logger.warning(f"Could not copy file {file_path}: {e}")
            
            # Build command
            # Use python from current environment
            python_cmd = "python"  # Will use system Python
            
            cmd = [python_cmd, str(code_file)]
            
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

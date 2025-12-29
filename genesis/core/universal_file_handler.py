"""
Universal File Handler - Process ANY file type dynamically.

Generates parsing code on-the-fly for each file format.
No pre-built parsers!
"""

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind


@dataclass
class FileProcessingResult:
    """Result of file processing."""
    success: bool
    file_type: str
    data: Dict[str, Any]
    summary: str
    error: Optional[str] = None


class UniversalFileHandler:
    """
    Process ANY file format by generating parsing code dynamically.
    
    Supported formats (dynamically expandable):
    - Documents: PDF, DOCX, TXT
    - Spreadsheets: XLSX, XLS, CSV
    - Data: JSON, YAML, XML
    - Images: PNG, JPG (with analysis)
    - Code: PY, JS, etc.
    - Archives: ZIP, TAR
    - And any other format!
    """
    
    # Library suggestions for common formats
    FORMAT_LIBRARIES = {
        'pdf': 'PyPDF2, pdfplumber',
        'docx': 'python-docx',
        'xlsx': 'pandas, openpyxl',
        'xls': 'pandas, xlrd',
        'csv': 'pandas, csv',
        'json': 'json',
        'yaml': 'pyyaml',
        'xml': 'lxml, xml.etree',
        'html': 'beautifulsoup4',
        'txt': 'built-in',
        'md': 'markdown',
        'png': 'PIL, cv2',
        'jpg': 'PIL, cv2',
        'jpeg': 'PIL, cv2',
        'zip': 'zipfile',
        'tar': 'tarfile',
        'gz': 'gzip',
    }
    
    def __init__(self, mind: 'Mind'):
        """Initialize file handler."""
        self.mind = mind
    
    async def process_file(
        self,
        file_path: Path,
        user_request: str
    ) -> FileProcessingResult:
        """
        Process file based on user's intent.
        
        Args:
            file_path: Path to file
            user_request: What user wants to do with file
            
        Returns:
            FileProcessingResult with extracted data
        """
        
        try:
            # Detect file type
            file_type = self._detect_file_type(file_path)
            
            self.mind.logger.info(f"[FILE_HANDLER] Processing {file_path.name} as {file_type}")
            
            # Generate parsing code
            parsing_code = await self._generate_parsing_code(
                file_path=file_path,
                file_type=file_type,
                user_request=user_request
            )
            
            # Execute parsing code
            exec_result = await self.mind.autonomous_orchestrator.code_executor.execute_code(
                code=parsing_code,
                files=[file_path],
                timeout=30
            )
            
            if exec_result.success:
                # Parse output as JSON
                try:
                    data = json.loads(exec_result.stdout)
                except Exception:
                    # If not JSON, wrap in dict
                    data = {"output": exec_result.stdout}
                
                # Generate summary
                summary = await self._generate_summary(data, user_request)
                
                # Store in memory
                await self._store_file_memory(file_path, file_type, user_request, data)
                
                return FileProcessingResult(
                    success=True,
                    file_type=file_type,
                    data=data,
                    summary=summary
                )
            else:
                return FileProcessingResult(
                    success=False,
                    file_type=file_type,
                    data={},
                    summary="",
                    error=exec_result.stderr or exec_result.error
                )
                
        except Exception as e:
            self.mind.logger.error(f"[FILE_HANDLER] Error: {e}")
            
            return FileProcessingResult(
                success=False,
                file_type="unknown",
                data={},
                summary="",
                error=str(e)
            )
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type from extension and MIME type."""
        
        # Try extension first
        ext = file_path.suffix.lower().lstrip('.')
        if ext:
            return ext
        
        # Fallback to MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            # Convert MIME to extension
            if 'pdf' in mime_type:
                return 'pdf'
            elif 'excel' in mime_type or 'spreadsheet' in mime_type:
                return 'xlsx'
            elif 'word' in mime_type or 'document' in mime_type:
                return 'docx'
            elif 'image' in mime_type:
                return 'image'
        
        return 'unknown'
    
    async def _generate_parsing_code(
        self,
        file_path: Path,
        file_type: str,
        user_request: str
    ) -> str:
        """
        Generate custom parsing code for this file.
        
        Returns:
            Python code to parse file and return JSON
        """
        
        libraries = self.FORMAT_LIBRARIES.get(file_type, 'standard library')
        
        prompt = f"""Generate Python code to read and process this file:

File: {file_path.name}
Type: {file_type}
User wants: {user_request}

Libraries available for {file_type}: {libraries}

Generate code that:
1. Reads the file from path: {file_path}
2. Extracts relevant data based on user request
3. Returns structured JSON output to stdout
4. Handles errors gracefully with try/except
5. Prints JSON result using print(json.dumps(result))

Example structure:
```python
import json
# Import necessary libraries

try:
    # Read and process file
    # For {file_type} files, use {libraries}
    
    result = {{
        "success": True,
        "data": ...,  # Extracted data
        "summary": "brief summary"
    }}
    print(json.dumps(result))
    
except Exception as e:
    result = {{
        "success": False,
        "error": str(e)
    }}
    print(json.dumps(result))
```

Return ONLY the code, no explanations.
"""
        
        code = await self.mind.think(prompt, temperature=0.2)
        
        # Extract code block
        import re
        pattern = r"```(?:python)?\n(.*?)\n```"
        match = re.search(pattern, code, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return code.strip()
    
    async def _generate_summary(self, data: Dict[str, Any], user_request: str) -> str:
        """Generate human-readable summary of file data."""
        
        prompt = f"""Summarize this file data in 1-2 sentences:

User request: {user_request}

Data:
{json.dumps(data, indent=2)[:500]}  # First 500 chars

Be concise and helpful."""
        
        summary = await self.mind.think(prompt, temperature=0.3, max_tokens=100)
        return summary.strip()
    
    async def _store_file_memory(
        self,
        file_path: Path,
        file_type: str,
        user_request: str,
        data: Dict[str, Any]
    ):
        """Store file processing in memory."""
        try:
            await self.mind.memory.add_episodic_memory(
                context=f"Processed file: {file_path.name}",
                content=f"User request: {user_request}\nFile type: {file_type}\nData extracted successfully",
                metadata={
                    "file_name": file_path.name,
                    "file_type": file_type,
                    "has_data": bool(data)
                }
            )
        except Exception as e:
            self.mind.logger.warning(f"Could not store file memory: {e}")

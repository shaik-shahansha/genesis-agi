"""
Intelligent Code Generator - Generates code on-the-fly for any task.

Uses LLM + RAG to create optimized, executable code for user requests.
No pre-built tools - pure dynamic generation!
"""

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind
    from genesis.core.autonomous_orchestrator import UploadedFile


@dataclass
class GeneratedCode:
    """Generated code with metadata."""
    source: str
    language: str
    dependencies: List[str]
    estimated_runtime: float


class IntelligentCodeGenerator:
    """
    Generate optimal code for any task using LLM + RAG.
    
    This is where the magic happens - no pre-built tools,
    just dynamic code generation for ANY request!
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize code generator."""
        self.mind = mind
    
    async def generate_solution(
        self,
        task: str,
        context: Dict[str, Any],
        files: Optional[List['UploadedFile']] = None
    ) -> GeneratedCode:
        """
        Generate complete, executable code for task.
        
        Args:
            task: Description of what to accomplish
            context: Execution context
            files: Uploaded files to process
            
        Returns:
            GeneratedCode with source and metadata
        """
        
        # Search for similar past solutions
        similar = await self._search_past_solutions(task)
        
        # Build context-aware prompt
        prompt = self._build_prompt(task, context, files, similar)
        
        # Generate code with LLM
        code = await self.mind.think(
            prompt=prompt,
            temperature=0.2,  # More deterministic for code
            max_tokens=4000
        )
        
        # Extract code from response
        code = self._extract_code_block(code)
        
        # Validate syntax
        if not self._validate_syntax(code):
            # Try to fix automatically
            code = await self._fix_syntax_errors(code)
        
        return GeneratedCode(
            source=code,
            language="python",
            dependencies=self._extract_dependencies(code),
            estimated_runtime=self._estimate_runtime(code)
        )
    
    def _build_prompt(
        self,
        task: str,
        context: Dict[str, Any],
        files: Optional[List['UploadedFile']],
        similar_solutions: List[Dict]
    ) -> str:
        """Build comprehensive prompt for code generation."""
        
        prompt = f"""Generate Python code to accomplish this task:
{task}

Context:
{json.dumps(context, indent=2)}

"""
        
        # Add file information if present
        if files:
            prompt += "\nFiles available:\n"
            for file in files:
                prompt += f"- {file.name} ({file.mime_type}, {file.size} bytes)\n"
                prompt += f"  Path: {file.path}\n"
        
        # Add similar past solutions if found
        if similar_solutions:
            prompt += "\n\nSimilar past solutions:\n"
            for sol in similar_solutions[:2]:  # Show top 2
                prompt += f"- {sol.get('context', 'Previous solution')}\n"
        
        prompt += """
Requirements:
1. Complete, executable Python code
2. Comprehensive error handling with try/except
3. Logging/print statements for debugging
4. Return results as JSON or structured data
5. Handle edge cases and invalid inputs
6. Include docstrings for main functions
7. Use type hints where appropriate
8. If files are involved, read and process them

Available libraries (install if needed):
- requests, beautifulsoup4, lxml (web scraping)
- pandas, numpy, matplotlib, seaborn (data analysis/viz)
- playwright, selenium (browser automation if needed, though prefer requests)
- python-pptx, python-docx, openpyxl (document generation)
- pillow, opencv-python (image processing)
- PyPDF2, pdfplumber (PDF processing)
- Standard library (json, csv, pathlib, datetime, etc.)

Code structure:
```python
import json
# Other imports...

def main():
    \"\"\"Main function.\"\"\"
    try:
        # Your code here
        result = {
            "success": True,
            "data": ...,
            # Include all relevant outputs
        }
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))

if __name__ == "__main__":
    main()
```

Return ONLY the code, no explanations or markdown.
"""
        
        return prompt
    
    async def _search_past_solutions(self, task: str) -> List[Dict]:
        """Search for similar past solutions in memory."""
        try:
            results = await self.mind.memory.search(
                query=task,
                memory_type="procedural",
                k=3
            )
            return results
        except Exception:
            return []
    
    def _extract_code_block(self, response: str) -> str:
        """Extract code from markdown code blocks."""
        # Try to find code block
        pattern = r"```(?:python)?\n(.*?)\n```"
        match = re.search(pattern, response, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # If no code block, return entire response
        return response.strip()
    
    def _validate_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    async def _fix_syntax_errors(self, code: str) -> str:
        """Try to fix syntax errors automatically."""
        prompt = f"""This Python code has syntax errors. Fix them:

```python
{code}
```

Return ONLY the corrected code, no explanations."""
        
        fixed = await self.mind.think(prompt, temperature=0.1)
        return self._extract_code_block(fixed)
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """Extract import statements from code."""
        dependencies = []
        
        # Parse imports
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)
        except Exception:
            pass
        
        return list(set(dependencies))
    
    def _estimate_runtime(self, code: str) -> float:
        """Estimate code execution time (rough heuristic)."""
        # Simple heuristic based on code complexity
        lines = len(code.split('\n'))
        
        # Look for expensive operations
        if 'requests.get' in code or 'BeautifulSoup' in code:
            return 10.0  # Web scraping
        elif 'pandas' in code and lines > 50:
            return 5.0  # Data processing
        elif 'playwright' in code:
            return 15.0  # Browser automation
        else:
            return 2.0  # Simple task

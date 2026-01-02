"""
Code Parser - Extract code from LLM responses with backticks.

Handles common LLM response patterns:
- ```python ... ```
- ``` ... ```
- Mixed text and code blocks
"""

import re
from typing import List, Tuple, Optional


class CodeBlock:
    """Represents an extracted code block."""
    
    def __init__(self, code: str, language: Optional[str] = None, start_pos: int = 0):
        """
        Initialize code block.
        
        Args:
            code: The code content
            language: Language identifier (e.g., 'python', 'javascript')
            start_pos: Position in original text
        """
        self.code = code.strip()
        self.language = language
        self.start_pos = start_pos
    
    def __repr__(self):
        lang = self.language or "unknown"
        preview = self.code[:50].replace('\n', ' ')
        return f"CodeBlock(lang={lang}, code='{preview}...')"


class CodeParser:
    """Parser for extracting code from markdown-style code blocks."""
    
    # Regex for fenced code blocks with optional language
    FENCED_CODE_PATTERN = re.compile(
        r'```(?P<language>\w+)?\s*\n(?P<code>.*?)```',
        re.DOTALL | re.MULTILINE
    )
    
    # Alternative pattern for code blocks without language specifier
    SIMPLE_CODE_PATTERN = re.compile(
        r'```\s*\n(?P<code>.*?)```',
        re.DOTALL | re.MULTILINE
    )
    
    @classmethod
    def extract_code_blocks(cls, text: str) -> List[CodeBlock]:
        """
        Extract all code blocks from text.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            List of CodeBlock objects
            
        Examples:
            >>> text = "Here's code:\\n```python\\nprint('hi')\\n```"
            >>> blocks = CodeParser.extract_code_blocks(text)
            >>> blocks[0].code
            "print('hi')"
            >>> blocks[0].language
            "python"
        """
        blocks = []
        
        for match in cls.FENCED_CODE_PATTERN.finditer(text):
            code = match.group('code')
            language = match.group('language')
            start_pos = match.start()
            
            blocks.append(CodeBlock(
                code=code,
                language=language,
                start_pos=start_pos
            ))
        
        return blocks
    
    @classmethod
    def extract_first_code_block(cls, text: str) -> Optional[CodeBlock]:
        """
        Extract first code block from text.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            First CodeBlock or None
        """
        blocks = cls.extract_code_blocks(text)
        return blocks[0] if blocks else None
    
    @classmethod
    def extract_python_code(cls, text: str) -> Optional[str]:
        """
        Extract first Python code block.
        
        This is the most common use case.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            Python code string or None
        """
        blocks = cls.extract_code_blocks(text)
        
        # First, look for explicitly marked Python blocks
        for block in blocks:
            if block.language and block.language.lower() in ('python', 'py'):
                return block.code
        
        # Fallback: return first block without language marker
        # (LLMs often forget to specify language)
        for block in blocks:
            if block.language is None:
                return block.code
        
        # Last resort: return first block regardless
        if blocks:
            return blocks[0].code
        
        return None
    
    @classmethod
    def remove_code_blocks(cls, text: str) -> str:
        """
        Remove all code blocks, leaving only surrounding text.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            Text with code blocks removed
        """
        return cls.FENCED_CODE_PATTERN.sub('', text)
    
    @classmethod
    def extract_text_and_code(cls, text: str) -> Tuple[str, List[CodeBlock]]:
        """
        Extract both text and code blocks separately.
        
        Args:
            text: Mixed text and code
            
        Returns:
            Tuple of (text_only, code_blocks)
        """
        blocks = cls.extract_code_blocks(text)
        text_only = cls.remove_code_blocks(text)
        return text_only.strip(), blocks
    
    @classmethod
    def has_code_blocks(cls, text: str) -> bool:
        """
        Check if text contains any code blocks.
        
        Args:
            text: Text to check
            
        Returns:
            True if code blocks found
        """
        return bool(cls.FENCED_CODE_PATTERN.search(text))
    
    @classmethod
    def clean_code(cls, code: str) -> str:
        """
        Clean code by removing common LLM artifacts.
        
        Removes:
        - Leading/trailing whitespace
        - Common comment markers like "# ... existing code ..."
        - Placeholder comments
        
        Args:
            code: Code to clean
            
        Returns:
            Cleaned code
        """
        lines = code.strip().split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip placeholder comments
            if re.search(r'#.*\.\.\.\s*(existing|rest of|more)\s+code', line, re.IGNORECASE):
                continue
            if re.search(r'#.*\(.*code omitted.*\)', line, re.IGNORECASE):
                continue
            if line.strip() == '# ...':
                continue
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()


# Convenience functions for common use cases

def extract_python(text: str) -> Optional[str]:
    """
    Quick function to extract Python code from text.
    
    Usage:
        code = extract_python(llm_response)
        if code:
            exec(code)
    """
    return CodeParser.extract_python_code(text)


def has_code(text: str) -> bool:
    """Quick check if text has code blocks."""
    return CodeParser.has_code_blocks(text)


def clean_code(code: str) -> str:
    """Quick function to clean code."""
    return CodeParser.clean_code(code)

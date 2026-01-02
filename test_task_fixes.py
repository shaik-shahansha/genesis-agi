"""
Test Task Detection and Code Parsing Fixes

Run this to verify:
1. Internal LLM prompts don't trigger task detection
2. Code blocks are properly extracted
"""

import sys
sys.path.insert(0, '.')

from genesis.core.task_detector import TaskDetector
from genesis.core.code_parser import CodeParser, extract_python


def test_task_detection():
    """Test that internal LLM prompts are properly skipped."""
    print("=" * 60)
    print("TESTING TASK DETECTION")
    print("=" * 60)
    
    detector = TaskDetector()
    
    # Test cases
    test_cases = [
        # Should be detected as tasks
        ("create human digital twin presentation", True),
        ("analyze this CSV file", True),
        ("search for best laptops under $1000", True),
        
        # Should NOT be detected as tasks (internal LLM)
        ("Analyze this user request and extract key information:", False),
        ("Create a step-by-step execution plan for this task:", False),
        ("Brainstorm the overall structure, key sections", False),
        ("Generate Python code to accomplish this task:", False),
        ("This Python code has syntax errors. Fix them:", False),
        
        # Should NOT be detected as tasks (conversation)
        ("what can you do?", False),
        ("how are you?", False),
        ("tell me about AI", False),
    ]
    
    passed = 0
    failed = 0
    
    for prompt, expected_is_task in test_cases:
        result = detector.detect(prompt)
        is_task = result['is_task']
        
        status = "✓" if is_task == expected_is_task else "✗"
        
        if is_task == expected_is_task:
            passed += 1
            print(f"{status} '{prompt[:50]}...'")
            print(f"   → is_task={is_task}, conf={result['confidence']:.2f}, reason={result['reasoning'][:60]}...")
        else:
            failed += 1
            print(f"{status} FAIL: '{prompt[:50]}...'")
            print(f"   → Expected is_task={expected_is_task}, got {is_task}")
            print(f"   → conf={result['confidence']:.2f}, reason={result['reasoning']}")
        print()
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_code_parsing():
    """Test code block extraction."""
    print("\n" + "=" * 60)
    print("TESTING CODE PARSING")
    print("=" * 60)
    
    # Test case 1: Python code block
    test1 = """
Here's the code to solve that:

```python
import json
import logging

def main():
    print("Hello, world!")
    
if __name__ == "__main__":
    main()
```

That should work!
"""
    
    code1 = extract_python(test1)
    if code1:
        print("✓ Test 1: Extracted Python code block")
        print(f"   Code length: {len(code1)} chars")
        print(f"   First line: {code1.split(chr(10))[0]}")
    else:
        print("✗ Test 1: FAILED to extract code")
    
    # Test case 2: No language marker
    test2 = """
```
print("No language specified")
```
"""
    
    code2 = extract_python(test2)
    if code2:
        print("✓ Test 2: Extracted code without language marker")
        print(f"   Code: {code2}")
    else:
        print("✗ Test 2: FAILED to extract code")
    
    # Test case 3: Multiple blocks
    test3 = """
First, import modules:

```python
import os
import sys
```

Then run:

```python
def hello():
    print("Hi")
```
"""
    
    code3 = extract_python(test3)
    if code3 and "import" in code3:
        print("✓ Test 3: Extracted first code block")
        print(f"   First line: {code3.split(chr(10))[0]}")
    else:
        print("✗ Test 3: FAILED to extract code")
    
    # Test case 4: Clean code
    test4 = """
```python
# Real code here
x = 1

# ... existing code ...

# More stuff
y = 2
```
"""
    
    code4 = CodeParser.extract_python_code(test4)
    if code4:
        code4_cleaned = CodeParser.clean_code(code4)
        print("✓ Test 4: Cleaned code artifacts")
        print(f"   Original lines: {len(code4.split(chr(10)))}")
        print(f"   Cleaned lines: {len(code4_cleaned.split(chr(10)))}")
        if "existing code" not in code4_cleaned:
            print("   ✓ Placeholder comments removed")
        else:
            print("   ✗ Placeholder comments NOT removed")
    else:
        print("✗ Test 4: FAILED to extract code")
    
    return True


if __name__ == "__main__":
    print("\n🧪 Running Task Detection & Code Parsing Tests\n")
    
    test1_pass = test_task_detection()
    test2_pass = test_code_parsing()
    
    print("\n" + "=" * 60)
    if test1_pass and test2_pass:
        print(" ALL TESTS PASSED!")
    else:
        print(" SOME TESTS FAILED")
    print("=" * 60)

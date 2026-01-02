"""
Test the improved task completion system.
This tests the fixes for intelligent task handling.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind

# Use existing Mind
EXISTING_MIND_GMID = "GMD-2026-658A-D910"


async def test_document_creation():
    """Test creating a document with proper filename."""
    print("\n" + "="*80)
    print("TEST: Document Creation with Specific Topic")
    print("="*80)
    
    try:
        mind = Mind.load(EXISTING_MIND_GMID)
        print(f"✓ Loaded Mind: {mind.identity.name}")
        
        # Test the same request from the logs
        request = "create word doc for human digital twins with benefits"
        print(f"\n📋 Request: {request}")
        print("\nExpected behavior:")
        print("  - Should create 'human_digital_twins_benefits.docx'")
        print("  - Should NOT search internet")
        print("  - Should use only code_execution step")
        print("  - Content should be about human digital twins and benefits")
        
        result = await mind.handle_request(
            user_request=request,
            user_email="test@example.com"
        )
        
        print(f"\n✅ Result:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Artifacts: {len(result.get('artifacts', []))}")
        
        if result.get('artifacts'):
            for artifact in result['artifacts']:
                print(f"  - {artifact.get('name', 'unknown')}: {artifact.get('path', 'unknown')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_presentation_creation():
    """Test creating a presentation."""
    print("\n" + "="*80)
    print("TEST: Presentation Creation")
    print("="*80)
    
    try:
        mind = Mind.load(EXISTING_MIND_GMID)
        
        request = "create a presentation about artificial intelligence future trends"
        print(f"\n📋 Request: {request}")
        print("\nExpected behavior:")
        print("  - Should create 'artificial_intelligence_future_trends.pptx'")
        print("  - Should include images from Pollinations.ai")
        print("  - Should NOT search internet")
        print("  - Should use only code_execution step")
        
        result = await mind.handle_request(
            user_request=request,
            user_email="test@example.com"
        )
        
        print(f"\n✅ Result:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Artifacts: {len(result.get('artifacts', []))}")
        
        if result.get('artifacts'):
            for artifact in result['artifacts']:
                print(f"  - {artifact.get('name', 'unknown')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run tests."""
    print("\n" + "="*80)
    print("🧪 TESTING IMPROVED TASK COMPLETION SYSTEM")
    print("="*80)
    
    test1 = await test_document_creation()
    test2 = await test_presentation_creation()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Document Creation: {'✓ PASSED' if test1 else '✗ FAILED'}")
    print(f"Presentation Creation: {'✓ PASSED' if test2 else '✗ FAILED'}")
    print("="*80 + "\n")
    
    return test1 and test2


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

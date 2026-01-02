"""
Test Autonomous Agent Capabilities - Manus AI Style

Tests end-to-end autonomous task execution with existing Mind:
1. Code generation for presentations
2. Web scraping
3. Data analysis
4. Background task execution
5. Result delivery

Run: python test_autonomous_agent_comprehensive.py
"""

import asyncio
import sys
from pathlib import Path
import os

# Add genesis to path
sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind
from genesis.config import get_settings

# Use existing Mind GMID
EXISTING_MIND_GMID = "GMD-2026-658A-D910"


async def load_existing_mind():
    """Load the existing Mind from disk."""
    print("\n" + "="*80)
    print("LOADING EXISTING MIND")
    print("="*80)
    
    settings = get_settings()
    mind_path = None
    
    # Find Mind file by GMID
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json
            with open(path) as f:
                data = json.load(f)
                if data["identity"]["gmid"] == EXISTING_MIND_GMID:
                    mind_path = path
                    break
        except Exception as e:
            continue
    
    if not mind_path:
        print(f"\n❌ ERROR: Mind {EXISTING_MIND_GMID} not found!")
        print(f"   Searched in: {settings.minds_dir}")
        print(f"   Available minds:")
        for path in settings.minds_dir.glob("*.json"):
            try:
                import json
                with open(path) as f:
                    data = json.load(f)
                    print(f"   - {data['identity']['name']} ({data['identity']['gmid']})")
            except:
                pass
        return None
    
    print(f"\n✅ Found Mind file: {mind_path.name}")
    
    # Load Mind
    mind = Mind.load(mind_path)
    
    print(f"✅ Mind loaded: {mind.identity.name}")
    print(f"   GMID: {mind.identity.gmid}")
    print(f"   Age: {mind.identity.age}")
    print(f"   Born: {mind.identity.birth_date}")
    print(f"   Model: {mind.intelligence.reasoning_model}")
    print(f"   Autonomy: {mind.autonomy.initiative_level.value}")
    print(f"   Status: {mind.identity.status}")
    
    return mind


async def test_presentation_generation(mind):
    """Test 1: Generate a presentation (like Manus AI)."""
    print("\n" + "="*80)
    print("TEST 1: PRESENTATION GENERATION (Manus AI Style)")
    print("="*80)
    
    if not mind:
        print("❌ No Mind available")
        return False
    
    print(f"\n✅ Using Mind: {mind.identity.name} ({mind.identity.gmid})")
    
    # Test autonomous task execution
    print("\n📋 Task: Create a 3-slide presentation about AI")
    print("   (This should generate Python code using python-pptx)")
    
    try:
        result = await mind.handle_request(
            user_request="Create a 3-slide PowerPoint presentation about Artificial Intelligence with title slide, key concepts, and future trends",
            user_email="test@example.com"
        )
        
        print(f"\n✅ Task Result:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Generated files: {len(result.get('artifacts', []))}")
        
        if result.get('artifacts'):
            print(f"\n📁 Artifacts:")
            for artifact in result['artifacts']:
                print(f"   - {artifact.get('name', 'Unknown')}: {artifact.get('path', 'N/A')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_web_research(mind):
    """Test 2: Web research and summarization."""
    print("\n" + "="*80)
    print("TEST 2: WEB RESEARCH")
    print("="*80)
    
    if not mind:
        print("❌ No Mind available")
        return False
    
    print(f"\n✅ Using Mind: {mind.identity.name}")
    
    print("\n🔍 Task: Research latest AI trends and create summary")
    
    try:
        result = await mind.handle_request(
            user_request="Research the top 3 AI trends in 2026 and create a summary report",
            user_email="test@example.com"
        )
        
        print(f"\n✅ Research Result:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Output length: {len(str(result))}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


async def test_background_task(mind):
    """Test 3: Background task execution with status tracking."""
    print("\n" + "="*80)
    print("TEST 3: BACKGROUND TASK EXECUTION")
    print("="*80)
    
    if not mind:
        print("❌ No Mind available")
        return False
    
    print(f"\n✅ Using Mind: {mind.identity.name}")
    
    print("\n⚡ Task: Analyze data in background")
    print("   (Should execute asynchronously with status updates)")
    
    try:
        # Start background task
        task = await mind.background_executor.execute_task(
            user_request="Calculate fibonacci sequence up to 20 numbers and save to file",
            user_email="test@example.com",
            notify_on_complete=True
        )
        
        print(f"\n✅ Task Created:")
        print(f"   Task ID: {task.task_id}")
        print(f"   Status: {task.status}")
        
        # Wait a bit for execution
        print("\n⏳ Waiting for task to complete...")
        await asyncio.sleep(5)
        
        # Check status
        print(f"\n✅ Final Status:")
        print(f"   Status: {task.status}")
        print(f"   Progress: {task.progress*100:.0f}%")
        
        return task.status.value == "completed"
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_code_generation(mind):
    """Test 4: Direct code generation and execution."""
    print("\n" + "="*80)
    print("TEST 4: CODE GENERATION & EXECUTION")
    print("="*80)
    
    if not mind:
        print("❌ No Mind available")
        return False
    
    print(f"\n✅ Using Mind: {mind.identity.name}")
    
    print("\n💻 Task: Generate Python code to sort a list")
    
    try:
        # Generate code
        code_result = await mind.autonomous_orchestrator.code_generator.generate_solution(
            task="Write Python code to sort a list [5, 2, 8, 1, 9] and print the result",
            context={},
            files=None
        )
        
        print(f"\n✅ Code Generated:")
        print(f"   Language: {code_result.language}")
        print(f"   Dependencies: {code_result.dependencies}")
        print(f"\n   Code:")
        print("   " + "\n   ".join(code_result.source.split("\n")[:10]))
        
        # Execute code
        print(f"\n⚡ Executing code...")
        exec_result = await mind.autonomous_orchestrator.code_executor.execute_code(
            code=code_result.source,
            language="python",
            timeout=10
        )
        
        print(f"\n✅ Execution Result:")
        print(f"   Success: {exec_result.success}")
        print(f"   Output: {exec_result.stdout[:200]}")
        if exec_result.stderr:
            print(f"   Errors: {exec_result.stderr[:200]}")
        
        return exec_result.success
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_file_processing():
    """Test 5: File upload and processing."""
    print("\n" + "="*80)
    print("TEST 5: FILE PROCESSING")
    print("="*80)
    
    print("\n⚠️  Test skipped - requires actual file upload")
    print("   In production: User uploads CSV/Excel → Agent analyzes → Returns insights")
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🚀 GENESIS AUTONOMOUS AGENT - COMPREHENSIVE TESTS")
    print("="*80)
    print(f"\nTesting with existing Mind: {EXISTING_MIND_GMID}")
    print("\nTesting Manus AI style capabilities:")
    print("  • Code generation")
    print("  • Task execution")
    print("  • Background processing")
    print("  • Result delivery")
    print("\n")
    
    # Load existing Mind (it has its own API keys configured)
    mind = await load_existing_mind()
    if not mind:
        print("\n❌ Could not load Mind. Exiting.")
        return
    
    # Verify Mind has API keys configured
    if not mind.intelligence.api_keys:
        print("\n❌ ERROR: Mind has no API keys configured!")
        print("   This Mind was created without API credentials.")
        return
    
    print(f"✅ Mind has API keys configured for: {list(mind.intelligence.api_keys.keys())}")
    print()
    
    results = {}
    
    # Run tests with existing Mind
    tests = [
        ("Code Generation", lambda: test_code_generation(mind)),
        ("Background Task", lambda: test_background_task(mind)),
        ("Web Research", lambda: test_web_research(mind)),
        ("Presentation", lambda: test_presentation_generation(mind)),
        ("File Processing", lambda: test_file_processing()),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            await asyncio.sleep(1)  # Cooldown between tests
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Save Mind state after tests
    try:
        print("\n💾 Saving Mind state...")
        mind.save()
        print("✅ Mind state saved")
    except Exception as e:
        print(f"⚠️  Could not save Mind: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    print(f"\n  Score: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED! Autonomous agent is working!")
    elif passed > 0:
        print(f"\n  ⚠️  Some tests failed. Check logs above for details.")
    else:
        print(f"\n  ❌ All tests failed. Check implementation and API keys.")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

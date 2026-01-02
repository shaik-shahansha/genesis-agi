"""
Test Task Execution Directly - Simulating Web Playground Chat

This tests task execution as if calling from the web playground.
Tests both via server API and direct Mind instance.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind


async def test_direct_mind_execution():
    """Test task execution directly through Mind instance (how server uses it)."""
    print("\n" + "="*80)
    print("TEST 1: DIRECT MIND EXECUTION (Server/Daemon Mode)")
    print("="*80 + "\n")
    
    # Find first available mind
    from genesis.config import get_settings
    settings = get_settings()
    mind_files = list(settings.minds_dir.glob("*.json"))
    if not mind_files:
        print("   ✗ No minds found!")
        return False
    
    mind_id = mind_files[0].stem
    print(f"Using mind: {mind_id}")
    
    # Load the mind (like the server does)
    print(f"1. Loading Mind {mind_id}...")
    try:
        mind = Mind.load(mind_id)
        print(f"   OK Mind loaded: {mind.identity.name}")
        print(f"   - Provider: {mind.intelligence.primary_provider}")
        print(f"   - Reasoning model: {mind.intelligence.reasoning_model}")
        print(f"   - Has orchestrator: {hasattr(mind, 'autonomous_orchestrator')}")
        print(f"   - Has background_executor: {hasattr(mind, 'background_executor')}")
        print(f"   - Has task_detector: {hasattr(mind, 'task_detector')}")
    except Exception as e:
        print(f"   ERROR loading mind: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test task detection
    print(f"\n2. Testing task detection...")
    test_request = "create a simple presentation about AI"
    
    if hasattr(mind, 'task_detector') and mind.task_detector:
        detection = mind.task_detector.detect(test_request)
        print(f"   Task Detection Result:")
        print(f"   - is_task: {detection['is_task']}")
        print(f"   - task_type: {detection['task_type']}")
        print(f"   - confidence: {detection['confidence']:.2f}")
        print(f"   - reasoning: {detection.get('reasoning', 'N/A')}")
    else:
        print(f"   ✗ No task_detector found on mind!")
    
    # Test via think() method (like chat endpoint does)
    print(f"\n3. Calling mind.think() (like web chat does)...")
    print(f"   Request: '{test_request}'")
    
    try:
        response = await mind.think(
            prompt=test_request,
            user_email="test@example.com",
            skip_task_detection=False  # Allow task detection
        )
        
        print(f"\n   Response:")
        print(f"   {response}")
        
        # Check if background task was created
        if hasattr(mind, 'background_executor'):
            active_tasks = mind.background_executor.get_active_tasks()
            print(f"\n   Active background tasks: {len(active_tasks)}")
            
            if active_tasks:
                task = active_tasks[0]
                print(f"   - Task ID: {task.task_id}")
                print(f"   - Status: {task.status.value}")
                print(f"   - Request: {task.user_request}")
                
                # Monitor task execution
                print(f"\n4. Monitoring task execution (max 120 seconds)...")
                for i in range(120):
                    await asyncio.sleep(1)
                    
                    current_task = mind.background_executor.get_task(task.task_id)
                    if current_task:
                        status = current_task.status.value
                        progress = current_task.progress * 100
                        print(f"   [{i+1}s] Status: {status}, Progress: {progress:.0f}%", end='\r')
                        
                        if status == "completed":
                            print(f"\n   ✓ Task COMPLETED!")
                            print(f"\n   Result: {current_task.result}")
                            
                            # Check if result has expected structure
                            if isinstance(current_task.result, dict):
                                print(f"\n   Result structure:")
                                print(f"   - success: {current_task.result.get('success')}")
                                print(f"   - artifacts: {len(current_task.result.get('artifacts', []))}")
                                print(f"   - results: {len(current_task.result.get('results', []))}")
                            return True
                        elif status == "failed":
                            print(f"\n   ✗ Task FAILED!")
                            print(f"   Error: {current_task.error}")
                            return False
                    else:
                        print(f"\n   ✗ Task disappeared from executor")
                        return False
                
                print(f"\n   ⚠ Task still running after 120 seconds")
                return False
            else:
                print(f"   ⚠ No background task was created - treated as regular chat?")
        
    except Exception as e:
        print(f"\n   ✗ ERROR in mind.think(): {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_direct_orchestrator():
    """Test calling orchestrator directly (bypassing think/task detection)."""
    print("\n" + "="*80)
    print("TEST 2: DIRECT ORCHESTRATOR CALL (What background task does)")
    print("="*80 + "\n")
    
    # Find first available mind
    from genesis.config import get_settings
    settings = get_settings()
    mind_files = list(settings.minds_dir.glob("*.json"))
    if not mind_files:
        print("   ✗ No minds found!")
        return False
    
    mind_id = mind_files[0].stem
    
    # Load the mind
    print(f"1. Loading Mind {mind_id}...")
    try:
        mind = Mind.load(mind_id)
        print(f"   ✓ Mind loaded: {mind.identity.name}")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return
    
    # Call handle_request directly (what background executor does)
    print(f"\n2. Calling mind.handle_request() directly...")
    test_request = "create a simple presentation about AI with 3 slides"
    
    try:
        result = await mind.handle_request(
            user_request=test_request,
            uploaded_files=None,
            context=None,
            user_email="test@example.com",
            skip_task_detection=True
        )
        
        print(f"\n   ✓ handle_request() returned!")
        print(f"\n   Result type: {type(result)}")
        print(f"\n   Result:")
        
        if isinstance(result, dict):
            print(f"   - success: {result.get('success')}")
            print(f"   - error: {result.get('error')}")
            print(f"   - artifacts: {len(result.get('artifacts', []))}")
            print(f"   - results: {len(result.get('results', []))}")
            print(f"   - execution_time: {result.get('execution_time')}s")
            
            # Show artifacts details
            if result.get('artifacts'):
                print(f"\n   Artifacts created:")
                for artifact in result['artifacts']:
                    print(f"   - {artifact}")
            
            # Show results details
            if result.get('results'):
                print(f"\n   Execution steps:")
                for i, step_result in enumerate(result['results']):
                    print(f"   Step {i+1}: {step_result}")
        else:
            print(f"   {result}")
        
        return result.get('success', False) if isinstance(result, dict) else False
        
    except Exception as e:
        print(f"\n   ✗ ERROR in handle_request(): {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_via_background_executor():
    """Test via background executor (exactly like web chat does)."""
    print("\n" + "="*80)
    print("TEST 3: VIA BACKGROUND EXECUTOR (Exact Web Flow)")
    print("="*80 + "\n")
    
    # Find first available mind
    from genesis.config import get_settings
    settings = get_settings()
    mind_files = list(settings.minds_dir.glob("*.json"))
    if not mind_files:
        print("   ✗ No minds found!")
        return False
    
    mind_id = mind_files[0].stem
    
    # Load the mind
    print(f"1. Loading Mind {mind_id}...")
    try:
        mind = Mind.load(mind_id)
        print(f"   ✓ Mind loaded: {mind.identity.name}")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return
    
    # Submit task via background executor
    print(f"\n2. Submitting task via background_executor.execute_task()...")
    test_request = "create a presentation about quantum computing with 5 slides"
    
    try:
        task = await mind.background_executor.execute_task(
            user_request=test_request,
            user_email="test@example.com",
            notify_on_complete=False
        )
        
        print(f"   ✓ Task submitted: {task.task_id}")
        print(f"   - Status: {task.status.value}")
        
        # Monitor execution
        print(f"\n3. Monitoring execution...")
        for i in range(120):
            await asyncio.sleep(1)
            
            current_task = mind.background_executor.get_task(task.task_id)
            if current_task:
                status = current_task.status.value
                progress = current_task.progress * 100
                print(f"   [{i+1}s] Status: {status}, Progress: {progress:.0f}%", end='\r')
                
                if status == "completed":
                    print(f"\n   ✓ Task COMPLETED!")
                    print(f"\n   Result: {current_task.result}")
                    return True
                elif status == "failed":
                    print(f"\n   ✗ Task FAILED!")
                    print(f"   Error: {current_task.error}")
                    
                    # Print full traceback if available
                    import traceback
                    if current_task.error:
                        print(f"\n   Error details:")
                        print(f"   {current_task.error}")
                    return False
        
        print(f"\n   ⚠ Task still running after 120 seconds")
        return False
        
    except Exception as e:
        print(f"\n   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TESTING TASK EXECUTION - WEB PLAYGROUND SIMULATION")
    print("="*80)
    print("\nSimulating: create presentation request from web chat")
    print("\n" + "="*80)
    
    # Test 1: Via think() - how web chat calls it
    success1 = await test_direct_mind_execution()
    
    # Test 2: Direct orchestrator call
    # success2 = await test_direct_orchestrator()
    
    # Test 3: Via background executor
    # success3 = await test_via_background_executor()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Test 1 (mind.think): {'✓ PASSED' if success1 else '✗ FAILED'}")
    # print(f"Test 2 (orchestrator): {'✓ PASSED' if success2 else '✗ FAILED'}")
    # print(f"Test 3 (background executor): {'✓ PASSED' if success3 else '✗ FAILED'}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

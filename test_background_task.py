"""
Test Background Task Execution Directly

This tests the actual task execution to see what's happening.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind


async def test_simple_task():
    """Test a simple task execution."""
    print("\n" + "=" * 60)
    print("TESTING SIMPLE BACKGROUND TASK")
    print("=" * 60 + "\n")
    
    # Create a test mind
    print("1. Creating test mind...")
    mind = Mind.create(
        name="TestMind",
        template="assistant",
        primary_purpose="Testing background tasks"
    )
    print(f"   ✓ Mind created: {mind.identity.name} ({mind.identity.gmid})\n")
    
    # Test simple task
    print("2. Submitting background task: 'create simple test file'")
    task = await mind.background_executor.execute_task(
        user_request="create a simple test.txt file with hello world",
        user_email="test@example.com",
        notify_on_complete=False  # Disable notifications for testing
    )
    print(f"   ✓ Task submitted: {task.task_id}\n")
    
    # Wait and monitor
    print("3. Waiting for task to complete (max 60 seconds)...")
    for i in range(60):
        await asyncio.sleep(1)
        
        # Check status
        current_task = mind.background_executor.get_task(task.task_id)
        if current_task:
            status = current_task.status.value
            progress = current_task.progress * 100
            print(f"   [{i+1}s] Status: {status}, Progress: {progress:.0f}%", end='\r')
            
            if current_task.status.value == "completed":
                print(f"\n   ✓ Task COMPLETED!")
                print(f"\n   Result: {current_task.result}")
                return True
            elif current_task.status.value == "failed":
                print(f"\n   ✗ Task FAILED!")
                print(f"   Error: {current_task.error}")
                return False
        else:
            print(f"   [{i+1}s] Task not found (might have completed)")
    
    print("\n   ✗ Task did not complete in 60 seconds")
    return False


async def test_task_detection():
    """Test that task detection works properly."""
    print("\n" + "=" * 60)
    print("TESTING TASK DETECTION IN THINK")
    print("=" * 60 + "\n")
    
    # Create a test mind
    print("1. Creating test mind...")
    mind = Mind.create(
        name="TaskTestMind",
        template="assistant",
        primary_purpose="Testing task detection"
    )
    print(f"   ✓ Mind created: {mind.identity.name}\n")
    
    # Test with a task prompt
    print("2. Testing with task prompt (should create background task)...")
    response = await mind.think(
        prompt="create a simple presentation about AI",
        user_email="test@example.com"
    )
    
    print(f"\n   Response preview: {response[:200]}...\n")
    
    # Check if task was created
    active_tasks = mind.background_executor.get_active_tasks()
    if active_tasks:
        print(f"   ✓ Background task created: {len(active_tasks)} active task(s)")
        for task in active_tasks:
            print(f"     - Task ID: {task.task_id}")
            print(f"     - Status: {task.status.value}")
            print(f"     - Request: {task.user_request[:60]}...")
        
        # Wait a bit to see progress
        print("\n3. Monitoring task progress (15 seconds)...")
        for i in range(15):
            await asyncio.sleep(1)
            task = active_tasks[0]
            current = mind.background_executor.get_task(task.task_id)
            if current:
                print(f"   [{i+1}s] {current.status.value} - {current.progress*100:.0f}%", end='\r')
        
        print("\n")
        return True
    else:
        print("   ✗ No background task created")
        return False


async def test_conversation_vs_task():
    """Test that conversations don't create tasks."""
    print("\n" + "=" * 60)
    print("TESTING CONVERSATION VS TASK")
    print("=" * 60 + "\n")
    
    mind = Mind.create(
        name="ConvoTestMind",
        template="assistant",
        primary_purpose="Testing"
    )
    
    # Test conversation
    print("1. Testing conversation: 'what can you do?'")
    response1 = await mind.think(
        prompt="what can you do?",
        user_email="test@example.com"
    )
    tasks_after_convo = len(mind.background_executor.get_active_tasks())
    print(f"   Active tasks after conversation: {tasks_after_convo}")
    
    # Test task
    print("\n2. Testing task: 'create a report on climate change'")
    response2 = await mind.think(
        prompt="create a report on climate change",
        user_email="test@example.com"
    )
    tasks_after_task = len(mind.background_executor.get_active_tasks())
    print(f"   Active tasks after task: {tasks_after_task}")
    
    if tasks_after_convo == 0 and tasks_after_task == 1:
        print("\n   PASS: Conversation didn't create task, but task prompt did")
        return True
    else:
        print(f"\n   FAIL: Expected 0 tasks after convo, 1 after task. Got {tasks_after_convo}, {tasks_after_task}")
        return False


async def main():
    """Run all tests."""
    print("\n### BACKGROUND TASK SYSTEM TEST ###\n")
    
    try:
        # Test 1: Simple background task
        test1 = await test_simple_task()
        
        # Test 2: Task detection in think()
        test2 = await test_task_detection()
        
        # Test 3: Conversation vs task
        test3 = await test_conversation_vs_task()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Simple Background Task: {'PASS' if test1 else 'FAIL'}")
        print(f"Task Detection in think(): {'PASS' if test2 else 'FAIL'}")
        print(f"Conversation vs Task: {'PASS' if test3 else 'FAIL'}")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nTEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

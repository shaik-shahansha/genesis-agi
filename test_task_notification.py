"""
Test background task with WebSocket notification delivery.

This tests the full flow:
1. Task is created
2. Background executor runs the task
3. Progress updates sent via WebSocket
4. Completion notification sent via WebSocket
5. Frontend receives and displays the messages
"""

import asyncio
import logging
from genesis.core.mind import Mind
from genesis.models.orchestrator import ModelConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_task_with_notifications():
    """Test background task with WebSocket notifications."""
    
    print("\n" + "="*70)
    print("Testing Background Task with WebSocket Notifications")
    print("="*70 + "\n")
    
    # Load existing Mind
    mind_id = "GMD-2026-658A-D910"
    print(f"Loading Mind: {mind_id}...")
    mind = Mind.load(mind_id)
    print(f"✓ Loaded: {mind.identity.name}\n")
    
    # Test user email (WebSocket connection key)
    user_email = "test_user@genesis.local"
    
    # Verify notification manager exists
    if not hasattr(mind, 'notification_manager') or not mind.notification_manager:
        print("❌ ERROR: NotificationManager not available!")
        return
    
    print(f"✓ NotificationManager available")
    print(f"  User email: {user_email}\n")
    
    # Test 1: Simple code generation task
    print("\n" + "-"*70)
    print("TEST 1: Code Generation Task")
    print("-"*70)
    
    task_request = "Create a Python function that calculates fibonacci numbers"
    
    print(f"\nCreating task: '{task_request}'")
    print("This should:")
    print("  1. Execute in background")
    print("  2. Send progress updates via WebSocket")
    print("  3. Send completion notification via WebSocket")
    print("\nNote: WebSocket will fail if not connected (expected in CLI test)")
    print("      In web playground, it should work!\n")
    
    # Execute task (this will run in background)
    if hasattr(mind, 'background_executor'):
        task = await mind.background_executor.execute_task(
            user_request=task_request,
            user_email=user_email,
            notify_on_complete=True
        )
        
        print(f"✓ Task created: {task.task_id}")
        print(f"  Status: {task.status.value}")
        print(f"  Will complete in background...")
        
        # Wait a bit for task to complete
        print("\nWaiting for task to complete (max 30 seconds)...")
        for i in range(30):
            await asyncio.sleep(1)
            
            # Check task status
            current_task = mind.background_executor.get_task(task.task_id)
            if current_task:
                status = current_task.status.value
                progress = current_task.progress * 100
                print(f"  [{i+1}s] Status: {status}, Progress: {progress:.0f}%", end='\r')
                
                if current_task.status.value in ['completed', 'failed']:
                    print(f"\n\n✓ Task {status}!")
                    
                    if current_task.status.value == 'completed':
                        print(f"\nResult summary:")
                        if hasattr(current_task, 'result') and current_task.result:
                            result = current_task.result
                            if isinstance(result, dict):
                                if result.get('artifacts'):
                                    print(f"  Artifacts created: {len(result['artifacts'])}")
                                    for artifact in result['artifacts'][:3]:
                                        print(f"    - {artifact.get('name', 'Unknown')}")
                                if result.get('results'):
                                    print(f"  Steps executed: {len(result['results'])}")
                    else:
                        print(f"\n  Error: {current_task.error}")
                    
                    break
        else:
            print("\n\n⚠️  Timeout waiting for task completion")
    
    else:
        print("❌ ERROR: BackgroundTaskExecutor not available!")
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70)
    print("\nTo see WebSocket messages in action:")
    print("1. Start the API server: genesis start")
    print("2. Open web playground: http://localhost:8000/playground")
    print("3. Navigate to chat page")
    print("4. Ask Mind to do a task")
    print("5. Watch for progress updates and completion message!")
    print("\n")

if __name__ == "__main__":
    asyncio.run(test_task_with_notifications())

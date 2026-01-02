"""
Simple test for task execution - simulating web chat
"""

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind
from genesis.config import get_settings


async def test_task():
    """Test task execution like web chat does."""
    print("\n" + "="*80)
    print("TASK EXECUTION TEST")
    print("="*80 + "\n")
    
    # Find first mind
    settings = get_settings()
    mind_files = list(settings.minds_dir.glob("*.json"))
    if not mind_files:
        print("[ERROR] No minds found!")
        return False
    
    mind_id = mind_files[0].stem
    print(f"[INFO] Using mind: {mind_id}\n")
    
    # Load mind
    print("[INFO] Loading mind...")
    
    # Find the mind file path
    mind_path = None
    for path in settings.minds_dir.glob("*.json"):
        if path.stem == mind_id:
            mind_path = path
            break
    
    if not mind_path:
        print(f"[ERROR] Mind file not found for {mind_id}")
        return False
    
    mind = Mind.load(mind_path)
    print(f"[OK] Mind loaded: {mind.identity.name}")
    print(f"     Model: {mind.intelligence.reasoning_model}")
    print(f"     Has task_detector: {hasattr(mind, 'task_detector')}\n")
    
    # Test task detection
    test_request = "create a simple presentation about AI"
    print(f"[INFO] Testing: '{test_request}'\n")
    
    if hasattr(mind, 'task_detector') and mind.task_detector:
        detection = mind.task_detector.detect(test_request)
        print(f"[DETECTION] is_task={detection['is_task']}, type={detection['task_type']}, confidence={detection['confidence']:.2f}\n")
    else:
        print("[WARN] No task_detector found!\n")
    
    # Call mind.think (like web chat does)
    print("[INFO] Calling mind.think()...")
    try:
        response = await mind.think(
            prompt=test_request,
            user_email="test@example.com",
            skip_task_detection=False
        )
        
        print(f"\n[RESPONSE]\n{response}\n")
        
        # Check for background task
        if hasattr(mind, 'background_executor'):
            active_tasks = mind.background_executor.get_active_tasks()
            print(f"[INFO] Active tasks: {len(active_tasks)}")
            
            if active_tasks:
                task = active_tasks[0]
                print(f"[TASK] ID={task.task_id}, Status={task.status.value}\n")
                
                # Monitor execution
                print("[INFO] Monitoring task (max 120s)...")
                for i in range(120):
                    await asyncio.sleep(1)
                    
                    current_task = mind.background_executor.get_task(task.task_id)
                    if current_task:
                        status = current_task.status.value
                        progress = int(current_task.progress * 100)
                        print(f"     [{i+1}s] Status={status}, Progress={progress}%", end='\r')
                        
                        if status == "completed":
                            print(f"\n\n[OK] Task completed!")
                            try:
                                result_str = str(current_task.result)
                                # Remove problematic unicode characters for Windows console
                                result_str = result_str.encode('ascii', errors='replace').decode('ascii')
                                print(f"[RESULT] {result_str}\n")
                            except Exception as e:
                                print(f"[RESULT] <result contains special characters>\n")
                            return True
                        elif status == "failed":
                            print(f"\n\n[FAIL] Task failed!")
                            print(f"[ERROR] {current_task.error}\n")
                            return False
                
                print(f"\n\n[WARN] Task timeout after 120s")
                return False
            else:
                print("[WARN] No background task created\n")
                return False
        else:
            print("[WARN] No background_executor found\n")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_task())
    print("\n" + "="*80)
    print(f"RESULT: {'PASS' if result else 'FAIL'}")
    print("="*80 + "\n")

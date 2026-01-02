"""
Monitor Background Tasks in Real-Time

Run this while testing through the web UI to see what's happening.
Uses the API to monitor tasks in the actual running server.
"""

import asyncio
import sys
from pathlib import Path
import httpx
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"


async def monitor_mind(mind_id: str, api_token: str):
    """Monitor a specific mind's background tasks via API."""
    print("\n" + "=" * 70)
    print(f"MONITORING MIND VIA API: {mind_id}")
    print("=" * 70)
    
    headers = {"Authorization": f"Bearer {api_token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Verify mind exists
        try:
            response = await client.get(
                f"{API_BASE}/minds/{mind_id}",
                headers=headers
            )
            if response.status_code == 200:
                mind_data = response.json()
                print(f"\nMind: {mind_data['name']}")
                print(f"GMID: {mind_data['gmid']}")
                print("\nMonitoring tasks via API...")
                print("Submit tasks through web UI and watch here!\n")
            else:
                print(f"\nERROR: Could not load mind (status {response.status_code})")
                print(f"Response: {response.text}")
                return
        except Exception as e:
            print(f"\nERROR: Could not connect to API: {e}")
            print(f"\nMake sure the API server is running on {API_BASE}")
            return
        
        # Monitor loop
        last_active_count = 0
        last_completed_count = 0
        last_task_ids = set()
        
        try:
            while True:
                await asyncio.sleep(2)
                
                # Query tasks from API
                try:
                    response = await client.get(
                        f"{API_BASE}/minds/{mind_id}/tasks",
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        print(f"\nAPI Error: {response.status_code}")
                        continue
                    
                    all_tasks = response.json()
                    
                    # Separate active and completed
                    active = [t for t in all_tasks if t['status'] in ['pending', 'running', 'retrying']]
                    completed = [t for t in all_tasks if t['status'] in ['completed', 'failed']]
                    
                    # Check for changes
                    current_task_ids = {t['task_id'] for t in all_tasks}
                    if len(active) != last_active_count or len(completed) != last_completed_count or current_task_ids != last_task_ids:
                        now = datetime.now().strftime("%H:%M:%S")
                        print(f"\n[{now}] --- STATUS UPDATE ---")
                        
                        # Show active tasks
                        if active:
                            print(f"\nACTIVE TASKS ({len(active)}):")
                            for task in active:
                                print(f"  - [{task['task_id'][:8]}] {task['status'].upper()}")
                                print(f"    Request: {task['user_request'][:60]}...")
                                print(f"    Progress: {task['progress']*100:.0f}%")
                                if task.get('error'):
                                    print(f"    Error: {task['error'][:100]}")
                        else:
                            print("\nNo active tasks")
                        
                        # Show recent completed
                        if completed:
                            print(f"\nRECENT COMPLETED ({len(completed)}):")
                            for task in completed[-3:]:  # Last 3
                                status_icon = "✓ OK" if task['status'] == "completed" else "✗ FAIL"
                                print(f"  - [{task['task_id'][:8]}] {status_icon}")
                                print(f"    Request: {task['user_request'][:60]}...")
                                if task.get('error'):
                                    print(f"    Error: {task['error'][:100]}")
                        
                        last_active_count = len(active)
                        last_completed_count = len(completed)
                        last_task_ids = current_task_ids
                        print()
                
                except httpx.HTTPStatusError as e:
                    print(f"\nHTTP Error: {e}")
                except Exception as e:
                    print(f"\nError querying tasks: {e}")
                    await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")


async def main():
    """Main entry point."""
    mind_id = "GMD-2025-5D5E-6B25"
    api_token = "default_dev_token_12345"  # Default dev token
    
    if len(sys.argv) > 1:
        mind_id = sys.argv[1]
    if len(sys.argv) > 2:
        api_token = sys.argv[2]
    
    print("\nBACKGROUND TASK MONITOR (API Mode)")
    print("=" * 70)
    print("\nInstructions:")
    print("1. Make sure API server is running: python -m genesis.api.server")
    print("2. Open browser: http://localhost:3000/chat/GMD-2025-5D5E-6B25")
    print("3. Submit a task like: 'create presentation on human digital twin'")
    print("4. Watch this monitor for real-time updates")
    print("5. Press Ctrl+C to stop monitoring\n")
    
    await monitor_mind(mind_id, api_token)


if __name__ == "__main__":
    asyncio.run(main())

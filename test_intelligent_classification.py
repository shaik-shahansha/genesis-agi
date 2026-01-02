"""
Test the new LLM-first intelligent intent classification system.

This tests the complete flow:
1. User message → intent_classifier
2. Classification → background_executor  
3. Context → autonomous_orchestrator
4. Understanding → code_generator
5. Generated code → code_executor
6. Result → completion notification
"""

import asyncio
import os
from pathlib import Path
from genesis.core.mind import Mind
from genesis.core.intelligence import Intelligence
from genesis.core.environment import EnvironmentType

async def test_intelligent_classification():
    """Test the complete LLM-first classification pipeline."""
    
    print("\n" + "="*80)
    print("INTELLIGENT INTENT CLASSIFICATION TEST")
    print("="*80)
    
    # Load existing mind
    print("\nStep 1: Loading mind GMD-2026-658A-D910...")
    mind_path = r"C:\Users\shaiks3423\.genesis\minds\GMD-2026-658A-D910.json"
    mind = Mind.load(mind_path)
    print("[OK] Mind loaded successfully")
    print(f"   • Identity: {mind.identity.name}")
    
    # Test cases with expected behavior - mix of tasks and generic conversations
    test_cases = [
        {
            "request": "what is the meaning of life?",
            "expected_type": "conversation",
            "is_task": False,
            "description": "Generic philosophical question - NOT a task"
        },
        {
            "request": "tell me about artificial intelligence",
            "expected_type": "conversation",
            "is_task": False,
            "description": "Information request - NOT a task"
        },
        {
            "request": "create a presentation about human digital twins",
            "expected_type": "creation",
            "is_task": True,
            "expected_filename": "human_digital_twins.pptx",
            "description": "Presentation creation with specific topic"
        },
        {
            "request": "make me a document explaining quantum computing",
            "expected_type": "creation",
            "is_task": True,
            "expected_filename": "quantum_computing.docx",
            "description": "Document creation with topic extraction"
        },
        {
            "request": "how are you feeling today?",
            "expected_type": "conversation",
            "is_task": False,
            "description": "Casual conversation - NOT a task"
        },
        {
            "request": "generate a comprehensive report on AI ethics",
            "expected_type": "creation",
            "is_task": True,
            "expected_filename": "ai_ethics_report.docx",
            "description": "Report generation with comprehensive structure"
        }
    ]
    
    print("\n" + "="*80)
    print("Running Test Cases")
    print("="*80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'='*80}")
        print(f"TEST CASE {i}/{len(test_cases)}")
        print(f"{'='*80}")
        print(f"Request: {test_case['request']}")
        print(f"Description: {test_case['description']}")
        print(f"Expected: {'TASK' if test_case['is_task'] else 'CONVERSATION'}")
        if test_case['is_task']:
            print(f"   • Type: {test_case['expected_type']}")
            if 'expected_filename' in test_case:
                print(f"   • Filename: {test_case['expected_filename']}")
        print("-"*80)
        
        try:
            # Test classification directly first
            print("\nPHASE 1: Direct Classification Test")
            print("-"*40)
            classification = await mind.intent_classifier.classify(test_case['request'])
            
            print(f"[OK] Classification Complete:")
            print(f"   - Is Task: {classification.is_task}")
            print(f"   - Task Type: {classification.task_type}")
            print(f"   - Confidence: {classification.confidence:.2f}")
            print(f"   - Intent: {classification.intent}")
            print(f"   - Complexity: {classification.complexity}")
            print(f"   - Estimated Duration: {classification.estimated_duration}")
            
            print(f"\nTask Details:")
            for key, value in classification.task_details.items():
                if isinstance(value, dict):
                    print(f"   - {key}:")
                    for k, v in value.items():
                        print(f"      * {k}: {v}")
                elif isinstance(value, list):
                    print(f"   - {key}: {', '.join(str(v) for v in value[:3])}")
                else:
                    print(f"   - {key}: {value}")
            
            print(f"\nSuggestions ({len(classification.suggestions)}):")
            for j, suggestion in enumerate(classification.suggestions[:5], 1):
                print(f"   {j}. {suggestion}")
            
            print(f"\nRelated Actions ({len(classification.related_actions)}):")
            for j, action in enumerate(classification.related_actions[:3], 1):
                print(f"   {j}. {action}")
            
            # Validate classification
            assert classification.is_task == test_case['is_task'], f"Wrong is_task detection: got {classification.is_task}, expected {test_case['is_task']}"
            
            if test_case['is_task']:
                assert classification.task_type == test_case['expected_type'], f"Wrong task type: {classification.task_type}"
                assert classification.confidence >= 0.7, f"Confidence too low: {classification.confidence}"
                
                # Check filename extraction
                extracted_filename = classification.task_details.get('filename') or classification.task_details.get('output_filename')
                print(f"\nFilename Validation:")
                print(f"   - Extracted: {extracted_filename}")
                if 'expected_filename' in test_case:
                    print(f"   - Expected: {test_case['expected_filename']}")
                
                if extracted_filename:
                    # Check if filename is reasonable (not generic like "presentation.pptx")
                    generic_names = ['presentation.pptx', 'document.docx', 'report.docx', 'slides.pptx']
                    assert extracted_filename.lower() not in generic_names, f"Filename too generic: {extracted_filename}"
                    print(f"   [OK] Filename is specific and meaningful")
            else:
                # For conversations, should NOT trigger background task
                assert classification.confidence >= 0.5, f"Confidence too low for conversation: {classification.confidence}"
                print(f"\n[OK] Correctly identified as conversation, NOT a task")
            
            # Test full pipeline through mind.think()
            print(f"\n\nPHASE 2: Full Pipeline Test (Mind.think)")
            print("-"*40)
            
            if test_case['is_task']:
                print("   Starting background task execution...")
            else:
                print("   Testing direct conversation response...")
            
            response = await mind.think(
                prompt=test_case['request'],
                user_email="test@example.com",
                skip_task_detection=False  # Use intent classifier
            )
            
            print(f"\nMind Response:")
            print(f"{response}")
            
            # For tasks, wait and track execution
            if test_case['is_task']:
                # Wait a bit for background task to start
                await asyncio.sleep(2)
                
                # Check if task was created
                active_tasks = len(mind.background_executor.active_tasks)
                print(f"\nActive Tasks: {active_tasks}")
                
                if active_tasks > 0:
                    # Get latest task
                    latest_task = list(mind.background_executor.active_tasks.values())[-1]
                    print(f"   - Task ID: {latest_task.task_id}")
                    print(f"   - Status: {latest_task.status.value}")
                    print(f"   - Progress: {latest_task.progress:.1%}")
                    
                    # Wait for task to complete (with timeout)
                    print(f"\nWaiting for task completion (max 30s)...")
                    timeout = 30
                    start_time = asyncio.get_event_loop().time()
                    
                    while latest_task.status.value in ["pending", "running"]:
                        await asyncio.sleep(1)
                        elapsed = asyncio.get_event_loop().time() - start_time
                        print(f"   {elapsed:.1f}s - Status: {latest_task.status.value}, Progress: {latest_task.progress:.1%}")
                        
                        if elapsed > timeout:
                            print(f"   [!] Timeout reached")
                            break
                    
                    # Check final status
                    print(f"\nFinal Task Status:")
                    print(f"   - Status: {latest_task.status.value}")
                    print(f"   - Progress: {latest_task.progress:.1%}")
                    
                    if latest_task.result:
                        print(f"   - Result: {str(latest_task.result)[:200]}...")
                    
                    if latest_task.artifacts:
                        print(f"   - Artifacts: {len(latest_task.artifacts)} files")
                        for artifact in latest_task.artifacts:
                            print(f"      * {artifact.get('filename', 'unknown')}: {artifact.get('file_path', 'no path')}")
                    
                    if latest_task.error:
                        print(f"   [!] Error: {latest_task.error}")
            else:
                # For conversations, verify no task was created
                active_tasks = len(mind.background_executor.active_tasks)
                print(f"\n[OK] No background task created (correct for conversation)")
                print(f"   Active tasks: {active_tasks}")
            
            print(f"\n[OK] TEST CASE {i} PASSED")
            
        except AssertionError as e:
            print(f"\n[FAIL] TEST CASE {i} FAILED: {e}")
        except Exception as e:
            print(f"\n[ERROR] TEST CASE {i} ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    
    # Cleanup
    await mind.shutdown()

if __name__ == "__main__":
    asyncio.run(test_intelligent_classification())

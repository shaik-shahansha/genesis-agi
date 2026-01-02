"""
Test code generation and extraction process.

This directly tests the code generator to see where it's failing.
"""

import asyncio
import json
import sys

# Enable intelligence debug logging
sys._genesis_debug_intelligence = True

from genesis.core.mind import Mind

async def test_code_generation():
    print("\n" + "="*80)
    print("Testing Code Generation & Extraction")
    print("="*80 + "\n")
    
    # Load Mind
    mind_id = "GMD-2026-658A-D910"
    print(f"Loading Mind: {mind_id}...")
    
    from genesis.config import get_settings
    settings = get_settings()
    mind_path = settings.minds_dir / (mind_id + ".json")
    
    mind = Mind.load(str(mind_path))
    print(f"OK Loaded: {mind.identity.name}\n")
    
    print(f"[TEST] Intelligence after load:")
    print(f"  reasoning_model: {mind.intelligence.reasoning_model}")
    print(f"  fast_model: {mind.intelligence.fast_model}\n")
    
    # Test task
    task = "Create a 3-slide PowerPoint presentation about apartment green cultivation"
    
    print(f"Task: {task}\n")
    print("-"*80)
    
    # Test code generation directly
    print("\n[1] Generating code with LLM...")
    print("-"*80)
    
    code_generator = mind.autonomous_orchestrator.code_generator
    
    try:
        result = await code_generator.generate_solution(
            task=task,
            context={"format": "presentation", "slides": 3},
            files=None
        )
        
        print(f"\n✓ Code generation complete!")
        print(f"\nGenerated code:")
        print("="*80)
        print(result.source)
        print("="*80)
        
        print(f"\nMetadata:")
        print(f"  Language: {result.language}")
        print(f"  Dependencies: {result.dependencies}")
        print(f"  Estimated runtime: {result.estimated_runtime}s")
        
        # Test execution
        print("\n[2] Testing code execution...")
        print("-"*80)
        
        executor = mind.autonomous_orchestrator.code_executor
        exec_result = await executor.execute_code(
            code=result.source,
            language=result.language,
            timeout=30
        )
        
        if exec_result.success:
            print(f"\n✓ Execution successful!")
            print(f"\nOutput:")
            print(exec_result.stdout if exec_result.stdout else "(no output)")
            
            # Check if output contains JSON result
            if exec_result.stdout:
                try:
                    result_data = json.loads(exec_result.stdout)
                    if result_data.get("success"):
                        print(f"\n✓ Task completed successfully")
                        if "files" in result_data:
                            print(f"  Files created: {result_data['files']}")
                except:
                    pass
        else:
            print(f"\n✗ Execution failed!")
            print(f"\nError:")
            print(exec_result.stderr)
        
    except Exception as e:
        print(f"\nX Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Final intelligence check
    print("\n[TEST] Intelligence at end of test:")
    print(f"  reasoning_model: {mind.intelligence.reasoning_model}")
    print(f"  fast_model: {mind.intelligence.fast_model}")
    
    print("\n" + "="*80)
    print("Test Complete")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_code_generation())

"""
Debug script to check if a specific Mind has task detection capabilities.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind


def check_mind(mind_id: str):
    """Check if a Mind has task detection."""
    print(f"\n{'='*80}")
    print(f"Checking Mind: {mind_id}")
    print(f"{'='*80}\n")
    
    try:
        # Load Mind
        from genesis.config import get_settings
        settings = get_settings()
        minds_dir = settings.minds_dir
        
        # Find Mind file
        mind_file = None
        for file in minds_dir.glob("*.json"):
            import json
            with open(file) as f:
                data = json.load(f)
            if data["identity"]["gmid"] == mind_id:
                mind_file = file
                break
        
        if not mind_file:
            print(f"❌ Mind '{mind_id}' not found")
            return
        
        print(f"Found Mind file: {mind_file}\n")
        
        # Load Mind
        mind = Mind.load(mind_file)
        
        print(f"Mind Name: {mind.identity.name}")
        print(f"GMID: {mind.identity.gmid}")
        print(f"\nCapabilities Check:")
        print(f"  - task_detector: {'✓ YES' if hasattr(mind, 'task_detector') else '✗ NO'}")
        print(f"  - background_executor: {'✓ YES' if hasattr(mind, 'background_executor') else '✗ NO'}")
        
        # If has task detector, test it
        if hasattr(mind, 'task_detector'):
            print(f"\nTesting task detection:")
            test_input = "create presentation on digital twins"
            detection = mind.task_detector.detect(test_input)
            print(f"  Input: '{test_input}'")
            print(f"  Is Task: {detection['is_task']}")
            print(f"  Confidence: {detection['confidence']:.2f}")
            print(f"  Should use orchestrator: {mind.task_detector.should_use_orchestrator(test_input)}")
        else:
            print(f"\n❌ Mind does NOT have task_detector!")
            print(f"\nTo fix, run:")
            print(f"  python upgrade_minds_for_tasks.py {mind.identity.name}")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mind_id = sys.argv[1]
    else:
        mind_id = "GMD-2025-5D5E-6B25"  # Default from user's URL
    
    check_mind(mind_id)

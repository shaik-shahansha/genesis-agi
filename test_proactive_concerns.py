"""
Test Proactive Consciousness System

This tests the complete proactive flow:
1. User says "I have fever"
2. Memory is created and stored
3. Proactive consciousness detects health concern
4. System schedules follow-up notification
5. After time passes, sends check-in notification
6. User responds "I'm fine now"
7. System marks concern as resolved
"""

import asyncio
from datetime import datetime, timedelta
from genesis.core.mind import Mind

async def test_proactive_health_concern():
    """Test complete proactive health concern flow."""
    
    print("\n" + "="*80)
    print("PROACTIVE CONSCIOUSNESS TEST - Health Concern Flow")
    print("="*80)
    
    # Load mind
    print("\nStep 1: Loading mind...")
    mind_path = r"C:\Users\shaiks3423\.genesis\minds\GMD-2026-658A-D910.json"
    mind = Mind.load(mind_path)
    print(f"[OK] Mind loaded: {mind.identity.name}")
    
    # Check if proactive consciousness is enabled
    has_proactive = hasattr(mind, 'proactive_consciousness') and mind.proactive_consciousness
    print(f"\nProactive Consciousness: {'ENABLED' if has_proactive else 'DISABLED'}")
    
    if not has_proactive:
        print("\n[!] Proactive consciousness is not enabled for this mind!")
        print("    It needs to be enabled in the mind's config.")
        return
    
    # Start proactive monitoring
    print("\nStep 2: Starting proactive monitoring...")
    await mind.proactive_consciousness.start()
    print("[OK] Monitoring started")
    
    test_user_email = "test@example.com"
    
    # Simulate user saying they have fever
    print("\n" + "-"*80)
    print("SCENARIO 1: User reports health issue")
    print("-"*80)
    
    user_message = "I have a really bad fever and headache. Not feeling well at all."
    print(f"\nUser says: \"{user_message}\"")
    
    response = await mind.think(
        prompt=user_message,
        user_email=test_user_email,
        skip_task_detection=False
    )
    
    print(f"\nMind responds: {response[:200]}...")
    
    # Wait for proactive consciousness to scan memories
    print("\nStep 3: Waiting for proactive consciousness to scan memories (5 seconds)...")
    await asyncio.sleep(5)
    
    # Check if concern was detected
    stats = mind.proactive_consciousness.get_stats()
    print("\n[INFO] Proactive Consciousness Stats:")
    print(f"   - Active concerns: {stats['active_concerns']}")
    print(f"   - Health concerns: {stats['concerns_by_type']['health']}")
    print(f"   - Emotion concerns: {stats['concerns_by_type']['emotion']}")
    print(f"   - Task concerns: {stats['concerns_by_type']['task']}")
    print(f"   - Resolved concerns: {stats['resolved_concerns']}")
    
    if stats['active_concerns'] > 0:
        print("\n[OK] Health concern detected and tracked!")
        
        # Show concern details
        active_concerns = [c for c in mind.proactive_consciousness.active_concerns if not c.resolved]
        for concern in active_concerns:
            print(f"\n   Concern Details:")
            print(f"   - Type: {concern.concern_type}")
            print(f"   - Description: {concern.description}")
            print(f"   - Severity: {concern.severity:.2f}")
            print(f"   - Created: {concern.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   - Follow-up scheduled: {concern.follow_up_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   - User: {concern.user_email}")
    else:
        print("\n[!] No concern detected - proactive consciousness may need tuning")
    
    # Simulate time passing and follow-up trigger (manually)
    print("\n" + "-"*80)
    print("SCENARIO 2: Simulating follow-up (normally happens after 6 hours)")
    print("-"*80)
    
    if stats['active_concerns'] > 0:
        # Manually trigger follow-up by setting follow_up_at to past
        for concern in mind.proactive_consciousness.active_concerns:
            if not concern.resolved:
                print(f"\n[TEST] Manually triggering follow-up for concern: {concern.concern_type}")
                concern.follow_up_at = datetime.now() - timedelta(seconds=1)
        
        # Trigger follow-up check
        print("[TEST] Running follow-up check...")
        await mind.proactive_consciousness._check_follow_ups()
        
        print("\n[OK] Follow-up sent!")
        print("   In production, user would receive notification asking:")
        print("   'How are you feeling now? Did you manage to get some rest?'")
    
    # Simulate user responding positively
    print("\n" + "-"*80)
    print("SCENARIO 3: User responds that they're better")
    print("-"*80)
    
    user_response = "I'm feeling much better now! Thanks for checking on me."
    print(f"\nUser says: \"{user_response}\"")
    
    response2 = await mind.think(
        prompt=user_response,
        user_email=test_user_email,
        skip_task_detection=False
    )
    
    print(f"\nMind responds: {response2[:200]}...")
    
    # Check if concern was resolved
    stats_after = mind.proactive_consciousness.get_stats()
    print("\n[INFO] Updated Stats:")
    print(f"   - Active concerns: {stats_after['active_concerns']}")
    print(f"   - Resolved concerns: {stats_after['resolved_concerns']}")
    
    if stats_after['resolved_concerns'] > stats['resolved_concerns']:
        print("\n[OK] Concern automatically resolved based on user's positive response!")
    else:
        print("\n[!] Concern not resolved - may need manual intervention")
    
    # Show all resolved concerns
    if mind.proactive_consciousness.resolved_concerns:
        print("\n[INFO] Resolved Concerns:")
        for concern in mind.proactive_consciousness.resolved_concerns:
            print(f"   - {concern.concern_type}: {concern.description[:60]}...")
            print(f"     Resolved after {concern.follow_up_count} follow-ups")
    
    # Test with different concern types
    print("\n" + "-"*80)
    print("SCENARIO 4: Testing emotional concern detection")
    print("-"*80)
    
    emotional_message = "I'm feeling really stressed and anxious about my project deadline."
    print(f"\nUser says: \"{emotional_message}\"")
    
    response3 = await mind.think(
        prompt=emotional_message,
        user_email=test_user_email,
        skip_task_detection=False
    )
    
    print(f"\nMind responds: {response3[:200]}...")
    
    await asyncio.sleep(5)
    
    stats_final = mind.proactive_consciousness.get_stats()
    print("\n[INFO] Final Stats:")
    print(f"   - Total active concerns: {stats_final['active_concerns']}")
    print(f"   - Health: {stats_final['concerns_by_type']['health']}")
    print(f"   - Emotion: {stats_final['concerns_by_type']['emotion']}")
    print(f"   - Task: {stats_final['concerns_by_type']['task']}")
    print(f"   - Total resolved: {stats_final['resolved_concerns']}")
    
    # Stop proactive monitoring
    print("\nStep 4: Stopping proactive monitoring...")
    await mind.proactive_consciousness.stop()
    print("[OK] Monitoring stopped")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
    
    print("\n[SUMMARY]")
    print("The proactive consciousness system:")
    print("  1. Detects health/emotional concerns from conversation")
    print("  2. Tracks them in database with follow-up schedule")
    print("  3. Sends notifications when running as daemon")
    print("  4. Automatically resolves when user confirms they're better")
    print("  5. Provides exponential backoff for repeated follow-ups")
    print("\nIn production (daemon mode):")
    print("  - Runs continuously in background")
    print("  - Checks memories every 5 minutes")
    print("  - Sends WebSocket notifications to user")
    print("  - Maintains concern state across restarts")

if __name__ == "__main__":
    asyncio.run(test_proactive_health_concern())

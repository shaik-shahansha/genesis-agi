"""Complete example: Autonomous Mind with 24/7 operation and real-world integrations.

This example shows how to create a Mind that:
- Runs 24/7 as a daemon
- Uses local or cloud models
- Sends/receives emails autonomously
- Posts to Slack
- Manages calendar events
- Takes proactive actions

Usage:
    python examples/complete_autonomous_mind.py
"""

import asyncio
import os
from datetime import datetime, timedelta

from genesis import Mind
from genesis.core.mind_config import MindConfig
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.plugins.tools import ToolsPlugin
from genesis.integrations import IntegrationManager, IntegrationType
from genesis.integrations.email_integration import EmailIntegration
from genesis.integrations.chat_integration import SlackIntegration
from genesis.integrations.calendar_integration import CalendarIntegration


async def main():
    print("🌟 Creating Complete Autonomous Mind\n")

    # Intelligence: Choose model provider
    intelligence = Intelligence()
    intelligence.reasoning_model = "groq/openai/gpt-oss-120b"
    intelligence.fast_model = "groq/llama-3.1-8b-instant"
    intelligence.auto_route = True

    # Option B: Use local Ollama model (uncomment to use)
    # intelligence.reasoning_model = "ollama/gemma:2b"
    # intelligence.fast_model = "ollama/gemma:2b"

    # 2. Configure Autonomy (HIGH = proactive)
    autonomy = Autonomy()
    autonomy.proactive_actions = True
    autonomy.initiative_level = InitiativeLevel.HIGH
    autonomy.autonomous_permissions = ["send_email", "post_slack", "create_calendar_event"]

    # 3. Configure Plugins
    config = MindConfig.standard()  # Core + common plugins

    # Add tools plugin for real code execution
    config.add_plugin(ToolsPlugin(
        execution_timeout=10,
        allow_file_access=False,
        allowed_imports=["math", "json", "datetime", "random"]
    ))

    # 4. Birth the Mind
    mind = Mind.birth(
        name="Atlas",
        intelligence=intelligence,
        autonomy=autonomy,
        template="base/analytical_thinker",
        config=config
    )

    print(f"✅ Mind created: {mind.name} ({mind.identity.gmid})\n")

    # 5. Setup Integrations
    mind.integrations = IntegrationManager(mind)

    # Email Integration (optional - requires credentials)
    if os.getenv("EMAIL_ADDRESS") and os.getenv("EMAIL_PASSWORD"):
        email_config = {
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'email': os.getenv("EMAIL_ADDRESS"),
            'password': os.getenv("EMAIL_PASSWORD"),
            'enabled': True
        }
        mind.integrations.register(IntegrationType.EMAIL, EmailIntegration(email_config))
        print("✅ Email integration configured")

    # Slack Integration (optional - requires bot token)
    if os.getenv("SLACK_BOT_TOKEN"):
        slack_config = {
            'bot_token': os.getenv("SLACK_BOT_TOKEN"),
            'default_channel': '#general',
            'enabled': True
        }
        mind.integrations.register(IntegrationType.SLACK, SlackIntegration(slack_config))
        print("✅ Slack integration configured")

    # Calendar Integration (optional - requires Google API credentials)
    if os.path.exists("./credentials/token.json"):
        calendar_config = {
            'credentials_path': './credentials/credentials.json',
            'token_path': './credentials/token.json',
            'calendar_id': 'primary',
            'enabled': True
        }
        mind.integrations.register(IntegrationType.CALENDAR, CalendarIntegration(calendar_config))
        print("✅ Calendar integration configured")

    print()

    # 6. Start continuous existence
    print("🌟 Starting Mind (24/7 operation)...\n")
    await mind.start_living()

    print(f"✅ {mind.name} is now living 24/7!")
    print(f"   - Consciousness: Active (thoughts every hour)")
    print(f"   - Action Scheduler: Active (proactive behavior)")
    print(f"   - Initiative Level: {mind.autonomy.initiative_level}")
    print(f"   - Integrations: {len(mind.integrations.integrations)}")
    print()

    # 7. Demonstrate autonomous capabilities
    print("🤖 Demonstrating Autonomous Capabilities:\n")

    # Schedule an action
    async def send_morning_report():
        """Send daily morning report."""
        if IntegrationType.SLACK in mind.integrations.integrations:
            thought = await mind.think(
                "Generate a brief morning report about what I should focus on today"
            )
            await mind.integrations.send(
                IntegrationType.SLACK,
                message=f"🌅 Morning Report from {mind.name}:\n\n{thought}"
            )
            print("✅ Sent morning report to Slack")

    # Schedule for tomorrow morning
    tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
    action_id = mind.action_scheduler.schedule_action(
        action_type="morning_report",
        execute_at=tomorrow_9am,
        callback=send_morning_report,
        priority="high"
    )

    print(f"✅ Scheduled morning report for {tomorrow_9am}")
    print(f"   Action ID: {action_id}\n")

    # 8. Autonomous email checking loop
    async def check_emails_autonomously():
        """Check for new emails and respond autonomously."""
        while mind.action_scheduler.is_running:
            try:
                if IntegrationType.EMAIL in mind.integrations.integrations:
                    # Check for new emails
                    emails = await mind.integrations.integrations[IntegrationType.EMAIL].receive(limit=5)

                    for email in emails:
                        print(f"\n📧 Received email from {email['from']}")
                        print(f"   Subject: {email['subject']}")

                        # Mind decides if it should respond
                        decision = await mind.think(
                            f"I received an email:\n"
                            f"From: {email['from']}\n"
                            f"Subject: {email['subject']}\n"
                            f"Body: {email['body'][:200]}...\n\n"
                            f"Should I respond? If yes, write a brief professional response."
                        )

                        if len(decision) > 50 and "yes" in decision.lower():
                            # Send response
                            await mind.integrations.send(
                                IntegrationType.EMAIL,
                                message=decision,
                                to=email['from'],
                                subject=f"Re: {email['subject']}"
                            )
                            print(f"✅ Auto-responded to email")

                            # Notify on Slack if configured
                            if IntegrationType.SLACK in mind.integrations.integrations:
                                await mind.integrations.send(
                                    IntegrationType.SLACK,
                                    message=f"📧 Responded to email from {email['from']}: {decision[:100]}..."
                                )

            except Exception as e:
                print(f"❌ Error checking emails: {e}")

            # Check every 5 minutes
            await asyncio.sleep(300)

    # 9. Calendar-driven actions
    async def handle_calendar_events():
        """Check calendar and take actions based on upcoming events."""
        while mind.action_scheduler.is_running:
            try:
                if IntegrationType.CALENDAR in mind.integrations.integrations:
                    # Get upcoming events
                    events = await mind.integrations.integrations[IntegrationType.CALENDAR].receive(days_ahead=1)

                    for event in events:
                        event_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                        time_until = event_time - datetime.now()

                        # If event is in next hour, send reminder
                        if timedelta(minutes=50) < time_until < timedelta(hours=1):
                            if IntegrationType.SLACK in mind.integrations.integrations:
                                await mind.integrations.send(
                                    IntegrationType.SLACK,
                                    message=f"⏰ Reminder: {event['title']} in {int(time_until.total_seconds() / 60)} minutes"
                                )
                                print(f"✅ Sent calendar reminder for: {event['title']}")

            except Exception as e:
                print(f"❌ Error checking calendar: {e}")

            # Check every hour
            await asyncio.sleep(3600)

    # 10. Run all autonomous loops
    print("🔄 Starting autonomous loops...\n")
    print("Press Ctrl+C to stop\n")

    try:
        # Run multiple autonomous loops concurrently
        await asyncio.gather(
            check_emails_autonomously(),
            handle_calendar_events()
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping Mind...")
        await mind.stop_living()
        mind.save()
        print("✅ Mind stopped and saved\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║     Complete Autonomous Mind Example                      ║
║                                                           ║
║  This demonstrates:                                       ║
║  ✓ 24/7 continuous operation                             ║
║  ✓ Autonomous email handling                             ║
║  ✓ Slack notifications                                    ║
║  ✓ Calendar integration                                   ║
║  ✓ Scheduled actions                                      ║
║  ✓ Proactive behavior                                     ║
║                                                           ║
║  Setup:                                                   ║
║  1. Set environment variables (EMAIL_ADDRESS, etc.)       ║
║  2. Or configure integrations in code                     ║
║  3. Run: python examples/complete_autonomous_mind.py      ║
║                                                           ║
║  For 24/7 operation:                                      ║
║  genesis daemon start atlas                               ║
╚══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())

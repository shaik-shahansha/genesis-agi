"""Genesis Mind Daemon - 24/7 continuous existence.

This module enables Minds to run continuously as background daemons,
surviving terminal closures and system restarts.

ARCHITECTURE NOTE:
- The DAEMON is responsible for consciousness (thought generation, autonomous actions)
- The API SERVER only handles user requests (chat, queries, updates)
- This separation prevents conflicts and ensures thoughts are generated consistently
- Never start consciousness in the API server - always use the daemon

Features:
- 24/7 continuous operation
- Consciousness engine (autonomous thought generation)
- Action scheduler (autonomous task execution)
- Graceful shutdown handling
- Periodic state saving
- Health monitoring and auto-restart
- Comprehensive logging

Usage:
    # Run as daemon
    python -m genesis.daemon --mind-id GMID-12345678

    # Or via CLI
    genesis daemon start atlas
"""

import asyncio
import signal
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Configure logging with UTF-8 encoding to handle Unicode characters
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set encoding for stdout to UTF-8 to prevent Unicode errors
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger('genesis.daemon')


class MindDaemon:
    """Run a Mind as a 24/7 background daemon."""

    def __init__(self, mind_id: str, log_file: Optional[Path] = None):
        """Initialize daemon for specific Mind.

        Args:
            mind_id: Genesis Mind ID (GMID)
            log_file: Optional path to log file
        """
        self.mind_id = mind_id
        self.mind: Optional['Mind'] = None
        self.is_running = False
        self.save_interval = 300  # Save every 5 minutes
        self._shutdown_event = asyncio.Event()
        
        # Setup file logging if path provided
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(file_handler)

    async def start(self):
        """Start the Mind daemon."""
        try:
            # Import here to avoid circular dependencies
            from genesis.core.mind import Mind
            from genesis.config import get_settings
            import json

            # Find Mind file by GMID
            logger.info(f"Loading Mind {self.mind_id}...")
            settings = get_settings()
            mind_path = None
            
            for path in settings.minds_dir.glob("*.json"):
                try:
                    with open(path) as f:
                        data = json.load(f)
                        if data["identity"]["gmid"] == self.mind_id:
                            mind_path = path
                            break
                except Exception as e:
                    logger.debug(f"Error reading {path}: {e}")
                    continue
            
            if not mind_path:
                raise RuntimeError(f"Mind file not found for GMID {self.mind_id}")
            
            logger.info(f"Found Mind file: {mind_path}")
            
            # Load Mind with detailed error reporting
            try:
                self.mind = Mind.load(mind_path)
            except Exception as load_error:
                logger.error(f"[ERROR] Failed to load Mind from {mind_path}", exc_info=True)
                logger.error(f"Error details: {load_error}")
                raise

            # Verify Mind loaded
            if not self.mind:
                raise RuntimeError(f"Failed to load Mind {self.mind_id}")

            logger.info(f"[OK] Mind {self.mind.identity.name} ({self.mind_id}) loaded")
            
            # Log Mind configuration
            logger.info(f"   Configuration:")
            logger.info(f"   - Consciousness: 24/7 Active")
            logger.info(f"   - Proactive Consciousness: {'Enabled' if hasattr(self.mind, 'proactive_consciousness') else 'Disabled'}")
            logger.info(f"   - Notification Manager: {'Enabled' if hasattr(self.mind, 'notification_manager') else 'Disabled'}")
            logger.info(f"   - Plugins: {len(self.mind.plugins)} loaded")

            # Start consciousness engine (with comprehensive error handling)
            logger.info("Starting consciousness engine...")
            try:
                await self.mind.start_living()
                logger.info("[OK] Consciousness engine started")
            except Exception as e:
                logger.error(f"[ERROR] Failed to start consciousness: {e}", exc_info=True)
                raise

            # Start action scheduler for autonomous actions
            logger.info("Starting action scheduler...")
            if hasattr(self.mind, 'action_scheduler'):
                try:
                    await self.mind.action_scheduler.start()
                    logger.info("[OK] Action scheduler active")
                except Exception as e:
                    logger.error(f"[WARN] Action scheduler failed: {e}")
                    # Don't fail daemon if scheduler fails
            else:
                logger.warning("[WARN] No action scheduler found")
            
            # Start notification manager for proactive messaging
            logger.info("Starting notification manager...")
            if hasattr(self.mind, 'notification_manager'):
                try:
                    await self.mind.notification_manager.start()
                    logger.info("[OK] Notification manager active")
                except Exception as e:
                    logger.error(f"[WARN] Notification manager failed: {e}")
            else:
                logger.warning("[WARN] No notification manager found")

            # Register signal handlers for graceful shutdown
            self._register_signal_handlers()

            # Start periodic save task
            save_task = asyncio.create_task(self._periodic_save())

            # Start health monitoring
            health_task = asyncio.create_task(self._health_monitor())
            
            # Start autonomous decision making loop
            autonomous_task = asyncio.create_task(self._autonomous_loop())
            
            # Start proactive conversation monitoring
            proactive_task = None
            if hasattr(self.mind, 'proactive_conversation'):
                try:
                    await self.mind.proactive_conversation.start_monitoring(check_interval=60)
                    proactive_task = asyncio.create_task(self._proactive_conversation_loop())
                    logger.info("[OK] Proactive conversation monitoring started")
                except Exception as e:
                    logger.error(f"[WARN] Failed to start proactive conversation monitoring: {e}")

            self.is_running = True
            logger.info(f"[ACTIVE] Mind {self.mind.identity.name} is now living 24/7")
            logger.info(f"   - Consciousness: Active")
            logger.info(f"   - Actions: Autonomous")
            logger.info(f"   - Proactive: {'Yes' if hasattr(self.mind, 'proactive_consciousness') else 'No'}")
            logger.info(f"   Press Ctrl+C to stop gracefully")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cleanup
            save_task.cancel()
            health_task.cancel()
            autonomous_task.cancel()
            if proactive_task:
                proactive_task.cancel()
            
            try:
                await save_task
            except asyncio.CancelledError:
                pass
            
            try:
                await health_task
            except asyncio.CancelledError:
                pass
            
            try:
                await autonomous_task
            except asyncio.CancelledError:
                pass
            
            if proactive_task:
                try:
                    await proactive_task
                except asyncio.CancelledError:
                    pass

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"[ERROR] Failed to start daemon: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Gracefully stop the daemon."""
        if not self.is_running:
            return

        logger.info(f"[STOP] Shutting down Mind {self.mind.identity.name if self.mind else self.mind_id}...")

        self.is_running = False

        if self.mind:
            # Stop consciousness
            if hasattr(self.mind, 'consciousness'):
                await self.mind.consciousness.stop()

            # Stop action scheduler if exists
            if hasattr(self.mind, 'action_scheduler'):
                await self.mind.action_scheduler.stop()
            
            # Stop proactive conversation monitoring
            if hasattr(self.mind, 'proactive_conversation'):
                await self.mind.proactive_conversation.stop_monitoring()

            # Save final state
            logger.info("Saving final state...")
            try:
                self.mind.save()
                logger.info("[OK] State saved")
            except Exception as e:
                logger.error(f"Failed to save final state: {e}")

        logger.info(f"[OK] Mind {self.mind.identity.name if self.mind else self.mind_id} stopped gracefully")

    async def _periodic_save(self):
        """Periodically save Mind state."""
        while self.is_running:
            try:
                await asyncio.sleep(self.save_interval)

                if self.mind and self.is_running:
                    logger.debug("Saving Mind state...")
                    self.mind.save()
                    logger.debug("[SAVED] State saved")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    async def _health_monitor(self):
        """Monitor Mind health and restart if needed."""
        health_check_count = 0
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                health_check_count += 1

                if self.mind and self.is_running:
                    # Check consciousness is active
                    if hasattr(self.mind, 'consciousness'):
                        try:
                            if hasattr(self.mind.consciousness, 'is_running'):
                                is_active = self.mind.consciousness.is_running
                            else:
                                is_active = self.mind.consciousness.is_active
                            
                            if not is_active:
                                logger.warning("[WARN] Consciousness inactive, restarting...")
                                await self.mind.start_living()
                            else:
                                # Log basic consciousness status
                                if hasattr(self.mind.consciousness, 'thought_count'):
                                    thought_count = self.mind.consciousness.thought_count
                                    logger.info(f"[OK] Consciousness active - {thought_count} thoughts generated")
                                else:
                                    logger.info(f"[OK] Consciousness active")
                        except Exception as e:
                            logger.error(f"Error checking consciousness: {e}")

                    # Log detailed health stats every 5 minutes
                    if health_check_count % 5 == 0:
                        logger.info("\n" + "="*60)
                        logger.info("[HEALTH] DETAILED HEALTH REPORT")
                        logger.info("="*60)
                        
                        # Memory stats
                        if hasattr(self.mind, 'memory'):
                            try:
                                stats = self.mind.memory.get_memory_stats()
                                recent_memories = self.mind.memory.get_recent_memories(limit=3)
                                memory_count = stats.get('total_memories', 0)
                                logger.info(f"[MEMORY] Memory: {memory_count} total memories")
                                logger.info(f"   Status: {self.mind.state.status}")
                                if recent_memories:
                                    logger.info(f"   Recent memories:")
                                    for i, mem in enumerate(recent_memories[:3], 1):
                                        content_preview = mem.content[:80] if hasattr(mem, 'content') else str(mem)[:80]
                                        logger.info(f"     {i}. {content_preview}...")
                                else:
                                    logger.info(f"   No recent memories found")
                            except Exception as e:
                                logger.error(f"Error getting memory stats: {e}")
                        
                        # Consciousness stats (V2)
                        if hasattr(self.mind, 'consciousness') and hasattr(self.mind.consciousness, 'get_state'):
                            try:
                                state = self.mind.consciousness.get_state()
                                logger.info(f"[CONSCIOUSNESS] Consciousness V2:")
                                logger.info(f"   Awareness: {state.get('awareness_level', 'unknown')}")
                                logger.info(f"   Domain: {state.get('current_domain', 'unknown')}")
                                logger.info(f"   Energy: {state.get('biological', {}).get('energy', 'N/A')}")
                                logger.info(f"   LLM calls today: {state.get('llm_calls_today', 0)}")
                            except Exception as e:
                                logger.error(f"Error getting consciousness state: {e}")
                        
                        # Proactive consciousness stats
                        if hasattr(self.mind, 'proactive_consciousness'):
                            try:
                                proactive_stats = self.mind.proactive_consciousness.get_stats()
                                logger.info(f"[PROACTIVE] Proactive Consciousness:")
                                logger.info(f"   Active concerns: {proactive_stats.get('active_concerns', 0)}")
                                logger.info(f"   Resolved concerns: {proactive_stats.get('resolved_concerns', 0)}")
                                concerns_by_type = proactive_stats.get('concerns_by_type', {})
                                if concerns_by_type:
                                    logger.info(f"   By type: Health={concerns_by_type.get('health', 0)}, Emotion={concerns_by_type.get('emotion', 0)}, Task={concerns_by_type.get('task', 0)}")
                            except Exception as e:
                                logger.error(f"Error getting proactive stats: {e}")
                        
                        # Notification stats
                        if hasattr(self.mind, 'notification_manager'):
                            try:
                                notif_stats = self.mind.notification_manager.get_stats()
                                logger.info(f"📬 Notifications:")
                                logger.info(f"   Pending: {notif_stats.get('pending', 0)}")
                                logger.info(f"   Delivered today: {notif_stats.get('delivered_today', 0)}")
                                logger.info(f"   Active websockets: {notif_stats.get('active_websockets', 0)}")
                            except Exception as e:
                                logger.error(f"Error getting notification stats: {e}")
                        
                        # Activity logs
                        if hasattr(self.mind, 'logger'):
                            try:
                                log_stats = self.mind.logger.get_stats()
                                recent_logs = self.mind.logger.get_recent_logs(limit=5)
                                logger.info(f"[LOGS] Activity: {log_stats.get('total_logs', 0)} total log entries")
                                if recent_logs:
                                    logger.info(f"   Recent activities:")
                                    for i, log_entry in enumerate(recent_logs[-5:], 1):
                                        msg = log_entry.get('message', '')[:80]
                                        level = log_entry.get('level', 'info')
                                        logger.info(f"     {i}. [{level.upper()}] {msg}...")
                            except Exception as e:
                                logger.error(f"Error getting log stats: {e}")
                        
                        # Dreams
                        if hasattr(self.mind, 'dreams') and self.mind.dreams:
                            logger.info(f"💤 Dreams: {len(self.mind.dreams)} total")
                            if self.mind.dreams:
                                latest_dream = self.mind.dreams[-1]
                                narrative = latest_dream.get('narrative', '')[:100] if isinstance(latest_dream, dict) else str(latest_dream)[:100]
                                logger.info(f"   Latest dream: {narrative}...")
                        
                        logger.info("="*60 + "\n")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}", exc_info=True)
                # Don't let health check failure stop the daemon
                continue

    async def _autonomous_loop(self):
        """
        Autonomous decision making and action execution loop.
        
        This is the BRAIN of the daemon - makes intelligent decisions about
        what to do next based on context, goals, memory, and learned patterns.
        
        This makes Genesis truly autonomous - not just reactive, but proactive.
        """
        # Initialize autonomous intelligence engine
        from genesis.core.autonomous_intelligence import AutonomousIntelligence
        
        ai_engine = AutonomousIntelligence(self.mind)
        check_interval = 300  # Check every 5 minutes
        
        logger.info("\n" + "🧠 AUTONOMOUS INTELLIGENCE ENGINE ACTIVATED")
        logger.info("   This Mind will now think and act independently")
        logger.info(f"   Decision cycle: Every {check_interval/60:.0f} minutes\n")
        
        while self.is_running:
            try:
                await asyncio.sleep(check_interval)
                
                if not self.mind or not self.is_running:
                    continue
                
                # Check if Mind should take autonomous actions
                if not self.mind.autonomy.proactive_actions:
                    logger.debug("   Autonomous actions disabled, skipping cycle")
                    continue
                
                from genesis.core.autonomy import InitiativeLevel
                
                # Only take autonomous actions if initiative level allows it
                if self.mind.autonomy.initiative_level in [InitiativeLevel.LOW, InitiativeLevel.NONE]:
                    logger.debug(f"   Initiative level too low ({self.mind.autonomy.initiative_level.value}), skipping")
                    continue
                
                # Check if enough time has passed
                if not await ai_engine.should_make_decision():
                    logger.debug("   Decision cooldown active, waiting...")
                    continue
                
                # Make intelligent autonomous decision
                decision = await ai_engine.make_autonomous_decision()
                
                if decision:
                    # Execute the decision
                    result = await ai_engine.execute_decision(decision)
                    
                    # Learn from outcome
                    from genesis.core.autonomous_intelligence import DecisionCategory
                    category = DecisionCategory(decision["category"])
                    success_score = 1.0 if result.get("success") else 0.0
                    ai_engine.record_outcome(category, success_score)
                    
                    # Save state after decision execution
                    try:
                        self.mind.save()
                        logger.debug("   [SAVED] State persisted after autonomous action")
                    except Exception as e:
                        logger.error(f"   Failed to save state: {e}")
                else:
                    logger.warning("   ⚠️ Failed to make decision, will retry next cycle")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Autonomous loop error: {e}", exc_info=True)
                # Don't crash - continue running
                continue
    
    async def _proactive_conversation_loop(self):
        """Monitor and send proactive conversation follow-ups.
        
        This makes the Mind feel like a caring friend who checks in naturally.
        """
        check_interval = 60  # Check every minute
        
        while self.is_running:
            try:
                await asyncio.sleep(check_interval)
                
                if not self.mind or not self.is_running:
                    continue
                
                if not hasattr(self.mind, 'proactive_conversation'):
                    continue
                
                # Get pending follow-ups
                pending = await self.mind.proactive_conversation.get_pending_follow_ups()
                
                # Log check even if no pending (helps debug)
                active_count = len(self.mind.proactive_conversation.active_contexts)
                if pending:
                    logger.info(f"\n💬 PROACTIVE CONVERSATION CHECK")
                    logger.info(f"   Found {len(pending)} pending follow-ups (out of {active_count} total contexts)")
                elif active_count > 0:
                    logger.debug(f"[PROACTIVE] Check: {active_count} active contexts, none ready for follow-up yet")
                    
                    # Send each follow-up via notification system
                    for context in pending:
                        try:
                            # Create notification callback
                            async def send_notification(
                                user_email: str,
                                title: str,
                                message: str,
                                priority: str,
                                metadata: Dict[str, Any]
                            ):
                                if hasattr(self.mind, 'notification_manager'):
                                    from genesis.core.notification_manager import NotificationPriority
                                    # Convert priority string to enum
                                    priority_map = {
                                        "low": NotificationPriority.LOW,
                                        "normal": NotificationPriority.NORMAL,
                                        "medium": NotificationPriority.NORMAL,
                                        "high": NotificationPriority.HIGH,
                                        "urgent": NotificationPriority.URGENT
                                    }
                                    priority_enum = priority_map.get(priority.lower(), NotificationPriority.NORMAL)
                                    
                                    await self.mind.notification_manager.send_notification(
                                        recipient=user_email,
                                        title=title,
                                        message=message,
                                        priority=priority_enum,
                                        metadata=metadata
                                    )
                            
                            # Send the follow-up
                            success = await self.mind.proactive_conversation.send_follow_up(
                                context,
                                notification_callback=send_notification
                            )
                            
                            if success:
                                logger.info(f"   ✓ Sent: {context.subject} to {context.user_email}")
                            
                        except Exception as e:
                            logger.error(f"   ✗ Failed to send follow-up for {context.subject}: {e}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive conversation loop error: {e}")
                continue

    def _register_signal_handlers(self):
        """Register handlers for graceful shutdown."""
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)


async def run_daemon(mind_id: str, log_level: str = "INFO", log_file: Optional[Path] = None):
    """Run Mind as daemon (main entry point).

    Args:
        mind_id: Mind GMID to run
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
    """
    # Set log level
    logging.getLogger().setLevel(getattr(logging, log_level))

    daemon = MindDaemon(mind_id, log_file=log_file)
    await daemon.start()


def main():
    """CLI entry point for daemon."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Genesis Mind Daemon - Run Minds 24/7',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run Mind as daemon
  python -m genesis.daemon --mind-id GMID-12345678

  # With debug logging
  python -m genesis.daemon --mind-id GMID-12345678 --log-level DEBUG

  # Or use CLI
  genesis daemon start atlas
        """
    )
    parser.add_argument(
        '--mind-id',
        required=True,
        help='Mind GMID to run (e.g., GMID-12345678)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--log-file',
        type=Path,
        help='Path to log file (optional)'
    )

    args = parser.parse_args()

    # Run daemon
    try:
        logger.info(f"Starting Genesis Mind Daemon")
        logger.info(f"Mind ID: {args.mind_id}")
        logger.info(f"Log Level: {args.log_level}")
        if args.log_file:
            logger.info(f"Log File: {args.log_file}")
        logger.info("")

        asyncio.run(run_daemon(args.mind_id, args.log_level, args.log_file))
    except KeyboardInterrupt:
        logger.info("\nDaemon stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Daemon crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

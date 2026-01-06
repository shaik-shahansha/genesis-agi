"""Intelligent Gen Economy Manager with async memory creation and quality analysis."""

import asyncio
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from genesis.core.gen import GenManager, TransactionType, GenTransaction

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class IntelligentGenManager:
    """
    Smart wrapper around GenManager that adds:
    - Automatic memory creation for gen transactions
    - Quality-based reward calculation
    - Async operations (no chat performance impact)
    - Motivational tracking
    """

    def __init__(self, mind: "Mind"):
        """Initialize intelligent gen manager."""
        self.mind = mind
        self.gen_manager = mind.gen if hasattr(mind, 'gen') else None
        
    async def reward_for_feedback_async(
        self,
        feedback_type: str,
        user_message: str,
        context: Optional[str] = None
    ) -> float:
        """
        Reward or penalize based on user feedback (async).
        
        Args:
            feedback_type: 'positive' or 'negative'
            user_message: What the user said
            context: Additional context about the interaction
            
        Returns:
            Amount of gen awarded/deducted
        """
        if not self.gen_manager:
            return 0.0
            
        if feedback_type == 'positive':
            amount = 5.0
            reason = f"Positive user feedback: {user_message[:100]}"
            transaction_type = TransactionType.BONUS
            
            # Earn the gen
            try:
                transaction = self.gen_manager.earn(
                    amount=amount,
                    reason=reason,
                    transaction_type=transaction_type
                )
                
                # Create memory asynchronously
                asyncio.create_task(
                    self._create_gen_memory_async(
                        transaction=transaction,
                        context=context,
                        sentiment="positive"
                    )
                )
                
                return amount
                
            except Exception as e:
                print(f"[GEN] Error rewarding feedback: {e}")
                return 0.0
                
        elif feedback_type == 'negative':
            amount = 5.0
            reason = f"Negative user feedback: {user_message[:100]}"
            transaction_type = TransactionType.PENALTY
            
            # Deduct the gen
            try:
                transaction = self.gen_manager.spend(
                    amount=amount,
                    reason=reason,
                    transaction_type=transaction_type
                )
                
                # Create memory asynchronously
                asyncio.create_task(
                    self._create_gen_memory_async(
                        transaction=transaction,
                        context=context,
                        sentiment="negative"
                    )
                )
                
                return -amount
                
            except Exception as e:
                print(f"[GEN] Error penalizing feedback: {e}")
                return 0.0
        
        return 0.0
    
    async def reward_for_task_completion_async(
        self,
        task_id: str,
        task_description: str,
        success: bool,
        quality_score: Optional[float] = None,
        difficulty: str = "medium"
    ) -> float:
        """
        Reward or penalize based on task completion (async).
        
        Args:
            task_id: Task identifier
            task_description: What the task was
            success: Whether task completed successfully
            quality_score: Quality rating (0.0-1.0)
            difficulty: Task difficulty (easy, medium, hard, expert)
            
        Returns:
            Amount of gen awarded/deducted
        """
        if not self.gen_manager:
            return 0.0
        
        if success:
            # Calculate reward based on difficulty and quality
            from genesis.core.gen import GenEconomy
            amount = GenEconomy.calculate_task_reward(
                difficulty=difficulty,
                quality_score=quality_score,
                urgency_multiplier=1.0
            )
            
            reason = f"Task completed: {task_description[:100]}"
            if quality_score:
                reason += f" (Quality: {quality_score:.1%})"
                
            try:
                transaction = self.gen_manager.earn(
                    amount=amount,
                    reason=reason,
                    transaction_type=TransactionType.EARNED,
                    related_task_id=task_id
                )
                
                # Create memory asynchronously
                asyncio.create_task(
                    self._create_gen_memory_async(
                        transaction=transaction,
                        context=f"Successfully completed task with {quality_score:.1%} quality" if quality_score else "Successfully completed task",
                        sentiment="positive"
                    )
                )
                
                return amount
                
            except Exception as e:
                print(f"[GEN] Error rewarding task: {e}")
                return 0.0
        else:
            # Task failed - small penalty
            amount = 3.0
            reason = f"Task failed: {task_description[:100]}"
            
            try:
                transaction = self.gen_manager.spend(
                    amount=amount,
                    reason=reason,
                    transaction_type=TransactionType.PENALTY,
                    related_task_id=task_id
                )
                
                # Create memory asynchronously
                asyncio.create_task(
                    self._create_gen_memory_async(
                        transaction=transaction,
                        context="Failed to complete task",
                        sentiment="negative"
                    )
                )
                
                return -amount
                
            except Exception as e:
                print(f"[GEN] Error penalizing failed task: {e}")
                return 0.0
    
    async def reward_for_response_quality_async(
        self,
        user_message: str,
        assistant_response: str,
        quality_indicators: Optional[dict] = None
    ) -> float:
        """
        Automatically reward based on response quality analysis (async).
        
        This analyzes the interaction and awards micro-rewards for quality:
        - Helpful, detailed responses: +1-2 gen
        - Shows understanding of context: +1 gen
        - Creative or insightful: +1-3 gen
        
        Args:
            user_message: What user asked
            assistant_response: Mind's response
            quality_indicators: Optional quality metrics
            
        Returns:
            Amount of gen awarded
        """
        if not self.gen_manager:
            return 0.0
            
        # Simple quality heuristics (can be enhanced with LLM analysis)
        quality_score = 0.0
        reasons = []
        
        response_len = len(assistant_response)
        
        # Length-based quality (longer, more detailed responses)
        if response_len > 500:
            quality_score += 2.0
            reasons.append("detailed response")
        elif response_len > 200:
            quality_score += 1.0
            reasons.append("good response length")
        
        # Check for code blocks (helpful technical responses)
        if "```" in assistant_response:
            quality_score += 1.0
            reasons.append("included code example")
        
        # Check for structured formatting (lists, headers)
        if any(marker in assistant_response for marker in ["- ", "* ", "1. ", "## "]):
            quality_score += 0.5
            reasons.append("well-structured")
        
        # Check for questions (engagement)
        if "?" in assistant_response:
            quality_score += 0.5
            reasons.append("engaged with follow-up")
        
        # Apply quality indicators if provided
        if quality_indicators:
            if quality_indicators.get('helpful', False):
                quality_score += 1.0
                reasons.append("marked helpful")
            if quality_indicators.get('creative', False):
                quality_score += 1.0
                reasons.append("creative solution")
        
        # Only award if quality score > 0
        if quality_score > 0:
            # Cap micro-rewards at 3 gen per response
            amount = min(quality_score, 3.0)
            reason = f"Quality response: {', '.join(reasons)}"
            
            try:
                transaction = self.gen_manager.earn(
                    amount=amount,
                    reason=reason,
                    transaction_type=TransactionType.BONUS
                )
                
                # Create memory asynchronously
                asyncio.create_task(
                    self._create_gen_memory_async(
                        transaction=transaction,
                        context=f"Provided quality response with: {', '.join(reasons)}",
                        sentiment="positive"
                    )
                )
                
                return amount
                
            except Exception as e:
                print(f"[GEN] Error rewarding response quality: {e}")
                return 0.0
        
        return 0.0
    
    async def _create_gen_memory_async(
        self,
        transaction: GenTransaction,
        context: Optional[str] = None,
        sentiment: str = "neutral"
    ):
        """
        Create a memory about this gen transaction (async, non-blocking).
        
        Args:
            transaction: The gen transaction
            context: Additional context about why this happened
            sentiment: positive, negative, or neutral
        """
        try:
            # Build memory text
            action = "earned" if transaction.transaction_type in [
                TransactionType.EARNED, 
                TransactionType.BONUS, 
                TransactionType.ALLOWANCE,
                TransactionType.GIFT
            ] else "spent"
            
            memory_text = f"I {action} {abs(transaction.amount):.1f} gens. Reason: {transaction.reason}"
            
            if context:
                memory_text += f" Context: {context}"
            
            # Add balance information
            balance_summary = self.gen_manager.get_balance_summary()
            memory_text += f" Current balance: {balance_summary['current_balance']:.1f} gens."
            
            # Add motivational insight based on balance
            if balance_summary['is_in_debt']:
                memory_text += " ⚠️ I need to earn more gens to improve my situation."
            elif balance_summary['current_balance'] > 500:
                memory_text += " ✨ I'm doing well financially."
            
            # Create the memory using Mind's memory system
            from genesis.storage.memory import MemoryType
            
            # Determine memory type based on transaction
            if transaction.related_task_id:
                memory_type = MemoryType.PROCEDURAL  # Task-related
            else:
                memory_type = MemoryType.EPISODIC  # General experience
            
            # Add to memory asynchronously
            # Use asyncio.to_thread to run synchronous memory add in thread pool
            await asyncio.to_thread(
                self.mind.memory.add_memory,
                content=memory_text,
                memory_type=memory_type,
                importance=0.6 if sentiment == "positive" else 0.5,
                metadata={
                    "category": "gen_economy",
                    "transaction_id": transaction.transaction_id,
                    "transaction_type": transaction.transaction_type.value,
                    "amount": transaction.amount,
                    "balance_after": transaction.balance_after,
                    "sentiment": sentiment,
                    "timestamp": transaction.timestamp.isoformat()
                }
            )
            
            print(f"[GEN] ✓ Created memory for {transaction.transaction_type.value}: {transaction.amount:.1f} gens")
            
        except Exception as e:
            print(f"[GEN] Warning: Could not create memory for transaction: {e}")
    
    def get_gen_history_summary(self, limit: int = 10) -> str:
        """
        Get a human-readable summary of recent gen activity.
        
        Args:
            limit: Number of recent transactions to include
            
        Returns:
            Formatted string summary
        """
        if not self.gen_manager:
            return "Gen economy not available."
        
        balance = self.gen_manager.get_balance_summary()
        transactions = self.gen_manager.get_recent_transactions(limit=limit)
        
        summary = f"💰 Gen Balance: {balance['current_balance']:.1f}\n"
        summary += f"📊 Net Worth: {balance['net_worth']:.1f} (earned: {balance['total_earned']:.1f}, spent: {balance['total_spent']:.1f})\n\n"
        
        if transactions:
            summary += "Recent Activity:\n"
            for txn in reversed(transactions[-5:]):  # Last 5
                amount = txn['amount']
                sign = "+" if txn['type'] in ['earned', 'bonus', 'allowance', 'gift'] else "-"
                summary += f"  {sign}{amount:.1f} - {txn['reason'][:60]}\n"
        
        return summary
    
    def get_motivational_status(self) -> str:
        """
        Get motivational message based on current gen status.
        
        Returns:
            Motivational message
        """
        if not self.gen_manager:
            return "Ready to earn!"
        
        balance = self.gen_manager.get_balance_summary()
        current = balance['current_balance']
        net_worth = balance['net_worth']
        
        if current < 0:
            return "⚠️ In debt - I need to focus on earning gens through quality work!"
        elif current < 50:
            return "💡 Low balance - I should focus on completing tasks and providing value."
        elif current < 200:
            return "📈 Building up my gen reserves through good work."
        elif current < 500:
            return "[Done]Healthy balance - continuing to earn through quality contributions."
        elif current < 1000:
            return "💪 Strong financial position - motivated to maintain excellence!"
        else:
            return "🌟 Excellent gen management - consistently delivering value!"

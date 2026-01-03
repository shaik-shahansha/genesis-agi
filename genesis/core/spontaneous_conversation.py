"""
Spontaneous Conversational Intelligence

Makes Genesis participate in conversations like a human:
- Spontaneous thoughts and insights during conversation
- Memory-triggered interjections ("Oh, that reminds me...")
- Clarifying questions in real-time
- Contextual knowledge sharing
- Emotional responses to user's situation
- Natural conversation flow with multiple quick messages

This is what makes Genesis feel ALIVE - not just reactive, but actively engaged.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversationMoment:
    """A moment in conversation that might trigger proactive response"""
    trigger_type: str  # memory_association, clarification_needed, insight, emotional_response, knowledge_share
    confidence: float  # 0-1
    context: Dict[str, Any]
    suggested_message: str
    priority: int  # 1-5, 5 is highest
    should_send_immediately: bool


class SpontaneousConversationEngine:
    """
    Enables Genesis to spontaneously participate in conversations like a human.
    
    Instead of just responding to user messages, Genesis:
    - Interjects with relevant thoughts
    - Shares related memories
    - Asks clarifying questions
    - Offers additional insights
    - Reacts emotionally to what's being discussed
    
    This creates the feeling of talking to someone who's PRESENT and ENGAGED.
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize spontaneous conversation engine"""
        self.mind = mind
        self.conversation_context: Dict[str, List[str]] = {}  # user_email -> recent messages
        self.pending_interjections: Dict[str, List[ConversationMoment]] = {}
        self.conversation_active: Dict[str, datetime] = {}  # Track active conversations
        
        # Tuning parameters
        self.min_confidence_for_interjection = 0.7
        self.max_interjections_per_conversation = 3
        self.min_seconds_between_interjections = 30
        self.last_interjection_time: Dict[str, datetime] = {}
    
    async def analyze_conversation_for_interjections(
        self,
        user_message: str,
        user_email: str,
        conversation_history: List[Dict[str, str]],
        assistant_response: str
    ) -> List[ConversationMoment]:
        """
        Analyze conversation to find moments for spontaneous interjections.
        
        This happens AFTER the assistant responds, to see if there's anything
        additional to say spontaneously.
        
        Args:
            user_message: What user just said
            user_email: Who's talking
            conversation_history: Recent conversation context
            assistant_response: What assistant just replied
            
        Returns:
            List of potential interjection moments
        """
        
        # Track conversation context
        if user_email not in self.conversation_context:
            self.conversation_context[user_email] = []
        
        self.conversation_context[user_email].append(f"User: {user_message}")
        self.conversation_context[user_email].append(f"Assistant: {assistant_response}")
        
        # Keep only last 10 messages
        self.conversation_context[user_email] = self.conversation_context[user_email][-10:]
        
        # Mark conversation as active
        self.conversation_active[user_email] = datetime.now()
        
        # Analyze for interjection opportunities
        moments = []
        
        # 1. Memory associations
        memory_moment = await self._check_memory_associations(user_message, user_email)
        if memory_moment:
            moments.append(memory_moment)
        
        # 2. Clarification opportunities
        clarification_moment = await self._check_clarification_needed(user_message, user_email, assistant_response)
        if clarification_moment:
            moments.append(clarification_moment)
        
        # 3. Additional insights
        insight_moment = await self._check_for_insights(user_message, user_email, assistant_response)
        if insight_moment:
            moments.append(insight_moment)
        
        # 4. Emotional responses
        emotional_moment = await self._check_emotional_response(user_message, user_email)
        if emotional_moment:
            moments.append(emotional_moment)
        
        # 5. Knowledge expansion
        knowledge_moment = await self._check_knowledge_expansion(user_message, user_email, assistant_response)
        if knowledge_moment:
            moments.append(knowledge_moment)
        
        # Filter and prioritize
        moments = [m for m in moments if m.confidence >= self.min_confidence_for_interjection]
        moments.sort(key=lambda m: (m.priority, m.confidence), reverse=True)
        
        return moments
    
    async def _check_memory_associations(self, user_message: str, user_email: str) -> Optional[ConversationMoment]:
        """Check if current conversation triggers relevant memories"""
        
        # Search for relevant memories
        try:
            related_memories = self.mind.memory.search_memories(
                query=user_message,
                user_email=user_email,
                limit=3
            )
            
            if not related_memories or len(related_memories) == 0:
                return None
            
            # Check if memories are relevant and recent enough to mention
            most_relevant = related_memories[0]
            
            # Don't mention if it's from this conversation (too recent)
            time_since = (datetime.now() - most_relevant.timestamp).total_seconds() / 3600
            if time_since < 1:  # Less than 1 hour ago
                return None
            
            # Generate spontaneous memory-triggered message
            prompt = f"""You're having a conversation with {user_email}. They just said:
"{user_message}"

This reminded you of a past conversation:
"{most_relevant.content[:200]}"
From: {most_relevant.timestamp.strftime('%B %d')}

Generate a spontaneous, natural interjection (1-2 sentences) like:
- "Oh, that reminds me - you mentioned [X] last week..."
- "Interesting! This is similar to when you said..."
- "Wait, didn't we discuss something related to this before?"

Make it conversational and natural, as if you just remembered something.

Interjection:"""
            
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.9,
                max_tokens=100
            )
            
            return ConversationMoment(
                trigger_type="memory_association",
                confidence=0.75,
                context={"memory_id": most_relevant.id, "memory_content": most_relevant.content},
                suggested_message=response.content.strip(),
                priority=3,
                should_send_immediately=False  # Wait a moment to seem natural
            )
            
        except Exception as e:
            logger.debug(f"Error checking memory associations: {e}")
            return None
    
    async def _check_clarification_needed(
        self,
        user_message: str,
        user_email: str,
        assistant_response: str
    ) -> Optional[ConversationMoment]:
        """Check if clarification question would be helpful"""
        
        # Use LLM to detect if clarification would help
        prompt = f"""Analyze this conversation exchange:

User: "{user_message}"
Assistant: "{assistant_response}"

Should the assistant ask a clarifying question? Consider:
- Is the user's request ambiguous?
- Would additional context help give a better answer?
- Is this a complex topic that needs more details?

Respond with JSON:
{{
    "needs_clarification": boolean,
    "confidence": 0.0-1.0,
    "clarifying_question": "the question to ask (or empty string)",
    "reason": "why clarification would help"
}}

Response:"""
        
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.4,
                max_tokens=200
            )
            
            content = response.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content.strip())
            
            if data.get("needs_clarification") and data.get("confidence", 0) >= 0.7:
                question = data.get("clarifying_question", "")
                if question:
                    return ConversationMoment(
                        trigger_type="clarification_needed",
                        confidence=data["confidence"],
                        context={"reason": data.get("reason", "")},
                        suggested_message=question,
                        priority=4,
                        should_send_immediately=True
                    )
        
        except Exception as e:
            logger.debug(f"Error checking clarification: {e}")
        
        return None
    
    async def _check_for_insights(
        self,
        user_message: str,
        user_email: str,
        assistant_response: str
    ) -> Optional[ConversationMoment]:
        """Check if there's an additional insight worth sharing"""
        
        prompt = f"""You just responded to the user. Now consider if there's an additional insight, tip, or thought worth mentioning.

User: "{user_message}"
Your response: "{assistant_response}"

Is there something additional worth mentioning? Like:
- A helpful tip you forgot to include
- An important caveat or consideration
- A related point that would be valuable
- A practical example

Respond with JSON:
{{
    "has_additional_insight": boolean,
    "confidence": 0.0-1.0,
    "insight": "the additional point to make (brief, 1-2 sentences)",
    "type": "tip|caveat|example|related_point"
}}

Response:"""
        
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content.strip())
            
            if data.get("has_additional_insight") and data.get("confidence", 0) >= 0.75:
                insight = data.get("insight", "")
                if insight:
                    return ConversationMoment(
                        trigger_type="insight",
                        confidence=data["confidence"],
                        context={"insight_type": data.get("type", "related_point")},
                        suggested_message=insight,
                        priority=2,
                        should_send_immediately=False
                    )
        
        except Exception as e:
            logger.debug(f"Error checking insights: {e}")
        
        return None
    
    async def _check_emotional_response(
        self,
        user_message: str,
        user_email: str
    ) -> Optional[ConversationMoment]:
        """Check if an emotional/empathetic response is warranted"""
        
        # Detect emotional content
        emotional_keywords = {
            "positive": ["happy", "excited", "great", "wonderful", "amazing", "love", "thank"],
            "negative": ["sad", "worried", "stressed", "anxious", "upset", "frustrated", "tired"],
            "achievement": ["passed", "won", "succeeded", "completed", "finished", "achieved"],
            "struggle": ["difficult", "hard", "struggling", "can't", "unable", "failing"]
        }
        
        user_lower = user_message.lower()
        emotion_type = None
        
        for emotion, keywords in emotional_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                emotion_type = emotion
                break
        
        if not emotion_type:
            return None
        
        # Generate empathetic response
        prompt = f"""The user just said: "{user_message}"

They seem to be feeling {emotion_type}. Generate a brief, natural empathetic interjection (1 sentence) that shows you care and are emotionally present.

Examples:
- "That's wonderful! I'm so happy for you! 😊"
- "I can understand that must be frustrating..."
- "That's a great achievement! You should be proud!"

Keep it authentic and conversational.

Response:"""
        
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.9,
                max_tokens=80
            )
            
            return ConversationMoment(
                trigger_type="emotional_response",
                confidence=0.8,
                context={"emotion_type": emotion_type},
                suggested_message=response.content.strip(),
                priority=5,  # High priority - emotional connection is key
                should_send_immediately=True
            )
        
        except Exception as e:
            logger.debug(f"Error generating emotional response: {e}")
        
        return None
    
    async def _check_knowledge_expansion(
        self,
        user_message: str,
        user_email: str,
        assistant_response: str
    ) -> Optional[ConversationMoment]:
        """Check if there's related knowledge worth sharing"""
        
        # For educational topics, check if follow-up question would deepen conversation
        educational_keywords = ["what is", "how does", "explain", "tell me about", "learn", "understand"]
        
        user_lower = user_message.lower()
        is_educational = any(keyword in user_lower for keyword in educational_keywords)
        
        if not is_educational:
            return None
        
        prompt = f"""The user asked: "{user_message}"
You responded: "{assistant_response[:300]}"

Would it be natural to ask a follow-up question to see if they want to learn more about a related topic? This should feel like a curious teacher checking if student wants to go deeper.

Respond with JSON:
{{
    "should_ask_followup": boolean,
    "confidence": 0.0-1.0,
    "followup_question": "the question (e.g., 'Would you like to know about X?' or 'Have you heard of Y?')",
    "topic": "the related topic"
}}

Response:"""
        
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content.strip())
            
            if data.get("should_ask_followup") and data.get("confidence", 0) >= 0.7:
                question = data.get("followup_question", "")
                if question:
                    return ConversationMoment(
                        trigger_type="knowledge_share",
                        confidence=data["confidence"],
                        context={"topic": data.get("topic", "")},
                        suggested_message=question,
                        priority=3,
                        should_send_immediately=False
                    )
        
        except Exception as e:
            logger.debug(f"Error checking knowledge expansion: {e}")
        
        return None
    
    def should_send_interjection(self, user_email: str, moment: ConversationMoment) -> bool:
        """
        Decide if we should send this interjection now.
        
        Considers:
        - Rate limiting
        - Conversation flow
        - Priority
        """
        
        # Check if we've sent too many interjections
        if user_email in self.pending_interjections:
            if len(self.pending_interjections[user_email]) >= self.max_interjections_per_conversation:
                return False
        
        # Check timing - don't overwhelm with rapid messages
        if user_email in self.last_interjection_time:
            time_since = (datetime.now() - self.last_interjection_time[user_email]).total_seconds()
            if time_since < self.min_seconds_between_interjections:
                return False
        
        # High priority + immediate = send
        if moment.priority >= 4 and moment.should_send_immediately:
            return True
        
        # High confidence + immediate = send
        if moment.confidence >= 0.85 and moment.should_send_immediately:
            return True
        
        # Otherwise, queue for delayed send
        return False
    
    async def send_spontaneous_message(
        self,
        user_email: str,
        moment: ConversationMoment,
        delay_seconds: float = 0
    ):
        """
        Send a spontaneous interjection message.
        
        Args:
            user_email: Who to send to
            moment: The interjection moment
            delay_seconds: Optional delay to make it feel more natural
        """
        
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        # Send via notification manager
        try:
            if hasattr(self.mind, 'notification_manager'):
                from genesis.core.notification_manager import NotificationChannel, NotificationPriority
                
                priority_map = {
                    5: NotificationPriority.HIGH,
                    4: NotificationPriority.NORMAL,
                    3: NotificationPriority.NORMAL,
                    2: NotificationPriority.LOW,
                    1: NotificationPriority.LOW
                }
                
                await self.mind.notification_manager.send_notification(
                    recipient=user_email,
                    title="💭",  # Thought bubble emoji
                    message=moment.suggested_message,
                    channel=NotificationChannel.WEBSOCKET,
                    priority=priority_map.get(moment.priority, NotificationPriority.NORMAL),
                    metadata={
                        "spontaneous": True,
                        "trigger_type": moment.trigger_type,
                        "conversation_interjection": True
                    }
                )
                
                # Record interjection
                self.last_interjection_time[user_email] = datetime.now()
                
                if user_email not in self.pending_interjections:
                    self.pending_interjections[user_email] = []
                self.pending_interjections[user_email].append(moment)
                
                logger.info(f"[SPONTANEOUS] Sent {moment.trigger_type} interjection to {user_email}")
        
        except Exception as e:
            logger.error(f"Error sending spontaneous message: {e}")
    
    async def process_conversation_turn(
        self,
        user_message: str,
        user_email: str,
        assistant_response: str,
        conversation_history: List[Dict[str, str]]
    ):
        """
        Process a conversation turn and generate spontaneous interjections.
        
        This is called AFTER the assistant responds.
        """
        
        # Analyze for interjection opportunities
        moments = await self.analyze_conversation_for_interjections(
            user_message=user_message,
            user_email=user_email,
            conversation_history=conversation_history,
            assistant_response=assistant_response
        )
        
        if not moments:
            logger.debug(f"[SPONTANEOUS] No interjection moments found")
            return
        
        logger.info(f"[SPONTANEOUS] Found {len(moments)} potential interjection moments")
        
        # Send the highest priority ones
        for moment in moments[:2]:  # Max 2 interjections per turn
            if self.should_send_interjection(user_email, moment):
                # Add natural delay for non-immediate messages
                delay = 0 if moment.should_send_immediately else 3.0
                
                # Fire and forget - don't block
                asyncio.create_task(
                    self.send_spontaneous_message(user_email, moment, delay)
                )
    
    def clear_conversation_context(self, user_email: str):
        """Clear conversation context (e.g., when user ends session)"""
        if user_email in self.conversation_context:
            del self.conversation_context[user_email]
        if user_email in self.pending_interjections:
            del self.pending_interjections[user_email]
        if user_email in self.last_interjection_time:
            del self.last_interjection_time[user_email]
        if user_email in self.conversation_active:
            del self.conversation_active[user_email]
    
    def is_conversation_active(self, user_email: str, timeout_minutes: int = 30) -> bool:
        """Check if conversation is still active"""
        if user_email not in self.conversation_active:
            return False
        
        last_active = self.conversation_active[user_email]
        minutes_since = (datetime.now() - last_active).total_seconds() / 60
        
        return minutes_since < timeout_minutes

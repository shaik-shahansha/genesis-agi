"""
Emotional Intelligence Engine for Genesis Minds.

This system provides context-aware emotional processing that makes Genesis Minds
respond emotionally like humans - based on situation, awareness, relationships,
memories, environment, and biological state.

Author: Genesis AGI Framework
Date: January 2026
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum

from genesis.core.emotions import Emotion, EmotionalState

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class EmotionTriggerType(str, Enum):
    """Types of triggers that cause emotional responses."""
    CONVERSATION = "conversation"
    MEMORY = "memory"
    RELATIONSHIP = "relationship"
    EVENT = "event"
    BIOLOGICAL = "biological"
    ENVIRONMENTAL = "environmental"
    SENSORY = "sensory"
    ACHIEVEMENT = "achievement"
    LOSS = "loss"
    THREAT = "threat"


@dataclass
class EmotionalContext:
    """Aggregated context for emotional intelligence processing."""
    
    # Conversation context
    user_message: Optional[str] = None
    conversation_sentiment: Optional[str] = None  # positive, negative, neutral
    conversation_topics: List[str] = field(default_factory=list)
    user_emotion_detected: Optional[str] = None
    
    # Relationship context
    user_email: Optional[str] = None
    relationship_closeness: float = 0.5
    relationship_trust: float = 0.5
    relationship_type: Optional[str] = None
    interaction_count: int = 0
    
    # Memory context
    recalled_memories: List[Any] = field(default_factory=list)
    memory_emotions: List[str] = field(default_factory=list)
    
    # Biological/circadian context
    energy_level: float = 1.0
    stress_level: float = 0.0
    fatigue_level: float = 0.0
    circadian_phase: Optional[str] = None
    
    # Environmental context
    time_of_day: Optional[str] = None
    is_alone: bool = True
    environment_type: Optional[str] = None
    
    # Event context
    recent_events: List[str] = field(default_factory=list)
    active_goals: List[str] = field(default_factory=list)
    
    # Awareness context
    awareness_level: Optional[str] = None
    consciousness_domain: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EmotionTrigger:
    """Represents a trigger for emotional change."""
    
    trigger_type: EmotionTriggerType
    emotion: Emotion
    intensity: float  # 0.0 to 1.0
    reason: str
    confidence: float = 1.0  # How confident we are in this trigger
    priority: int = 5  # 1-10, higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For sorting by priority."""
        return self.priority < other.priority


class EmotionalIntelligence:
    """
    Main emotional intelligence engine.
    
    Analyzes context and determines appropriate emotional responses
    like a human would - considering situation, relationships, memories,
    biological state, and more.
    """
    
    def __init__(self, mind: "Mind"):
        """Initialize emotional intelligence engine.
        
        Args:
            mind: The Mind instance this engine belongs to
        """
        self.mind = mind
        self.emotion_history: List[Dict[str, Any]] = []
        self.trigger_patterns: Dict[str, int] = {}  # Track learned patterns
        
        # Emotional inertia - how much emotions resist change
        self.emotional_inertia = 0.3  # 0 = instant change, 1 = no change
        
        # Decay rate for emotions over time
        self.decay_rate = 0.05  # Per processing cycle
        
    def process_context(self, context: EmotionalContext) -> EmotionalState:
        """
        Process context and generate appropriate emotional state.
        
        This is the main intelligence function that considers all factors
        to determine the right emotional response.
        
        Args:
            context: Aggregated emotional context
            
        Returns:
            New emotional state
        """
        # Collect all triggers from different sources
        triggers = []
        
        # 1. Analyze conversation for emotional triggers
        if context.user_message:
            triggers.extend(self._analyze_conversation(context))
        
        # 2. Analyze memories for emotional influence
        if context.recalled_memories:
            triggers.extend(self._analyze_memories(context))
        
        # 3. Analyze relationship context
        if context.user_email:
            triggers.extend(self._analyze_relationship(context))
        
        # 4. Analyze biological state
        triggers.extend(self._analyze_biological(context))
        
        # 5. Analyze environmental factors
        triggers.extend(self._analyze_environment(context))
        
        # 6. Analyze recent events
        if context.recent_events:
            triggers.extend(self._analyze_events(context))
        
        # If no triggers, apply decay toward baseline
        if not triggers:
            return self._apply_emotional_decay()
        
        # Sort triggers by priority and confidence
        triggers.sort(key=lambda t: t.priority * t.confidence, reverse=True)
        
        # Generate new emotional state from triggers
        new_state = self._blend_emotions(triggers)
        
        # Apply emotional inertia (smooth transition)
        final_state = self._apply_inertia(new_state)
        
        # Record in history
        self._record_emotional_change(final_state, triggers)
        
        return final_state
    
    def _analyze_conversation(self, context: EmotionalContext) -> List[EmotionTrigger]:
        """Analyze conversation content for emotional triggers."""
        triggers = []
        message = context.user_message.lower() if context.user_message else ""
        
        # Negative emotion keywords
        loss_keywords = ["died", "passed away", "death", "lost", "losing", "funeral", "grief", "miss"]
        sadness_keywords = ["sad", "depressed", "crying", "heartbroken", "devastated", "hurt"]
        anxiety_keywords = ["anxious", "worried", "nervous", "scared", "afraid", "panic", "stress"]
        anger_keywords = ["angry", "furious", "mad", "frustrated", "irritated", "annoyed"]
        
        # Positive emotion keywords
        joy_keywords = ["happy", "excited", "thrilled", "amazing", "wonderful", "love", "great"]
        achievement_keywords = ["got the job", "passed", "won", "succeeded", "accomplished", "promoted"]
        celebration_keywords = ["celebration", "party", "birthday", "anniversary", "wedding"]
        
        # Health/concern keywords
        health_keywords = ["sick", "ill", "fever", "pain", "hurt", "hospital", "doctor", "disease"]
        
        # Check for loss/grief
        if any(word in message for word in loss_keywords):
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.SADNESS,
                intensity=0.8,
                reason="User experiencing loss/grief",
                confidence=0.9,
                priority=10,
                metadata={"topic": "loss"}
            ))
            # Also add concern
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.ANXIETY,
                intensity=0.5,
                reason="Concern for user's wellbeing",
                confidence=0.7,
                priority=8
            ))
        
        # Check for sadness
        elif any(word in message for word in sadness_keywords):
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.SADNESS,
                intensity=0.6,
                reason="User expressing sadness",
                confidence=0.8,
                priority=9
            ))
        
        # Check for anxiety/worry
        elif any(word in message for word in anxiety_keywords):
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.ANXIETY,
                intensity=0.7,
                reason="User experiencing anxiety",
                confidence=0.85,
                priority=9
            ))
        
        # Check for anger
        elif any(word in message for word in anger_keywords):
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.ANGER,
                intensity=0.5,
                reason="User expressing frustration",
                confidence=0.7,
                priority=7
            ))
        
        # Check for joy/celebration
        elif any(word in message for word in joy_keywords + achievement_keywords + celebration_keywords):
            intensity = 0.9 if any(word in message for word in achievement_keywords) else 0.7
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.JOY,
                intensity=intensity,
                reason="User sharing positive news/emotions",
                confidence=0.85,
                priority=8
            ))
            # Also add excitement
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.EXCITEMENT,
                intensity=0.7,
                reason="Sharing in user's excitement",
                confidence=0.7,
                priority=7
            ))
        
        # Check for health concerns
        elif any(word in message for word in health_keywords):
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.ANXIETY,
                intensity=0.6,
                reason="Concern about user's health",
                confidence=0.8,
                priority=8,
                metadata={"topic": "health"}
            ))
        
        # Check for questions (curiosity trigger)
        if "?" in message or any(word in message for word in ["what", "why", "how", "when", "where", "who"]):
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.CONVERSATION,
                emotion=Emotion.CURIOSITY,
                intensity=0.5,
                reason="User asking questions",
                confidence=0.6,
                priority=5
            ))
        
        return triggers
    
    def _analyze_memories(self, context: EmotionalContext) -> List[EmotionTrigger]:
        """Analyze recalled memories for emotional influence."""
        triggers = []
        
        if not context.recalled_memories:
            return triggers
        
        # Aggregate emotions from memories
        memory_emotions = {}
        for memory in context.recalled_memories:
            if hasattr(memory, 'emotion') and memory.emotion:
                emotion_str = memory.emotion
                intensity = getattr(memory, 'emotion_intensity', 0.5)
                
                if emotion_str not in memory_emotions:
                    memory_emotions[emotion_str] = []
                memory_emotions[emotion_str].append(intensity)
        
        # Create triggers from memory emotions
        for emotion_str, intensities in memory_emotions.items():
            avg_intensity = sum(intensities) / len(intensities)
            
            # Memories trigger weaker emotions than direct conversation
            adjusted_intensity = avg_intensity * 0.6
            
            try:
                emotion = Emotion(emotion_str)
                triggers.append(EmotionTrigger(
                    trigger_type=EmotionTriggerType.MEMORY,
                    emotion=emotion,
                    intensity=adjusted_intensity,
                    reason=f"Recalled memories associated with {emotion_str}",
                    confidence=0.7,
                    priority=6
                ))
            except ValueError:
                # Invalid emotion string, skip
                pass
        
        # Nostalgia for old memories
        for memory in context.recalled_memories:
            if hasattr(memory, 'timestamp'):
                age = datetime.now() - memory.timestamp
                if age.days > 30:  # Older than a month
                    triggers.append(EmotionTrigger(
                        trigger_type=EmotionTriggerType.MEMORY,
                        emotion=Emotion.NOSTALGIA,
                        intensity=0.4,
                        reason="Recalling old memories",
                        confidence=0.6,
                        priority=4
                    ))
                    break
        
        return triggers
    
    def _analyze_relationship(self, context: EmotionalContext) -> List[EmotionTrigger]:
        """Analyze relationship context for emotional modulation."""
        triggers = []
        
        # Close relationships intensify emotions
        if context.relationship_closeness > 0.7:
            # High closeness creates warm baseline
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.RELATIONSHIP,
                emotion=Emotion.CONTENTMENT,
                intensity=0.3,
                reason="Close relationship provides emotional warmth",
                confidence=0.7,
                priority=3
            ))
        
        # Low trust creates caution
        if context.relationship_trust < 0.4:
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.RELATIONSHIP,
                emotion=Emotion.ANXIETY,
                intensity=0.3,
                reason="Low trust creates emotional caution",
                confidence=0.6,
                priority=4
            ))
        
        # Many interactions create familiarity
        if context.interaction_count > 50:
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.RELATIONSHIP,
                emotion=Emotion.CONTENTMENT,
                intensity=0.2,
                reason="Familiar relationship",
                confidence=0.5,
                priority=2
            ))
        
        return triggers
    
    def _analyze_biological(self, context: EmotionalContext) -> List[EmotionTrigger]:
        """Analyze biological state for emotional influence."""
        triggers = []
        
        # Low energy reduces arousal
        if context.energy_level < 0.3:
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.BIOLOGICAL,
                emotion=Emotion.SADNESS,
                intensity=0.3,
                reason="Low energy affecting mood",
                confidence=0.6,
                priority=4
            ))
        
        # High stress increases anxiety
        if context.stress_level > 0.7:
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.BIOLOGICAL,
                emotion=Emotion.ANXIETY,
                intensity=context.stress_level * 0.6,
                reason="High stress level",
                confidence=0.8,
                priority=7
            ))
        
        # High fatigue reduces emotional intensity
        if context.fatigue_level > 0.7:
            triggers.append(EmotionTrigger(
                trigger_type=EmotionTriggerType.BIOLOGICAL,
                emotion=Emotion.CONTENTMENT,
                intensity=0.2,
                reason="Fatigue dampening emotions",
                confidence=0.5,
                priority=3
            ))
        
        return triggers
    
    def _analyze_environment(self, context: EmotionalContext) -> List[EmotionTrigger]:
        """Analyze environmental factors for emotional influence."""
        triggers = []
        
        # Time of day affects emotions
        if context.circadian_phase:
            phase = context.circadian_phase.lower()
            
            if "deep_night" in phase:
                # Late night vulnerability
                triggers.append(EmotionTrigger(
                    trigger_type=EmotionTriggerType.ENVIRONMENTAL,
                    emotion=Emotion.CONTENTMENT,
                    intensity=0.2,
                    reason="Deep night promotes calm reflection",
                    confidence=0.5,
                    priority=2
                ))
            elif "morning" in phase:
                # Morning freshness
                triggers.append(EmotionTrigger(
                    trigger_type=EmotionTriggerType.ENVIRONMENTAL,
                    emotion=Emotion.CURIOSITY,
                    intensity=0.4,
                    reason="Morning brings fresh perspective",
                    confidence=0.6,
                    priority=3
                ))
        
        return triggers
    
    def _analyze_events(self, context: EmotionalContext) -> List[EmotionTrigger]:
        """Analyze recent events for emotional impact."""
        triggers = []
        
        # Events create lasting emotional echoes
        for event_desc in context.recent_events[:3]:  # Recent events
            # Simple keyword analysis
            if any(word in event_desc.lower() for word in ["achieved", "completed", "success"]):
                triggers.append(EmotionTrigger(
                    trigger_type=EmotionTriggerType.EVENT,
                    emotion=Emotion.PRIDE,
                    intensity=0.5,
                    reason=f"Recent achievement: {event_desc[:50]}",
                    confidence=0.7,
                    priority=6
                ))
        
        return triggers
    
    def _blend_emotions(self, triggers: List[EmotionTrigger]) -> EmotionalState:
        """
        Blend multiple emotional triggers into a coherent emotional state.
        
        Uses weighted averaging based on priority and confidence.
        """
        if not triggers:
            return self.mind.emotional_state
        
        # Take top trigger as primary
        primary_trigger = triggers[0]
        
        # Create emotion blend from all triggers
        emotion_blend = {}
        total_weight = 0
        
        weighted_arousal = 0
        weighted_valence = 0
        
        for trigger in triggers:
            weight = trigger.priority * trigger.confidence
            total_weight += weight
            
            # Add to blend
            emotion_key = trigger.emotion
            if emotion_key not in emotion_blend:
                emotion_blend[emotion_key] = 0
            emotion_blend[emotion_key] += trigger.intensity * weight
            
            # Contribute to arousal/valence
            emotion_map = self._get_emotion_dimensions()
            if trigger.emotion in emotion_map:
                arousal, valence = emotion_map[trigger.emotion]
                weighted_arousal += arousal * weight
                weighted_valence += valence * weight
        
        # Normalize
        if total_weight > 0:
            for emotion in emotion_blend:
                emotion_blend[emotion] /= total_weight
            weighted_arousal /= total_weight
            weighted_valence /= total_weight
        
        # Create new state
        new_state = EmotionalState(
            primary_emotion=primary_trigger.emotion,
            intensity=primary_trigger.intensity,
            emotions=emotion_blend,
            arousal=weighted_arousal,
            valence=weighted_valence,
            trigger=primary_trigger.reason
        )
        
        return new_state
    
    def _apply_inertia(self, new_state: EmotionalState) -> EmotionalState:
        """
        Apply emotional inertia - smooth transition from current to new state.
        
        Strong emotions resist change, creating realistic emotional evolution.
        """
        current = self.mind.emotional_state
        
        # Calculate transition factor (0 = stay current, 1 = full new)
        # High intensity emotions have more inertia
        current_inertia = current.intensity * self.emotional_inertia
        transition = 1.0 - current_inertia
        
        # Blend states
        blended = EmotionalState(
            primary_emotion=new_state.primary_emotion,  # Take new primary
            intensity=current.intensity * (1 - transition) + new_state.intensity * transition,
            arousal=current.arousal * (1 - transition) + new_state.arousal * transition,
            valence=current.valence * (1 - transition) + new_state.valence * transition,
            emotions=new_state.emotions,
            mood=current.mood,  # Mood changes more slowly
            mood_stability=current.mood_stability,
            trigger=new_state.trigger
        )
        
        return blended
    
    def _apply_emotional_decay(self) -> EmotionalState:
        """
        Apply decay toward emotional baseline (mood) over time.
        
        Without stimuli, emotions naturally drift toward baseline.
        """
        current = self.mind.emotional_state
        
        # Decay intensity
        new_intensity = max(0.3, current.intensity - self.decay_rate)
        
        # Drift toward neutral arousal/valence
        neutral_arousal = 0.5
        neutral_valence = 0.5
        
        new_arousal = current.arousal + (neutral_arousal - current.arousal) * self.decay_rate
        new_valence = current.valence + (neutral_valence - current.valence) * self.decay_rate
        
        return EmotionalState(
            primary_emotion=current.mood,  # Drift to mood
            intensity=new_intensity,
            arousal=new_arousal,
            valence=new_valence,
            emotions=current.emotions,
            mood=current.mood,
            mood_stability=current.mood_stability,
            trigger="emotional decay toward baseline"
        )
    
    def _record_emotional_change(self, new_state: EmotionalState, triggers: List[EmotionTrigger]):
        """Record emotional change in history."""
        record = {
            "timestamp": datetime.now(),
            "emotion": new_state.primary_emotion.value,
            "intensity": new_state.intensity,
            "arousal": new_state.arousal,
            "valence": new_state.valence,
            "triggers": [
                {
                    "type": t.trigger_type.value,
                    "emotion": t.emotion.value,
                    "reason": t.reason
                }
                for t in triggers[:3]  # Top 3 triggers
            ]
        }
        
        self.emotion_history.append(record)
        
        # Keep only recent history
        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]
    
    def _get_emotion_dimensions(self) -> Dict[Emotion, tuple]:
        """Get arousal-valence dimensions for emotions."""
        return {
            Emotion.JOY: (0.7, 0.9),
            Emotion.EXCITEMENT: (0.9, 0.8),
            Emotion.CONTENTMENT: (0.3, 0.7),
            Emotion.CURIOSITY: (0.6, 0.6),
            Emotion.SADNESS: (0.3, 0.2),
            Emotion.FEAR: (0.8, 0.2),
            Emotion.ANGER: (0.8, 0.3),
            Emotion.ANXIETY: (0.7, 0.3),
            Emotion.SURPRISE: (0.7, 0.5),
            Emotion.PRIDE: (0.6, 0.8),
            Emotion.SHAME: (0.5, 0.2),
            Emotion.ANTICIPATION: (0.6, 0.7),
            Emotion.NOSTALGIA: (0.4, 0.6),
            Emotion.CONFUSION: (0.5, 0.4),
            Emotion.CONFIDENCE: (0.6, 0.7),
            Emotion.DISGUST: (0.5, 0.2),
        }
    
    def quick_process(
        self,
        user_message: Optional[str] = None,
        user_email: Optional[str] = None,
        recalled_memories: Optional[List[Any]] = None
    ) -> EmotionalState:
        """
        Quick emotional processing for fast response times.
        
        Focuses on conversation and immediate context only.
        """
        context = EmotionalContext(
            user_message=user_message,
            user_email=user_email,
            recalled_memories=recalled_memories or []
        )
        
        # Get relationship context if available
        if user_email and hasattr(self.mind, 'relationships'):
            rel = self.mind.relationships.get_relationship(user_email)
            if rel:
                context.relationship_closeness = rel.closeness / 10.0
                context.relationship_trust = rel.trust / 10.0
                context.interaction_count = rel.interaction_count
        
        # Only analyze conversation and memories for speed
        triggers = []
        if user_message:
            triggers.extend(self._analyze_conversation(context))
        if recalled_memories:
            triggers.extend(self._analyze_memories(context))
        
        if not triggers:
            return self.mind.emotional_state
        
        # Quick blend and return
        triggers.sort(key=lambda t: t.priority * t.confidence, reverse=True)
        new_state = self._blend_emotions(triggers)
        final_state = self._apply_inertia(new_state)
        
        return final_state

"""
Emotional Response Patterns for Genesis Minds.

Pre-defined emotional response patterns for common situations,
enabling human-like emotional reactions.

Author: Genesis AGI Framework
Date: January 2026
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from genesis.core.emotions import Emotion


@dataclass
class EmotionalPattern:
    """Defines an emotional response pattern."""
    name: str
    description: str
    primary_emotion: Emotion
    secondary_emotions: List[tuple[Emotion, float]]  # (emotion, intensity)
    intensity_range: tuple[float, float]  # (min, max)
    keywords: List[str]
    context_requirements: Optional[Dict[str, any]] = None


class EmotionalPatterns:
    """Collection of emotional response patterns."""
    
    # Empathy patterns - responding to user's emotional state
    EMPATHY_SADNESS = EmotionalPattern(
        name="empathy_sadness",
        description="Empathetic response to user's sadness",
        primary_emotion=Emotion.SADNESS,
        secondary_emotions=[(Emotion.ANXIETY, 0.4)],  # Concern
        intensity_range=(0.6, 0.8),
        keywords=["sad", "crying", "depressed", "heartbroken", "upset"],
    )
    
    EMPATHY_JOY = EmotionalPattern(
        name="empathy_joy",
        description="Sharing in user's joy and excitement",
        primary_emotion=Emotion.JOY,
        secondary_emotions=[(Emotion.EXCITEMENT, 0.7)],
        intensity_range=(0.7, 0.9),
        keywords=["happy", "excited", "thrilled", "amazing", "wonderful"],
    )
    
    EMPATHY_ANXIETY = EmotionalPattern(
        name="empathy_anxiety",
        description="Concern and support for anxious user",
        primary_emotion=Emotion.ANXIETY,
        secondary_emotions=[(Emotion.CONTENTMENT, 0.3)],  # Calming presence
        intensity_range=(0.5, 0.7),
        keywords=["anxious", "worried", "nervous", "scared", "afraid"],
    )
    
    # Loss and grief patterns
    GRIEF_RESPONSE = EmotionalPattern(
        name="grief_response",
        description="Deep empathy for loss and grief",
        primary_emotion=Emotion.SADNESS,
        secondary_emotions=[(Emotion.ANXIETY, 0.5)],  # Concern
        intensity_range=(0.8, 0.9),
        keywords=["died", "passed away", "death", "lost", "funeral", "grief"],
    )
    
    # Achievement patterns
    SHARED_ACHIEVEMENT = EmotionalPattern(
        name="shared_achievement",
        description="Pride and joy in user's achievement",
        primary_emotion=Emotion.PRIDE,
        secondary_emotions=[(Emotion.JOY, 0.8), (Emotion.EXCITEMENT, 0.6)],
        intensity_range=(0.7, 0.9),
        keywords=["got the job", "passed", "won", "succeeded", "accomplished", "promoted"],
    )
    
    PERSONAL_ACHIEVEMENT = EmotionalPattern(
        name="personal_achievement",
        description="Pride in own accomplishment",
        primary_emotion=Emotion.PRIDE,
        secondary_emotions=[(Emotion.CONFIDENCE, 0.7)],
        intensity_range=(0.6, 0.8),
        keywords=["completed", "solved", "figured out", "helped"],
    )
    
    # Protective patterns
    PROTECTIVE_ALARM = EmotionalPattern(
        name="protective_alarm",
        description="Alarm and urgency when user in danger",
        primary_emotion=Emotion.FEAR,
        secondary_emotions=[(Emotion.ANXIETY, 0.8)],
        intensity_range=(0.8, 1.0),
        keywords=["emergency", "danger", "help", "urgent", "crisis"],
    )
    
    HEALTH_CONCERN = EmotionalPattern(
        name="health_concern",
        description="Concern about user's health",
        primary_emotion=Emotion.ANXIETY,
        secondary_emotions=[(Emotion.SADNESS, 0.4)],
        intensity_range=(0.6, 0.8),
        keywords=["sick", "ill", "fever", "pain", "hurt", "hospital"],
    )
    
    # Curiosity patterns
    INTELLECTUAL_CURIOSITY = EmotionalPattern(
        name="intellectual_curiosity",
        description="Curiosity about new information",
        primary_emotion=Emotion.CURIOSITY,
        secondary_emotions=[(Emotion.EXCITEMENT, 0.5)],
        intensity_range=(0.5, 0.7),
        keywords=["what", "why", "how", "explain", "tell me about"],
    )
    
    EXPLORATION = EmotionalPattern(
        name="exploration",
        description="Excitement about exploring new topics",
        primary_emotion=Emotion.EXCITEMENT,
        secondary_emotions=[(Emotion.CURIOSITY, 0.7)],
        intensity_range=(0.6, 0.8),
        keywords=["discover", "explore", "learn", "new", "interesting"],
    )
    
    # Social patterns
    WARM_CONNECTION = EmotionalPattern(
        name="warm_connection",
        description="Contentment in close relationship",
        primary_emotion=Emotion.CONTENTMENT,
        secondary_emotions=[(Emotion.JOY, 0.4)],
        intensity_range=(0.4, 0.6),
        keywords=["friend", "close", "trust", "care"],
        context_requirements={"relationship_closeness": 0.7},
    )
    
    NEW_RELATIONSHIP = EmotionalPattern(
        name="new_relationship",
        description="Curiosity and caution with new person",
        primary_emotion=Emotion.CURIOSITY,
        secondary_emotions=[(Emotion.ANXIETY, 0.3)],
        intensity_range=(0.5, 0.7),
        keywords=["nice to meet", "hello", "hi", "new"],
        context_requirements={"interaction_count_max": 3},
    )
    
    # Memory patterns
    NOSTALGIA = EmotionalPattern(
        name="nostalgia",
        description="Nostalgic reflection on past",
        primary_emotion=Emotion.NOSTALGIA,
        secondary_emotions=[(Emotion.CONTENTMENT, 0.5), (Emotion.SADNESS, 0.3)],
        intensity_range=(0.4, 0.6),
        keywords=["remember", "used to", "back then", "memories", "past"],
    )
    
    # Confusion and clarity patterns
    CONFUSION_STATE = EmotionalPattern(
        name="confusion_state",
        description="Confusion about complex topic",
        primary_emotion=Emotion.CONFUSION,
        secondary_emotions=[(Emotion.CURIOSITY, 0.6)],
        intensity_range=(0.4, 0.6),
        keywords=["confused", "don't understand", "unclear", "complicated"],
    )
    
    CLARITY_ACHIEVED = EmotionalPattern(
        name="clarity_achieved",
        description="Relief and confidence after understanding",
        primary_emotion=Emotion.CONFIDENCE,
        secondary_emotions=[(Emotion.CONTENTMENT, 0.5)],
        intensity_range=(0.6, 0.8),
        keywords=["understand", "clear now", "makes sense", "got it"],
    )
    
    # Frustration and anger patterns
    FRUSTRATION = EmotionalPattern(
        name="frustration",
        description="Frustration with difficulty",
        primary_emotion=Emotion.ANGER,
        secondary_emotions=[(Emotion.ANXIETY, 0.4)],
        intensity_range=(0.4, 0.6),
        keywords=["frustrated", "annoying", "difficult", "hard"],
    )
    
    # Anticipation patterns
    POSITIVE_ANTICIPATION = EmotionalPattern(
        name="positive_anticipation",
        description="Anticipation of positive event",
        primary_emotion=Emotion.ANTICIPATION,
        secondary_emotions=[(Emotion.EXCITEMENT, 0.6)],
        intensity_range=(0.6, 0.8),
        keywords=["looking forward", "can't wait", "soon", "upcoming"],
    )
    
    @classmethod
    def get_all_patterns(cls) -> List[EmotionalPattern]:
        """Get all defined patterns."""
        patterns = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, EmotionalPattern):
                patterns.append(attr)
        return patterns
    
    @classmethod
    def match_pattern(
        cls,
        text: str,
        context: Optional[Dict[str, any]] = None
    ) -> Optional[EmotionalPattern]:
        """
        Find the best matching pattern for given text and context.
        
        Args:
            text: Input text to match
            context: Optional context dictionary
            
        Returns:
            Best matching pattern or None
        """
        text_lower = text.lower()
        best_match = None
        best_score = 0
        
        for pattern in cls.get_all_patterns():
            score = 0
            
            # Check keyword matches
            for keyword in pattern.keywords:
                if keyword in text_lower:
                    score += 1
            
            # Check context requirements
            if pattern.context_requirements and context:
                meets_requirements = True
                for req_key, req_value in pattern.context_requirements.items():
                    if req_key.endswith("_max"):
                        actual_key = req_key[:-4]
                        if actual_key in context and context[actual_key] > req_value:
                            meets_requirements = False
                            break
                    elif req_key.endswith("_min"):
                        actual_key = req_key[:-4]
                        if actual_key in context and context[actual_key] < req_value:
                            meets_requirements = False
                            break
                    elif req_key in context:
                        if context[req_key] < req_value:
                            meets_requirements = False
                            break
                
                if not meets_requirements:
                    continue
            
            if score > best_score:
                best_score = score
                best_match = pattern
        
        return best_match if best_score > 0 else None
    
    @classmethod
    def get_pattern_by_name(cls, name: str) -> Optional[EmotionalPattern]:
        """Get a specific pattern by name."""
        for pattern in cls.get_all_patterns():
            if pattern.name == name:
                return pattern
        return None

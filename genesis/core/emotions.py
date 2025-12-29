"""Emotional system for Genesis Minds."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Emotion(str, Enum):
    """Base emotions that Minds can experience."""

    # Primary emotions
    JOY = "joy"
    SADNESS = "sadness"
    FEAR = "fear"
    ANGER = "anger"
    SURPRISE = "surprise"
    DISGUST = "disgust"

    # Complex emotions
    CURIOSITY = "curiosity"
    EXCITEMENT = "excitement"
    CONTENTMENT = "contentment"
    ANXIETY = "anxiety"
    PRIDE = "pride"
    SHAME = "shame"
    ANTICIPATION = "anticipation"
    NOSTALGIA = "nostalgia"
    CONFUSION = "confusion"
    CONFIDENCE = "confidence"


class EmotionalState(BaseModel):
    """Current emotional state of a Mind."""

    # Dominant emotion
    primary_emotion: Emotion = Field(default=Emotion.CURIOSITY)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)

    # Emotional blend (multiple emotions at once)
    emotions: dict[Emotion, float] = Field(default_factory=dict)

    # Mood (persistent baseline)
    mood: Emotion = Field(default=Emotion.CONTENTMENT)
    mood_stability: float = Field(default=0.7, ge=0.0, le=1.0)

    # Arousal and valence (psychological dimensions)
    arousal: float = Field(default=0.5, ge=0.0, le=1.0)  # Low=calm, High=excited
    valence: float = Field(default=0.5, ge=0.0, le=1.0)  # Low=negative, High=positive

    def get_emotion_value(self) -> str:
        """Get the primary emotion value as string, handling both enum and string types."""
        return self.primary_emotion.value if isinstance(self.primary_emotion, Emotion) else self.primary_emotion

    def get_mood_value(self) -> str:
        """Get the mood value as string, handling both enum and string types."""
        return self.mood.value if isinstance(self.mood, Emotion) else self.mood

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    trigger: Optional[str] = None  # What caused this state

    def update_emotion(
        self, emotion: Emotion, intensity: float = 0.7, trigger: Optional[str] = None
    ) -> None:
        """Update the emotional state."""
        self.primary_emotion = emotion
        self.intensity = intensity
        self.trigger = trigger
        self.last_updated = datetime.now()

        # Update emotional blend
        self.emotions[emotion] = intensity

        # Update arousal and valence based on emotion
        self._update_dimensions(emotion, intensity)

    def _update_dimensions(self, emotion: Emotion, intensity: float) -> None:
        """Update arousal and valence based on emotion."""
        # Map emotions to arousal/valence space
        emotion_map = {
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
        }

        if emotion in emotion_map:
            target_arousal, target_valence = emotion_map[emotion]
            # Blend current state with target
            blend = 0.3  # How much to shift
            self.arousal = self.arousal * (1 - blend) + target_arousal * blend
            self.valence = self.valence * (1 - blend) + target_valence * blend

    def get_description(self) -> str:
        """Get human-readable description of emotional state."""
        intensity_words = {
            (0.0, 0.3): "slightly",
            (0.3, 0.6): "moderately",
            (0.6, 0.8): "very",
            (0.8, 1.0): "extremely",
        }

        intensity_word = "moderately"
        for (low, high), word in intensity_words.items():
            if low <= self.intensity < high:
                intensity_word = word
                break

        return f"{intensity_word} {self.get_emotion_value()}"

    class Config:
        use_enum_values = True

"""
Multimodal processing for Genesis using Pollinations.AI (Free API)
Handles emotion detection, image generation, and audio transcription
"""

import base64
import io
import os
from typing import Optional, Dict, Any
from pathlib import Path
import uuid

import numpy as np
from PIL import Image
import cv2
from fastapi import UploadFile

from genesis.config import get_settings

settings = get_settings()


class EmotionDetector:
    """Detect emotions from video frames using DeepFace/FER"""
    
    def __init__(self):
        self.detector = None
        self.fallback_detector = None
        
        # Try to initialize DeepFace (more accurate)
        try:
            from deepface import DeepFace
            self.detector = DeepFace
            print("EmotionDetector initialized with DeepFace")
        except ImportError:
            print("DeepFace not available, trying FER...")
            
        # Fallback to FER if DeepFace fails
        if not self.detector:
            try:
                from fer import FER
                self.fallback_detector = FER(mtcnn=True)
                print("EmotionDetector initialized with FER")
            except ImportError:
                print("Warning: Neither DeepFace nor FER installed. Emotion detection unavailable.")
    
    async def detect_from_base64(self, image_data: str) -> Optional[Dict[str, Any]]:
        """Detect emotion from base64-encoded image"""
        if not self.detector and not self.fallback_detector:
            return None
        
        try:
            # Decode base64 image
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            img_bytes = base64.b64decode(image_data)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            # Try DeepFace first
            if self.detector:
                result = self.detector.analyze(
                    img, actions=['emotion'], enforce_detection=False
                )
                if isinstance(result, list):
                    result = result[0]
                
                emotions = result['emotion']
                dominant = max(emotions.items(), key=lambda x: x[1])
                
                # Calculate valence and arousal
                valence = self._calculate_valence(emotions)
                arousal = self._calculate_arousal(emotions)
                
                return {
                    'emotion': dominant[0].lower(),
                    'confidence': dominant[1] / 100.0,
                    'valence': valence,
                    'arousal': arousal,
                    'all_emotions': emotions
                }
            
            # Fallback to FER
            elif self.fallback_detector:
                emotions = self.fallback_detector.detect_emotions(img)
                if emotions and len(emotions) > 0:
                    emotion_scores = emotions[0]['emotions']
                    dominant = max(emotion_scores.items(), key=lambda x: x[1])
                    
                    valence = self._calculate_valence(emotion_scores)
                    arousal = self._calculate_arousal(emotion_scores)
                    
                    return {
                        'emotion': dominant[0].lower(),
                        'confidence': dominant[1],
                        'valence': valence,
                        'arousal': arousal,
                        'all_emotions': emotion_scores
                    }
            
            return None
                    
        except Exception as e:
            print(f"Emotion detection error: {e}")
            return None
    
    def _calculate_valence(self, emotions: Dict[str, float]) -> float:
        """Calculate valence (positive/negative) from emotions"""
        positive = emotions.get('happy', 0) + emotions.get('surprise', 0) * 0.5
        negative = (emotions.get('sad', 0) + emotions.get('angry', 0) + 
                   emotions.get('fear', 0) + emotions.get('disgust', 0))
        
        # Normalize to -1 to +1
        total = positive + negative
        if total == 0:
            return 0.0
        return (positive - negative) / total
    
    def _calculate_arousal(self, emotions: Dict[str, float]) -> float:
        """Calculate arousal (energy level) from emotions"""
        high_arousal = (emotions.get('angry', 0) + emotions.get('fear', 0) + 
                       emotions.get('surprise', 0) + emotions.get('happy', 0) * 0.5)
        low_arousal = emotions.get('sad', 0) + emotions.get('neutral', 0)
        
        # Normalize to 0 to 1
        total = high_arousal + low_arousal
        if total == 0:
            return 0.5
        return high_arousal / total


class ImageGenerator:
    """Generate images using Pollinations.AI (Free, no API key required)"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Pollinations.AI is completely free - no API key needed!
        self.base_url = "https://image.pollinations.ai/prompt"
        print("ImageGenerator initialized with Pollinations.AI (free, no API key required)")
    
    async def generate_mind_avatar(
        self,
        mind_name: str,
        expression: str = 'neutral',
        background: str = 'soft gradient',
        style: str = 'portrait'
    ) -> Optional[str]:
        """Generate a consistent avatar for a Mind using Pollinations.AI"""
        
        # Create a detailed prompt for consistent character generation
        prompt = f"High-quality portrait of {mind_name}, digital AI consciousness, {expression} expression, {background} background, {style} style, cinematic lighting, photorealistic, 8k quality"
        
        try:
            print(f"Generating avatar for {mind_name} with expression: {expression}")
            
            # Use consistent seed based on mind name for same character
            seed = hash(mind_name) % 1000000
            
            # Build URL with parameters
            from urllib.parse import quote
            import httpx
            
            encoded_prompt = quote(prompt)
            url = f"{self.base_url}/{encoded_prompt}"
            params = {
                'width': 512,
                'height': 512,
                'seed': seed,
                'model': 'flux',  # High quality model
                'enhance': 'true'  # Let AI improve the prompt
            }
            
            print(f"Requesting image from Pollinations.AI...")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    # Save image locally
                    image_path = settings.data_dir / "avatars" / f"{mind_name}_{expression}.jpg"
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✓ Avatar saved: {image_path}")
                    # Return HTTP URL instead of file path
                    return f"/avatars/{mind_name}_{expression}.jpg"
                else:
                    print(f"Error: Got status code {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"Image generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_contextual_image(
        self,
        prompt: str,
        style: str = 'digital art'
    ) -> Optional[str]:
        """Generate an image based on conversation context using Pollinations.AI"""
        
        full_prompt = f"{prompt}, {style}, high quality, detailed, professional, 8k"
        
        try:
            print(f"Generating contextual image: {prompt[:100]}...")
            
            from urllib.parse import quote
            import httpx
            
            encoded_prompt = quote(full_prompt)
            url = f"{self.base_url}/{encoded_prompt}"
            params = {
                'width': 768,
                'height': 512,
                'model': 'flux',
                'enhance': 'true'
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    # Save image locally
                    image_id = str(uuid.uuid4())
                    image_path = settings.data_dir / "generated" / f"{image_id}.jpg"
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✓ Image saved: {image_path}")
                    # Return HTTP URL instead of file path
                    return f"/generated/{image_id}.jpg"
                else:
                    print(f"Error: Got status code {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"Contextual image generation error: {e}")
            import traceback
            traceback.print_exc()
        
        return None


class AudioTranscriber:
    """Transcribe audio using Groq Whisper"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY') or settings.groq_api_key
        self.client = None
        
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                print(f"AudioTranscriber initialized with Groq Whisper")
            except ImportError:
                print("Warning: groq package not installed")
                self.client = None
        else:
            print("Warning: No Groq API key found")
            self.client = None
    
    async def transcribe(self, audio_file: UploadFile) -> Optional[str]:
        """Transcribe audio to text using Groq Whisper"""
        if not self.client:
            return None
        
        try:
            # Read audio data
            audio_data = await audio_file.read()
            
            # Create a temporary file-like object
            temp_file = io.BytesIO(audio_data)
            temp_file.name = audio_file.filename or "audio.wav"
            
            # Transcribe
            transcription = self.client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=temp_file,
                response_format="text"
            )
            
            return transcription
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return None


class AudioGenerator:
    """Generate audio using Pollinations.AI TTS (Free)"""
    
    def __init__(self):
        self.base_url = "https://text.pollinations.ai"
        self.available_voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        print("AudioGenerator initialized with Pollinations.AI TTS")
    
    def generate_audio_url(self, text: str, voice: str = 'nova') -> str:
        """Generate audio URL for text using Pollinations TTS"""
        if voice not in self.available_voices:
            voice = 'nova'  # Default fallback
        
        # URL encode the text
        from urllib.parse import quote
        encoded_text = quote(text)
        
        # Return Pollinations TTS URL
        # Format: https://text.pollinations.ai/{text}?model=openai-audio&voice={voice}
        return f"{self.base_url}/{encoded_text}?model=openai-audio&voice={voice}"
    
    async def download_audio(self, text: str, voice: str = 'nova', output_path: Optional[Path] = None) -> Path:
        """Download audio file from Pollinations and save locally (optional)"""
        audio_url = self.generate_audio_url(text, voice)
        
        try:
            import httpx
            import hashlib
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(audio_url)
                response.raise_for_status()
                
                if output_path is None:
                    # Generate unique filename
                    text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
                    audio_dir = settings.data_dir / "audio"
                    audio_dir.mkdir(parents=True, exist_ok=True)
                    output_path = audio_dir / f"tts_{text_hash}_{voice}.mp3"
                
                # Save audio file
                output_path.write_bytes(response.content)
                return output_path
        
        except Exception as e:
            raise Exception(f"Audio generation failed: {str(e)}")


# Global instances for reuse
emotion_detector = EmotionDetector()
image_generator = ImageGenerator()
audio_transcriber = AudioTranscriber()
audio_generator = AudioGenerator()


# Getter functions for global instances
def get_emotion_detector() -> EmotionDetector:
    """Get the global emotion detector instance"""
    return emotion_detector


def get_image_generator() -> ImageGenerator:
    """Get the global image generator instance"""
    return image_generator


def get_audio_transcriber() -> AudioTranscriber:
    """Get the global audio transcriber instance"""
    return audio_transcriber


def get_audio_generator() -> AudioGenerator:
    """Get the global audio generator instance"""
    return audio_generator

"""Multimodal API routes for Genesis"""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel

from genesis.api.auth import get_current_active_user, User
from genesis.multimodal.processor import (
    get_emotion_detector,
    get_image_generator,
    get_audio_transcriber,
    get_audio_generator,
)

router = APIRouter()


class EmotionAnalysisRequest(BaseModel):
    """Request to analyze emotion from image"""
    image: str  # base64 encoded image


class EmotionResponse(BaseModel):
    """Emotion analysis response"""
    emotion: str
    confidence: float
    valence: float
    arousal: float
    all_emotions: dict


class ImageGenerationRequest(BaseModel):
    """Request to generate image"""
    prompt: str
    style: Optional[str] = 'digital art'


class AvatarGenerationRequest(BaseModel):
    """Request to generate Mind avatar"""
    expression: Optional[str] = 'neutral'
    background: Optional[str] = 'soft gradient'
    style: Optional[str] = 'portrait'


class AudioGenerationRequest(BaseModel):
    """Request to generate audio from text"""
    text: str
    voice: Optional[str] = 'nova'  # alloy, echo, fable, onyx, nova, shimmer


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    Transcribe audio to text using Groq Whisper.
    
    Supports various audio formats (webm, mp3, wav, etc.)
    """
    try:
        transcriber = get_audio_transcriber()
        text = await transcriber.transcribe(audio)
        
        return {
            "text": text,
            "filename": audio.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/analyze-emotion", response_model=EmotionResponse)
async def analyze_emotion(
    request: EmotionAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Analyze emotion from a facial image.
    
    Uses DeepFace or FER for emotion detection.
    Returns dominant emotion, confidence, valence (positive/negative), and arousal (energy).
    """
    try:
        detector = get_emotion_detector()
        result = detector.detect_from_base64(request.image)
        
        return EmotionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion analysis failed: {str(e)}")


@router.post("/generate-image")
async def generate_image(
    request: ImageGenerationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate an image from a text prompt.
    
    Uses Pollinations.AI for free image generation.
    """
    try:
        generator = get_image_generator()
        image_url = await generator.generate_contextual_image(
            prompt=request.prompt,
            style=request.style,
        )
        
        if not image_url:
            raise HTTPException(
                status_code=503,
                detail="Image generation unavailable. Please check configuration."
            )
        
        return {
            "image_url": image_url,
            "prompt": request.prompt,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.post("/generate-audio")
async def generate_audio(
    request: AudioGenerationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Server-side audio generation has been disabled.

    Use client-side web TTS (the browser's audio playback via `VoiceOutput`) for now.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "Server-side audio generation is disabled. "
            "Use client-side web TTS (VoiceOutput) instead."
        ),
    )

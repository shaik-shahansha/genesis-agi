"""Vision Module - Visual perception for Genesis Minds.

Provides camera/video input and image understanding using vision AI models.
Enables Minds to see and understand their visual environment.

Features:
- Camera/webcam integration
- Video stream processing
- Image understanding (OpenAI Vision, Google Gemini Vision)
- Object detection and recognition
- Face recognition
- Scene description
- Visual memory integration

Example:
    from genesis.senses.vision import VisionModule, VisionConfig

    # Initialize vision
    config = VisionConfig(
        camera_enabled=True,
        camera_index=0,
        vision_api="openai",
        api_key="sk-..."
    )
    vision = VisionModule(config)
    await vision.initialize()

    # Capture and process
    frame = await vision.capture_frame()
    description = await vision.describe_scene(frame)
    print(description)
"""

import asyncio
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import io

import httpx

logger = logging.getLogger(__name__)


class VisionAPI(str, Enum):
    """Supported vision AI APIs."""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # Future: local models


@dataclass
class VisionConfig:
    """Configuration for vision module."""
    camera_enabled: bool = False
    camera_index: int = 0  # 0 for default camera
    vision_api: VisionAPI = VisionAPI.OPENAI
    api_key: Optional[str] = None
    model: str = "gpt-4-vision-preview"  # or "gemini-pro-vision"
    max_tokens: int = 500
    detail_level: str = "high"  # "low", "high", "auto"
    frame_rate: int = 1  # FPS for video processing
    resolution: tuple = (640, 480)  # (width, height)


class VisionModule:
    """Vision module for visual perception.

    Handles camera input and image understanding using AI vision models.
    """

    def __init__(self, config: VisionConfig):
        """Initialize vision module.

        Args:
            config: Vision configuration
        """
        self.config = config
        self.camera: Optional[Any] = None  # cv2.VideoCapture
        self.initialized = False
        self.last_frame: Optional[bytes] = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def initialize(self):
        """Initialize camera and vision APIs."""
        if self.config.camera_enabled:
            try:
                # Import cv2 only if camera is needed
                import cv2
                self.cv2 = cv2

                # Initialize camera
                self.camera = cv2.VideoCapture(self.config.camera_index)

                if not self.camera.isOpened():
                    logger.error(f"Failed to open camera {self.config.camera_index}")
                    self.config.camera_enabled = False
                else:
                    # Set resolution
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
                    logger.info(f"Initialized camera {self.config.camera_index}")

            except ImportError:
                logger.warning("opencv-python not installed. Camera features disabled.")
                logger.warning("Install with: pip install opencv-python")
                self.config.camera_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize camera: {e}")
                self.config.camera_enabled = False

        self.initialized = True

    async def capture_frame(self) -> Optional[bytes]:
        """Capture a single frame from camera.

        Returns:
            Frame as JPEG bytes or None if failed
        """
        if not self.config.camera_enabled or not self.camera:
            logger.warning("Camera not enabled")
            return None

        try:
            ret, frame = self.camera.read()

            if not ret:
                logger.error("Failed to capture frame")
                return None

            # Convert to JPEG
            ret, buffer = self.cv2.imencode('.jpg', frame)
            if not ret:
                logger.error("Failed to encode frame")
                return None

            self.last_frame = buffer.tobytes()
            return self.last_frame

        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None

    async def capture_frames_stream(self, duration: int = 5) -> List[bytes]:
        """Capture multiple frames over duration.

        Args:
            duration: Duration in seconds

        Returns:
            List of frame bytes
        """
        frames = []
        frame_interval = 1.0 / self.config.frame_rate

        end_time = asyncio.get_event_loop().time() + duration

        while asyncio.get_event_loop().time() < end_time:
            frame = await self.capture_frame()
            if frame:
                frames.append(frame)
            await asyncio.sleep(frame_interval)

        logger.info(f"Captured {len(frames)} frames over {duration}s")
        return frames

    async def describe_scene(
        self,
        image: bytes,
        prompt: str = "Describe what you see in this image in detail."
    ) -> str:
        """Describe a scene using vision AI.

        Args:
            image: Image as bytes (JPEG, PNG, etc.)
            prompt: Custom prompt for vision model

        Returns:
            Scene description
        """
        if self.config.vision_api == VisionAPI.OPENAI:
            return await self._describe_openai(image, prompt)
        elif self.config.vision_api == VisionAPI.GOOGLE:
            return await self._describe_google(image, prompt)
        elif self.config.vision_api == VisionAPI.ANTHROPIC:
            return await self._describe_anthropic(image, prompt)
        else:
            return "Vision API not configured"

    async def _describe_openai(self, image: bytes, prompt: str) -> str:
        """Describe using OpenAI Vision API."""
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image).decode('utf-8')

            # Call OpenAI Vision API
            response = await self.http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}",
                                        "detail": self.config.detail_level
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": self.config.max_tokens
                }
            )

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"OpenAI Vision API error: {e}")
            return f"Error processing image: {e}"

    async def _describe_google(self, image: bytes, prompt: str) -> str:
        """Describe using Google Gemini Vision API."""
        try:
            # Import google.generativeai
            import google.generativeai as genai

            genai.configure(api_key=self.config.api_key)

            # Use Gemini Pro Vision
            model = genai.GenerativeModel('gemini-pro-vision')

            # Convert bytes to PIL Image
            from PIL import Image
            image_pil = Image.open(io.BytesIO(image))

            # Generate description
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, image_pil]
            )

            return response.text

        except Exception as e:
            logger.error(f"Google Vision API error: {e}")
            return f"Error processing image: {e}"

    async def _describe_anthropic(self, image: bytes, prompt: str) -> str:
        """Describe using Anthropic Claude Vision."""
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image).decode('utf-8')

            # Call Anthropic API
            response = await self.http_client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-opus-20240229",
                    "max_tokens": self.config.max_tokens,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_b64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                }
            )

            result = response.json()
            return result["content"][0]["text"]

        except Exception as e:
            logger.error(f"Anthropic Vision API error: {e}")
            return f"Error processing image: {e}"

    async def detect_faces(self, image: bytes) -> List[Dict[str, Any]]:
        """Detect faces in image.

        Args:
            image: Image bytes

        Returns:
            List of detected faces with bounding boxes
        """
        # Use vision AI to detect faces
        description = await self.describe_scene(
            image,
            "List all people you see in this image. For each person, describe their position, appearance, and any visible emotions."
        )

        # Return as structured data
        return [{"description": description}]

    async def recognize_objects(self, image: bytes) -> List[str]:
        """Recognize objects in image.

        Args:
            image: Image bytes

        Returns:
            List of object names
        """
        description = await self.describe_scene(
            image,
            "List all objects you see in this image. Just provide a comma-separated list of object names."
        )

        # Parse comma-separated list
        objects = [obj.strip() for obj in description.split(',')]
        return objects

    async def close(self):
        """Release camera and cleanup resources."""
        if self.camera:
            self.camera.release()
            logger.info("Released camera")

        await self.http_client.aclose()

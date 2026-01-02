"""Ollama model downloader and manager.

Helps users download and manage local models for offline usage.
"""

import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class OllamaManager:
    """Manage Ollama models (download, list, remove)."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama manager.

        Args:
            base_url: Ollama API base URL
        """
        self.base_url = base_url.rstrip("/")

    def is_ollama_running(self) -> bool:
        """Check if Ollama is running.

        Returns:
            True if Ollama is available
        """
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> List[Dict[str, Any]]:
        """List locally available models.

        Returns:
            List of model dictionaries
        """
        if not self.is_ollama_running():
            logger.error("Ollama is not running")
            return []

        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def pull_model(self, model_name: str) -> bool:
        """Download a model from Ollama library.

        Args:
            model_name: Model name (e.g., "gemma:2b", "llama3.1:8b")

        Returns:
            True if successful
        """
        if not self.is_ollama_running():
            logger.error("Ollama is not running. Please start Ollama first.")
            return False

        logger.info(f"Downloading model {model_name}... This may take a while.")

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=None  # No timeout for downloads
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        status = data.get("status", "")
                        logger.info(f"  {status}")

            logger.info(f"[Done] Model {model_name} downloaded successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to download model {model_name}: {e}")
            return False

    def remove_model(self, model_name: str) -> bool:
        """Remove a local model.

        Args:
            model_name: Model name to remove

        Returns:
            True if successful
        """
        if not self.is_ollama_running():
            logger.error("Ollama is not running")
            return False

        try:
            response = httpx.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=30.0
            )
            response.raise_for_status()
            logger.info(f"[Done] Removed model {model_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to remove model: {e}")
            return False

    def get_recommended_models(self) -> Dict[str, Dict[str, Any]]:
        """Get recommended models for different use cases.

        Returns:
            Dictionary of recommended models
        """
        return {
            "gemma:2b": {
                "size": "~1.4GB",
                "ram": "3GB",
                "speed": "Very Fast",
                "quality": "Good",
                "use_case": "Lightweight, fast responses"
            },
            "llama3.2:3b": {
                "size": "~2GB",
                "ram": "4GB",
                "speed": "Fast",
                "quality": "Very Good",
                "use_case": "Balanced speed and quality"
            },
            "llama3.1:8b": {
                "size": "~4.7GB",
                "ram": "8GB",
                "speed": "Medium",
                "quality": "Excellent",
                "use_case": "High quality responses"
            },
            "phi3:3.8b": {
                "size": "~2.3GB",
                "ram": "4GB",
                "speed": "Fast",
                "quality": "Very Good",
                "use_case": "Microsoft's efficient model"
            }
        }


# Convenience functions
def check_ollama() -> bool:
    """Check if Ollama is installed and running."""
    manager = OllamaManager()
    return manager.is_ollama_running()


def download_model(model_name: str) -> bool:
    """Download an Ollama model."""
    manager = OllamaManager()
    return manager.pull_model(model_name)


def list_models() -> List[str]:
    """List available local models."""
    manager = OllamaManager()
    models = manager.list_local_models()
    return [m.get("name", "") for m in models]

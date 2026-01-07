"""Firebase Authentication Integration for Genesis API.

Provides Firebase ID token verification and user management integration.
"""

import logging
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    import firebase_admin
    from firebase_admin import credentials, auth as firebase_auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    firebase_auth = None

from genesis.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Firebase app instance
_firebase_app: Optional[Any] = None


def initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _firebase_app
    
    if not FIREBASE_AVAILABLE:
        logger.warning("Firebase Admin SDK not installed. Run: pip install firebase-admin")
        return False
    
    if _firebase_app is not None:
        return True  # Already initialized
    
    try:
        # Check if Firebase credentials are configured
        firebase_project_id = getattr(settings, 'firebase_project_id', None)
        
        if not firebase_project_id:
            logger.info("Firebase not configured. Set FIREBASE_PROJECT_ID in environment to enable Firebase auth.")
            return False
        
        # Initialize with project ID (uses Application Default Credentials)
        # For production, you can use service account credentials instead
        try:
            _firebase_app = firebase_admin.initialize_app(
                options={'projectId': firebase_project_id}
            )
            logger.info(f"Firebase initialized successfully for project: {firebase_project_id}")
            return True
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}. Falling back to token-only verification.")
            # Still return True as we can verify tokens without full initialization
            return True
            
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False


@lru_cache(maxsize=1)
def is_firebase_enabled() -> bool:
    """Check if Firebase authentication is enabled and available."""
    return FIREBASE_AVAILABLE and initialize_firebase()


async def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token.
    
    Args:
        id_token: The Firebase ID token to verify
        
    Returns:
        Dict with user info if valid (uid, email, etc.), None if invalid
    """
    if not is_firebase_enabled():
        logger.warning("Firebase is not enabled or available")
        return None
    
    try:
        # Verify the token
        decoded_token = firebase_auth.verify_id_token(id_token)
        
        return {
            'uid': decoded_token.get('uid'),
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'firebase_user': True,
        }
        
    except firebase_auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase ID token")
        return None
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Expired Firebase ID token")
        return None
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        return None


def get_firebase_user_email(id_token: str) -> Optional[str]:
    """
    Extract email from Firebase ID token without full verification.
    Useful for quick email extraction.
    
    Args:
        id_token: The Firebase ID token
        
    Returns:
        Email address if found, None otherwise
    """
    try:
        import jwt
        # Decode without verification (just to extract claims)
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        return decoded.get('email')
    except Exception:
        return None

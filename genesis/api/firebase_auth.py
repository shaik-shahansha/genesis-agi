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
        
        # Initialize with project ID only (for token verification)
        # This works without service account credentials for token verification
        try:
            _firebase_app = firebase_admin.initialize_app(
                options={'projectId': firebase_project_id}
            )
            logger.info(f"Firebase initialized successfully for project: {firebase_project_id}")
            return True
        except ValueError as e:
            # ValueError usually means app already initialized
            if "already exists" in str(e):
                logger.info(f"Firebase app already initialized for project: {firebase_project_id}")
                return True
            else:
                logger.warning(f"Firebase initialization failed: {e}. Token verification may not work.")
                return False
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}. Token verification may not work.")
            # For development, try to initialize without credentials
            try:
                logger.info("Attempting Firebase initialization without credentials...")
                _firebase_app = firebase_admin.initialize_app(
                    credentials=None,
                    options={'projectId': firebase_project_id}
                )
                logger.info(f"Firebase initialized without credentials for project: {firebase_project_id}")
                return True
            except Exception as e2:
                logger.error(f"Failed to initialize Firebase even without credentials: {e2}")
                return False
            
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False


@lru_cache(maxsize=1)
def is_firebase_enabled() -> bool:
    """Check if Firebase authentication is enabled and available."""
    return FIREBASE_AVAILABLE and initialize_firebase()


async def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token using Firebase REST API.
    
    Args:
        id_token: The Firebase ID token to verify
        
    Returns:
        Dict with user info if valid (uid, email, etc.), None if invalid
    """
    print(f"DEBUG FIREBASE: verify_firebase_token called")
    print(f"DEBUG FIREBASE: Token length: {len(id_token)}")
    
    if not is_firebase_enabled():
        print("DEBUG FIREBASE: Firebase is not enabled")
        logger.warning("Firebase is not enabled or available")
        return None
    
    print("DEBUG FIREBASE: Firebase is enabled, attempting REST API verification")
    
    # Get Firebase API key from settings - MUST be set via environment variable
    firebase_api_key = getattr(settings, 'firebase_api_key', None)
    if not firebase_api_key:
        logger.error("Firebase API key not configured. Set FIREBASE_API_KEY environment variable.")
        return None
    
    try:
        import requests
        
        # Use Firebase Identity Toolkit REST API to verify token
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={firebase_api_key}'
        headers = {'Content-Type': 'application/json'}
        data = {'idToken': id_token}
        
        print(f"DEBUG FIREBASE: Making request to Firebase API")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"DEBUG FIREBASE: Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            users = result.get('users', [])
            if users:
                user_info = users[0]
                print(f"DEBUG FIREBASE: Token verified successfully")
                print(f"DEBUG FIREBASE: UID: {user_info.get('localId')}")
                print(f"DEBUG FIREBASE: Email: {user_info.get('email')}")
                
                return {
                    'uid': user_info.get('localId'),
                    'email': user_info.get('email'),
                    'email_verified': user_info.get('emailVerified', False),
                    'name': user_info.get('displayName'),
                    'picture': user_info.get('photoUrl'),
                    'firebase_user': True,
                }
        else:
            error_data = response.json()
            print(f"DEBUG FIREBASE: Token verification failed: {error_data}")
            
    except requests.exceptions.RequestException as e:
        print(f"DEBUG FIREBASE: Request error: {e}")
        logger.error(f"Error verifying Firebase token via REST API: {e}")
    except Exception as e:
        print(f"DEBUG FIREBASE: Exception during verification: {e}")
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

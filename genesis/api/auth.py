"""Authentication and authorization for Genesis API.

Provides:
- JWT token generation and validation
- Firebase ID token verification
- API key authentication
- User management
- Role-based access control
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
from enum import Enum

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

from genesis.config import get_settings
from genesis.api.firebase_auth import verify_firebase_token, is_firebase_enabled

settings = get_settings()

# Security configurations
SECRET_KEY = settings.api_secret_key if hasattr(settings, 'api_secret_key') else secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole(str, Enum):
    """User roles for access control."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    role: UserRole = UserRole.USER
    disabled: bool = False


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """JWT token payload."""
    username: Optional[str] = None
    role: Optional[str] = None


# In-memory user store (should be replaced with database in production)
# Lazy initialization to avoid hashing at import time
USERS_DB: Dict[str, Dict[str, Any]] = {}

def _initialize_default_users():
    """Initialize default users if not already done."""
    if "admin" not in USERS_DB:
        USERS_DB["admin"] = {
            "username": "admin",
            "email": "admin@genesis.local",
            "hashed_password": get_password_hash("genesis-admin-2026"),  # Default password
            "role": UserRole.ADMIN,
            "disabled": False,
        }

# In-memory API keys (should be replaced with database in production)
API_KEYS: Dict[str, Dict[str, Any]] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Truncate to 72 bytes for bcrypt limit
    plain_password_bytes = plain_password[:72].encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Truncate to 72 bytes for bcrypt limit
    password_bytes = password[:72].encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    _initialize_default_users()
    user_dict = USERS_DB.get(username)
    if not user_dict:
        return None
    if not verify_password(password, user_dict["hashed_password"]):
        return None
    return User(**user_dict)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_api_key(username: str, description: Optional[str] = None) -> str:
    """Create a new API key for a user."""
    api_key = f"gsk_{secrets.token_urlsafe(32)}"
    API_KEYS[api_key] = {
        "username": username,
        "description": description,
        "created_at": datetime.utcnow().isoformat(),
        "last_used": None,
    }
    return api_key


def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    if api_key in API_KEYS:
        del API_KEYS[api_key]
        return True
    return False


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[User]:
    """Get current user from JWT token or Firebase ID token."""
    print(f"DEBUG AUTH: get_current_user_from_token called")
    print(f"DEBUG AUTH: credentials present: {credentials is not None}")
    
    if not credentials:
        print("DEBUG AUTH: No credentials provided")
        return None

    token = credentials.credentials
    print(f"DEBUG AUTH: Token present: {token is not None}")
    print(f"DEBUG AUTH: Token length: {len(token) if token else 0}")
    print(f"DEBUG AUTH: Token starts with: {token[:50] if token and len(token) > 50 else token}")

    # First, try Firebase token verification if Firebase is enabled
    print(f"DEBUG AUTH: Checking if Firebase is enabled...")
    firebase_enabled = is_firebase_enabled()
    print(f"DEBUG AUTH: Firebase enabled result: {firebase_enabled}")
    if firebase_enabled:
        print("DEBUG AUTH: Firebase is enabled, trying Firebase token verification")
        firebase_user = await verify_firebase_token(token)
        print(f"DEBUG AUTH: Firebase user result: {firebase_user is not None}")
        if firebase_user:
            print(f"DEBUG AUTH: Firebase user email: {firebase_user.get('email')}")
            # Create or get user from Firebase data
            email = firebase_user.get('email')
            uid = firebase_user.get('uid')
            
            if email:
                # Use Firebase UID as username (prefixed to avoid collisions)
                username = f"firebase_{uid}"
                print(f"DEBUG AUTH: Using username: {username}")
                
                # Check if user exists in local DB, create if not
                _initialize_default_users()
                if username not in USERS_DB:
                    print(f"DEBUG AUTH: Creating new user: {username}")
                    # Auto-create user from Firebase
                    USERS_DB[username] = {
                        "username": username,
                        "email": email,
                        "hashed_password": "",  # No password for Firebase users
                        "role": UserRole.USER,
                        "disabled": False,
                    }
                
                user_dict = USERS_DB[username]
                # Update email in case it changed
                user_dict["email"] = email
                
                return User(**user_dict)

    # Fallback to JWT token verification
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        email: str = payload.get("email")  # Extract email from token if present

        if username is None:
            return None

        token_data = TokenData(username=username, role=role)
    except JWTError:
        return None

    _initialize_default_users()
    user_dict = USERS_DB.get(token_data.username)
    if user_dict is None:
        return None

    # If email is in token, update the user dict with it
    if email:
        user_dict = user_dict.copy()
        user_dict["email"] = email

    return User(**user_dict)


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[User]:
    """Get current user from API key."""
    if not api_key:
        return None

    key_data = API_KEYS.get(api_key)
    if not key_data:
        return None

    # Update last used timestamp
    key_data["last_used"] = datetime.utcnow().isoformat()

    username = key_data["username"]
    user_dict = USERS_DB.get(username)
    if not user_dict:
        return None

    return User(**user_dict)


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key),
) -> User:
    """
    Get current authenticated user (from JWT token or API key).

    Raises:
        HTTPException: If no valid authentication provided
    """
    user = token_user or api_key_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a valid JWT token or API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (alias for get_current_user)."""
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def require_write_access(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require write access (admin or user role)."""
    if current_user.role == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required",
        )
    return current_user


def create_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    role: UserRole = UserRole.USER,
) -> User:
    """Create a new user."""
    if username in USERS_DB:
        raise ValueError(f"User {username} already exists")

    user_dict = {
        "username": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "role": role,
        "disabled": False,
    }

    USERS_DB[username] = user_dict
    return User(**user_dict)


def delete_user(username: str) -> bool:
    """Delete a user."""
    if username in USERS_DB:
        del USERS_DB[username]
        return True
    return False


def update_user_password(username: str, new_password: str) -> bool:
    """Update user password."""
    if username not in USERS_DB:
        return False

    USERS_DB[username]["hashed_password"] = get_password_hash(new_password)
    return True


def update_user_email(username: str, email: str) -> bool:
    """Update user email."""
    if username not in USERS_DB:
        return False

    USERS_DB[username]["email"] = email
    return True


# Optional: Authentication can be disabled for development
AUTHENTICATION_ENABLED = getattr(settings, 'api_authentication_enabled', True)


async def optional_auth(
    current_user: Optional[User] = Depends(get_current_user),
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    Used when authentication is disabled for development.
    """
    if not AUTHENTICATION_ENABLED:
        # Return a default admin user when auth is disabled
        return User(username="dev", email="dev@genesis.local", role=UserRole.ADMIN)
    return current_user

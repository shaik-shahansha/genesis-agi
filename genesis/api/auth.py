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
import os
import secrets
import logging
from enum import Enum

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

from genesis.config import get_settings
from genesis.config.settings import Settings, _INSECURE_ALLOWED_ENVS
from genesis.api.firebase_auth import verify_firebase_token, is_firebase_enabled

logger = logging.getLogger(__name__)

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


#: In-memory user store (should be replaced with database in production)
#: Lazy initialization to avoid hashing at import time
USERS_DB: Dict[str, Dict[str, Any]] = {}

#: Username of the account seeded to make a fresh install reachable at all.
DEFAULT_ADMIN_USERNAME = "admin"

#: The password seeded in test/development. **Published in this repository**, so
#: it must never be usable outside those environments — see
#: `_bootstrap_admin_password`.
DEFAULT_DEV_ADMIN_PASSWORD = "genesis-admin-2026"

#: Set this to bootstrap the first admin on a real deployment.
ADMIN_PASSWORD_ENV = "GENESIS_ADMIN_PASSWORD"

#: Shortest bootstrap password accepted as real. Below this it is refused rather
#: than used, because a deliberately-configured weak secret is *more* dangerous
#: than a default: it is assumed to have been chosen carefully.
MINIMUM_ADMIN_PASSWORD_LENGTH = 12


def _bootstrap_admin_password() -> Optional[str]:
    """The password to seed the first admin with, or `None` to seed nothing.

    The rule is: an explicit configuration wins, otherwise the published
    development password is used **only** in test/development.

    This exists because the account used to be created unconditionally, in every
    environment, as a side effect of someone trying to log in. The password has
    been in this repository the whole time, so every reachable Genesis install
    had a publicly-known administrator login — the same class of mistake the
    signing-key check prevents, and invisible for the same reason: it looks like
    a convenience and behaves like a working credential.
    """
    configured = os.environ.get(ADMIN_PASSWORD_ENV, "").strip()
    if configured:
        if len(configured) < MINIMUM_ADMIN_PASSWORD_LENGTH:
            logger.error(
                "%s is set but shorter than %d characters, so no admin account has been "
                "created. A weak configured password is worse than none, because it is "
                "assumed to have been chosen deliberately. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(24))"',
                ADMIN_PASSWORD_ENV,
                MINIMUM_ADMIN_PASSWORD_LENGTH,
            )
            return None
        return configured

    if Settings.environment_name() in _INSECURE_ALLOWED_ENVS:
        return DEFAULT_DEV_ADMIN_PASSWORD

    return None


def _initialize_default_users():
    """Seed the bootstrap admin, if this environment is allowed to have one.

    Order matters and is the whole design:

      1. Already cached — done.
      2. **The database has the account** — use it and stop. The database is
         authoritative, so an operator who rotated the admin password does not
         have it silently reset to the configured value on the next restart.
      3. Otherwise seed, from `GENESIS_ADMIN_PASSWORD` or — in test/development
         only — the published development password. The row is written to the
         database, so the account is durable and rotatable like any other.

    Before, this only touched the in-memory dict: the bootstrap admin had no row,
    so it could not survive a restart on its own (it was re-derived from the
    environment) and `update_user_password("admin", ...)` failed with "no such
    user" because there was nothing to update.
    """
    if DEFAULT_ADMIN_USERNAME in USERS_DB:
        return

    existing = _persisted_user(DEFAULT_ADMIN_USERNAME)
    if existing:
        USERS_DB[DEFAULT_ADMIN_USERNAME] = existing
        return

    password = _bootstrap_admin_password()
    if password is None:
        logger.warning(
            "No admin account exists and none was created, because GENESIS_ENV=%s and "
            "%s is not set. Set %s to bootstrap the first administrator:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(24))"\n'
            "Then export it as %s and restart. Until you do, there is no account that "
            "can sign in.",
            Settings.environment_name(),
            ADMIN_PASSWORD_ENV,
            ADMIN_PASSWORD_ENV,
            ADMIN_PASSWORD_ENV,
        )
        return

    if password == DEFAULT_DEV_ADMIN_PASSWORD:
        logger.warning(
            "Seeded the development admin (%s) because GENESIS_ENV=%s. The password is "
            "published in this repository, so do not expose this process to a network.",
            DEFAULT_ADMIN_USERNAME,
            Settings.environment_name(),
        )

    email = os.environ.get("GENESIS_ADMIN_EMAIL", "admin@genesis.local").strip() or "admin@genesis.local"
    password_hash = get_password_hash(password)

    # Durable first. An admin that exists only in memory is the bug this whole
    # change is about, and for this account it was the *only* way in.
    try:
        from genesis.database.manager import MetaverseDB
        MetaverseDB().create_user_record(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=password_hash,
            email=email,
            role=UserRole.ADMIN.value,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Could not persist the bootstrap admin, so it will not survive a restart: %s",
            exc,
        )

    USERS_DB[DEFAULT_ADMIN_USERNAME] = {
        "username": DEFAULT_ADMIN_USERNAME,
        "email": email,
        "hashed_password": password_hash,
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


def invalidate_user_cache(username: str) -> None:
    """Drop a user from the process cache so the next read comes from the database.

    Needed wherever a role, email or disabled flag is changed outside this
    module — otherwise the change takes effect at the next restart and not
    before, because token resolution reads the cache.
    """
    USERS_DB.pop(username, None)


def _persisted_user(username: str) -> Optional[Dict[str, Any]]:
    """Read a user's login material from the database, or None.

    Returns the shape `USERS_DB` uses, so callers cannot tell the two apart. A
    database failure returns None rather than raising: authentication is allowed
    to fail closed, but it must not turn a transient database problem into a 500
    on the login endpoint.
    """
    try:
        from genesis.database.manager import MetaverseDB
        return MetaverseDB().get_user_credentials(username)
    except Exception as exc:  # noqa: BLE001 - any failure means "cannot authenticate"
        logger.warning("Could not read credentials for %s: %s", username, exc)
        return None


def load_user(username: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve a user, from the process cache first and the database second.

    The database is the source of truth. `USERS_DB` is only a cache in front of
    it, which is what stops a restart from signing everybody out: before this,
    the dict *was* the store, so a token issued seconds earlier stopped resolving
    the moment the process was replaced.

    A row with no credential is still returned — it carries the role and email,
    which is what token and API-key auth need. Whether it can password-authenticate
    is a separate question, answered by whether `hashed_password` is set.
    """
    if not username:
        return None

    cached = USERS_DB.get(username)
    if cached:
        return cached

    record = _persisted_user(username)
    if record is None:
        return None

    USERS_DB[username] = record
    return record


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password.

    A disabled account is refused here rather than after token issue, so a
    disabled user cannot obtain a credential at all.

    An account with no stored hash cannot password-authenticate. That is a real
    case and not an error: Firebase users have no password, and rows written by
    older builds recorded none. Previously this called bcrypt with an empty hash,
    which raises `ValueError: Invalid salt` — an unhandled 500 on the login
    endpoint for a plain wrong-username guess.
    """
    _initialize_default_users()

    user_dict = load_user(username)
    if not user_dict:
        return None

    if user_dict.get("disabled"):
        return None

    stored_hash = user_dict.get("hashed_password")
    if not stored_hash:
        return None

    if not verify_password(password, stored_hash):
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


async def resolve_user_from_token(token: str) -> Optional[User]:
    """Resolve a user from a raw JWT or Firebase ID token.

    This is the single verification path. HTTP bearer auth and WebSocket
    authentication both call it, so the two transports cannot drift apart
    (see docs/v3/SECURITY_BASELINE.md SEC-01).

    Returns None when the token is missing, malformed, expired, or belongs to an
    unknown user.
    """
    if not token:
        return None

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

                # Persist to DB for admin visibility
                try:
                    from genesis.database.manager import MetaverseDB
                    db = MetaverseDB()
                    db.create_user_record(username=username, email=email, role=UserRole.USER)
                except Exception:
                    pass

                # If email is a global admin in DB, elevate role
                try:
                    from genesis.database.manager import MetaverseDB
                    db = MetaverseDB()
                    if db.is_global_admin(email):
                        user_dict = user_dict.copy()
                        user_dict["role"] = UserRole.ADMIN
                except Exception:
                    pass

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
    user_dict = load_user(token_data.username)
    if user_dict is None:
        return None

    if user_dict.get("disabled"):
        return None

    # If email is in token, update the user dict with it
    if email:
        user_dict = user_dict.copy()
        user_dict["email"] = email

        # If email is a global admin in DB, elevate role
        try:
            from genesis.database.manager import MetaverseDB
            db = MetaverseDB()
            if db.is_global_admin(email):
                user_dict["role"] = UserRole.ADMIN
        except Exception:
            pass

    return User(**user_dict)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[User]:
    """Get current user from a JWT or Firebase ID token (HTTP bearer)."""
    if not credentials or not credentials.credentials:
        return None
    return await resolve_user_from_token(credentials.credentials)


async def resolve_user_from_api_key(api_key: str) -> Optional[User]:
    """Resolve a user from a raw API key.

    Shared by HTTP `X-API-Key` auth and WebSocket authentication.
    """
    if not api_key:
        return None

    key_data = API_KEYS.get(api_key)
    if not key_data:
        return None

    # Update last used timestamp
    key_data["last_used"] = datetime.utcnow().isoformat()

    username = key_data["username"]
    user_dict = load_user(username)
    if not user_dict or user_dict.get("disabled"):
        return None

    # If the user's email is a global admin in DB, elevate role
    try:
        from genesis.database.manager import MetaverseDB
        db = MetaverseDB()
        email = user_dict.get('email')
        if email and db.is_global_admin(email):
            user_dict = user_dict.copy()
            user_dict['role'] = UserRole.ADMIN
    except Exception:
        pass

    return User(**user_dict)


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[User]:
    """Get current user from API key (HTTP)."""
    if not api_key:
        return None
    return await resolve_user_from_api_key(api_key)


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


async def authenticate_websocket(websocket) -> Optional[User]:
    """Authenticate a WebSocket from its handshake, BEFORE the socket is accepted.

    Uses exactly the same verification as HTTP auth (``resolve_user_from_token``
    / ``resolve_user_from_api_key``) so the two transports cannot diverge.
    Fixes SEC-01, where the socket was accepted with no credential and the caller
    supplied its own identity via ``?user_email=``.

    Credential sources, tried in order:

    1. ``Authorization: Bearer <jwt>`` header
    2. ``?token=<jwt>`` query parameter (browsers cannot set WS headers)
    3. ``X-API-Key`` header, or ``?api_key=`` query parameter

    Returns None when no usable credential is present or it fails verification.
    Callers MUST treat None as unauthorized and close the handshake.

    Note: a token in a query string can be captured by access logs and browser
    history. The bundled nginx config strips query strings from access logs for
    this reason; prefer the header form for non-browser clients.
    """
    headers = websocket.headers
    query = websocket.query_params

    auth_header = headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            user = await resolve_user_from_token(token)
            if user:
                return user

    token = (query.get("token") or "").strip()
    if token:
        user = await resolve_user_from_token(token)
        if user:
            return user

    api_key = (headers.get("x-api-key") or query.get("api_key") or "").strip()
    if api_key:
        user = await resolve_user_from_api_key(api_key)
        if user:
            return user

    return None


def create_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    role: UserRole = UserRole.USER,
) -> User:
    """Create a user, durably.

    The password hash is written to the `users` row. It used to be kept only in
    the in-memory dict while the row was created without it, so the account
    existed in the database and could not sign in after a restart.

    Raises:
        ValueError: if the username is taken.
    """
    if load_user(username):
        raise ValueError(f"User {username} already exists")

    password_hash = get_password_hash(password)
    user_dict = {
        "username": username,
        "email": email,
        "hashed_password": password_hash,
        "role": role,
        "disabled": False,
    }

    # Durable first. If this fails the account must not appear to exist, because
    # an account that only lives in memory is exactly the bug being fixed here.
    from genesis.database.manager import MetaverseDB
    MetaverseDB().create_user_record(
        username=username,
        password_hash=password_hash,
        email=email,
        role=role.value if isinstance(role, UserRole) else role,
    )

    USERS_DB[username] = user_dict
    return User(**user_dict)


def delete_user(username: str) -> bool:
    """Delete a user from the database and the cache."""
    from genesis.database.manager import MetaverseDB

    removed_db = MetaverseDB().delete_user_record(username)
    removed_cache = USERS_DB.pop(username, None) is not None
    return removed_db or removed_cache


def update_user_password(username: str, new_password: str) -> bool:
    """Set a user's password, durably.

    This is also the recovery path for accounts written by an older build, which
    have a row but no credential: setting one here makes them usable again.
    """
    user_dict = load_user(username)
    if not user_dict:
        return False

    password_hash = get_password_hash(new_password)

    from genesis.database.manager import MetaverseDB
    if not MetaverseDB().set_user_password(username, password_hash):
        return False

    user_dict["hashed_password"] = password_hash
    return True



def update_user_email(username: str, email: str) -> bool:
    """Update a user's email address, durably."""
    user_dict = load_user(username)
    if not user_dict:
        return False

    from genesis.database.manager import MetaverseDB
    if not MetaverseDB().update_user_record(username, email=email):
        return False

    user_dict["email"] = email
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

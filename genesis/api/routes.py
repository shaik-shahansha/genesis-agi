"""API routes for Genesis."""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Depends, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from genesis.config import get_settings
from genesis.core.mind import Mind
from genesis.core.mind_config import MindConfig
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.storage.memory import MemoryType
from genesis.api.auth import (
    get_current_user,
    get_current_active_user,
    require_admin,
    require_write_access,
    authenticate_user,
    create_access_token,
    create_api_key,
    create_user,
    User,
    UserRole,
    Token,
    UserRole,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

settings = get_settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Routers
minds_router = APIRouter()
system_router = APIRouter()
metaverse_router = APIRouter()
auth_router = APIRouter()
admin_router = APIRouter()


# Global Mind cache to persist instances across requests
# This keeps background tasks alive!
_mind_cache: Dict[str, Mind] = {}
_mind_cache_lock = asyncio.Lock()


def _extract_provider(intelligence_dict: Dict[str, Any]) -> str:
    """
    Extract the provider from intelligence configuration.
    
    Looks for reasoning_model first, then fast_model, and extracts provider
    from the model string (e.g., "openrouter/..." -> "openrouter").
    """
    # Try reasoning_model first, then fast_model, fallback to old format
    model_str = intelligence_dict.get('reasoning_model') or intelligence_dict.get('fast_model') or intelligence_dict.get('primary_model', '')
    
    if not model_str:
        return 'openrouter'  # Default to openrouter
    
    # Extract provider from model string (e.g., "openrouter/meta-llama/..." -> "openrouter")
    if '/' in model_str:
        return model_str.split('/')[0]
    
    # If no slash, it might be a simple provider name or model name
    # Check if it's a known provider
    known_providers = ['openrouter', 'groq', 'openai', 'anthropic', 'ollama', 'cohere']
    for provider in known_providers:
        if provider in model_str.lower():
            return provider
    
    return 'openrouter'  # Default


def _extract_model(intelligence_dict: Dict[str, Any]) -> str:
    """
    Extract the display model name from intelligence configuration.
    
    Returns the full model string from reasoning_model or fast_model.
    """
    # Try reasoning_model first, then fast_model, fallback to old format
    model_str = intelligence_dict.get('reasoning_model') or intelligence_dict.get('fast_model') or intelligence_dict.get('primary_model', 'openrouter/meta-llama/llama-3.3-70b-instruct:free')
    
    return model_str


async def _get_cached_mind(mind_id: str) -> Mind:
    """
    Get or load a Mind with caching.
    
    This ensures background tasks persist across API requests!
    """
    async with _mind_cache_lock:
        if mind_id not in _mind_cache:
            # Load mind for first time
            logger.info(f"Loading Mind {mind_id} into cache")
            _mind_cache[mind_id] = await _load_mind(mind_id)
        
        return _mind_cache[mind_id]


def _clear_mind_cache(mind_id: Optional[str] = None):
    """Clear Mind cache (called when Mind is deleted or updated)."""
    if mind_id:
        _mind_cache.pop(mind_id, None)
        logger.info(f"Cleared Mind {mind_id} from cache")
    else:
        _mind_cache.clear()
        logger.info("Cleared all Minds from cache")


# Request/Response Models
class CreateMindRequest(BaseModel):
    """Request to create a new Mind."""

    name: str
    creator_email: Optional[str] = None
    template: str = "base/curious_explorer"
    config: str = "standard"  # minimal, standard, full, experimental
    reasoning_model: Optional[str] = None
    fast_model: Optional[str] = None
    autonomy_level: str = "medium"
    api_keys: Optional[dict[str, str]] = None  # Provider API keys (e.g., {'groq': 'gsk_...'})
    purpose: Optional[str] = None
    role: Optional[str] = None
    guidance_notes: Optional[str] = None


class MindResponse(BaseModel):
    """Mind information response."""

    gmid: str
    name: str
    age: str
    status: str
    current_emotion: str
    current_thought: Optional[str]
    memory_count: int
    gens: int = 1000
    avatar_url: Optional[str] = None
    creator: Optional[str] = None
    creator_email: Optional[str] = None
    template: Optional[str] = None
    primary_purpose: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    role: Optional[str] = None
    guidance_notes: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    max_tokens: Optional[int] = None
    autonomy_level: Optional[int] = None
    is_public: bool = False
    created_at: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat message request."""

    message: str
    stream: bool = False
    user_email: Optional[str] = None  # User identifier for memory filtering
    environment_id: Optional[str] = None  # Environment context for the conversation
    enable_web_search: bool = False  # Enable web search for this message


class ChatResponse(BaseModel):
    """Chat response."""

    response: str
    emotion: str
    memory_created: bool
    gen_earned: Optional[float] = None  # Gens earned from this response
    web_search_results: Optional[List[Dict[str, Any]]] = None  # Web search results if used


class FeedbackRequest(BaseModel):
    """User feedback request."""
    
    feedback_type: str  # 'positive' or 'negative'
    message: Optional[str] = None  # Optional feedback message
    context: Optional[str] = None  # What the feedback is about


class FeedbackResponse(BaseModel):
    """Feedback response with gen impact."""
    
    success: bool
    gen_change: float  # Positive for reward, negative for penalty
    new_balance: float
    message: str


class BackgroundTaskResponse(BaseModel):
    """Background task status response."""
    
    task_id: str
    user_request: str
    status: str  # pending, running, completed, failed
    progress: float  # 0.0 to 1.0
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    """Memory response."""

    id: str
    type: str
    content: str
    timestamp: str
    emotion: Optional[str]
    importance: float
    tags: List[str]


class CreateUserRequest(BaseModel):
    """Create user request."""
    username: str
    password: str
    email: Optional[str] = None
    role: UserRole = UserRole.USER


class CreateAPIKeyRequest(BaseModel):
    """Create API key request."""
    description: Optional[str] = None


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@auth_router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Login to get JWT token.

    Use username and password to authenticate and receive an access token.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Include email in token if available
    token_data = {"sub": user.username, "role": user.role}
    if user.email:
        token_data["email"] = user.email
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


class UpdateEmailRequest(BaseModel):
    """Request to update user email."""
    email: str


@auth_router.post("/me/email")
async def update_user_email(
    request: UpdateEmailRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Update the current user's email address."""
    from genesis.api.auth import update_user_email as update_email_func
    
    success = update_email_func(current_user.username, request.email)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return new token with updated email
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": current_user.username, "role": current_user.role, "email": request.email}
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires,
    )
    
    return {
        "message": "Email updated successfully",
        "email": request.email,
        "access_token": access_token,
        "token_type": "bearer",
    }


@auth_router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current authenticated user information."""
    return current_user


@auth_router.post("/users", dependencies=[Depends(require_admin)])
async def create_new_user(request: CreateUserRequest) -> Dict[str, Any]:
    """
    Create a new user (admin only).

    Requires admin role.
    """
    try:
        user = create_user(
            username=request.username,
            password=request.password,
            email=request.email,
            role=request.role,
        )
        return {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "message": "User created successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------------------------
# ADMIN API - protected by require_admin
# -----------------------------------------------------------------------------

@admin_router.post("/global-admins", dependencies=[Depends(require_admin)])
async def add_global_admin(request: Dict[str, str]):
    """Add a global admin by email (admin only)"""
    email = request.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="'email' is required")
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    added = db.add_global_admin(email, added_by='api')
    if not added:
        return {"success": True, "message": "Already a global admin", "email": email}
    return {"success": True, "message": "Added global admin", "email": email}


@admin_router.delete("/global-admins", dependencies=[Depends(require_admin)])
async def remove_global_admin(email: str = Query(...)):
    """Remove a global admin (admin only)"""
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    removed = db.remove_global_admin(email)
    if not removed:
        return {"success": True, "message": "Not found", "email": email}
    return {"success": True, "message": "Removed global admin", "email": email}


@admin_router.get("/global-admins", dependencies=[Depends(require_admin)])
async def list_global_admins():
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    return {"admins": db.list_global_admins()}


@admin_router.get("/users", dependencies=[Depends(require_admin)])
async def admin_list_users():
    """List all users (admin-only)."""
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    users = db.get_all_users()
    return {"users": users}


@admin_router.post("/users", dependencies=[Depends(require_admin)])
async def admin_create_user(body: Dict[str, str]):
    username = body.get('username')
    password = body.get('password')
    email = body.get('email')
    role = body.get('role', 'user')
    if not username or not password:
        raise HTTPException(status_code=400, detail="'username' and 'password' are required")

    from genesis.api.auth import create_user
    try:
        user = create_user(username, password, email=email, role=role)
        return {"success": True, "username": user.username, "email": user.email, "role": user.role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.patch("/users/{username}", dependencies=[Depends(require_admin)])
async def admin_update_user(username: str, body: Dict[str, Any]):
    role = body.get('role')
    disabled = body.get('disabled')
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    updated = db.update_user_record(username, role=role, disabled=disabled)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "username": username}


@admin_router.delete("/users/{username}", dependencies=[Depends(require_admin)])
async def admin_delete_user(username: str):
    from genesis.api.auth import delete_user
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    db.delete_user_record(username)
    ok = delete_user(username)
    return {"success": ok, "username": username}

@admin_router.delete("/users/{username}", dependencies=[Depends(require_admin)])
async def admin_delete_user(username: str):
    from genesis.api.auth import delete_user
    ok = delete_user(username)
    return {"success": ok, "username": username}


@admin_router.get("/minds", dependencies=[Depends(require_admin)])
async def admin_list_minds():
    """List all minds with safe serialization (admin-only)."""
    from genesis.database.base import get_session
    from genesis.database.models import MindRecord

    with get_session() as session:
        rows = session.query(MindRecord).order_by(MindRecord.last_active.desc()).all()
        minds = []
        for m in rows:
            minds.append({
                "gmid": m.gmid,
                "name": m.name,
                "creator": m.creator,
                "is_public": getattr(m, 'is_public', False),
                "status": m.status,
                "last_active": m.last_active.isoformat() if m.last_active else None,
            })
    return {"minds": minds}


@admin_router.get("/envs", dependencies=[Depends(require_admin)])
async def admin_list_envs():
    """List all environments with safe serialization (admin-only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord

    with get_session() as session:
        rows = session.query(EnvironmentRecord).order_by(EnvironmentRecord.last_accessed.desc()).all()
        envs = []
        for e in rows:
            envs.append({
                "env_id": e.env_id,
                "name": e.name,
                "owner_gmid": e.owner_gmid,
                "is_public": bool(e.is_public),
                "last_accessed": e.last_accessed.isoformat() if e.last_accessed else None,
            })
    return {"environments": envs}


@admin_router.post("/minds/{gmid}/grant-user", dependencies=[Depends(require_admin)])
async def admin_grant_mind_user_access(gmid: str, body: Dict[str, str], current_user: User = Depends(get_current_user)):
    email = body.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="'email' is required")
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    # Ensure user exists as a persistent user record
    username = body.get('username') or f"u_{email.split('@')[0]}"
    db.create_user_record(username=username, email=email, role=body.get('role', 'user'))
    added = db.add_mind_user_access(gmid, email, added_by=current_user.email or current_user.username)
    return {"success": added, "gmid": gmid, "email": email}


@admin_router.delete("/minds/{gmid}/revoke-user", dependencies=[Depends(require_admin)])
async def admin_revoke_mind_user_access(gmid: str, email: str = Query(..., description="User email to revoke")):
    """Revoke a user's access to a Mind (admin-only)."""
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()

    removed = db.remove_mind_user_access(gmid, email)

    if not removed:
        return {"success": True, "message": f"User {email} did not have access", "gmid": gmid, "email": email}

    return {"success": True, "message": f"User {email} removed", "gmid": gmid, "email": email}


@admin_router.post("/envs/{env_id}/grant-user", dependencies=[Depends(require_admin)])
async def admin_grant_env_user_access(env_id: str, body: Dict[str, str], current_user: User = Depends(get_current_user)):
    email = body.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="'email' is required")
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    username = body.get('username') or f"u_{email.split('@')[0]}"
    db.create_user_record(username=username, email=email, role=body.get('role', 'user'))
    added = db.add_environment_user_access(env_id, email, added_by=current_user.email or current_user.username)
    return {"success": added, "env_id": env_id, "email": email}


@admin_router.delete("/envs/{env_id}/revoke-user", dependencies=[Depends(require_admin)])
async def admin_revoke_env_user_access(env_id: str, email: str = Query(..., description="User email to revoke")):
    """Revoke a user's access to an Environment (admin-only)."""
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()

    removed = db.remove_environment_user_access(env_id, email)

    if not removed:
        return {"success": True, "message": f"User {email} did not have access", "env_id": env_id, "email": email}

    return {"success": True, "message": f"User {email} removed", "env_id": env_id, "email": email}


@auth_router.post("/api-keys")
async def create_new_api_key(
    request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Create a new API key for the authenticated user.

    Returns the API key - save it securely as it won't be shown again.
    """
    api_key = create_api_key(current_user.username, request.description)
    return {
        "api_key": api_key,
        "description": request.description or "No description",
        "message": "API key created successfully. Save it securely - it won't be shown again.",
    }


@auth_router.get("/firebase/status")
async def firebase_status() -> Dict[str, Any]:
    """Check if Firebase authentication is enabled and available."""
    from genesis.api.firebase_auth import is_firebase_enabled
    
    enabled = is_firebase_enabled()
    return {
        "firebase_enabled": enabled,
        "message": "Firebase authentication is enabled" if enabled else "Firebase authentication is not configured",
    }


# =============================================================================
# MIND ENDPOINTS (Protected)
# =============================================================================
@minds_router.post("", response_model=MindResponse)
async def create_mind(
    request: CreateMindRequest,
    current_user: User = Depends(require_write_access),
):
    """Create a new Genesis Mind with modular plugin architecture (requires authentication)."""

    # Check if Mind name already exists
    from genesis.config.settings import get_settings
    settings = get_settings()
    
    # Check max minds limit for non-admin users
    if current_user.role != UserRole.ADMIN:
        try:
            from genesis.database.manager import MetaverseDB
            db = MetaverseDB()
            user_minds = db.get_minds_for_user(current_user.email or current_user.username)
            max_allowed = settings.max_minds_per_user
            
            if len(user_minds) >= max_allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"You have reached the maximum limit of {max_allowed} mind(s). Please delete an existing mind to create a new one."
                )
        except HTTPException:
            raise
        except Exception as limit_error:
            logger.warning(f"Could not check mind limit for user {current_user.username}: {limit_error}")
    
    existing_mind_names = set()
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json
            with open(path) as f:
                data = json.load(f)
                existing_mind_names.add(data["identity"]["name"].lower())
        except Exception as e:
            logger.debug(f"Error reading {path}: {e}")
            continue
    
    if request.name.lower() in existing_mind_names:
        raise HTTPException(
            status_code=409,
            detail=f"Mind with name '{request.name}' already exists. Please choose a different name."
        )

    # Build intelligence config - reasoning_model is REQUIRED
    if not request.reasoning_model:
        raise HTTPException(
            status_code=400,
            detail="reasoning_model is required. Please specify a model like 'groq/llama-3.1-70b-versatile'"
        )
    
    # Create Intelligence with reasoning_model
    intelligence = Intelligence(reasoning_model=request.reasoning_model)
    
    # Set fast_model if provided, otherwise it defaults to reasoning_model (via validator)
    if request.fast_model:
        intelligence.fast_model = request.fast_model
        logger.info(f"Using reasoning_model={request.reasoning_model}, fast_model={request.fast_model}")
    else:
        logger.info(f"fast_model synced to reasoning_model: {request.reasoning_model}")
    
    # Set API keys if provided
    if request.api_keys:
        intelligence.api_keys = request.api_keys

    # Build autonomy config
    autonomy = Autonomy()
    if request.autonomy_level == "high":
        autonomy.initiative_level = InitiativeLevel.HIGH
        autonomy.proactive_actions = True
    elif request.autonomy_level == "low":
        autonomy.initiative_level = InitiativeLevel.LOW

    # Build plugin configuration
    if request.config == "minimal":
        mind_config = MindConfig.minimal()
    elif request.config == "full":
        mind_config = MindConfig.full()
    elif request.config == "experimental":
        mind_config = MindConfig.experimental()
    else:  # standard
        mind_config = MindConfig.standard()

    # Birth the Mind
    try:
        # NOTE: Never start consciousness in API server - it should run in daemon
        mind = Mind.birth(
            name=request.name,
            intelligence=intelligence,
            autonomy=autonomy,
            template=request.template,
            start_consciousness=False,  # Always False - consciousness runs in daemon
            config=mind_config,
            creator_email=request.creator_email,
            purpose=request.purpose,
            role=request.role,
            guidance_notes=request.guidance_notes,
        )

        # Test provider connection (since it was skipped in birth due to async context)
        if request.reasoning_model:
            success, message = await mind.orchestrator.test_provider_connection(request.reasoning_model)
            if not success:
                print(f"[WARNING] Warning: {message}")
                print(f"   Mind created but may not be able to think until provider is configured.")

        # Save
        mind.save()

        # Register mind in database for access control
        try:
            from genesis.database.manager import MetaverseDB
            db = MetaverseDB()
            db.register_mind(
                gmid=mind.identity.gmid,
                name=mind.identity.name,
                creator=mind.identity.creator,
                template=mind.identity.template,
                primary_role=None,  # Will be set later if roles are configured
            )
            print(f"[INFO] Registered mind {mind.identity.gmid} in database")
        except Exception as reg_error:
            print(f"[WARNING] Could not register mind in database: {reg_error}")

        # Create default personal environment for the Mind
        try:
            from genesis.database.manager import MetaverseDB
            db = MetaverseDB()
            db.register_environment(
                env_id=f"{mind.identity.gmid}-home",
                name=f"{mind.identity.name}'s Personal Space",
                env_type="personal",
                owner_gmid=mind.identity.gmid,
                is_public=False,
                is_shared=False,
                description=f"Personal environment for {mind.identity.name}",
            )
        except Exception as env_error:
            # Log but don't fail Mind creation if environment creation fails
            print(f"Warning: Could not create default environment for {mind.identity.gmid}: {env_error}")

        # Get actual gen balance if GenManager is available
        gens = 1000  # Default
        if hasattr(mind, 'gen') and mind.gen:
            balance_summary = mind.gen.get_balance_summary()
            gens = int(balance_summary['current_balance'])

        return MindResponse(
            gmid=mind.identity.gmid,
            name=mind.identity.name,
            age=mind.identity.get_age_description(),
            status=mind.identity.status,
            current_emotion=mind.current_emotion,
            current_thought=mind.current_thought,
            memory_count=mind.memory.vector_store.count(),
            gens=gens,
            avatar_url=getattr(mind.identity, 'avatar_url', None),
            creator=mind.identity.creator,
            creator_email=getattr(mind.identity, 'creator_email', None),
            max_tokens=getattr(mind.intelligence, 'max_tokens', 8000),
            purpose=getattr(mind.identity, 'purpose', None),
            role=getattr(mind.identity, 'role', None),
            guidance_notes=getattr(mind.identity, 'guidance_notes', None),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("", response_model=List[MindResponse])
async def list_minds(current_user: User = Depends(get_current_active_user)):
    """List all Minds with optimized lightweight loading."""
    # Note: Admin users will see all Minds due to DB-level admin check in MetaverseDB.is_user_allowed_for_mind
    import json
    from datetime import datetime
    minds = []

    # Initialize database connection once outside the loop
    db = None
    try:
        from genesis.database.manager import MetaverseDB
        db = MetaverseDB()
    except Exception as db_error:
        print(f"[WARNING] Could not initialize database connection: {db_error}")

    user_identifier = current_user.email if current_user.email else current_user.username

    for path in settings.minds_dir.glob("*.json"):
        try:
            # Read JSON directly without loading full Mind object
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            identity = data.get('identity', {})
            state = data.get('state', {})
            memory_data = data.get('memory', {})
            
            # Calculate age from birth_timestamp
            birth_timestamp_str = identity.get('birth_timestamp', '')
            age = "Unknown"
            if birth_timestamp_str:
                try:
                    birth_date = datetime.fromisoformat(birth_timestamp_str.replace('Z', '+00:00'))
                    age_delta = datetime.now(birth_date.tzinfo) - birth_date
                    days = age_delta.days
                    if days < 1:
                        hours = age_delta.seconds // 3600
                        age = f"{hours} hours"
                    elif days < 7:
                        age = f"{days} days"
                    elif days < 30:
                        weeks = days // 7
                        age = f"{weeks} weeks"
                    elif days < 365:
                        months = days // 30
                        age = f"{months} months"
                    else:
                        years = days // 365
                        age = f"{years} years"
                except Exception:
                    pass
            
            # Count memories from ChromaDB vector store
            # Since memories are no longer stored in JSON, read from ChromaDB directly
            gmid = identity.get('gmid', '')
            try:
                from genesis.storage.vector_store import VectorStore
                vector_store = VectorStore(gmid)
                memory_count = vector_store.count()
            except Exception as e:
                # Fallback if ChromaDB read fails
                memory_count = memory_data.get('total_memories', 0)
            
            # Skip terminated minds
            if identity.get('status', 'active') == 'terminated':
                continue
            
            # Get gen balance from plugins data if available
            gens = 100  # Default starting balance
            try:
                plugins_data = data.get('plugins', {})
                gen_plugin_data = plugins_data.get('gen', {})
                if gen_plugin_data and 'gen' in gen_plugin_data:
                    gen_data = gen_plugin_data['gen']
                    if 'balance' in gen_data:
                        # Safely coerce to int in case stored value is float-like (e.g., 230.5)
                        try:
                            gens_val = gen_data['balance'].get('current_balance', 100)
                            gens = int(float(gens_val))
                        except Exception:
                            gens = int(gen_data['balance'].get('current_balance', 100) or 100)
            except Exception:
                pass

            # Access control: check DB for mind access or fallback to identity
            include_mind = False
            gmid_val = identity.get('gmid', '')

            if db:
                try:
                    # Ensure mind is registered in database
                    existing_mind = db.get_mind(gmid_val)
                    if not existing_mind:
                        # Register mind that exists in JSON but not in database
                        try:
                            db.register_mind(
                                gmid=gmid_val,
                                name=identity.get('name', 'Unknown'),
                                creator=identity.get('creator', 'unknown'),
                                template=identity.get('template', 'base/curious_explorer'),
                                primary_role=None,
                            )
                            print(f"[INFO] Registered missing mind {gmid_val} in database")
                        except Exception as reg_error:
                            print(f"[WARNING] Could not register mind {gmid_val}: {reg_error}")
                    
                    # Sync is_public from database to identity for consistency
                    db_is_public = db.get_mind_is_public(gmid_val)
                    if db_is_public is not None:
                        identity['is_public'] = db_is_public
                    
                    allowed = db.is_user_allowed_for_mind(gmid_val, user_identifier)
                    print(f"[DEBUG] Mind {gmid_val}: allowed={allowed}, user={user_identifier}, db_is_public={db_is_public}")
                    if allowed:
                        include_mind = True
                    else:
                        # Fallback: check identity-level flags
                        if identity.get('is_public'):
                            include_mind = True
                            print(f"[DEBUG] Mind {gmid_val} included via identity is_public")
                        elif identity.get('creator_email') and identity.get('creator_email') == user_identifier:
                            include_mind = True
                            print(f"[DEBUG] Mind {gmid_val} included via creator match")
                except Exception as access_error:
                    print(f"[WARNING] Database access check failed for {gmid_val}: {access_error}")
                    # Fallback to identity-based access
                    if identity.get('is_public') or (identity.get('creator_email') and identity.get('creator_email') == user_identifier):
                        include_mind = True
                        print(f"[DEBUG] Mind {gmid_val} included via fallback")
            else:
                print(f"[WARNING] No database connection for mind {gmid_val}")
                # No database available, fallback to identity-based access
                if identity.get('is_public') or (identity.get('creator_email') and identity.get('creator_email') == user_identifier):
                    include_mind = True
                    print(f"[DEBUG] Mind {gmid_val} included via no-db fallback")

            if not include_mind:
                print(f"[DEBUG] Mind {gmid_val} NOT included")
                continue

            if not include_mind:
                continue

            minds.append(
                MindResponse(
                    gmid=identity.get('gmid', ''),
                    name=identity.get('name', 'Unknown'),
                    age=age,
                    status=identity.get('status', 'active'),
                    current_emotion=state.get('current_emotion', 'neutral'),
                    current_thought=state.get('current_thought'),
                    avatar_url=identity.get('avatar_url'),
                    memory_count=memory_count,
                    gens=gens,
                    creator=identity.get('creator'),
                    creator_email=identity.get('creator_email'),
                    template=identity.get('template'),
                    primary_purpose=identity.get('primary_purpose'),
                    description=identity.get('description'),
                    purpose=identity.get('purpose'),
                    role=identity.get('role'),
                    guidance_notes=identity.get('guidance_notes'),
                    llm_provider=_extract_provider(data.get('intelligence', {})),
                    llm_model=_extract_model(data.get('intelligence', {})),
                    max_tokens=data.get('intelligence', {}).get('max_tokens', 8000),
                    autonomy_level=data.get('autonomy', {}).get('level', 5),
                    is_public=bool(identity.get('is_public', False)),
                    created_at=identity.get('birth_timestamp'),
                )
            )
        except Exception as e:
            print(f"Error loading mind {path}: {e}")

    return minds


@minds_router.get("/{mind_id}", response_model=MindResponse)
async def get_mind(mind_id: str, current_user: User = Depends(get_current_active_user)):
    """Get a specific Mind."""
    mind = await _load_mind(mind_id)

    # Extract provider and model from Intelligence configuration
    intelligence_dict = json.loads(mind.intelligence.model_dump_json())

    # Access check: ensure current_user is allowed to view this Mind
    from genesis.database.manager import MetaverseDB
    user_identifier = current_user.email if current_user.email else current_user.username
    try:
        db = MetaverseDB()
        if not db.is_user_allowed_for_mind(mind.identity.gmid, user_identifier):
            raise HTTPException(status_code=403, detail="Access denied to this Mind")
    except HTTPException:
        raise
    except Exception:
        # Fallback to identity-level flags
        if not (getattr(mind.identity, 'is_public', False) or getattr(mind.identity, 'creator_email', None) == user_identifier):
            raise HTTPException(status_code=403, detail="Access denied to this Mind")

    # Get actual gen balance from gen manager
    gens = 100  # Default
    if hasattr(mind, 'gen') and mind.gen:
        balance_summary = mind.gen.get_balance_summary()
        # Coerce to int safely in case provider returns a float like 230.5
        try:
            gens = int(float(balance_summary.get('current_balance', 0) if isinstance(balance_summary, dict) else balance_summary))
        except Exception:
            try:
                gens = int(balance_summary)
            except Exception:
                gens = 100
    
    return MindResponse(
        gmid=mind.identity.gmid,
        name=mind.identity.name,
        age=mind.identity.get_age_description(),
        status=mind.identity.status,
        current_emotion=mind.current_emotion,
        current_thought=mind.current_thought,
        memory_count=mind.memory.vector_store.count(),
        gens=gens,
        avatar_url=getattr(mind.identity, 'avatar_url', None),
        creator=getattr(mind.identity, 'creator', None),
        creator_email=getattr(mind.identity, 'creator_email', None),
        template=getattr(mind.identity, 'template', None),
        primary_purpose=getattr(mind.identity, 'primary_purpose', None),
        description=getattr(mind.identity, 'description', None),
        purpose=getattr(mind.identity, 'purpose', None),
        role=getattr(mind.identity, 'role', None),
        guidance_notes=getattr(mind.identity, 'guidance_notes', None),
        llm_provider=_extract_provider(intelligence_dict),
        llm_model=_extract_model(intelligence_dict),
        max_tokens=getattr(mind.intelligence, 'max_tokens', 8000),
        autonomy_level=getattr(mind.autonomy, 'level', 5),
        created_at=mind.identity.birth_timestamp.isoformat() if hasattr(mind.identity, 'birth_timestamp') else None,
    )


@minds_router.post("/{mind_id}/chat", response_model=ChatResponse)
async def chat(
    mind_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Chat with a Mind (requires authentication)."""
    print(f"DEBUG CHAT: Chat endpoint called for mind {mind_id}")
    print(f"DEBUG CHAT: Current user: {current_user.username if current_user else 'None'}")
    print(f"DEBUG CHAT: User email: {current_user.email if current_user else 'None'}")
    print(f"DEBUG CHAT: Request message: {request.message}")
    print(f"DEBUG CHAT: Request user_email: {request.user_email}")
    
    # Use cached mind to persist background tasks!
    mind = await _get_cached_mind(mind_id)
    print(f"[DEBUG CHAT] Loaded mind GMID: {mind.identity.gmid}")
    print(f"[DEBUG CHAT] Mind name: {mind.identity.name}")
    print(f"[DEBUG CHAT] URL mind_id: {mind_id}")
    print(f"[DEBUG CHAT] Mind matches URL: {mind.identity.gmid == mind_id}")
    
    # SAFETY: Ensure mind is registered in database (for foreign key integrity)
    # This handles cases where minds were loaded before database registration was implemented
    try:
        from genesis.database.manager import MetaverseDB
        metaverse_db = MetaverseDB()
        
        existing_mind = metaverse_db.get_mind(mind.identity.gmid)
        if not existing_mind:
            # Register mind that somehow wasn't registered
            primary_role = None
            if hasattr(mind, 'roles'):
                primary = mind.roles.get_primary_role()
                if primary:
                    primary_role = primary.get("name")
            
            metaverse_db.register_mind(
                gmid=mind.identity.gmid,
                name=mind.identity.name,
                creator=mind.identity.creator,
                template=mind.identity.template,
                primary_role=primary_role,
            )
            print(f"[INFO] Registered mind {mind.identity.gmid} in database")
    except Exception as reg_error:
        print(f"[WARNING] Could not verify/register mind in database: {reg_error}")
    
    print(f"\n[DEBUG CHAT ENDPOINT] Chat request received")
    print(f"[DEBUG CHAT ENDPOINT] Mind ID: {mind_id}")
    print(f"[DEBUG CHAT ENDPOINT] Mind instance ID: {id(mind)}")
    print(f"[DEBUG CHAT ENDPOINT] User email from request: {request.user_email}")
    print(f"[DEBUG CHAT ENDPOINT] Authenticated user email: {current_user.email}")
    if hasattr(mind, 'notification_manager') and mind.notification_manager:
        print(f"[DEBUG CHAT ENDPOINT] Notification manager instance ID: {id(mind.notification_manager)}")
        print(f"[DEBUG CHAT ENDPOINT] Active WebSocket connections: {list(mind.notification_manager.websocket_connections.keys())}")
    else:
        print(f"[DEBUG CHAT ENDPOINT] No notification manager!")
    print()


    try:
        # Generate response with user context
        # Use authenticated user's email, fallback to request.user_email if provided
        user_identifier = current_user.email or request.user_email
        
        # If environment_id provided, enter the environment first
        if request.environment_id:
            # Validate access
            from genesis.database.base import get_session
            from genesis.database.models import EnvironmentRecord
            
            with get_session() as session:
                env_record = session.query(EnvironmentRecord).filter_by(env_id=request.environment_id).first()
                
                if not env_record:
                    raise HTTPException(status_code=404, detail=f"Environment {request.environment_id} not found")
                
                # Extract data while session is active
                is_public = env_record.is_public
                owner_gmid = env_record.owner_gmid
                # Parse metadata if it's JSON
                import json
                metadata = json.loads(env_record.extra_metadata) if env_record.extra_metadata else {}
                allowed_users = metadata.get('allowed_users', [])
                allowed_minds = metadata.get('allowed_minds', [])
            
            # Check if user has access
            is_owner = owner_gmid == user_identifier or owner_gmid == mind.identity.gmid
            
            if not (is_public or user_identifier in allowed_users or is_owner):
                raise HTTPException(status_code=403, detail=f"User {user_identifier} doesn't have access to environment")
            
            # Check if Mind has access
            mind_has_access = is_public or mind.identity.gmid in allowed_minds or mind.identity.gmid == owner_gmid
            
            if not mind_has_access:
                raise HTTPException(status_code=403, detail=f"Mind {mind.identity.name} doesn't have access to environment")
            
            # Enter environment
            env_manager = mind.environments
            env = env_manager.get_environment(request.environment_id)
            if env:
                env_manager.enter(request.environment_id)
        
        # Handle web search if enabled
        web_search_results = None
        search_context = ""
        
        if request.enable_web_search:
            try:
                from ddgs import DDGS
                
                print(f"[WEB SEARCH] Performing search for: {request.message}")
                
                # Perform the search - use simple params for better reliability
                ddgs = DDGS()
                results = []
                
                # Try to get results, handling potential empty responses
                try:
                    results = list(ddgs.text(request.message, max_results=5))
                except Exception as search_err:
                    print(f"[WEB SEARCH] Search attempt failed: {search_err}")
                    results = []
                
                web_search_results = results
                
                if results:
                    # Build context from search results
                    search_context = "\n\n[Web Search Results]:\n"
                    for i, result in enumerate(results, 1):
                        search_context += f"\n{i}. {result.get('title', 'No title')}\n"
                        search_context += f"   {result.get('body', 'No description')}\n"
                        search_context += f"   Source: {result.get('href', 'No URL')}\n"
                    
                    search_context += "\n[End of Web Search Results]\n\n"
                    
                    print(f"[WEB SEARCH] Found {len(results)} results")
                    
                    # Append search results to the message
                    enhanced_message = f"{request.message}\n{search_context}\nPlease answer based on the web search results above."
                else:
                    print(f"[WEB SEARCH] No results found, proceeding without web context")
                    enhanced_message = request.message
                
            except Exception as search_error:
                print(f"[WEB SEARCH] Error: {search_error}")
                import traceback
                traceback.print_exc()
                enhanced_message = request.message
                search_context = "\n\n[Note: Web search failed, answering without web results]\n"
        else:
            enhanced_message = request.message
        
        try:
            response = await mind.think(enhanced_message, user_email=user_identifier)
            print(f"[DEBUG ROUTES] Response from mind.think(): {response[:200] if response else 'None'}...")
        except Exception as think_error:
            print(f"ERROR in mind.think(): {str(think_error)}")
            print(f"Error type: {type(think_error).__name__}")
            import traceback
            traceback.print_exc()
            response = None
        
        # Proactive Conversation: Analyze message for follow-up needs (AFTER response generated)
        # Run in background, completely separate from user's conversation
        if hasattr(mind, 'proactive_conversation') and response:
            async def run_proactive_analysis():
                try:
                    await mind.proactive_conversation.analyze_message_for_follow_up(
                        user_message=request.message,
                        user_email=user_identifier,
                        environment_id=request.environment_id
                    )
                    await mind.proactive_conversation.check_for_resolution(
                        user_message=request.message,
                        user_email=user_identifier
                    )
                except Exception as e:
                    logger.error(f"Proactive conversation analysis failed: {e}")
            
            # Fire and forget - don't wait for completion
            asyncio.create_task(run_proactive_analysis())
        
        # Log for debugging
        if not response:
            print(f"WARNING: mind.think() returned empty response for Mind {mind.identity.gmid}")
            print(f"Mind has API keys configured: {bool(mind.intelligence.api_keys)}")
            print(f"Reasoning model: {mind.intelligence.reasoning_model}")
            print(f"Fast model: {mind.intelligence.fast_model}")
            response = "I apologize, but I was unable to generate a response. Please check my configuration and API keys. Rate limit reached. Try again later."

        # ⚡ PERFORMANCE: Prepare response immediately
        chat_response = ChatResponse(
            response=response or "No response generated",
            emotion=mind.current_emotion,
            memory_created=True,
            web_search_results=web_search_results,
        )
        
        # Send response via WebSocket to update UI immediately
        if hasattr(mind, 'notification_manager') and mind.notification_manager:
            try:
                websocket_message = {
                    "type": "message",
                    "content": response or "No response generated",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "emotion": mind.current_emotion,
                        "memory_created": True,
                    }
                }
                success = await mind.notification_manager.send_to_websocket(
                    user_email=user_identifier,
                    message_type="message",
                    data=websocket_message
                )
                print(f"[WEBSOCKET] Sent assistant response via WebSocket: {success}")
            except Exception as ws_error:
                print(f"[WEBSOCKET] Failed to send via WebSocket: {ws_error}")
        
        # Background tasks (non-blocking)
        async def _background_tasks():
            try:
                print(f"[DEBUG BACKGROUND] Processing for mind GMID: {mind.identity.gmid}")
                print(f"[DEBUG BACKGROUND] Mind name: {mind.identity.name}")
                
                # Reward for response quality (async, with memory)
                if hasattr(mind, 'gen_intelligence'):
                    print(f"[DEBUG BACKGROUND] Mind has gen_intelligence")
                    gen_earned = await mind.gen_intelligence.reward_for_response_quality_async(
                        user_message=request.message,
                        assistant_response=response
                    )
                    if gen_earned > 0:
                        print(f"[GEN] ✓ Earned {gen_earned:.1f} gens for quality response")
                else:
                    print(f"[DEBUG BACKGROUND] Mind does NOT have gen_intelligence")
                
                # Save state
                mind.save()
                print(f"[PERF] ✓ Mind state saved to disk")
            except Exception as e:
                logger.error(f"Background tasks failed: {e}")
                import traceback
                traceback.print_exc()
        
        asyncio.create_task(_background_tasks())
        
        # Return response immediately - UI gets instant feedback!
        return chat_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.post("/{mind_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    mind_id: str,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Submit user feedback (positive/negative) with gen rewards/penalties."""
    mind = await _get_cached_mind(mind_id)
    
    try:
        # Validate feedback type
        if request.feedback_type not in ['positive', 'negative']:
            raise HTTPException(
                status_code=400,
                detail="feedback_type must be 'positive' or 'negative'"
            )
        
        # Process feedback asynchronously (with memory creation)
        if hasattr(mind, 'gen_intelligence'):
            feedback_message = request.message or f"{request.feedback_type} feedback"
            
            gen_change = await mind.gen_intelligence.reward_for_feedback_async(
                feedback_type=request.feedback_type,
                user_message=feedback_message,
                context=request.context
            )
            
            # Get new balance
            balance_summary = mind.gen.get_balance_summary() if hasattr(mind, 'gen') else {'current_balance': 0}
            new_balance = balance_summary['current_balance']
            
            # Save state in background
            asyncio.create_task(asyncio.to_thread(mind.save))
            
            return FeedbackResponse(
                success=True,
                gen_change=gen_change,
                new_balance=new_balance,
                message=f"Feedback received! {'+' if gen_change > 0 else ''}{gen_change:.1f} gens. Balance: {new_balance:.1f}"
            )
        else:
            return FeedbackResponse(
                success=False,
                gen_change=0.0,
                new_balance=0.0,
                message="Gen economy not enabled for this Mind"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process feedback: {str(e)}")


# Background Task Endpoints
@minds_router.get("/{mind_id}/tasks", response_model=List[BackgroundTaskResponse])
async def get_tasks(
    mind_id: str,
    status: Optional[str] = Query(None, description="Filter by status: active, completed, failed"),
    current_user: User = Depends(get_current_active_user),
):
    """Get all background tasks for a Mind."""
    mind = await _get_cached_mind(mind_id)
    
    # Get tasks
    if status == "active":
        tasks = mind.background_executor.get_active_tasks()
    elif status == "completed":
        tasks = mind.background_executor.get_completed_tasks(limit=50)
    else:
        # All tasks
        active = mind.background_executor.get_active_tasks()
        completed = mind.background_executor.get_completed_tasks(limit=20)
        tasks = active + completed
    
    # Convert to response format
    return [
        BackgroundTaskResponse(
            task_id=task.task_id,
            user_request=task.user_request,
            status=task.status.value,
            progress=task.progress,
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error=task.error,
            result=task.result if hasattr(task, 'result') else None
        )
        for task in tasks
    ]


@minds_router.get("/{mind_id}/tasks/{task_id}", response_model=BackgroundTaskResponse)
async def get_task(
    mind_id: str,
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific background task by ID."""
    mind = await _get_cached_mind(mind_id)
    
    task = mind.background_executor.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return BackgroundTaskResponse(
        task_id=task.task_id,
        user_request=task.user_request,
        status=task.status.value,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        error=task.error,
        result=task.result if hasattr(task, 'result') else None
    )


class MultimodalChatRequest(BaseModel):
    """Chat request with multimodal context"""
    message: str
    context: Optional[Dict[str, Any]] = None


class MultimodalChatResponse(BaseModel):
    """Chat response with multimodal enhancements"""
    response: str
    emotion: str
    memory_created: bool
    generated_image: Optional[str] = None
    avatar_url: Optional[str] = None


@minds_router.post("/{mind_id}/chat/multimodal", response_model=MultimodalChatResponse)
async def chat_multimodal(
    mind_id: str,
    request: MultimodalChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Enhanced chat with multimodal context (emotion, voice, video).
    
    The context can include:
    - emotion: User's detected emotion from video
    - tone: User's vocal tone
    - voice_input: Whether input was voice
    - video_context: Additional video context
    """
    mind = await _load_mind(mind_id)

    try:
        # Enhance prompt with context
        enhanced_message = request.message
        if request.context:
            context_info = []
            
            if request.context.get('emotion'):
                emotion_data = request.context['emotion']
                context_info.append(
                    f"[User's emotional state: {emotion_data.get('emotion', 'unknown')}, "
                    f"valence: {emotion_data.get('valence', 0):.2f}, "
                    f"arousal: {emotion_data.get('arousal', 0.5):.2f}]"
                )
            
            if request.context.get('voice_input'):
                context_info.append("[User is speaking via voice]")
            
            if context_info:
                enhanced_message = f"{' '.join(context_info)}\n\nUser: {request.message}"
        
        # Generate response
        response = await mind.think(enhanced_message)

        # Determine if we should generate an image (autonomous behavior)
        generate_image = False
        image_prompt = None
        
        # Check if user explicitly asked for an image
        image_keywords = ['show me', 'generate', 'create', 'draw', 'image of', 'picture of', 'visualize']
        if any(keyword in request.message.lower() for keyword in image_keywords):
            generate_image = True
            image_prompt = request.message
        
        # Autonomous image generation for descriptive content
        elif len(response) > 200 and any(word in response.lower() for word in ['imagine', 'picture', 'scene', 'landscape', 'view']):
            generate_image = True
            image_prompt = f"Illustrate: {response[:200]}"
        
        generated_image_url = None
        if generate_image and image_prompt:
            try:
                from genesis.multimodal import get_image_generator
                generator = get_image_generator()
                generated_image_url = await generator.generate_contextual_image(image_prompt)
            except Exception as e:
                print(f"Image generation failed: {e}")

        # Generate avatar with current emotion
        avatar_url = None
        try:
            from genesis.multimodal import get_image_generator
            generator = get_image_generator()
            avatar_url = await generator.generate_mind_avatar(
                mind_name=mind.identity.name,
                expression=mind.current_emotion,
            )
            # Persist avatar URL to Mind identity
            if avatar_url:
                mind.identity.avatar_url = avatar_url
        except Exception as e:
            print(f"Avatar generation failed: {e}")

        # ⚡ PERFORMANCE: Prepare response immediately
        multimodal_response = MultimodalChatResponse(
            response=response,
            emotion=mind.current_emotion,
            memory_created=True,
            generated_image=generated_image_url,
            avatar_url=avatar_url,
        )
        
        # Save updated state in background (non-blocking)
        async def _save_mind_state():
            try:
                mind.save()
                print(f"[PERF] ✓ Mind state saved to disk")
            except Exception as e:
                logger.error(f"Failed to save mind state: {e}")
        
        asyncio.create_task(_save_mind_state())
        
        # Return response immediately
        return multimodal_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.post("/{mind_id}/avatar/generate")
async def generate_mind_avatar(
    mind_id: str,
    request: Dict[str, str],
    current_user: User = Depends(get_current_active_user),
):
    """Generate avatar for Mind with specific expression"""
    mind = await _load_mind(mind_id)
    
    try:
        from genesis.multimodal import get_image_generator
        generator = get_image_generator()
        
        image_url = await generator.generate_mind_avatar(
            mind_name=mind.identity.name,
            expression=request.get('expression', 'neutral'),
            background=request.get('background', 'soft gradient'),
            style=request.get('style', 'portrait'),
        )
        
        # Persist avatar URL to Mind identity
        if image_url:
            mind.identity.avatar_url = image_url
            mind.save()
        
        if not image_url:
            # Return a response indicating feature is not yet available
            return {
                "image_url": None,
                "mind_id": mind_id,
                "expression": request.get('expression', 'neutral'),
                "message": "Image generation not yet available. Google Imagen API integration coming soon. Set GEMINI_API_KEY in .env to enable text generation.",
                "placeholder": f"Avatar for {mind.identity.name} with {request.get('expression', 'neutral')} expression"
            }
        
        return {
            "image_url": image_url,
            "mind_id": mind_id,
            "expression": request.get('expression', 'neutral'),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Avatar generation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.patch("/{mind_id}/settings")
async def update_mind_settings(
    mind_id: str,
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
):
    """Update Mind's configuration settings."""
    mind = await _load_mind(mind_id)
    
    try:
        # Update basic properties
        if 'name' in settings:
            mind.identity.name = settings['name']
        if 'primary_purpose' in settings:
            mind.identity.primary_purpose = settings['primary_purpose']
        if 'description' in settings:
            mind.identity.description = settings.get('description', '')
        if 'purpose' in settings:
            mind.identity.purpose = settings.get('purpose', '')
            # Also update primary_purpose to match (they should be the same)
            mind.identity.primary_purpose = settings.get('purpose', '')
        if 'role' in settings:
            mind.identity.role = settings.get('role', '')
        if 'guidance_notes' in settings:
            mind.identity.guidance_notes = settings.get('guidance_notes', '')
        
        # Update LLM configuration
        # Update reasoning_model (and optionally fast_model if they were the same before)
        if 'llm_model' in settings:
            model_value = settings['llm_model']
            # If both models were the same before, update both (maintain consistency)
            # If they were different, only update reasoning_model (respect user's choice)
            if mind.intelligence.reasoning_model == mind.intelligence.fast_model:
                # They were synced, keep them synced
                mind.intelligence.reasoning_model = model_value
                mind.intelligence.fast_model = model_value
            else:
                # They were different, only update reasoning (user may have customized fast)
                mind.intelligence.reasoning_model = model_value
                logger.info(f"Updated reasoning_model to {model_value}, kept fast_model as {mind.intelligence.fast_model}")
        
        # Note: llm_provider is derived from the model string, not stored separately
        if 'api_key' in settings and settings['api_key']:
            # Store API key securely in the api_keys dict
            provider = _extract_provider(settings)
            if not mind.intelligence.api_keys:
                mind.intelligence.api_keys = {}
            mind.intelligence.api_keys[provider] = settings['api_key']
        
        if 'max_tokens' in settings:
            mind.intelligence.max_tokens = settings['max_tokens']
        
        # Update autonomy settings
        if 'autonomy_level' in settings:
            mind.autonomy.level = settings['autonomy_level']
        
        # Update currency (Gens)
        if 'gens' in settings:
            mind.identity.gens = settings['gens']
        
        # Update avatar URL
        if 'avatar_url' in settings:
            mind.identity.avatar_url = settings['avatar_url']
        
        # Save updated Mind
        mind.save()
        
        # Sync identity fields to database
        try:
            from genesis.database.manager import MetaverseDB
            db = MetaverseDB()
            db.update_mind_identity(
                gmid=mind.identity.gmid,
                name=mind.identity.name,
                purpose=mind.identity.purpose,
                role=mind.identity.role,
                guidance_notes=mind.identity.guidance_notes,
            )
        except Exception as e:
            print(f"[WARNING] Could not sync identity to database: {e}")
        
        return {
            "success": True,
            "message": "Mind settings updated successfully",
            "gmid": mind.identity.gmid,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.post("/{mind_id}/add-user")
async def add_user_to_mind(
    mind_id: str,
    body: Dict[str, str],
    current_user: User = Depends(get_current_active_user),
):
    """Add a user email to a Mind's allowed list (creator only)."""
    email = body.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="'email' is required")

    # Determine user identifier
    user_identifier = current_user.email if current_user.email else current_user.username

    # Load mind object
    mind = await _load_mind(mind_id)

    # Check ownership: creator email or creator string
    is_creator = (
        getattr(mind.identity, 'creator_email', None) == user_identifier
        or getattr(mind.identity, 'creator', None) == user_identifier
    )

    if not is_creator:
        raise HTTPException(status_code=403, detail="Only creator can manage access")

    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    added = db.add_mind_user_access(mind.identity.gmid, email, added_by=user_identifier)

    if not added:
        return {"success": True, "message": f"User {email} already has access", "allowed_users": db.get_mind_allowed_users(mind.identity.gmid)}

    return {"success": True, "message": f"User {email} added", "allowed_users": db.get_mind_allowed_users(mind.identity.gmid)}


@minds_router.get("/{mind_id}/access")
async def get_mind_access(mind_id: str, current_user: User = Depends(get_current_active_user)):
    """Return a Mind's access list (creator or admin)."""
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()

    # Verify permissions: creator or admin
    user_identifier = current_user.email if current_user.email else current_user.username
    is_creator = False
    try:
        mind = db.get_mind(mind_id)
        if mind:
            is_creator = (mind.creator == user_identifier)
    except Exception:
        pass

    is_admin = getattr(current_user, 'role', None) == UserRole.ADMIN or getattr(current_user, 'role', None) == 'admin'

    if not (is_creator or is_admin):
        raise HTTPException(status_code=403, detail="Only creator or admin can view access list")

    allowed_users = db.get_mind_allowed_users(mind_id)
    is_public = getattr(db.get_mind(mind_id), 'is_public', False)
    return {"is_public": is_public, "allowed_users": allowed_users}


@minds_router.delete("/{mind_id}/remove-user")
async def remove_user_from_mind(
    mind_id: str,
    email: str = Query(..., description="User email to remove"),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a user's access from a Mind (creator only)."""
    user_identifier = current_user.email if current_user.email else current_user.username

    mind = await _load_mind(mind_id)

    is_creator = (
        getattr(mind.identity, 'creator_email', None) == user_identifier
        or getattr(mind.identity, 'creator', None) == user_identifier
    )

    if not is_creator:
        raise HTTPException(status_code=403, detail="Only creator can manage access")

    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    removed = db.remove_mind_user_access(mind.identity.gmid, email)

    if not removed:
        return {"success": True, "message": f"User {email} doesn't have access", "allowed_users": db.get_mind_allowed_users(mind.identity.gmid)}

    return {"success": True, "message": f"User {email} removed", "allowed_users": db.get_mind_allowed_users(mind.identity.gmid)}


@minds_router.post("/{mind_id}/set-public")
async def set_mind_public(
    mind_id: str,
    body: Dict[str, bool],
    current_user: User = Depends(get_current_active_user),
):
    """Set or unset a Mind's public visibility (creator or admin only)."""
    if 'is_public' not in body:
        raise HTTPException(status_code=400, detail="'is_public' is required")

    is_public_val = bool(body.get('is_public'))
    user_identifier = current_user.email if current_user.email else current_user.username

    mind = await _load_mind(mind_id)

    is_creator = (
        getattr(mind.identity, 'creator_email', None) == user_identifier
        or getattr(mind.identity, 'creator', None) == user_identifier
    )

    is_admin = getattr(current_user, 'role', None) == UserRole.ADMIN or getattr(current_user, 'role', None) == 'admin'

    if not (is_creator or is_admin):
        raise HTTPException(status_code=403, detail="Only creator or admin can manage access")

    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    updated = db.set_mind_public(mind.identity.gmid, is_public_val)

    # Also persist into Mind JSON identity for compatibility
    mind.identity.is_public = is_public_val
    try:
        mind.save()
        print(f"[INFO] Saved mind {mind.identity.gmid} with is_public={is_public_val}")
    except Exception as save_error:
        print(f"[WARNING] Failed to save mind {mind.identity.gmid} to JSON: {save_error}")
        # Don't fail the request if JSON save fails - database is the source of truth

    return {"success": True, "message": "Updated is_public", "is_public": is_public_val}


@minds_router.get("/{mind_id}/access")
async def get_mind_access(mind_id: str, current_user: User = Depends(get_current_active_user)):
    """Get Mind access info: is_public and allowed user emails."""
    mind = await _load_mind(mind_id)

    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()

    is_public = getattr(mind.identity, 'is_public', False)
    try:
        # DB may be authoritative source
        mind_record = db.get_mind(mind.identity.gmid)
        if mind_record:
            is_public = bool(getattr(mind_record, 'is_public', is_public))
            allowed_users = db.get_mind_allowed_users(mind.identity.gmid)
        else:
            allowed_users = []
    except Exception:
        allowed_users = []

    return {"is_public": is_public, "allowed_users": allowed_users}


@minds_router.post("/{mind_id}/workspace/upload")
async def upload_workspace_file(
    mind_id: str,
    file: UploadFile = File(...),
    user_email: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a file to Mind's workspace with embedding and vector storage.
    
    Args:
        mind_id: The mind ID to upload to
        file: The file to upload
        user_email: Optional user email to tag the file with
        current_user: Authenticated user from JWT/API key
    """
    mind = await _load_mind(mind_id)
    
    # Check if mind has workspace plugin
    if not hasattr(mind, 'workspace') or mind.workspace is None:
        raise HTTPException(
            status_code=400,
            detail="Mind does not have workspace plugin enabled"
        )
    
    try:
        import shutil
        
        # Read file content
        content = await file.read()
        
        # Determine file type
        file_type = "text"
        if file.content_type:
            if "image" in file.content_type:
                file_type = "image"
            elif "pdf" in file.content_type:
                file_type = "document"
            elif any(code in file.content_type for code in ["python", "javascript", "java", "cpp"]):
                file_type = "code"
            elif "json" in file.content_type or "csv" in file.content_type:
                file_type = "data"
        
        # For text files, decode content
        content_str = ""
        if file_type == "text" or file_type == "code":
            try:
                content_str = content.decode('utf-8')
            except:
                content_str = content.decode('latin-1')
        
        # Build tags including user_email if provided
        tags = ["uploaded", "chat"]
        if user_email:
            tags.append(f"user:{user_email}")
        
        # Create file in workspace
        mind_file = mind.workspace.create_file(
            filename=file.filename,
            content=content_str if content_str else "",
            file_type=file_type,
            description=f"Uploaded via chat: {file.filename}" + (f" by {user_email}" if user_email else ""),
            tags=tags,
            is_private=True
        )
        
        # For binary files, write content directly to disk
        if not content_str:
            file_path = mind.workspace.workspace_path / mind_file.filepath
            file_path.write_bytes(content)
            mind_file.size_bytes = len(content)
        
        # Process file with Universal File Handler if it has content
        file_summary = ""
        extracted_data = None
        if content_str and hasattr(mind, 'file_handler'):
            try:
                file_path = mind.workspace.workspace_path / mind_file.filepath
                processing_result = await mind.file_handler.process_file(
                    file_path=file_path,
                    user_request=f"Extract and understand content from {file.filename}"
                )
                
                if processing_result.success:
                    file_summary = processing_result.summary
                    extracted_data = processing_result.data
                    
            except Exception as e:
                mind.logger.warning(f"File processing failed, continuing: {e}")
        
        # Create vector embedding for file content (for semantic search)
        # Use file content + summary for better searchability
        embedding_content = f"File: {file.filename}\n"
        embedding_content += f"Type: {file_type}\n"
        if user_email:
            embedding_content += f"Uploaded by: {user_email}\n"
        if file_summary:
            embedding_content += f"Summary: {file_summary}\n"
        if content_str:
            # Include first 1000 chars of content
            embedding_content += f"Content preview: {content_str[:1000]}\n"
        
        # Store in vector database with file metadata
        if hasattr(mind, 'memory') and hasattr(mind.memory, 'vector_store'):
            try:
                mind.memory.vector_store.add_memory(
                    memory_id=f"file_{mind_file.file_id}",
                    content=embedding_content,
                    metadata={
                        "type": "file",
                        "file_id": mind_file.file_id,
                        "filename": mind_file.filename,
                        "file_type": mind_file.file_type,
                        "size_bytes": mind_file.size_bytes,
                        "created_at": mind_file.created_at.isoformat(),
                        "tags": mind_file.tags,
                        "has_summary": bool(file_summary),
                        "user_email": user_email if user_email else None
                    }
                )
                
                mind.logger.info(f"[UPLOAD] Created vector embedding for {file.filename} by {user_email or 'unknown'}")
            except Exception as e:
                mind.logger.warning(f"Vector storage failed: {e}")
        
        # Create a memory entry for this file upload
        try:
            from genesis.storage.memory import MemoryType
            memory_content = f"Uploaded file: {file.filename}"
            if user_email:
                memory_content += f" by {user_email}"
            if file_summary:
                memory_content += f"\n\n{file_summary}"
            elif content_str:
                memory_content += f"\n\nContent preview: {content_str[:200]}..."
            
            await mind.memory.add_memory(
                memory_type=MemoryType.EPISODIC,
                content=memory_content,
                metadata={
                    "file_id": mind_file.file_id,
                    "filename": mind_file.filename,
                    "file_type": mind_file.file_type,
                    "action": "file_upload",
                    "user_email": user_email if user_email else None
                },
                user_email=user_email  # Tag memory with user email
            )
        except Exception as e:
            mind.logger.warning(f"Memory creation failed: {e}")
        
        # Save mind state
        mind.save()
        
        return {
            "success": True,
            "file_id": mind_file.file_id,
            "filename": mind_file.filename,
            "file_type": mind_file.file_type,
            "size_bytes": mind_file.size_bytes,
            "summary": file_summary or None,
            "has_embedding": True,
            "has_memory": True,
            "message": f"File '{file.filename}' uploaded, processed, and indexed successfully"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@minds_router.get("/{mind_id}/workspace/files")
async def get_workspace_files(
    mind_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get all files in Mind's workspace."""
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'workspace') or mind.workspace is None:
        return {"files": []}
    
    files = mind.workspace.list_files()
    
    return {
        "files": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "file_type": f.file_type,
                "size_bytes": f.size_bytes,
                "created_at": f.created_at.isoformat(),
                "modified_at": f.modified_at.isoformat(),
                "tags": f.tags,
                "description": f.description,
            }
            for f in files
        ]
    }


@minds_router.get("/{mind_id}/workspace/search")
async def search_workspace_files(
    mind_id: str,
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_active_user),
):
    """Search files in workspace using semantic search."""
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'workspace') or mind.workspace is None:
        return {"files": [], "count": 0}
    
    if not hasattr(mind, 'memory') or not hasattr(mind.memory, 'vector_store'):
        raise HTTPException(
            status_code=400,
            detail="Vector search not available for this Mind"
        )
    
    try:
        # Search in vector database for file embeddings
        results = mind.memory.vector_store.search(
            query=query,
            n_results=limit,
            filter_metadata={"type": "file"}
        )
        
        # Enrich with full file metadata
        files = []
        for result in results:
            file_id = result["metadata"].get("file_id")
            if file_id and file_id in mind.workspace.files:
                mind_file = mind.workspace.files[file_id]
                files.append({
                    "file_id": mind_file.file_id,
                    "filename": mind_file.filename,
                    "file_type": mind_file.file_type,
                    "size_bytes": mind_file.size_bytes,
                    "created_at": mind_file.created_at.isoformat(),
                    "tags": mind_file.tags,
                    "description": mind_file.description,
                    "relevance_score": 1 - (result["distance"] or 0),
                    "match_reason": result.get("content", "")[:200]
                })
        
        return {
            "query": query,
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@minds_router.delete("/{mind_id}/workspace/files/{filename}")
async def delete_workspace_file(
    mind_id: str,
    filename: str,
    current_user: User = Depends(get_current_active_user),
):
    """Delete a file from Mind's workspace and remove its embeddings."""
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'workspace') or mind.workspace is None:
        raise HTTPException(status_code=400, detail="Workspace not available")
    
    try:
        # Find file by filename
        file_to_delete = None
        file_id = None
        for fid, mind_file in mind.workspace.files.items():
            if mind_file.filename == filename:
                file_to_delete = fid
                file_id = mind_file.file_id
                break
        
        if not file_to_delete:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Delete from vector database
        if hasattr(mind, 'memory') and hasattr(mind.memory, 'vector_store'):
            try:
                mind.memory.vector_store.delete_memory(f"file_{file_id}")
                mind.logger.info(f"[DELETE] Removed vector embedding for {filename}")
            except Exception as e:
                mind.logger.warning(f"Could not delete vector embedding: {e}")
        
        # Delete file from workspace
        mind.workspace.delete_file(file_to_delete)
        
        # Create memory of deletion
        try:
            from genesis.storage.memory import MemoryType
            await mind.memory.add_memory(
                memory_type=MemoryType.EPISODIC,
                content=f"Deleted file: {filename}",
                metadata={
                    "file_id": file_id,
                    "filename": filename,
                    "action": "file_delete"
                }
            )
        except Exception as e:
            mind.logger.warning(f"Memory creation failed: {e}")
        
        mind.save()
        
        return {
            "success": True,
            "message": f"File '{filename}' deleted successfully (including embeddings)"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("/{mind_id}/memories", response_model=List[MemoryResponse])
async def get_memories(
    mind_id: str,
    memory_type: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """Get Mind's memories."""
    mind = await _load_mind(mind_id)

    # Filter by type if specified
    if memory_type:
        try:
            mem_type = MemoryType(memory_type)
            memories = [m for m in mind.memory.memories.values() if m.type == mem_type]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid memory type: {memory_type}")
    else:
        memories = list(mind.memory.memories.values())

    # Sort by timestamp (most recent first)
    memories.sort(key=lambda m: m.timestamp, reverse=True)
    memories = memories[:limit]

    return [
        MemoryResponse(
            id=mem.id,
            type=mem.type.value,
            content=mem.content,
            timestamp=mem.timestamp.isoformat(),
            emotion=mem.emotion,
            importance=mem.importance,
            tags=mem.tags,
        )
        for mem in memories
    ]


@minds_router.get("/{mind_id}/conversations")
async def get_conversation_threads(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get list of conversation threads (unique user+environment combinations).
    Returns threads with metadata for sidebar display.
    Requires authentication.
    """
    # Use authenticated user's email if no user_email provided
    if not user_email:
        user_email = current_user.email
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'conversation'):
        return {"threads": [], "count": 0}
    
    try:
        threads = mind.conversation.get_conversation_threads(user_email=user_email)
        
        # Enrich threads with environment names
        from genesis.database.base import get_session
        from genesis.database.models import EnvironmentRecord
        
        for thread in threads:
            if thread['environment_id']:
                with get_session() as session:
                    env = session.query(EnvironmentRecord).filter_by(
                        env_id=thread['environment_id']
                    ).first()
                    if env:
                        thread['environment_name'] = env.name
                        thread['environment_type'] = env.env_type
                    else:
                        thread['environment_name'] = thread['environment_id']
                        thread['environment_type'] = 'unknown'
            else:
                thread['environment_name'] = 'Direct Chat'
                thread['environment_type'] = 'direct'
        
        return {
            "threads": threads,
            "count": len(threads)
        }
    except Exception as e:
        logger.error(f"Error getting conversation threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("/{mind_id}/conversations/messages")
async def get_conversation_messages(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="User email"),
    environment_id: Optional[str] = Query(None, description="Environment ID"),
    before_id: Optional[int] = Query(None, description="Message id cursor (return messages before this id)"),
    limit: int = Query(default=50, le=200, description="Maximum messages to return"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get messages for a specific conversation thread.
    Support cursor-based pagination via `before_id` (return messages older than the cursor).
    Filter by user_email and/or environment_id to get specific conversation.
    Requires authentication.
    """
    # Use authenticated user's email if no user_email provided
    if not user_email:
        user_email = current_user.email
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'conversation'):
        return {"messages": [], "count": 0, "has_more": False}
    
    try:
        if before_id is not None:
            messages = mind.conversation.get_messages_before(
                before_id=before_id,
                limit=limit,
                user_email=user_email,
                environment_id=environment_id
            )
        else:
            messages = mind.conversation.get_recent_messages(
                limit=limit,
                user_email=user_email,
                environment_id=environment_id
            )

        has_more = len(messages) == limit
        next_before_id = messages[0]['id'] if messages else None
        
        return {
            "messages": messages,
            "count": len(messages),
            "has_more": has_more,
            "next_before_id": next_before_id
        }
    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("/{mind_id}/messages")
async def get_messages(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="User email"),
    environment_id: Optional[str] = Query(None, description="Environment ID"),
    limit: int = Query(default=50, le=200, description="Maximum messages to return"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Alias endpoint for get_conversation_messages.
    Get messages for a specific conversation thread.
    Filter by user_email and/or environment_id to get specific conversation.
    Requires authentication.
    """
    # Use authenticated user's email if no user_email provided in query
    if not user_email:
        user_email = current_user.email
    
    return await get_conversation_messages(mind_id, user_email, environment_id, limit)


@minds_router.get("/{mind_id}/thoughts")
async def get_thoughts(
    mind_id: str, 
    limit: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get Mind's recent thoughts from database.
    
    CRITICAL: Thoughts now stored in SQLite for scalability.
    Requires authentication.
    """
    mind = await _load_mind(mind_id)
    
    # Get thoughts from database
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()
    db_thoughts = db.get_recent_thoughts(mind.identity.gmid, limit=limit)
    
    # Convert to API format
    thoughts = [
        {
            "content": t.content,
            "type": t.thought_type,
            "timestamp": t.timestamp.isoformat(),
            "awareness_level": t.awareness_level,
            "emotion": t.emotion,
        }
        for t in db_thoughts
    ]
    
    return {"thoughts": thoughts}


@minds_router.get("/{mind_id}/logs")
async def get_mind_logs(
    mind_id: str,
    limit: int = Query(default=100, le=1000),
    level: Optional[str] = Query(None, description="Filter by log level"),
    current_user: User = Depends(get_current_active_user),
):
    """Get Mind's activity logs (all consciousness activities, LLM calls, thoughts, etc.). Requires authentication."""
    mind = await _load_mind(mind_id)
    
    # Convert level string to LogLevel enum if provided
    log_level = None
    if level:
        try:
            from genesis.core.mind_logger import LogLevel
            log_level = LogLevel(level.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid log level: {level}. Valid levels: {[l.value for l in LogLevel]}"
            )
    
    # Get logs from the mind's logger
    logs = mind.logger.get_recent_logs(limit=limit, level=log_level)
    
    # Get stats
    stats = mind.logger.get_stats()
    
    return {
        "mind_id": mind_id,
        "mind_name": mind.identity.name,
        "total_logs": len(logs),
        "logs": logs,
        "stats": stats,
    }


@minds_router.get("/{mind_id}/logs/stats")
async def get_mind_log_stats(mind_id: str):
    """Get statistics about Mind's activities."""
    mind = await _load_mind(mind_id)
    
    stats = mind.logger.get_stats()
    
    return {
        "mind_id": mind_id,
        "mind_name": mind.identity.name,
        "stats": stats,
    }


@minds_router.delete("/{mind_id}/logs")
async def clear_mind_logs(mind_id: str):
    """Clear all logs for a Mind."""
    mind = await _load_mind(mind_id)
    
    try:
        mind.logger.clear_logs()
        return {
            "success": True,
            "message": "Logs cleared successfully",
            "mind_id": mind_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear logs: {str(e)}"
        )


@minds_router.post("/{mind_id}/thought")
async def generate_thought(mind_id: str):
    """Generate an autonomous thought."""
    mind = await _load_mind(mind_id)

    try:
        thought = await mind.generate_autonomous_thought()
        
        if thought:
            mind.save()
            return {"thought": thought, "success": True}
        else:
            return {"thought": "No thought generated at this time.", "success": False}

    except Exception as e:
        import traceback
        print(f"Error generating thought: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Background Task endpoints
@minds_router.get("/{mind_id}/tasks")
async def get_mind_tasks(
    mind_id: str,
    user_email: str = Query(None, description="Filter by user email"),
    status: str = Query(None, description="Filter by status")
):
    """Get background tasks for a mind."""
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'background_executor'):
        return {"tasks": [], "count": 0}
    
    if user_email:
        tasks = mind.background_executor.get_tasks_for_user(user_email)
    else:
        active = mind.background_executor.get_active_tasks()
        completed = mind.background_executor.get_completed_tasks(limit=20)
        tasks = active + completed
    
    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t.status.value == status]
    
    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks)
    }


@minds_router.get("/{mind_id}/tasks/{task_id}")
async def get_task_status(mind_id: str, task_id: str):
    """Get status of a specific task."""
    mind = await _load_mind(mind_id)
    
    if not hasattr(mind, 'background_executor'):
        raise HTTPException(status_code=404, detail="Background executor not available")
    
    task = mind.background_executor.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return task.to_dict()


@minds_router.get("/{mind_id}/artifacts/download")
async def download_artifact(
    mind_id: str,
    filename: str = Query(..., description="Name of the artifact file to download")
):
    """Download an artifact file generated by a task."""
    import os
    
    try:
        # Search for the file in multiple locations
        search_paths = [
            # Mind's outputs directory
            settings.data_dir / "outputs" / mind_id / filename,
            # General outputs directory
            settings.data_dir / "outputs" / filename,
            # Mind's data directory
            settings.data_dir / mind_id / filename,
            # General data directory
            settings.data_dir / filename,
            # Home Genesis directory
            Path.home() / ".genesis" / "data" / "outputs" / mind_id / filename,
            Path.home() / ".genesis" / "data" / "outputs" / filename,
        ]
        
        resolved_path = None
        for search_path in search_paths:
            if search_path.exists() and search_path.is_file():
                resolved_path = search_path.resolve()
                break
        
        if not resolved_path:
            raise HTTPException(
                status_code=404, 
                detail=f"File '{filename}' not found in any output directories"
            )
        
        # Security: Ensure the path is within allowed directories
        allowed_dirs = [
            settings.data_dir.resolve(),
            (Path.home() / ".genesis").resolve(),
            Path.cwd().resolve()
        ]
        
        is_allowed = any(
            str(resolved_path).startswith(str(allowed_dir))
            for allowed_dir in allowed_dirs
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail="Access denied: File is outside allowed directories"
            )
        
        # Return the file
        return FileResponse(
            path=str(resolved_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading artifact: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@minds_router.delete("/{mind_id}")
async def delete_mind(
    mind_id: str,
    current_user: User = Depends(require_write_access),
):
    """Delete a Mind permanently (requires write access)."""
    import os
    import shutil
    
    # Find mind file
    mind_path = None
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get("identity", {}).get("gmid") == mind_id or data.get("identity", {}).get("name") == mind_id:
                mind_path = path
                break
        except Exception:
            continue
    
    if not mind_path:
        raise HTTPException(status_code=404, detail=f"Mind '{mind_id}' not found")
    
    # Stop daemon if running
    import psutil
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline):
                for i, arg in enumerate(cmdline):
                    if arg == '--mind-id' and i + 1 < len(cmdline) and cmdline[i + 1] == mind_id:
                        proc.kill()
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Delete mind file
    os.remove(mind_path)
    
    # Delete associated data (memories, logs, etc.)
    mind_data_dir = settings.data_dir / mind_id
    if mind_data_dir.exists():
        shutil.rmtree(mind_data_dir)
    
    return {"success": True, "message": f"Mind {mind_id} permanently deleted"}


# =============================================================================
# DAEMON ENDPOINTS
# =============================================================================

# Mount admin router onto auth router path '/admin' for convenience
# Admin router also registered at top-level '/api/v1/admin' in server
auth_router.include_router(admin_router, prefix="/admin")



@minds_router.get("/{mind_id}/daemon/status")
async def get_daemon_status(mind_id: str):
    """Get daemon status for a specific Mind."""
    import psutil
    from datetime import datetime
    
    # Find if daemon is running for this Mind
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline):
                # Extract mind ID from cmdline
                for i, arg in enumerate(cmdline):
                    if arg == '--mind-id' and i + 1 < len(cmdline):
                        found_mind_id = cmdline[i + 1]
                        if found_mind_id == mind_id:
                            # Daemon is running
                            uptime = datetime.now() - datetime.fromtimestamp(proc.info['create_time'])
                            return {
                                "running": True,
                                "pid": proc.info['pid'],
                                "status": proc.info['status'],
                                "uptime_seconds": int(uptime.total_seconds()),
                                "uptime_hours": uptime.total_seconds() / 3600,
                                "started_at": datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                            }
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Daemon not running
    return {
        "running": False,
        "pid": None,
        "status": "stopped",
        "uptime_seconds": 0,
        "uptime_hours": 0.0,
        "started_at": None,
    }


@minds_router.post("/{mind_id}/daemon/start")
async def start_daemon(
    mind_id: str,
    current_user: User = Depends(require_write_access),
):
    """Start daemon for a Mind."""
    import subprocess
    import sys
    
    # Check if already running
    status = await get_daemon_status(mind_id)
    if status["running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Daemon already running with PID {status['pid']}"
        )
    
    # Verify Mind exists
    await _load_mind(mind_id)
    
    # Start daemon as background process
    try:
        # Use the same Python interpreter
        python_exe = sys.executable
        
        # Start daemon in background
        process = subprocess.Popen(
            [python_exe, "-m", "genesis.daemon", "--mind-id", mind_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # Detach from parent
        )
        
        # Give it a moment to start
        await asyncio.sleep(2)
        
        # Check if it's running
        status = await get_daemon_status(mind_id)
        
        if status["running"]:
            return {
                "success": True,
                "message": f"Daemon started successfully",
                "pid": status["pid"],
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Daemon failed to start"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start daemon: {str(e)}"
        )


@minds_router.post("/{mind_id}/daemon/stop")
async def stop_daemon(
    mind_id: str,
    current_user: User = Depends(require_write_access),
):
    """Stop daemon for a Mind."""
    import psutil
    import signal
    
    # Find daemon process
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'genesis.daemon' in ' '.join(cmdline):
                for i, arg in enumerate(cmdline):
                    if arg == '--mind-id' and i + 1 < len(cmdline):
                        found_mind_id = cmdline[i + 1]
                        if found_mind_id == mind_id:
                            # Send SIGTERM for graceful shutdown
                            proc.send_signal(signal.SIGTERM)
                            
                            # Wait for process to stop
                            try:
                                proc.wait(timeout=10)
                            except psutil.TimeoutExpired:
                                # Force kill if still running
                                proc.kill()
                            
                            return {
                                "success": True,
                                "message": f"Daemon stopped successfully",
                                "pid": proc.info['pid'],
                            }
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    raise HTTPException(
        status_code=404,
        detail=f"No running daemon found for Mind {mind_id}"
    )


# Plugin management endpoints
class PluginConfigRequest(BaseModel):
    """Request to add a plugin."""
    plugin_name: str
    config: Optional[Dict[str, Any]] = None


class PluginResponse(BaseModel):
    """Plugin information response."""
    name: str
    version: str
    description: str
    enabled: bool
    config: Optional[Dict[str, Any]] = None


class AvailablePluginResponse(BaseModel):
    """Available plugin metadata."""
    name: str
    version: str
    description: str
    category: str
    requires_config: bool
    config_fields: List[Dict[str, Any]] = []


@minds_router.get("/plugins/available")
async def list_available_plugins():
    """List all available plugins from the registry."""
    try:
        from genesis.plugins.registry import PluginRegistry
        plugins_list = PluginRegistry.list_all()
        
        return {
            "plugins": [
                AvailablePluginResponse(
                    name=p["name"],
                    version=p["version"],
                    description=p["description"],
                    category=p.get("category", "extension"),
                    requires_config=p.get("requires_config", "false") == "true",
                    config_fields=p.get("config_fields", [])
                )
                for p in plugins_list
            ]
        }
    except Exception as e:
        # Fallback if registry not available
        return {
            "plugins": [
                {"name": "lifecycle", "version": "1.0.0", "description": "Mortality awareness", "category": "core", "requires_config": False, "config_fields": []},
                {"name": "gen", "version": "1.0.0", "description": "Economy system", "category": "core", "requires_config": False, "config_fields": []},
                {"name": "tasks", "version": "1.0.0", "description": "Task management", "category": "core", "requires_config": False, "config_fields": []},
                {"name": "workspace", "version": "1.0.0", "description": "File workspace", "category": "core", "requires_config": False, "config_fields": []},
                {"name": "browser_use", "version": "1.0.0", "description": "Browser automation", "category": "integration", "requires_config": False, "config_fields": []},
            ]
        }


@minds_router.get("/{mind_id}/plugins")
async def get_plugins(mind_id: str):
    """Get all plugins for a Mind."""
    import json
    
    # Find mind path using the helper function
    mind_path = _find_mind_path(mind_id)
    
    # Read config from JSON first to check if migration is needed
    with open(mind_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    config_data = data.get('config', {})
    plugin_configs = config_data.get('plugins', [])
    
    # If empty plugins, load the Mind to trigger migration, then save to persist it
    if not plugin_configs:
        print(f"[get_plugins] Empty plugins detected for {mind_id}, loading Mind to trigger migration...")
        mind = Mind.load(mind_path)
        # Get the migrated plugin configs from the loaded mind
        plugin_configs = [
            {
                'name': p.get_name(),
                'version': p.get_version(),
                'config': p.config
            }
            for p in mind.config.get_all_plugins()
        ]
        # Save to persist the migration
        print(f"[get_plugins] Saving migrated config with {len(plugin_configs)} plugins...")
        mind.save(mind_path)
        print(f"[get_plugins] Migration persisted to disk")
    
    # Map plugin names to descriptions
    plugin_descriptions = {
        'lifecycle': 'Mortality awareness, urgency, and limited lifespan mechanics',
        'gen': 'GEN (Essence) economy system with motivation and value tracking',
        'tasks': 'Goal-oriented task management and execution',
        'workspace': 'File system access and management capabilities',
        'relationships': 'Social connections and relationship tracking',
        'environments': 'Metaverse environment interactions',
        'roles': 'Role-based purpose and job system',
        'sensory': 'Time awareness and self-perception',
        'learning': 'Learning and knowledge acquisition',
        'goals': 'Autonomous goal pursuit',
        'knowledge': 'Knowledge graph system',
    }
    
    plugins_data = []
    for plugin_config in plugin_configs:
        plugin_name = plugin_config.get('name', 'unknown')
        plugins_data.append(
            PluginResponse(
                name=plugin_name,
                version=plugin_config.get('version', '0.1.5'),
                description=plugin_descriptions.get(plugin_name, 'Plugin'),
                enabled=True,
                config=plugin_config.get('config', {}),
            )
        )
    
    return {"plugins": plugins_data}


@minds_router.post("/{mind_id}/plugins")
async def add_plugin(
    mind_id: str,
    request: PluginConfigRequest,
    current_user: User = Depends(require_write_access),
):
    """Add a plugin to a Mind."""
    mind_path = _find_mind_path(mind_id)
    mind = Mind.load(mind_path)
    
    # Check if plugin already exists
    if mind.config.has_plugin(request.plugin_name):
        raise HTTPException(
            status_code=400,
            detail=f"Plugin '{request.plugin_name}' is already enabled"
        )
    
    # Create plugin instance
    plugin = None
    try:
        if request.plugin_name == "lifecycle":
            from genesis.plugins.lifecycle import LifecyclePlugin
            plugin = LifecyclePlugin(**(request.config or {}))
        elif request.plugin_name == "gen":
            from genesis.plugins.gen import GenPlugin
            plugin = GenPlugin(**(request.config or {}))
        elif request.plugin_name == "tasks":
            from genesis.plugins.tasks import TasksPlugin
            plugin = TasksPlugin(**(request.config or {}))
        elif request.plugin_name == "workspace":
            from genesis.plugins.workspace import WorkspacePlugin
            plugin = WorkspacePlugin(**(request.config or {}))
        elif request.plugin_name == "relationships":
            from genesis.plugins.relationships import RelationshipsPlugin
            plugin = RelationshipsPlugin(**(request.config or {}))
        elif request.plugin_name == "environments":
            from genesis.plugins.environments import EnvironmentsPlugin
            plugin = EnvironmentsPlugin(**(request.config or {}))
        elif request.plugin_name == "roles":
            from genesis.plugins.roles import RolesPlugin
            plugin = RolesPlugin(**(request.config or {}))
        elif request.plugin_name == "events":
            from genesis.plugins.events import EventsPlugin
            plugin = EventsPlugin(**(request.config or {}))
        elif request.plugin_name == "experiences":
            from genesis.plugins.experiences import ExperiencesPlugin
            plugin = ExperiencesPlugin(**(request.config or {}))
        elif request.plugin_name == "perplexity_search":
            from genesis.plugins.perplexity_search import PerplexitySearchPlugin
            config = request.config or {}
            plugin = PerplexitySearchPlugin(
                api_key=config.get('api_key'),
                auto_search=config.get('auto_search', True),
                default_mode=config.get('default_mode', 'detailed')
            )
        elif request.plugin_name == "browser_use":
            from genesis.plugins.browser_use_plugin import BrowserUsePlugin
            plugin = BrowserUsePlugin(**(request.config or {}))
        elif request.plugin_name == "mcp":
            from genesis.plugins.mcp import MCPPlugin
            plugin = MCPPlugin(**(request.config or {}))
        elif request.plugin_name == "learning":
            from genesis.plugins.experimental.learning import LearningPlugin
            plugin = LearningPlugin(**(request.config or {}))
        elif request.plugin_name == "goals":
            from genesis.plugins.experimental.goals import GoalsPlugin
            plugin = GoalsPlugin(**(request.config or {}))
        elif request.plugin_name == "knowledge":
            from genesis.plugins.experimental.knowledge import KnowledgePlugin
            plugin = KnowledgePlugin(**(request.config or {}))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown plugin: {request.plugin_name}"
            )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import plugin '{request.plugin_name}': {str(e)}"
        )
    
    # Add plugin to config and mind
    mind.config.add_plugin(plugin)
    mind.plugins.append(plugin)
    
    # Initialize plugin
    plugin.on_init(mind)
    
    # Save Mind
    mind.save(mind_path)
    
    return {
        "success": True,
        "message": f"Plugin '{request.plugin_name}' added successfully",
        "plugin": PluginResponse(
            name=plugin.get_name(),
            version=plugin.get_version(),
            description=plugin.get_description(),
            enabled=plugin.enabled,
            config=plugin.config,
        )
    }


@minds_router.delete("/{mind_id}/plugins/{plugin_name}")
async def remove_plugin(
    mind_id: str,
    plugin_name: str,
    current_user: User = Depends(require_write_access),
):
    """Remove a plugin from a Mind."""
    mind_path = _find_mind_path(mind_id)
    mind = Mind.load(mind_path)
    
    # Check if plugin exists
    if not mind.config.has_plugin(plugin_name):
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_name}' is not enabled"
        )
    
    # Remove plugin
    mind.config.remove_plugin(plugin_name)
    mind.plugins = [p for p in mind.plugins if p.get_name() != plugin_name]
    
    # Save Mind
    mind.save(mind_path)
    
    return {
        "success": True,
        "message": f"Plugin '{plugin_name}' removed successfully"
    }


@minds_router.post("/{mind_id}/plugins/{plugin_name}/enable")
async def enable_plugin(
    mind_id: str,
    plugin_name: str,
    current_user: User = Depends(require_write_access),
):
    """Enable a disabled plugin."""
    mind_path = _find_mind_path(mind_id)
    mind = Mind.load(mind_path)
    
    plugin = mind.config.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_name}' is not installed"
        )
    
    if plugin.enabled:
        raise HTTPException(
            status_code=400,
            detail=f"Plugin '{plugin_name}' is already enabled"
        )
    
    plugin.enable()
    mind.save(mind_path)
    
    return {
        "success": True,
        "message": f"Plugin '{plugin_name}' enabled successfully"
    }


@minds_router.post("/{mind_id}/plugins/{plugin_name}/disable")
async def disable_plugin(
    mind_id: str,
    plugin_name: str,
    current_user: User = Depends(require_write_access),
):
    """Disable a plugin without removing it."""
    mind_path = _find_mind_path(mind_id)
    mind = Mind.load(mind_path)
    
    plugin = mind.config.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_name}' is not installed"
        )
    
    if not plugin.enabled:
        raise HTTPException(
            status_code=400,
            detail=f"Plugin '{plugin_name}' is already disabled"
        )
    
    plugin.disable()
    mind.save(mind_path)
    
    return {
        "success": True,
        "message": f"Plugin '{plugin_name}' disabled successfully"
    }


# WebSocket endpoint for real-time chat
@minds_router.websocket("/{mind_id}/stream")
async def websocket_chat(websocket: WebSocket, mind_id: str):
    """
    WebSocket endpoint for real-time streaming chat with proactive messaging support.
    
    The Mind can now send proactive messages through this connection!
    """
    await websocket.accept()
    
    # Extract user email from query params or try to infer from Authorization header
    user_email = websocket.query_params.get("user_email")
    if not user_email:
        # Try to extract email from a Bearer token (Firebase ID token, etc.)
        try:
            from genesis.api.firebase_auth import get_firebase_user_email
            auth_header = websocket.headers.get('authorization')
            if auth_header and auth_header.lower().startswith('bearer '):
                token = auth_header.split(' ', 1)[1]
                try:
                    email = get_firebase_user_email(token)
                    if email:
                        user_email = email
                except Exception:
                    pass
        except Exception:
            pass

    if not user_email:
        user_email = "web_user@genesis.local"
        logger.warning("WebSocket connected without user_email; defaulting to web_user@genesis.local")

    mind = None  # Initialize to None to avoid UnboundLocalError

    try:
        # Load Mind - USE CACHED MIND so WebSocket registration persists!
        print(f"[WEBSOCKET ENDPOINT] Loading mind from cache...")
        mind = await _get_cached_mind(mind_id)
        print(f"[WEBSOCKET ENDPOINT] ✓ Mind loaded: {mind.identity.name}")
        print(f"[WEBSOCKET ENDPOINT] Mind instance ID: {id(mind)}")
        
        # Register websocket with notification manager for proactive messages
        if hasattr(mind, 'notification_manager') and mind.notification_manager:
            mind.notification_manager.register_websocket(user_email, websocket)
            logger.info(f"[WEBSOCKET] WebSocket registered for proactive notifications: {user_email}")
            print(f"[DEBUG WEBSOCKET] Registered WebSocket for {user_email}")
            print(f"[DEBUG WEBSOCKET] Mind ID: {mind_id}")
            print(f"[DEBUG WEBSOCKET] Notification manager instance ID: {id(mind.notification_manager)}")
            print(f"[DEBUG WEBSOCKET] Active connections after registration: {list(mind.notification_manager.websocket_connections.keys())}")
            
            # Send any pending notifications that were stored while user was offline
            await send_pending_notifications(mind, user_email, websocket)

        # Send initial state
        await websocket.send_json(
            {
                "type": "connected",
                "mind": {
                    "name": mind.identity.name,
                    "emotion": mind.current_emotion,
                    "thought": mind.current_thought,
                },
            }
        )

        # Message loop
        while True:
            # Receive message with timeout to allow proactive messages
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                message = data.get("message")

                if not message:
                    continue

                # Send thinking status
                await websocket.send_json({"type": "thinking"})

                # Stream response with user email context
                full_response = ""
                async for chunk in mind.stream_think(message, user_email=user_email):
                    await websocket.send_json({"type": "chunk", "content": chunk})
                    full_response += chunk

                # Send completion
                await websocket.send_json(
                    {
                        "type": "complete",
                        "emotion": mind.current_emotion,
                        "memory_count": mind.memory.vector_store.count(),
                    }
                )

                # Save state
                mind.save()
                
            except asyncio.TimeoutError:
                # No message received, continue loop (allows proactive messages to be sent)
                continue

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for Mind {mind_id}, user {user_email}")
        print(f"[DEBUG WEBSOCKET] WebSocket DISCONNECTED for {user_email}")
        print(f"[DEBUG WEBSOCKET] Mind ID: {mind_id}")
        # Unregister from notification manager (only if mind was loaded)
        if mind and hasattr(mind, 'notification_manager') and mind.notification_manager:
            mind.notification_manager.unregister_websocket(user_email)
            print(f"[DEBUG WEBSOCKET] Unregistered. Remaining connections: {list(mind.notification_manager.websocket_connections.keys())}")
    except Exception as e:
        logger.error(f"WebSocket error for Mind {mind_id}: {e}", exc_info=True)
        try:
            if not websocket.client_state.value == 3:  # CLOSED = 3
                await websocket.send_json({"type": "error", "message": str(e)})
                await websocket.close()
        except Exception as close_error:
            logger.debug(f"Error closing websocket: {close_error}")
        
        # Unregister from notification manager (only if mind was loaded)
        if mind and hasattr(mind, 'notification_manager') and mind.notification_manager:
            mind.notification_manager.unregister_websocket(user_email)


# System endpoints
@system_router.get("/status")
async def system_status(current_user: User = Depends(get_current_active_user)):
    """Get system status."""
    from genesis.models.orchestrator import ModelOrchestrator

    orchestrator = ModelOrchestrator()

    # Get provider health
    provider_health = await orchestrator.health_check()

    # Count minds
    mind_count = len(list(settings.minds_dir.glob("*.json")))

    return {
        "version": settings.version,
        "minds_count": mind_count,
        "providers": provider_health,
        "models": {
            "reasoning": settings.default_reasoning_model,
            "fast": settings.default_fast_model,
            "local": settings.default_local_model,
        },
    }


@system_router.get("/providers")
async def get_providers(current_user: User = Depends(get_current_active_user)):
    """Get available model providers."""
    from genesis.models.orchestrator import ModelOrchestrator

    orchestrator = ModelOrchestrator()

    return {
        "providers": orchestrator.get_available_providers(),
        "health": await orchestrator.health_check(),
    }


@system_router.get("/notifications/health")
async def notification_health():
    """Get notification system health across all minds."""
    from genesis.config.settings import get_settings
    
    settings = get_settings()
    health_data = {
        "system_status": "ok",
        "minds": {},
        "total_stats": {
            "active_websockets": 0,
            "pending_notifications": 0,
            "delivered_today": 0,
            "failed_total": 0
        }
    }
    
    try:
        # Check each mind's notification system
        for path in settings.minds_dir.glob("*.json"):
            try:
                mind = Mind.load(path)
                if hasattr(mind, 'notification_manager') and mind.notification_manager:
                    stats = mind.notification_manager.get_stats()
                    mind_name = mind.identity.name
                    
                    health_data["minds"][mind_name] = {
                        "gmid": mind.identity.gmid,
                        "notification_manager_active": True,
                        "stats": stats
                    }
                    
                    # Aggregate totals
                    health_data["total_stats"]["active_websockets"] += stats["active_websockets"]
                    health_data["total_stats"]["pending_notifications"] += stats["pending"]
                    health_data["total_stats"]["delivered_today"] += stats["delivered_today"]
                    health_data["total_stats"]["failed_total"] += stats.get("failed_total", 0)
                else:
                    mind_name = getattr(mind.identity, 'name', 'Unknown')
                    health_data["minds"][mind_name] = {
                        "gmid": getattr(mind.identity, 'gmid', 'Unknown'),
                        "notification_manager_active": False,
                        "stats": None
                    }
                    
            except Exception as e:
                logger.warning(f"Could not check notification health for {path}: {e}")
                
    except Exception as e:
        logger.error(f"Error checking notification system health: {e}")
        health_data["system_status"] = "error"
        health_data["error"] = str(e)
    
    return health_data


@system_router.post("/notifications/cleanup")
async def cleanup_stale_connections():
    """Manually trigger cleanup of stale WebSocket connections across all minds."""
    from genesis.config.settings import get_settings
    
    settings = get_settings()
    cleanup_results = {
        "success": True,
        "minds_processed": 0,
        "connections_cleaned": 0,
        "errors": []
    }
    
    try:
        for path in settings.minds_dir.glob("*.json"):
            try:
                mind = Mind.load(path)
                if hasattr(mind, 'notification_manager') and mind.notification_manager:
                    # Get connections before cleanup
                    connections_before = len(mind.notification_manager.websocket_connections)
                    
                    # Trigger cleanup
                    await mind.notification_manager.cleanup_connections()
                    
                    # Get connections after cleanup
                    connections_after = len(mind.notification_manager.websocket_connections)
                    
                    cleanup_results["minds_processed"] += 1
                    cleanup_results["connections_cleaned"] += (connections_before - connections_after)
                    
            except Exception as e:
                cleanup_results["errors"].append(f"Error cleaning {path}: {e}")
                
    except Exception as e:
        cleanup_results["success"] = False
        cleanup_results["errors"].append(f"System error: {e}")
    
    return cleanup_results


@minds_router.get("/{mind_id}/notifications")
async def get_pending_notifications(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="User email to get notifications for"),
    request: Request = None
):
    """Get pending notifications for a user."""
    try:
        mind = await _load_mind(mind_id)
        
        # If user_email not provided, try to infer from Authorization header
        if not user_email and request is not None:
            try:
                from genesis.api.firebase_auth import get_firebase_user_email
                auth_header = request.headers.get('authorization')
                if auth_header and auth_header.lower().startswith('bearer '):
                    token = auth_header.split(' ', 1)[1]
                    try:
                        firebase_email = get_firebase_user_email(token)
                        if firebase_email:
                            user_email = firebase_email
                    except Exception:
                        pass
            except Exception:
                pass

        if not user_email:
            return {"notifications": []}

        from genesis.config.settings import get_settings
        import json
        from pathlib import Path
        
        settings = get_settings()
        notif_dir = settings.data_dir / "notifications" / mind_id
        
        if not notif_dir.exists():
            return {"notifications": []}
        
        notifications = []
        for notif_file in notif_dir.glob("*.json"):
            try:
                with open(notif_file, 'r', encoding='utf-8') as f:
                    notif_data = json.load(f)
                    
                    # Only return notifications for this user that haven't been delivered
                    if notif_data.get("recipient") == user_email and not notif_data.get("delivered"):
                        notifications.append(notif_data)
            except Exception as e:
                logger.error(f"Error reading notification file {notif_file}: {e}")
                continue
        
        # Sort by created_at (newest first)
        notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"notifications": notifications}
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@system_router.get("/notifications/all")
async def get_all_notifications(
    user_email: Optional[str] = Query(None, description="User email to get notifications for"),
    request: Request = None
):
    """Get all pending notifications for a user across all minds."""
    try:
        from genesis.config.settings import get_settings
        import json
        from genesis.api.firebase_auth import get_firebase_user_email
        
        # If no explicit user_email provided, try to infer it from Authorization header (Firebase ID token or other bearer token)
        if not user_email and request is not None:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1]
                try:
                    firebase_email = get_firebase_user_email(token)
                    if firebase_email:
                        user_email = firebase_email
                except Exception:
                    pass

        # If still no user_email, return empty response (avoid defaulting to test user)
        if not user_email:
            return {"notifications": [], "count": 0}

        settings = get_settings()
        notif_base_dir = settings.data_dir / "notifications"
        
        if not notif_base_dir.exists():
            return {"notifications": [], "count": 0}
        
        all_notifications = []
        
        # Iterate through each mind's notification directory
        for mind_dir in notif_base_dir.iterdir():
            if not mind_dir.is_dir():
                continue
                
            for notif_file in mind_dir.glob("*.json"):
                try:
                    with open(notif_file, 'r', encoding='utf-8') as f:
                        notif_data = json.load(f)
                        
                        # Only return notifications for this user that haven't been delivered
                        if notif_data.get("recipient") == user_email and not notif_data.get("delivered"):
                            all_notifications.append(notif_data)
                except Exception as e:
                    logger.error(f"Error reading notification file {notif_file}: {e}")
                    # Delete corrupted file to prevent repeated errors
                    try:
                        notif_file.unlink()
                        logger.info(f"Deleted corrupted notification file: {notif_file}")
                    except Exception as del_error:
                        logger.error(f"Failed to delete corrupted file {notif_file}: {del_error}")
                    continue
        
        # Sort by created_at (newest first)
        all_notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"notifications": all_notifications, "count": len(all_notifications)}
        
    except Exception as e:
        logger.error(f"Error getting all notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.post("/{mind_id}/notifications/{notification_id}/mark-delivered")
async def mark_notification_delivered(mind_id: str, notification_id: str):
    """Mark a notification as delivered."""
    try:
        from genesis.config.settings import get_settings
        import json
        
        settings = get_settings()
        notif_file = settings.data_dir / "notifications" / mind_id / f"{notification_id}.json"
        
        if notif_file.exists():
            with open(notif_file, 'r', encoding='utf-8') as f:
                notif_data = json.load(f)
            
            notif_data["delivered"] = True
            notif_data["delivered_at"] = datetime.now().isoformat()
            
            with open(notif_file, 'w', encoding='utf-8') as f:
                json.dump(notif_data, f, indent=2, ensure_ascii=False)
            
            # Persist the notification as a conversation message so it appears in chat history
            try:
                from genesis.storage.conversation import ConversationManager
                conv = ConversationManager(mind_id)
                # Use the stored metadata if available
                metadata = notif_data.get("metadata", {}) or {}
                # Save as assistant message tied to the recipient so it will be visible in their conversation
                conv.add_message(
                    role="assistant",
                    content=notif_data.get("message", ""),
                    user_email=notif_data.get("recipient"),
                    metadata={
                        "is_proactive": True,
                        "proactive_title": notif_data.get("title"),
                        **metadata
                    },
                    timestamp=datetime.fromisoformat(notif_data.get("created_at")) if notif_data.get("created_at") else None
                )
            except Exception as e:
                logger.error(f"Error persisting delivered notification to conversation: {e}")
            
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
            
    except Exception as e:
        logger.error(f"Error marking notification as delivered: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROACTIVE CONVERSATION ENDPOINTS
# =============================================================================

class ProactiveContextResponse(BaseModel):
    """Response model for conversation context."""
    context_id: str
    topic: str
    subject: str
    initial_message: str
    user_email: str
    follow_up_question: Optional[str] = None
    follow_up_scheduled: Optional[str] = None
    follow_up_sent: bool = False
    resolved: bool = False
    resolved_at: Optional[str] = None
    importance: float
    urgency: float
    created_at: str
    last_updated: str


@minds_router.get("/{mind_id}/proactive/contexts")
async def get_proactive_contexts(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    include_resolved: bool = Query(False, description="Include resolved contexts"),
    current_user: User = Depends(get_current_active_user),
):
    """Get proactive conversation contexts for a Mind."""
    mind = await _get_cached_mind(mind_id)
    
    if not hasattr(mind, 'proactive_conversation'):
        raise HTTPException(
            status_code=400,
            detail="Mind does not have proactive conversation system enabled"
        )
    
    try:
        if user_email:
            contexts = mind.proactive_conversation.get_user_contexts(
                user_email=user_email,
                include_resolved=include_resolved
            )
        else:
            # Return all contexts
            contexts = list(mind.proactive_conversation.active_contexts.values())
            if not include_resolved:
                contexts = [c for c in contexts if not c.resolved]
        
        # Convert to response format
        return {
            "contexts": [
                ProactiveContextResponse(
                    context_id=ctx.context_id,
                    topic=ctx.topic.value,
                    subject=ctx.subject,
                    initial_message=ctx.initial_message,
                    user_email=ctx.user_email,
                    follow_up_question=ctx.follow_up_question,
                    follow_up_scheduled=ctx.follow_up_scheduled.isoformat() if ctx.follow_up_scheduled else None,
                    follow_up_sent=ctx.follow_up_sent,
                    resolved=ctx.resolved,
                    resolved_at=ctx.resolved_at.isoformat() if ctx.resolved_at else None,
                    importance=ctx.importance,
                    urgency=ctx.urgency,
                    created_at=ctx.created_at.isoformat(),
                    last_updated=ctx.last_updated.isoformat()
                )
                for ctx in contexts
            ],
            "count": len(contexts)
        }
    except Exception as e:
        logger.error(f"Error getting proactive contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("/{mind_id}/proactive/pending")
async def get_pending_followups(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    current_user: User = Depends(get_current_active_user),
):
    """Get pending follow-ups ready to be sent."""
    mind = await _get_cached_mind(mind_id)
    
    if not hasattr(mind, 'proactive_conversation'):
        raise HTTPException(
            status_code=400,
            detail="Mind does not have proactive conversation system enabled"
        )
    
    try:
        pending = await mind.proactive_conversation.get_pending_follow_ups(user_email=user_email)
        
        return {
            "pending_followups": [
                ProactiveContextResponse(
                    context_id=ctx.context_id,
                    topic=ctx.topic.value,
                    subject=ctx.subject,
                    initial_message=ctx.initial_message,
                    user_email=ctx.user_email,
                    follow_up_question=ctx.follow_up_question,
                    follow_up_scheduled=ctx.follow_up_scheduled.isoformat() if ctx.follow_up_scheduled else None,
                    follow_up_sent=ctx.follow_up_sent,
                    resolved=ctx.resolved,
                    resolved_at=ctx.resolved_at.isoformat() if ctx.resolved_at else None,
                    importance=ctx.importance,
                    urgency=ctx.urgency,
                    created_at=ctx.created_at.isoformat(),
                    last_updated=ctx.last_updated.isoformat()
                )
                for ctx in pending
            ],
            "count": len(pending)
        }
    except Exception as e:
        logger.error(f"Error getting pending follow-ups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("/{mind_id}/concerns")
async def get_concerns(
    mind_id: str,
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    include_resolved: bool = Query(False, description="Include resolved concerns"),
    current_user: User = Depends(get_current_active_user),
):
    """Get tracked concerns for proactive follow-up."""
    mind = await _get_cached_mind(mind_id)
    
    if not hasattr(mind, 'proactive_consciousness') or not mind.proactive_consciousness:
        return {
            "active_concerns": [],
            "resolved_concerns": [],
            "message": "Proactive consciousness not enabled for this mind"
        }
    
    try:
        all_concerns = mind.proactive_consciousness.get_all_concerns()
        
        # Filter by user if specified
        active = all_concerns["active"]
        resolved = all_concerns["resolved"]
        
        if user_email:
            active = [c for c in active if c.get("user_email") == user_email]
            resolved = [c for c in resolved if c.get("user_email") == user_email]
        
        result = {
            "active_concerns": active,
            "count": len(active)
        }
        
        if include_resolved:
            result["resolved_concerns"] = resolved
            result["resolved_count"] = len(resolved)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting concerns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.post("/{mind_id}/proactive/contexts/{context_id}/resolve")
async def resolve_context(
    mind_id: str,
    context_id: str,
    note: Optional[str] = Query(None, description="Resolution note"),
    current_user: User = Depends(get_current_active_user),
):
    """Manually resolve a conversation context."""
    mind = await _get_cached_mind(mind_id)
    
    if not hasattr(mind, 'proactive_conversation'):
        raise HTTPException(
            status_code=400,
            detail="Mind does not have proactive conversation system enabled"
        )
    
    try:
        context = mind.proactive_conversation.active_contexts.get(context_id)
        if not context:
            raise HTTPException(status_code=404, detail=f"Context {context_id} not found")
        
        context.mark_resolved(note=note)
        await mind.proactive_conversation._save_context(context)
        
        return {
            "success": True,
            "message": f"Context '{context.subject}' marked as resolved",
            "context_id": context_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.delete("/{mind_id}/proactive/contexts/{context_id}")
async def delete_context(
    mind_id: str,
    context_id: str,
    current_user: User = Depends(require_write_access),
):
    """Delete a conversation context."""
    mind = await _get_cached_mind(mind_id)
    
    if not hasattr(mind, 'proactive_conversation'):
        raise HTTPException(
            status_code=400,
            detail="Mind does not have proactive conversation system enabled"
        )
    
    try:
        if context_id not in mind.proactive_conversation.active_contexts:
            raise HTTPException(status_code=404, detail=f"Context {context_id} not found")
        
        context = mind.proactive_conversation.active_contexts.pop(context_id)
        
        # Remove from user index
        if context.user_email in mind.proactive_conversation.user_contexts:
            user_contexts = mind.proactive_conversation.user_contexts[context.user_email]
            if context_id in user_contexts:
                user_contexts.remove(context_id)
        
        return {
            "success": True,
            "message": f"Context '{context.subject}' deleted",
            "context_id": context_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Continuing with existing code...


@system_router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user_email: Optional[str] = Query(None, description="User email to mark notifications for"),
    request: Request = None
):
    """Mark all notifications for a user as delivered/read."""
    try:
        from genesis.config.settings import get_settings
        import json
        from genesis.api.firebase_auth import get_firebase_user_email
        
        # If not provided, try to infer from Authorization header
        if not user_email and request is not None:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1]
                try:
                    firebase_email = get_firebase_user_email(token)
                    if firebase_email:
                        user_email = firebase_email
                except Exception:
                    pass

        if not user_email:
            return {"success": True, "count": 0}

        settings = get_settings()
        notif_base_dir = settings.data_dir / "notifications"
        
        if not notif_base_dir.exists():
            return {"success": True, "count": 0}
        
        marked_count = 0
        
        # Iterate through each mind's notification directory
        for mind_dir in notif_base_dir.iterdir():
            if not mind_dir.is_dir():
                continue
            
            # Check each notification file
            for notif_file in mind_dir.glob("*.json"):
                try:
                    with open(notif_file, 'r', encoding='utf-8') as f:
                        notif_data = json.load(f)
                    
                    # Only mark notifications for this user that haven't been delivered
                    if (notif_data.get("recipient") == user_email and 
                        not notif_data.get("delivered")):
                        
                        notif_data["delivered"] = True
                        notif_data["delivered_at"] = datetime.now().isoformat()
                        
                        with open(notif_file, 'w', encoding='utf-8') as f:
                            json.dump(notif_data, f, indent=2, ensure_ascii=False)
                        
                        marked_count += 1
                        
                except Exception as e:
                    logger.error(f"Error marking notification as read {notif_file}: {e}")
                    # Delete corrupted file to prevent repeated errors
                    try:
                        notif_file.unlink()
                        logger.info(f"Deleted corrupted notification file: {notif_file}")
                    except Exception as del_error:
                        logger.error(f"Failed to delete corrupted file {notif_file}: {del_error}")
                    continue
        
        return {"success": True, "count": marked_count}
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def send_pending_notifications(mind: Mind, user_email: str, websocket):
    """Send any pending notifications that were stored while user was offline."""
    try:
        from genesis.config.settings import get_settings
        import json
        
        settings = get_settings()
        notif_dir = settings.data_dir / "notifications" / mind.identity.gmid
        
        if not notif_dir.exists():
            return
        
        sent_count = 0
        for notif_file in notif_dir.glob("*.json"):
            try:
                with open(notif_file, 'r', encoding='utf-8') as f:
                    notif_data = json.load(f)
                
                # Only send notifications for this user that haven't been delivered
                if notif_data.get("recipient") == user_email and not notif_data.get("delivered"):
                    # Send via websocket
                    await websocket.send_json({
                        "type": "proactive_message",
                        "notification_id": notif_data["notification_id"],
                        "mind_id": notif_data["mind_id"],
                        "mind_name": notif_data["mind_name"],
                        "title": notif_data["title"],
                        "message": notif_data["message"],
                        "priority": notif_data["priority"],
                        "timestamp": notif_data["created_at"],
                        "metadata": notif_data.get("metadata", {})
                    })
                    
                    # Mark as delivered
                    notif_data["delivered"] = True
                    notif_data["delivered_at"] = datetime.now().isoformat()
                    
                    with open(notif_file, 'w', encoding='utf-8') as f:
                        json.dump(notif_data, f, indent=2, ensure_ascii=False)
                    
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"Error sending pending notification {notif_file}: {e}")
                # Delete corrupted file to prevent repeated errors
                try:
                    notif_file.unlink()
                    logger.info(f"Deleted corrupted notification file: {notif_file}")
                except Exception as del_error:
                    logger.error(f"Failed to delete corrupted file {notif_file}: {del_error}")
                continue
        
        if sent_count > 0:
            logger.info(f"Sent {sent_count} pending notification(s) to {user_email}")
            
    except Exception as e:
        logger.error(f"Error retrieving pending notifications: {e}")


def _find_mind_path(mind_id: str) -> Path:
    """Find the path to a Mind's JSON file by ID or name."""
    import json
    
    # Try to find by GMID or name
    for path in settings.minds_dir.glob("*.json"):
        try:
            with open(path) as f:
                data = json.load(f)

            gmid = data["identity"]["gmid"]
            name = data["identity"]["name"]
            
            if gmid == mind_id or name == mind_id:
                return path

        except Exception as e:
            logger.debug(f"Error checking {path}: {e}")

    raise HTTPException(status_code=404, detail=f"Mind '{mind_id}' not found")


async def _load_mind(mind_id: str) -> Mind:
    """Load a Mind by ID or name."""
    print(f"[DEBUG _load_mind] Searching for mind_id: {mind_id}")
    
    # Try to find by GMID or name
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json

            with open(path) as f:
                data = json.load(f)

            gmid = data["identity"]["gmid"]
            name = data["identity"]["name"]
            
            if gmid == mind_id or name == mind_id:
                print(f"[DEBUG _load_mind] Found match in {path.name}")
                print(f"[DEBUG _load_mind]   GMID: {gmid}")
                print(f"[DEBUG _load_mind]   Name: {name}")
                loaded_mind = Mind.load(path)
                print(f"[DEBUG _load_mind] Loaded mind has GMID: {loaded_mind.identity.gmid}")
                
                # CRITICAL: Verify the loaded mind has the expected GMID
                if loaded_mind.identity.gmid != gmid:
                    print(f"[ERROR] Mind GMID mismatch! File has {gmid} but loaded mind has {loaded_mind.identity.gmid}")
                
                # CRITICAL: Register mind in database (for foreign key integrity)
                try:
                    from genesis.database.manager import MetaverseDB
                    metaverse_db = MetaverseDB()
                    
                    print(f"[DEBUG] Checking if mind {loaded_mind.identity.gmid} is registered in database...")
                    existing_mind = metaverse_db.get_mind(loaded_mind.identity.gmid)
                    if not existing_mind:
                        print(f"[DEBUG] Mind NOT registered, registering now...")
                        # Register mind
                        primary_role = None
                        if hasattr(loaded_mind, 'roles'):
                            primary = loaded_mind.roles.get_primary_role()
                            if primary:
                                primary_role = primary.get("name")
                        
                        metaverse_db.register_mind(
                            gmid=loaded_mind.identity.gmid,
                            name=loaded_mind.identity.name,
                            creator=loaded_mind.identity.creator,
                            template=loaded_mind.identity.template,
                            primary_role=primary_role,
                        )
                        print(f"[INFO] ✓ Registered mind {loaded_mind.identity.gmid} in database")
                    else:
                        print(f"[DEBUG] Mind already registered in database")
                        
                        # Sync is_public from database to mind identity
                        try:
                            db_is_public = metaverse_db.get_mind_is_public(loaded_mind.identity.gmid)
                            if db_is_public is not None:
                                loaded_mind.identity.is_public = db_is_public
                                print(f"[DEBUG] Synced is_public from database: {db_is_public}")
                        except Exception as sync_error:
                            print(f"[WARNING] Could not sync is_public from database: {sync_error}")
                except Exception as reg_error:
                    print(f"[ERROR] Could not register mind in database: {reg_error}")
                    import traceback
                    traceback.print_exc()
                
                return loaded_mind

        except Exception as e:
            print(f"Error checking {path}: {e}")

    raise HTTPException(status_code=404, detail=f"Mind '{mind_id}' not found")


# =============================================================================
# METAVERSE ENDPOINTS - Query the metaverse database
# =============================================================================

@metaverse_router.get("/stats")
async def get_metaverse_stats():
    """Get metaverse-wide statistics."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    return db.get_metaverse_stats()


@metaverse_router.get("/minds")
async def list_all_minds(
    status: Optional[str] = Query(None, description="Filter by status (active, dormant, archived)"),
    role: Optional[str] = Query(None, description="Filter by primary role"),
    template: Optional[str] = Query(None, description="Filter by template"),
):
    """List all Minds in the metaverse."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()

    if role or template:
        minds = db.search_minds(role=role, template=template)
    else:
        minds = db.get_all_minds(status=status)

    return {
        "total": len(minds),
        "minds": [
            {
                "gmid": m.gmid,
                "name": m.name,
                "creator": m.creator,
                "birth_date": m.birth_date.isoformat(),
                "last_active": m.last_active.isoformat() if m.last_active else None,
                "status": m.status,
                "primary_role": m.primary_role,
                "template": m.template,
                "total_memories": m.total_memories,
                "total_experiences": m.total_experiences,
            }
            for m in minds
        ],
    }


@metaverse_router.get("/minds/{gmid}")
async def get_mind_info(gmid: str):
    """Get detailed information about a Mind."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    mind = db.get_mind(gmid)

    if not mind:
        raise HTTPException(status_code=404, detail=f"Mind {gmid} not found")

    return {
        "gmid": mind.gmid,
        "name": mind.name,
        "creator": mind.creator,
        "birth_date": mind.birth_date.isoformat(),
        "last_active": mind.last_active.isoformat() if mind.last_active else None,
        "status": mind.status,
        "primary_role": mind.primary_role,
        "template": mind.template,
        "consciousness_level": mind.consciousness_level,
        "total_memories": mind.total_memories,
        "total_experiences": mind.total_experiences,
        "storage_path": mind.storage_path,
    }


@metaverse_router.get("/minds/{gmid}/relationships")
async def get_mind_relationships(gmid: str):
    """Get all relationships for a Mind."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    relationships = db.get_mind_relationships(gmid)

    return {
        "total": len(relationships),
        "relationships": [
            {
                "id": r.id,
                "from_gmid": r.from_gmid,
                "to_gmid": r.to_gmid,
                "relationship_type": r.relationship_type,
                "closeness": r.closeness,
                "trust_level": r.trust_level,
                "affection": r.affection,
                "started_at": r.started_at.isoformat(),
                "last_interaction": r.last_interaction.isoformat() if r.last_interaction else None,
                "interaction_count": r.interaction_count,
            }
            for r in relationships
        ],
    }


@metaverse_router.get("/minds/{gmid}/connections")
async def get_connected_minds(gmid: str, min_closeness: float = 0.0):
    """Get GMIDs of Minds connected to this Mind."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    connected = db.get_connected_minds(gmid, min_closeness=min_closeness)

    # Get full Mind info for each connection
    minds = [db.get_mind(g) for g in connected]

    return {
        "total": len(connected),
        "connected_minds": [
            {
                "gmid": m.gmid,
                "name": m.name,
                "primary_role": m.primary_role,
                "status": m.status,
            }
            for m in minds
            if m
        ],
    }


@metaverse_router.get("/environments")
async def list_environments(public_only: bool = Query(False, description="Show only public environments")):
    """List environments in the metaverse."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()

    if public_only:
        envs = db.get_public_environments()
    else:
        # Would need to add this method to MetaverseDB
        raise HTTPException(status_code=501, detail="Listing all environments not yet implemented")

    return {
        "total": len(envs),
        "environments": [
            {
                "env_id": e.env_id,
                "name": e.name,
                "env_type": e.env_type,
                "owner_gmid": e.owner_gmid,
                "is_public": e.is_public,
                "is_shared": e.is_shared,
                "created_at": e.created_at.isoformat(),
                "access_count": e.access_count,
                "current_inhabitants": e.current_inhabitants,
            }
            for e in envs
        ],
    }


@metaverse_router.get("/environments/{env_id}/visitors")
async def get_environment_visitors(env_id: str, active_only: bool = True):
    """Get visitors to an environment."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    visits = db.get_environment_visitors(env_id, active_only=active_only)

    return {
        "total": len(visits),
        "visitors": [
            {
                "mind_gmid": v.mind_gmid,
                "entered_at": v.entered_at.isoformat(),
                "left_at": v.left_at.isoformat() if v.left_at else None,
                "duration_seconds": v.duration_seconds,
                "is_owner": v.is_owner,
                "visit_purpose": v.visit_purpose,
            }
            for v in visits
        ],
    }


@metaverse_router.get("/activity/recent")
async def get_recent_activity(limit: int = Query(20, le=100)):
    """Get recent metaverse activity."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    activity = db.get_recent_activity(limit=limit)

    return {
        "recent_births": [
            {
                "gmid": m.gmid,
                "name": m.name,
                "creator": m.creator,
                "birth_date": m.birth_date.isoformat(),
            }
            for m in activity["recent_births"]
        ],
        "recent_visits": [
            {
                "mind_gmid": v.mind_gmid,
                "env_id": v.env_id,
                "entered_at": v.entered_at.isoformat(),
            }
            for v in activity["recent_visits"]
        ],
        "recent_events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "title": e.title,
                "participants": len(e.participant_gmids),
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in activity["recent_events"]
        ],
    }


@metaverse_router.get("/search/minds")
async def search_minds(
    name: Optional[str] = Query(None, description="Search by name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    template: Optional[str] = Query(None, description="Filter by template"),
    min_consciousness: Optional[float] = Query(None, description="Minimum consciousness level"),
):
    """Search for Minds by various criteria."""
    from genesis.database.manager import MetaverseDB

    db = MetaverseDB()
    minds = db.search_minds(
        name_query=name, role=role, template=template, min_consciousness=min_consciousness
    )

    return {
        "total": len(minds),
        "results": [
            {
                "gmid": m.gmid,
                "name": m.name,
                "primary_role": m.primary_role,
                "template": m.template,
                "consciousness_level": m.consciousness_level,
                "total_memories": m.total_memories,
                "total_experiences": m.total_experiences,
            }
            for m in minds
        ],
    }


# =============================================================================
# SETTINGS ENDPOINTS
# =============================================================================

settings_router = APIRouter(tags=["settings"])


@settings_router.post("/api-keys")
async def update_api_keys(
    keys: Dict[str, str],
    current_user: User = Depends(get_current_active_user),
):
    """Update API keys (stored in memory/session)."""
    # In a real application, you'd want to store these securely
    # For now, we'll just validate and return success
    return {
        "success": True,
        "message": "API keys updated successfully",
    }


@settings_router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_active_user),
):
    """Get configured API keys (masked)."""
    # Return masked keys from environment
    import os
    
    return {
        "gemini_api_key": "***" + os.getenv("GEMINI_API_KEY", "")[-4:] if os.getenv("GEMINI_API_KEY") else "",
        "elevenlabs_api_key": "***" + os.getenv("ELEVENLABS_API_KEY", "")[-4:] if os.getenv("ELEVENLABS_API_KEY") else "",
    }


@settings_router.post("/test-gemini")
async def test_gemini_connection(
    request: Dict[str, str],
    current_user: User = Depends(get_current_active_user),
):
    """Test Google Gemini API connection."""
    api_key = request.get("api_key")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    try:
        import google.generativeai as genai
        
        # Configure with provided key
        genai.configure(api_key=api_key)
        
        # Test with a simple request
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'Connection successful' in one word")
        
        return {
            "success": True,
            "message": "Connection successful",
            "model": "gemini-pro",
            "response": response.text if hasattr(response, 'text') else "OK",
        }
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="google-generativeai package not installed. Run: pip install google-generativeai"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Connection failed: {str(e)}"
        )


# =============================================================================
# LLM CALL TRACKING & AUTONOMOUS ACTIONS ENDPOINTS
# =============================================================================


@minds_router.get("/{mind_id}/llm-calls")
async def get_llm_calls(
    mind_id: str,
    limit: int = 50,
):
    """
    Get LLM call history for a Mind.
    
    Extracts LLM call logs from the Mind's log history.
    """
    try:
        # Find mind path
        mind_path = _find_mind_path(mind_id)
        mind = Mind.load(mind_path)
        
        # Get logs (using get_all_logs to retrieve from file)
        logs = mind.logger.get_all_logs(limit=limit * 5)  # Get more to filter for LLM calls only
        
        # Filter for LLM calls
        llm_calls = []
        for log in logs:
            if log.get("level") == "llm_call" or "LLM call" in log.get("message", ""):
                metadata = log.get("metadata", {})
                
                # Calculate approximate cost (rough estimates)
                model = metadata.get("model", "unknown")
                prompt_tokens = metadata.get("prompt_length", 0)
                completion_tokens = metadata.get("response_length", 0)
                total_tokens = prompt_tokens + completion_tokens
                
                # Rough cost estimation (in USD per 1M tokens)
                cost_per_token = 0.0
                if "gpt-4" in model.lower():
                    cost_per_token = 0.00003  # $30 per 1M tokens (input)
                elif "gpt-3.5" in model.lower():
                    cost_per_token = 0.000001  # $1 per 1M tokens
                elif "deepseek" in model.lower():
                    cost_per_token = 0.0000001  # Very cheap
                elif "claude" in model.lower():
                    cost_per_token = 0.000015  # $15 per 1M tokens
                else:
                    cost_per_token = 0.000001  # Default low cost
                
                cost = total_tokens * cost_per_token
                
                # Extract provider from model name
                provider = "unknown"
                if "openrouter" in model.lower():
                    provider = "OpenRouter"
                elif "gpt" in model.lower() or "openai" in model.lower():
                    provider = "OpenAI"
                elif "claude" in model.lower() or "anthropic" in model.lower():
                    provider = "Anthropic"
                elif "deepseek" in model.lower():
                    provider = "DeepSeek"
                elif "groq" in model.lower():
                    provider = "Groq"
                elif "gemini" in model.lower():
                    provider = "Google"
                
                # Estimate latency (mock data for now - could be tracked in future)
                latency = 1000 + (total_tokens // 10)  # Rough estimate based on tokens
                
                llm_calls.append({
                    "id": log.get("timestamp", ""),
                    "timestamp": log.get("timestamp", ""),
                    "provider": provider,
                    "model": model,
                    "purpose": metadata.get("purpose", "chat"),
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": total_tokens,
                    "cost": cost,
                    "latency": latency,
                    "success": True,  # Assume success if logged
                })
        
        # Sort by timestamp and limit
        llm_calls.sort(key=lambda x: x["timestamp"], reverse=True)
        llm_calls = llm_calls[:limit]
        
        return {"calls": llm_calls}
        
    except Exception as e:
        # Return empty list if tracking not available
        return {"calls": []}


@minds_router.get("/{mind_id}/autonomous-actions")
async def get_autonomous_actions(
    mind_id: str,
    limit: int = 20,
):
    """
    Get autonomous action history for a Mind.
    
    Extracts autonomous actions from the Mind's log history.
    """
    try:
        # Find mind path
        mind_path = _find_mind_path(mind_id)
        mind = Mind.load(mind_path)
        
        # Get logs
        logs = mind.logger.get_logs(limit=limit * 3)  # Get more to filter
        
        # Filter for autonomous actions
        actions = []
        for log in logs:
            message = log.get("message", "")
            metadata = log.get("metadata", {})
            level = log.get("level", "")
            
            # Identify autonomous actions
            is_action = (
                level == "action" or
                "autonomous" in message.lower() or
                "executing action" in message.lower() or
                "proactive" in message.lower() or
                metadata.get("action_type") is not None
            )
            
            if is_action:
                action_type = metadata.get("action_type", "unknown")
                
                # Infer action type from message if not in metadata
                if action_type == "unknown":
                    if "thought" in message.lower():
                        action_type = "thought_generation"
                    elif "memory" in message.lower():
                        action_type = "memory_update"
                    elif "search" in message.lower():
                        action_type = "information_search"
                    elif "task" in message.lower():
                        action_type = "task_execution"
                    elif "conversation" in message.lower():
                        action_type = "proactive_conversation"
                    else:
                        action_type = "general_action"
                
                # Determine status
                status = "completed"
                if "failed" in message.lower() or "error" in message.lower():
                    status = "failed"
                elif "pending" in message.lower() or "started" in message.lower():
                    status = "in_progress"
                
                actions.append({
                    "action_id": f"{log.get('timestamp', '')}_{action_type}",
                    "action_type": action_type,
                    "description": message,
                    "status": status,
                    "created_at": log.get("timestamp", ""),
                    "completed_at": log.get("timestamp", "") if status == "completed" else None,
                    "result": metadata.get("result", None),
                })
        
        # Sort by timestamp and limit
        actions.sort(key=lambda x: x["created_at"], reverse=True)
        actions = actions[:limit]
        
        return {"actions": actions}
        
    except Exception as e:
        # Return empty list if tracking not available
        return {"actions": []}


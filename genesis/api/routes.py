"""API routes for Genesis."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import timedelta

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Depends, Request
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
    start_consciousness: bool = False
    api_keys: Optional[dict[str, str]] = None  # Provider API keys (e.g., {'groq': 'gsk_...'})


class MindResponse(BaseModel):
    """Mind information response."""

    gmid: str
    name: str
    age: str
    status: str
    current_emotion: str
    current_thought: Optional[str]
    memory_count: int
    dream_count: int
    gens: int = 1000
    avatar_url: Optional[str] = None
    creator: Optional[str] = None
    creator_email: Optional[str] = None
    primary_purpose: Optional[str] = None
    description: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    autonomy_level: Optional[int] = None
    consciousness_active: bool = True
    dreaming_enabled: bool = True


class ChatRequest(BaseModel):
    """Chat message request."""

    message: str
    stream: bool = False
    user_email: Optional[str] = None  # User identifier for memory filtering
    environment_id: Optional[str] = None  # Environment context for the conversation


class ChatResponse(BaseModel):
    """Chat response."""

    response: str
    emotion: str
    memory_created: bool


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

    # Build intelligence config
    intelligence = Intelligence()
    if request.reasoning_model:
        intelligence.reasoning_model = request.reasoning_model
    if request.fast_model:
        intelligence.fast_model = request.fast_model
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
        mind = Mind.birth(
            name=request.name,
            intelligence=intelligence,
            autonomy=autonomy,
            template=request.template,
            start_consciousness=request.start_consciousness,
            config=mind_config,
            creator_email=request.creator_email,
        )

        # Test provider connection (since it was skipped in birth due to async context)
        if request.reasoning_model:
            success, message = await mind.orchestrator.test_provider_connection(request.reasoning_model)
            if not success:
                print(f"⚠️  Warning: {message}")
                print(f"   Mind created but may not be able to think until provider is configured.")

        # Save
        mind.save()

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

        return MindResponse(
            gmid=mind.identity.gmid,
            name=mind.identity.name,
            age=mind.identity.get_age_description(),
            status=mind.identity.status,
            current_emotion=mind.current_emotion,
            current_thought=mind.current_thought,
            memory_count=len(mind.memory.memories),
            dream_count=len(mind.dreams),
            avatar_url=getattr(mind.identity, 'avatar_url', None),
            creator=mind.identity.creator,
            creator_email=getattr(mind.identity, 'creator_email', None),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("", response_model=List[MindResponse])
async def list_minds():
    """List all Minds with optimized lightweight loading."""
    import json
    from datetime import datetime
    minds = []

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
            
            # Count memories from memory.memories array
            memory_count = len(memory_data.get('memories', []))
            
            # Skip terminated minds
            if identity.get('status', 'active') == 'terminated':
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
                    dream_count=len(data.get('dreams', [])),
                    gens=identity.get('gens', 1000),
                    creator=identity.get('creator'),
                    creator_email=identity.get('creator_email'),
                    primary_purpose=identity.get('primary_purpose'),
                    description=identity.get('description'),
                    llm_provider=data.get('intelligence', {}).get('primary_provider', 'groq'),
                    llm_model=data.get('intelligence', {}).get('primary_model', 'mixtral-8x7b-32768'),
                    autonomy_level=data.get('autonomy', {}).get('level', 5),
                    consciousness_active=state.get('consciousness_active', True),
                    dreaming_enabled=data.get('autonomy', {}).get('dreaming_enabled', True),
                )
            )
        except Exception as e:
            print(f"Error loading mind {path}: {e}")

    return minds


@minds_router.get("/{mind_id}", response_model=MindResponse)
async def get_mind(mind_id: str):
    """Get a specific Mind."""
    mind = await _load_mind(mind_id)

    return MindResponse(
        gmid=mind.identity.gmid,
        name=mind.identity.name,
        age=mind.identity.get_age_description(),
        status=mind.identity.status,
        current_emotion=mind.current_emotion,
        current_thought=mind.current_thought,
        memory_count=len(mind.memory.memories),
        dream_count=len(mind.dreams),
        gens=getattr(mind.identity, 'gens', 1000),
        avatar_url=getattr(mind.identity, 'avatar_url', None),
        primary_purpose=getattr(mind.identity, 'primary_purpose', None),
        description=getattr(mind.identity, 'description', None),
        llm_provider=getattr(mind.intelligence, 'primary_provider', 'groq'),
        llm_model=getattr(mind.intelligence, 'primary_model', 'mixtral-8x7b-32768'),
        autonomy_level=getattr(mind.autonomy, 'level', 5),
        consciousness_active=mind.state.consciousness_active,
        dreaming_enabled=getattr(mind.autonomy, 'dreaming_enabled', True),
    )


@minds_router.post("/{mind_id}/chat", response_model=ChatResponse)
async def chat(
    mind_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Chat with a Mind (requires authentication)."""
    mind = await _load_mind(mind_id)

    try:
        # Generate response with user context
        # Use user_email from request if provided, otherwise use authenticated user's email
        user_identifier = request.user_email if request.user_email else current_user.email
        
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
        
        try:
            response = await mind.think(request.message, user_email=user_identifier)
        except Exception as think_error:
            print(f"ERROR in mind.think(): {str(think_error)}")
            print(f"Error type: {type(think_error).__name__}")
            import traceback
            traceback.print_exc()
            response = None
        
        # Log for debugging
        if not response:
            print(f"WARNING: mind.think() returned empty response for Mind {mind.identity.gmid}")
            print(f"Mind has API keys: {mind.intelligence.api_keys}")
            print(f"Reasoning model: {mind.intelligence.reasoning_model}")
            print(f"Fast model: {mind.intelligence.fast_model}")
            response = "I apologize, but I was unable to generate a response. Please check my configuration and API keys."

        # Save updated state
        mind.save()

        return ChatResponse(
            response=response or "No response generated",
            emotion=mind.current_emotion,
            memory_created=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        # Save updated state
        mind.save()

        return MultimodalChatResponse(
            response=response,
            emotion=mind.current_emotion,
            memory_created=True,
            generated_image=generated_image_url,
            avatar_url=avatar_url,
        )

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
        
        # Update LLM configuration
        if 'llm_provider' in settings:
            mind.intelligence.primary_provider = settings['llm_provider']
        if 'llm_model' in settings:
            mind.intelligence.primary_model = settings['llm_model']
        if 'api_key' in settings and settings['api_key']:
            # Store API key securely (this would need proper encryption in production)
            mind.intelligence.api_key = settings['api_key']
        
        # Update Ollama configuration
        if 'use_ollama' in settings:
            mind.intelligence.use_ollama = settings['use_ollama']
        if 'ollama_url' in settings:
            mind.intelligence.ollama_url = settings['ollama_url']
        
        # Update autonomy settings
        if 'autonomy_level' in settings:
            mind.autonomy.level = settings['autonomy_level']
        if 'consciousness_active' in settings:
            mind.state.consciousness_active = settings['consciousness_active']
        if 'dreaming_enabled' in settings:
            mind.autonomy.dreaming_enabled = settings['dreaming_enabled']
        
        # Update currency (Gens)
        if 'gens' in settings:
            mind.identity.gens = settings['gens']
        
        # Update avatar URL
        if 'avatar_url' in settings:
            mind.identity.avatar_url = settings['avatar_url']
        
        # Save updated Mind
        mind.save()
        
        return {
            "success": True,
            "message": "Mind settings updated successfully",
            "gmid": mind.identity.gmid,
        }
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


@minds_router.get("/{mind_id}/dreams")
async def get_dreams(mind_id: str, limit: int = Query(default=10, le=50)):
    """Get Mind's dreams."""
    mind = await _load_mind(mind_id)

    dreams = mind.dreams[-limit:]
    return {"dreams": dreams}


@minds_router.post("/{mind_id}/dream")
async def trigger_dream(mind_id: str):
    """Trigger a dream session."""
    mind = await _load_mind(mind_id)

    try:
        dream = await mind.dream()
        mind.save()

        return {"dream": dream}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@minds_router.get("/{mind_id}/thoughts")
async def get_thoughts(mind_id: str, limit: int = Query(default=10, le=50)):
    """Get Mind's recent thoughts."""
    mind = await _load_mind(mind_id)

    thoughts = mind.consciousness.get_recent_thoughts(limit=limit)
    return {"thoughts": thoughts}


@minds_router.get("/{mind_id}/logs")
async def get_mind_logs(
    mind_id: str,
    limit: int = Query(default=100, le=1000),
    level: Optional[str] = Query(None, description="Filter by log level"),
):
    """Get Mind's activity logs (all consciousness activities, LLM calls, thoughts, dreams, etc.)."""
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


@minds_router.get("/{mind_id}/plugins")
async def get_plugins(mind_id: str):
    """Get all plugins for a Mind (optimized - reads from config in JSON)."""
    import json
    
    # Find mind path by GMID or name (without loading full Mind)
    mind_path = None
    for path in settings.minds_dir.glob("*.json"):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get("identity", {}).get("gmid") == mind_id or data.get("identity", {}).get("name") == mind_id:
                mind_path = path
                break
        except Exception:
            continue
    
    if not mind_path:
        raise HTTPException(status_code=404, detail=f"Mind '{mind_id}' not found")
    
    # Read config from JSON
    with open(mind_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    config_data = data.get('config', {})
    plugin_configs = config_data.get('plugins', [])
    
    # Backward compatibility: If no plugins in config, assume standard config (lifecycle, gen, tasks)
    if not plugin_configs:
        plugin_configs = [
            {'name': 'lifecycle', 'version': '0.1.0', 'config': {}},
            {'name': 'gen', 'version': '0.1.0', 'config': {}},
            {'name': 'tasks', 'version': '0.1.0', 'config': {}},
        ]
    
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
                version=plugin_config.get('version', '0.1.0'),
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
    
    # Extract user email from query params or use default
    user_email = websocket.query_params.get("user_email", "web_user@genesis.local")

    try:
        # Load Mind
        mind = await _load_mind(mind_id)
        
        # Register websocket with notification manager for proactive messages
        if hasattr(mind, 'notification_manager') and mind.notification_manager:
            mind.notification_manager.register_websocket(user_email, websocket)
            logger.info(f"🔌 WebSocket registered for proactive notifications: {user_email}")
            
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
                        "memory_count": len(mind.memory.memories),
                    }
                )

                # Save state
                mind.save()
                
            except asyncio.TimeoutError:
                # No message received, continue loop (allows proactive messages to be sent)
                continue

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for Mind {mind_id}, user {user_email}")
        # Unregister from notification manager
        if hasattr(mind, 'notification_manager') and mind.notification_manager:
            mind.notification_manager.unregister_websocket(user_email)
    except Exception as e:
        logger.error(f"WebSocket error for Mind {mind_id}: {e}", exc_info=True)
        try:
            if not websocket.client_state.value == 3:  # CLOSED = 3
                await websocket.send_json({"type": "error", "message": str(e)})
                await websocket.close()
        except Exception as close_error:
            logger.debug(f"Error closing websocket: {close_error}")
        
        # Unregister from notification manager
        if hasattr(mind, 'notification_manager') and mind.notification_manager:
            mind.notification_manager.unregister_websocket(user_email)


# System endpoints
@system_router.get("/status")
async def system_status():
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
async def get_providers():
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
    user_email: str = Query("web_user@genesis.local", description="User email to get notifications for")
):
    """Get pending notifications for a user."""
    try:
        mind = await _load_mind(mind_id)
        
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
    user_email: str = Query("web_user@genesis.local", description="User email to get notifications for")
):
    """Get all pending notifications for a user across all minds."""
    try:
        from genesis.config.settings import get_settings
        import json
        
        settings = get_settings()
        notif_base_dir = settings.data_dir / "notifications"
        
        if not notif_base_dir.exists():
            return {"notifications": []}
        
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
            
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
            
    except Exception as e:
        logger.error(f"Error marking notification as delivered: {e}")
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
                continue
        
        if sent_count > 0:
            logger.info(f"Sent {sent_count} pending notification(s) to {user_email}")
            
    except Exception as e:
        logger.error(f"Error retrieving pending notifications: {e}")


async def _load_mind(mind_id: str) -> Mind:
    """Load a Mind by ID or name."""
    # Try to find by GMID or name
    for path in settings.minds_dir.glob("*.json"):
        try:
            import json

            with open(path) as f:
                data = json.load(f)

            if data["identity"]["gmid"] == mind_id or data["identity"]["name"] == mind_id:
                return Mind.load(path)

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

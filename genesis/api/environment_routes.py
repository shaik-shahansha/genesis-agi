"""
Environment API routes - WebSocket-based real-time environments.
"""

from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel, Field

from genesis.environments.realtime import get_environment_server
from genesis.environments.templates import (
    ENVIRONMENT_TEMPLATES,
    create_environment_from_template,
    list_templates,
    get_template_info,
)
from genesis.database.manager import MetaverseDB
from genesis.api.auth import get_current_active_user, get_current_user, User, UserRole


router = APIRouter()


# ==================== Request/Response Models ====================

class CreateEnvironmentRequest(BaseModel):
    """Request to create environment."""
    name: str = Field(..., min_length=3, max_length=100)
    env_type: str = "digital"
    description: Optional[str] = ""
    is_public: bool = True
    max_occupancy: int = Field(default=10, ge=1, le=1000)
    template: Optional[str] = None  # Optional template to use


class UpdateEnvironmentRequest(BaseModel):
    """Request to update environment."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    max_occupancy: Optional[int] = None


# ==================== Endpoints ====================

@router.post("/create")
async def create_environment(
    request: CreateEnvironmentRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new environment."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    import uuid
    
    # Use email for user identification, fallback to username if email not available
    user_identifier = current_user.email if current_user.email else current_user.username
    
    # Check if creator is a Mind (starts with GMD- or GMID-) or a user
    is_mind_creator = user_identifier.startswith(('GMD-', 'GMID-'))
    
    # If not a Mind, set owner_gmid to None and store user email in metadata
    owner_gmid = user_identifier if is_mind_creator else None

    if request.template:
        # Create from template
        try:
            env = create_environment_from_template(
                template_name=request.template,
                creator_gmid=owner_gmid,
                custom_name=request.name,
                is_public=request.is_public,
                user_creator=None if is_mind_creator else user_identifier,
            )
            # Access attributes immediately while session might still be active
            env_data = {
                "id": env.env_id,
                "name": env.name,
                "env_type": env.env_type,
                "description": env.description,
                "creator_gmid": env.owner_gmid,
                "creator_user": env.extra_metadata.get('user_creator') if env.extra_metadata else None,
                "is_public": env.is_public,
                "max_occupancy": env.extra_metadata.get('max_occupancy', request.max_occupancy) if env.extra_metadata else request.max_occupancy,
                "created_at": env.created_at.isoformat(),
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Create custom environment
        with get_session() as session:
            env_id = f"ENV-{uuid.uuid4().hex[:8].upper()}"
            
            # Prepare metadata with user creator if applicable
            metadata = {"max_occupancy": request.max_occupancy or 10}
            if not is_mind_creator:
                metadata["user_creator"] = user_identifier
            
            env = EnvironmentRecord(
                env_id=env_id,
                name=request.name,
                env_type=request.env_type,
                owner_gmid=owner_gmid,
                is_public=request.is_public,
                is_shared=False,
                description=request.description,
                extra_metadata=metadata,
                created_at=datetime.utcnow(),
            )
            session.add(env)
            session.commit()
            session.refresh(env)
            
            # Extract data while session is active
            env_data = {
                "id": env.env_id,
                "name": env.name,
                "env_type": env.env_type,
                "description": env.description,
                "creator_gmid": env.owner_gmid,
                "creator_user": metadata.get('user_creator'),
                "is_public": env.is_public,
                "max_occupancy": env.extra_metadata.get('max_occupancy', request.max_occupancy) if env.extra_metadata else request.max_occupancy,
                "created_at": env.created_at.isoformat(),
            }

    return {
        "success": True,
        "environment_id": env_data["id"],
        "environment": env_data
    }


@router.get("/list")
async def list_environments(
    is_public: Optional[bool] = Query(None),
    env_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """List available environments."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    with get_session() as session:
        query = session.query(EnvironmentRecord)
        
        # Filter
        if is_public is not None:
            query = query.filter_by(is_public=is_public)
        
        if env_type:
            query = query.filter_by(env_type=env_type)
        
        # Get total count
        total = query.count()
        
        # Paginate
        envs = query.offset(offset).limit(limit).all()
        
        # Convert to dict while session is active
        env_dicts = []
        for e in envs:
            env_dicts.append({
                "id": e.env_id,
                "name": e.name,
                "env_type": e.env_type,
                "description": e.description,
                "creator_gmid": e.owner_gmid,
                "is_public": e.is_public,
                "max_occupancy": e.extra_metadata.get('max_occupancy', 10) if e.extra_metadata else 10,
                "created_at": e.created_at.isoformat(),
            })
    
    # Get real-time info (occupancy) after session is closed
    env_server = get_environment_server()
    for env_dict in env_dicts:
        env_id = env_dict["id"]
        env_dict["current_occupancy"] = len(env_server.get_or_create_state(env_id).present_minds) if env_id in env_server.environment_states else 0

    return {
        "environments": env_dicts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/accessible")
async def get_accessible_environments(
    user_email: str = Query(..., description="User email to filter accessible environments"),
    mind_gmid: Optional[str] = Query(None, description="Optional Mind GMID to filter by Mind access"),
):
    """Get environments accessible to a user and optionally a specific Mind."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    try:
        with get_session() as session:
            all_envs = session.query(EnvironmentRecord).all()
            
            accessible = []
            for env in all_envs:
                # Check if user has access
                is_public = env.is_public
                allowed_users = env.allowed_users if env.allowed_users else []
                allowed_minds = env.allowed_minds if env.allowed_minds else []
                
                # User has access if:
                # 1. Environment is public, OR
                # 2. User email is in allowed_users, OR
                # 3. User is the owner
                user_has_access = (
                    is_public or
                    user_email in allowed_users or
                    env.owner_gmid == user_email
                )
                
                # If mind_gmid provided, also check Mind access
                if mind_gmid:
                    mind_has_access = (
                        is_public or
                        mind_gmid in allowed_minds or
                        mind_gmid == env.owner_gmid
                    )
                else:
                    mind_has_access = True
                
                if user_has_access and mind_has_access:
                    accessible.append({
                        "env_id": env.env_id,
                        "name": env.name,
                        "env_type": env.env_type,
                        "is_public": is_public,
                        "owner_gmid": env.owner_gmid,
                        "created_at": env.created_at.isoformat() if env.created_at else None,
                    })
            
            # If no environments found and mind_gmid provided, create a default personal environment
            if not accessible and mind_gmid:
                from genesis.database.base import get_session
                from genesis.database.models import EnvironmentRecord
                default_env_id = f"{mind_gmid}-home"
                
                # Check if default environment already exists, create if not
                with get_session() as session:
                    default_env = session.query(EnvironmentRecord).filter_by(env_id=default_env_id).first()
                    
                    if not default_env:
                        # Create new default environment
                        default_env = EnvironmentRecord(
                            env_id=default_env_id,
                            name=f"{mind_gmid}'s Personal Space",
                            env_type="personal",
                            owner_gmid=mind_gmid,
                            is_public=False,
                            is_shared=False,
                            description="Personal environment for private thoughts and work",
                            metadata={},
                            created_at=datetime.utcnow(),
                        )
                        session.add(default_env)
                        session.commit()
                        session.refresh(default_env)
                    
                    # Extract data while session is active
                    accessible.append({
                        "env_id": default_env.env_id,
                        "name": default_env.name,
                        "env_type": default_env.env_type,
                        "is_public": default_env.is_public,
                        "owner_gmid": default_env.owner_gmid,
                        "created_at": default_env.created_at.isoformat() if default_env.created_at else None,
                    })
        
            return {
                "environments": accessible,
                "count": len(accessible),
                "user_email": user_email,
                "mind_gmid": mind_gmid,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching environments: {str(e)}")


@router.get("/active")
async def get_active_environments():
    """Get all currently active environments (with people in them)."""
    env_server = get_environment_server()
    active = env_server.get_all_active_environments()

    return {
        "active_environments": active,
        "count": len(active),
    }


@router.get("/{environment_id}")
async def get_environment(environment_id: str):
    """Get environment details."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    with get_session() as session:
        env = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()
        
        if not env:
            raise HTTPException(status_code=404, detail="Environment not found")
        
        # Extract data while session is active
        env_data = {
            "id": env.env_id,
            "name": env.name,
            "env_type": env.env_type,
            "description": env.description,
            "creator_gmid": env.owner_gmid,
            "is_public": env.is_public,
            "max_occupancy": env.extra_metadata.get('max_occupancy', 10) if env.extra_metadata else 10,
            "metadata": env.extra_metadata,
            "created_at": env.created_at.isoformat(),
        }
    
    # Get real-time state after session is closed
    env_server = get_environment_server()
    state_info = env_server.get_environment_info(environment_id)
    env_data["realtime_state"] = state_info
    
    return env_data


@router.put("/{environment_id}")
async def update_environment(
    environment_id: str,
    request: UpdateEnvironmentRequest,
    current_user: User = Depends(get_current_user),
):
    """Update environment (creator only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    # Use email for user identification
    user_identifier = current_user.email if current_user.email else current_user.username
    
    with get_session() as session:
        env = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

        if not env:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check ownership: Mind ownership via owner_gmid OR User ownership via metadata
        is_mind_owner = env.owner_gmid == user_identifier
        is_user_owner = (
            env.extra_metadata and 
            env.extra_metadata.get('user_creator') == user_identifier
        )
        
        if not (is_mind_owner or is_user_owner):
            raise HTTPException(status_code=403, detail="Only creator can update environment")

        # Update fields
        if request.name:
            env.name = request.name
        if request.description:
            env.description = request.description
        if request.is_public is not None:
            env.is_public = request.is_public
        if request.max_occupancy:
            if not env.extra_metadata:
                env.extra_metadata = {}
            env.extra_metadata['max_occupancy'] = request.max_occupancy

        session.commit()

    return {"success": True}


@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete environment (creator only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    # Use email for user identification
    user_identifier = current_user.email if current_user.email else current_user.username
    
    with get_session() as session:
        env = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

        if not env:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check ownership: Mind ownership via owner_gmid OR User ownership via metadata
        is_mind_owner = env.owner_gmid == user_identifier
        is_user_owner = (
            env.extra_metadata and 
            env.extra_metadata.get('user_creator') == user_identifier
        )
        
        if not (is_mind_owner or is_user_owner):
            raise HTTPException(status_code=403, detail="Only creator can delete environment")

        session.delete(env)
        session.commit()

    return {"success": True}


@router.post("/{environment_id}/add-user")
async def add_user_to_environment(
    environment_id: str,
    user_email: str = Query(..., description="Email address to grant access"),
    current_user: User = Depends(get_current_user),
):
    """Add a user email to environment's allowed_users list (creator only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    # Use email for user identification
    user_identifier = current_user.email if current_user.email else current_user.username
    
    with get_session() as session:
        env_record = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

        if not env_record:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check ownership: Mind ownership via owner_gmid OR User ownership via metadata
        is_mind_owner = env_record.owner_gmid == user_identifier
        is_user_owner = (
            env_record.extra_metadata and 
            env_record.extra_metadata.get('user_creator') == user_identifier
        )
        
        if not (is_mind_owner or is_user_owner):
            raise HTTPException(status_code=403, detail="Only creator can manage access")

        # Get allowed_users list
        if not env_record.allowed_users:
            env_record.allowed_users = []
        
        if user_email in env_record.allowed_users:
            return {
                "success": True,
                "message": f"User {user_email} already has access",
                "allowed_users": env_record.allowed_users
            }
        
        # Add user
        env_record.allowed_users.append(user_email)
        session.commit()
        allowed_users = env_record.allowed_users

    return {
        "success": True,
        "message": f"Added user {user_email} to environment",
        "allowed_users": allowed_users
    }


@router.delete("/{environment_id}/remove-user")
async def remove_user_from_environment(
    environment_id: str,
    user_email: str = Query(..., description="Email address to revoke access"),
    current_user: User = Depends(get_current_user),
):
    """Remove a user email from environment's allowed_users list (creator only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    # Use email for user identification
    user_identifier = current_user.email if current_user.email else current_user.username
    
    with get_session() as session:
        env_record = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

        if not env_record:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check ownership: Mind ownership via owner_gmid OR User ownership via metadata
        is_mind_owner = env_record.owner_gmid == user_identifier
        is_user_owner = (
            env_record.extra_metadata and 
            env_record.extra_metadata.get('user_creator') == user_identifier
        )
        
        if not (is_mind_owner or is_user_owner):
            raise HTTPException(status_code=403, detail="Only creator can manage access")

        # Get allowed_users list
        if not env_record.allowed_users:
            env_record.allowed_users = []
        
        if user_email not in env_record.allowed_users:
            return {
                "success": True,
                "message": f"User {user_email} doesn't have access",
                "allowed_users": env_record.allowed_users
            }
        
        # Remove user
        env_record.allowed_users.remove(user_email)
        session.commit()
        allowed_users = env_record.allowed_users

    return {
        "success": True,
        "message": f"Removed user {user_email} from environment",
        "allowed_users": allowed_users
    }


@router.post("/{environment_id}/set-public")
async def set_environment_public(environment_id: str, body: Dict[str, bool], current_user: User = Depends(get_current_user)):
    """Set environment public or private (owner, creator, or admin only)."""
    if 'is_public' not in body:
        raise HTTPException(status_code=400, detail="'is_public' is required")

    is_public_val = bool(body.get('is_public'))
    user_identifier = current_user.email if current_user.email else current_user.username

    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    from genesis.database.manager import MetaverseDB

    with get_session() as session:
        env = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()
        if not env:
            raise HTTPException(status_code=404, detail="Environment not found")

        creator_user = env.extra_metadata.get('user_creator') if env.extra_metadata else None
        is_owner = (env.owner_gmid == user_identifier) or (creator_user == user_identifier)
        is_admin = getattr(current_user, 'role', None) == UserRole.ADMIN or getattr(current_user, 'role', None) == 'admin'

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Only owner, creator, or admin can manage access")

    db = MetaverseDB()
    updated = db.set_environment_public(environment_id, is_public_val)

    # Also persist any in-memory update if needed
    return {"success": True, "message": "Updated is_public", "is_public": is_public_val}


@router.get("/{environment_id}/access")
async def get_environment_access(environment_id: str, current_user: User = Depends(get_current_active_user)):
    """Return an Environment's access list (owner or admin)."""
    from genesis.database.manager import MetaverseDB
    db = MetaverseDB()

    # Determine identifier
    user_identifier = current_user.email if current_user.email else current_user.username

    is_owner = False
    try:
        env = db.get_environment(environment_id)
        if env:
            is_owner = (env.owner_gmid == user_identifier)
    except Exception:
        pass

    is_admin = getattr(current_user, 'role', None) == UserRole.ADMIN or getattr(current_user, 'role', None) == 'admin'

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Only owner or admin can view access list")

    allowed_users = db.get_environment_allowed_users(environment_id)
    is_public = bool(getattr(db.get_environment(environment_id), 'is_public', False))
    return {"is_public": is_public, "allowed_users": allowed_users}


@router.post("/{environment_id}/add-mind")
async def add_mind_to_environment(
    environment_id: str,
    mind_gmid: str = Query(..., description="GMID of Mind to grant access"),
    current_user: User = Depends(get_current_user),
):
    """Add a Mind to environment's allowed_minds list (creator only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    # Use email for user identification
    user_identifier = current_user.email if current_user.email else current_user.username
    
    with get_session() as session:
        env_record = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

        if not env_record:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check ownership: Mind ownership via owner_gmid OR User ownership via metadata
        is_mind_owner = env_record.owner_gmid == user_identifier
        is_user_owner = (
            env_record.extra_metadata and 
            env_record.extra_metadata.get('user_creator') == user_identifier
        )
        
        if not (is_mind_owner or is_user_owner):
            raise HTTPException(status_code=403, detail="Only creator can manage access")

        # Get allowed_minds list
        if not env_record.allowed_minds:
            env_record.allowed_minds = []
        
        if mind_gmid in env_record.allowed_minds:
            return {
                "success": True,
                "message": f"Mind {mind_gmid} already has access",
                "allowed_minds": env_record.allowed_minds
            }
        
        # Add Mind
        env_record.allowed_minds.append(mind_gmid)
        session.commit()
        allowed_minds = env_record.allowed_minds

    return {
        "success": True,
        "message": f"Added Mind {mind_gmid} to environment",
        "allowed_minds": allowed_minds
    }


@router.delete("/{environment_id}/remove-mind")
async def remove_mind_from_environment(
    environment_id: str,
    mind_gmid: str = Query(..., description="GMID of Mind to revoke access"),
    current_user: User = Depends(get_current_user),
):
    """Remove a Mind from environment's allowed_minds list (creator only)."""
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    
    # Use email for user identification
    user_identifier = current_user.email if current_user.email else current_user.username
    
    with get_session() as session:
        env_record = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

        if not env_record:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check ownership: Mind ownership via owner_gmid OR User ownership via metadata
        is_mind_owner = env_record.owner_gmid == user_identifier
        is_user_owner = (
            env_record.extra_metadata and 
            env_record.extra_metadata.get('user_creator') == user_identifier
        )
        
        if not (is_mind_owner or is_user_owner):
            raise HTTPException(status_code=403, detail="Only creator can manage access")

        # Get allowed_minds list
        if not env_record.allowed_minds:
            env_record.allowed_minds = []
        
        if mind_gmid not in env_record.allowed_minds:
            return {
                "success": True,
                "message": f"Mind {mind_gmid} doesn't have access",
                "allowed_minds": env_record.allowed_minds
            }
        
        # Remove Mind
        env_record.allowed_minds.remove(mind_gmid)
        session.commit()
        allowed_minds = env_record.allowed_minds

    return {
        "success": True,
        "message": f"Removed Mind {mind_gmid} from environment",
        "allowed_minds": allowed_minds
    }


@router.get("/templates/list")
async def get_templates():
    """Get all available environment templates."""
    return {
        "templates": [
            {
                "name": name,
                "description": desc,
                "details": get_template_info(name),
            }
            for name, desc in list_templates().items()
        ]
    }


@router.get("/templates/{template_name}")
async def get_template(template_name: str):
    """Get details of a specific template."""
    info = get_template_info(template_name)

    if not info:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template_name": template_name,
        "info": info,
    }


@router.websocket("/ws/{environment_id}")
async def websocket_environment(
    websocket: WebSocket,
    environment_id: str,
    mind_id: str = Query(...),
    mind_name: str = Query(...),
):
    """
    WebSocket endpoint for real-time environment interaction.

    Params:
        - environment_id: ID of environment to join
        - mind_id: GMID of Mind joining
        - mind_name: Name of Mind joining
    """
    env_server = get_environment_server()

    try:
        await env_server.handle_connection(
            environment_id=environment_id,
            mind_id=mind_id,
            mind_name=mind_name,
            websocket=websocket,
        )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

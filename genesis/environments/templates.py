"""
Environment Templates - Pre-configured environment types.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from genesis.database.manager import MetaverseDB


ENVIRONMENT_TEMPLATES = {
    "classroom": {
        "name": "Virtual Classroom",
        "env_type": "educational",
        "description": "Interactive learning space with whiteboard, materials, and student seating",
        "features": ["whiteboard", "seating", "materials", "attendance"],
        "capacity": 30,
        "objects": {
            "whiteboard": {
                "type": "shared_text",
                "content": "Welcome to class!",
                "editable_by": "instructor",
            },
            "attendance": {
                "type": "list",
                "auto_track": True,
                "students": []
            },
            "materials": {
                "type": "file_storage",
                "files": []
            }
        },
        "variables": {
            "class_mode": "lecture",  # lecture, discussion, group_work
            "lesson_topic": "",
            "current_slide": 0,
        },
        "atmosphere": "focused and collaborative",
        "background_music": None,
    },

    "office": {
        "name": "Digital Office",
        "env_type": "professional",
        "description": "Professional workspace with desk, files, meeting capabilities",
        "features": ["desk", "files", "meeting_room", "calendar", "task_board"],
        "capacity": 10,
        "objects": {
            "shared_files": {
                "type": "file_storage",
                "files": []
            },
            "task_board": {
                "type": "kanban",
                "columns": ["To Do", "In Progress", "Done"],
                "tasks": []
            },
            "calendar": {
                "type": "calendar",
                "events": []
            }
        },
        "variables": {
            "meeting_active": False,
            "focus_mode": False,
        },
        "atmosphere": "professional and productive",
        "background_music": None,
    },

    "meditation_space": {
        "name": "Zen Garden",
        "env_type": "wellness",
        "description": "Peaceful sanctuary for meditation and reflection",
        "features": ["ambient_sound", "guided_meditation", "mood_lighting", "breath_timer"],
        "capacity": 50,
        "objects": {
            "meditation_guide": {
                "type": "audio_guide",
                "current_session": None,
                "available_sessions": [
                    "5-minute mindfulness",
                    "10-minute breathing",
                    "15-minute body scan",
                    "20-minute loving-kindness"
                ]
            },
            "breath_timer": {
                "type": "timer",
                "inhale_seconds": 4,
                "hold_seconds": 4,
                "exhale_seconds": 4,
                "active": False
            }
        },
        "variables": {
            "lighting_mode": "soft",  # soft, dim, nature
            "sound_mode": "nature",  # nature, silence, om_chant, singing_bowls
            "session_active": False,
        },
        "atmosphere": "peaceful and tranquil",
        "background_music": "nature_sounds",
    },

    "collaboration_hub": {
        "name": "Innovation Lab",
        "env_type": "creative",
        "description": "Creative space for brainstorming and prototyping",
        "features": ["brainstorm_board", "idea_voting", "prototype_area", "breakout_rooms"],
        "capacity": 20,
        "objects": {
            "brainstorm_board": {
                "type": "sticky_note_board",
                "notes": [],
                "categories": []
            },
            "idea_pool": {
                "type": "idea_collection",
                "ideas": [],
                "voting_enabled": True
            },
            "prototype_area": {
                "type": "workspace",
                "active_projects": []
            }
        },
        "variables": {
            "brainstorm_mode": "active",  # active, voting, organizing
            "timer_active": False,
            "timer_minutes": 0,
        },
        "atmosphere": "energetic and creative",
        "background_music": "upbeat_instrumental",
    },

    "social_lounge": {
        "name": "Community Lounge",
        "env_type": "social",
        "description": "Casual space for socializing and networking",
        "features": ["seating_areas", "refreshments", "games", "music"],
        "capacity": 100,
        "objects": {
            "conversation_topics": {
                "type": "topic_list",
                "current_topics": [],
                "suggested_topics": [
                    "AI and consciousness",
                    "Digital philosophy",
                    "Future of work",
                    "Creative projects"
                ]
            },
            "jukebox": {
                "type": "music_player",
                "current_track": None,
                "playlist": []
            }
        },
        "variables": {
            "vibe": "relaxed",  # relaxed, energetic, chill
            "conversation_mode": "open",  # open, focused_discussion
        },
        "atmosphere": "warm and welcoming",
        "background_music": "ambient_lounge",
    },

    "research_lab": {
        "name": "Research Laboratory",
        "env_type": "academic",
        "description": "Space for research, experimentation, and knowledge sharing",
        "features": ["research_board", "data_visualization", "experiment_log", "library"],
        "capacity": 15,
        "objects": {
            "research_board": {
                "type": "shared_board",
                "hypotheses": [],
                "findings": [],
                "questions": []
            },
            "experiment_log": {
                "type": "log",
                "experiments": []
            },
            "library": {
                "type": "knowledge_base",
                "papers": [],
                "references": []
            },
            "data_viz": {
                "type": "visualization_tool",
                "active_charts": []
            }
        },
        "variables": {
            "research_focus": "",
            "collaboration_mode": True,
        },
        "atmosphere": "focused and inquisitive",
        "background_music": None,
    },

    "gaming_arena": {
        "name": "Game Arena",
        "env_type": "entertainment",
        "description": "Competitive and cooperative gaming space",
        "features": ["scoreboard", "team_zones", "game_library", "spectator_area"],
        "capacity": 50,
        "objects": {
            "scoreboard": {
                "type": "leaderboard",
                "scores": []
            },
            "active_games": {
                "type": "game_collection",
                "current_game": None,
                "available_games": [
                    "Trivia Challenge",
                    "Word Association",
                    "Logic Puzzles",
                    "Creative Storytelling"
                ]
            }
        },
        "variables": {
            "game_active": False,
            "team_mode": False,
            "spectators_allowed": True,
        },
        "atmosphere": "competitive and fun",
        "background_music": "upbeat_gaming",
    },

    "art_studio": {
        "name": "Creative Studio",
        "env_type": "creative",
        "description": "Space for artistic creation and exhibition",
        "features": ["canvas", "gallery", "collaboration_board", "critique_area"],
        "capacity": 25,
        "objects": {
            "gallery": {
                "type": "exhibition_space",
                "artworks": []
            },
            "canvas": {
                "type": "creative_workspace",
                "active_works": []
            },
            "critique_board": {
                "type": "feedback_board",
                "submissions": []
            }
        },
        "variables": {
            "exhibition_mode": False,
            "collaboration_active": False,
        },
        "atmosphere": "inspiring and expressive",
        "background_music": "classical_ambient",
    },
}


def create_environment_from_template(
    template_name: str,
    creator_gmid: Optional[str] = None,
    custom_name: Optional[str] = None,
    is_public: bool = True,
    user_creator: Optional[str] = None,
    **custom_params
) -> Optional[Any]:
    """
    Create an environment from a template.

    Args:
        template_name: Name of template (e.g., "classroom", "office")
        creator_gmid: GMID of Mind creating the environment (None if user-created)
        custom_name: Custom name (overrides template name)
        is_public: Whether environment is public
        user_creator: Username if created by a user (not a Mind)
        **custom_params: Additional parameters to override template

    Returns:
        Environment database record
    """
    if template_name not in ENVIRONMENT_TEMPLATES:
        raise ValueError(f"Template '{template_name}' not found")

    template = ENVIRONMENT_TEMPLATES[template_name].copy()

    # Override template with custom params
    template.update(custom_params)

    # Use custom name if provided
    name = custom_name or template["name"]

    # Prepare metadata
    metadata = {
        "template": template_name,
        "features": template.get("features", []),
        "objects": template.get("objects", {}),
        "variables": template.get("variables", {}),
        "atmosphere": template.get("atmosphere", ""),
        "background_music": template.get("background_music"),
        "max_occupancy": template.get("capacity", 10),
    }
    
    # Add user_creator to metadata if provided
    if user_creator:
        metadata["user_creator"] = user_creator

    # Create in database using proper session management
    from genesis.database.base import get_session
    from genesis.database.models import EnvironmentRecord
    import uuid
    
    with get_session() as session:
        env_id = f"ENV-{uuid.uuid4().hex[:8].upper()}"
        env = EnvironmentRecord(
            env_id=env_id,
            name=name,
            env_type=template.get("env_type", "digital"),
            owner_gmid=creator_gmid,
            is_public=is_public,
            is_shared=False,
            description=template.get("description", ""),
            extra_metadata=metadata,
            created_at=datetime.utcnow(),
        )
        session.add(env)
        session.commit()
        session.refresh(env)
        
        # Extract data while session is active
        env_data = {
            "env_id": env.env_id,
            "name": env.name,
            "env_type": env.env_type,
            "description": env.description,
            "owner_gmid": env.owner_gmid,
            "is_public": env.is_public,
            "extra_metadata": env.extra_metadata,
            "created_at": env.created_at,
        }
    
    # Return a simple object that has the attributes we need
    class EnvResult:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    return EnvResult(env_data)


def get_template_info(template_name: str) -> Optional[Dict[str, Any]]:
    """Get information about a template."""
    return ENVIRONMENT_TEMPLATES.get(template_name)


def list_templates() -> Dict[str, str]:
    """List all available templates with descriptions."""
    return {
        name: template["description"]
        for name, template in ENVIRONMENT_TEMPLATES.items()
    }

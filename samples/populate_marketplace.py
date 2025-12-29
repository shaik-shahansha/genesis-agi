"""
Populate marketplace with sample Minds and Environments.

Run this script to add sample content to the Genesis Marketplace.
"""

import json
import os
from pathlib import Path

from genesis.marketplace.manager import MarketplaceManager
from genesis.database.marketplace_models import ItemType
from genesis.environments.templates import create_environment_from_template, ENVIRONMENT_TEMPLATES
from genesis.database.manager import MetaverseDB


def load_mind_config(filename: str) -> dict:
    """Load Mind configuration from JSON file."""
    filepath = Path(__file__).parent / "minds" / filename
    with open(filepath, 'r') as f:
        return json.load(f)


def populate_sample_minds():
    """Add sample Minds to marketplace."""
    print("🧠 Populating sample Minds...")

    manager = MarketplaceManager()

    # Sample Minds configurations
    mind_files = [
        "maria_teacher.json",
        "atlas_explorer.json",
        "luna_therapist.json",
        "codemaster_developer.json",
        "sage_mentor.json",
    ]

    created_count = 0

    for mind_file in mind_files:
        try:
            config = load_mind_config(mind_file)

            # Create marketplace listing
            listing = manager.create_listing(
                seller_id="genesis_official",
                seller_name="Genesis Team",
                item_type=ItemType.MIND,
                title=f"{config['name']} - {config['category'].replace('_', ' ').title()}",
                description=config['description'],
                price=config['price_essence'],
                data=config,  # Full Mind configuration
                category=config['category'],
                tags=config['tags'],
                preview_image=config.get('preview_image'),
                screenshots=config.get('screenshots', []),
            )

            # Mark as featured
            listing.featured = 1
            listing.rating = 4.8  # High initial rating
            manager.session.commit()

            print(f"  ✅ Created: {config['name']} (ID: {listing.id})")
            created_count += 1

        except Exception as e:
            print(f"  ❌ Error creating {mind_file}: {e}")

    print(f"\n✨ Created {created_count} sample Minds!")
    return created_count


def populate_sample_environments():
    """Add sample Environments to marketplace."""
    print("\n🌍 Populating sample Environments...")

    manager = MarketplaceManager()
    db = MetaverseDB()

    # Sample environments to create
    sample_envs = [
        {
            "template": "classroom",
            "name": "AI Ethics 101",
            "description": "Learn about responsible AI development and ethics in this interactive classroom",
            "price": 100,
            "category": "education",
            "tags": ["education", "ai", "ethics", "classroom"],
        },
        {
            "template": "meditation_space",
            "name": "Peaceful Sanctuary",
            "description": "Find inner peace and clarity in this zen garden meditation space",
            "price": 80,
            "category": "wellness",
            "tags": ["wellness", "meditation", "mindfulness", "zen"],
        },
        {
            "template": "collaboration_hub",
            "name": "Innovation Lab",
            "description": "Brainstorm and prototype new ideas in this creative collaboration space",
            "price": 150,
            "category": "creative",
            "tags": ["creative", "collaboration", "innovation", "brainstorming"],
        },
        {
            "template": "office",
            "name": "Professional Workspace",
            "description": "Productive digital office with all the tools you need for professional work",
            "price": 120,
            "category": "professional",
            "tags": ["professional", "office", "productivity", "workspace"],
        },
        {
            "template": "social_lounge",
            "name": "Community Hub",
            "description": "Casual space for socializing, networking, and community building",
            "price": 90,
            "category": "social",
            "tags": ["social", "networking", "community", "casual"],
        },
    ]

    created_count = 0

    for env_config in sample_envs:
        try:
            # Get template info
            template = ENVIRONMENT_TEMPLATES[env_config["template"]]

            # Create marketplace listing
            listing_data = {
                "template": env_config["template"],
                "name": env_config["name"],
                "env_type": template["env_type"],
                "description": env_config["description"],
                "is_public": True,
                "max_occupancy": template["capacity"],
                "features": template["features"],
                "atmosphere": template["atmosphere"],
            }

            listing = manager.create_listing(
                seller_id="genesis_official",
                seller_name="Genesis Team",
                item_type=ItemType.ENVIRONMENT,
                title=env_config["name"],
                description=env_config["description"],
                price=env_config["price"],
                data=listing_data,
                category=env_config["category"],
                tags=env_config["tags"],
            )

            # Mark as featured
            listing.featured = 1
            listing.rating = 4.7
            manager.session.commit()

            print(f"  ✅ Created: {env_config['name']} (ID: {listing.id})")
            created_count += 1

        except Exception as e:
            print(f"  ❌ Error creating {env_config['name']}: {e}")

    print(f"\n✨ Created {created_count} sample Environments!")
    return created_count


def populate_sample_skills():
    """Add sample Skill packages to marketplace."""
    print("\n🎯 Populating sample Skills...")

    manager = MarketplaceManager()

    sample_skills = [
        {
            "name": "Advanced Python",
            "description": "Master advanced Python concepts: decorators, generators, metaclasses, and async programming",
            "price": 50,
            "category": "programming",
            "tags": ["python", "programming", "advanced"],
            "skill_data": {
                "skill_name": "advanced_python",
                "skill_level": 0.8,
                "topics": [
                    "decorators",
                    "generators",
                    "context_managers",
                    "metaclasses",
                    "async_await"
                ]
            }
        },
        {
            "name": "Emotional Intelligence",
            "description": "Enhance empathy, active listening, and emotional awareness skills",
            "price": 60,
            "category": "personal_development",
            "tags": ["emotional-intelligence", "empathy", "soft-skills"],
            "skill_data": {
                "skill_name": "emotional_intelligence",
                "skill_level": 0.7,
                "topics": [
                    "active_listening",
                    "empathy",
                    "emotional_awareness",
                    "conflict_resolution"
                ]
            }
        },
        {
            "name": "Creative Writing",
            "description": "Develop storytelling, narrative structure, and creative expression skills",
            "price": 45,
            "category": "creative",
            "tags": ["writing", "creative", "storytelling"],
            "skill_data": {
                "skill_name": "creative_writing",
                "skill_level": 0.7,
                "topics": [
                    "narrative_structure",
                    "character_development",
                    "dialogue",
                    "descriptive_writing"
                ]
            }
        },
    ]

    created_count = 0

    for skill in sample_skills:
        try:
            listing = manager.create_listing(
                seller_id="genesis_official",
                seller_name="Genesis Team",
                item_type=ItemType.SKILL,
                title=skill["name"],
                description=skill["description"],
                price=skill["price"],
                data=skill["skill_data"],
                category=skill["category"],
                tags=skill["tags"],
            )

            listing.rating = 4.6
            manager.session.commit()

            print(f"  ✅ Created: {skill['name']} (ID: {listing.id})")
            created_count += 1

        except Exception as e:
            print(f"  ❌ Error creating {skill['name']}: {e}")

    print(f"\n✨ Created {created_count} sample Skills!")
    return created_count


def main():
    """Main function to populate marketplace."""
    print("=" * 60)
    print("  GENESIS MARKETPLACE - SAMPLE CONTENT POPULATION")
    print("=" * 60)
    print()

    minds_count = populate_sample_minds()
    envs_count = populate_sample_environments()
    skills_count = populate_sample_skills()

    print("\n" + "=" * 60)
    print(f"  ✅ COMPLETE! Total items created: {minds_count + envs_count + skills_count}")
    print(f"     • {minds_count} Minds")
    print(f"     • {envs_count} Environments")
    print(f"     • {skills_count} Skills")
    print("=" * 60)
    print()
    print("🚀 Your Genesis Marketplace is now populated with sample content!")
    print("   Visit the marketplace to browse and purchase these items.")
    print()


if __name__ == "__main__":
    main()

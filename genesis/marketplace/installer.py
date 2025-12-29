"""
Item Installer - Install purchased marketplace items.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from genesis.core.mind import Mind
from genesis.core.mind_config import MindConfig
from genesis.database.marketplace_models import ItemType


class ItemInstaller:
    """Install purchased marketplace items."""

    @staticmethod
    def install_item(
        buyer_id: str,
        item_type: ItemType,
        item_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Install purchased item for buyer."""
        if item_type == ItemType.MIND:
            return ItemInstaller.install_mind(buyer_id, item_data)
        elif item_type == ItemType.ENVIRONMENT:
            return ItemInstaller.install_environment(buyer_id, item_data)
        elif item_type == ItemType.SKILL:
            return ItemInstaller.install_skill(buyer_id, item_data)
        elif item_type == ItemType.MEMORY_PACK:
            return ItemInstaller.install_memory_pack(buyer_id, item_data)
        elif item_type == ItemType.PERSONALITY_TRAIT:
            return ItemInstaller.install_personality_trait(buyer_id, item_data)
        elif item_type == ItemType.TOOL:
            return ItemInstaller.install_tool(buyer_id, item_data)
        else:
            return {"success": False, "error": f"Unknown item type: {item_type}"}

    @staticmethod
    def install_mind(buyer_id: str, mind_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install a pre-configured Mind."""
        try:
            # Extract Mind configuration
            name = mind_data.get("name", "Purchased Mind")
            template = mind_data.get("template")
            personality_traits = mind_data.get("personality_traits", {})
            plugins = mind_data.get("plugins", [])
            skills = mind_data.get("skills", [])

            # Create Mind configuration
            config = MindConfig()

            # Add plugins based on configuration
            from genesis.core.mind_config import MindConfig
            if "minimal" in mind_data.get("config_level", "standard"):
                config = MindConfig.minimal()
            elif "full" in mind_data.get("config_level", "standard"):
                config = MindConfig.full()
            else:
                config = MindConfig.standard()

            # Birth the Mind
            mind = Mind.birth(
                name=name,
                creator=buyer_id,
                template=template,
                config=config,
            )

            # Apply personality traits
            if personality_traits:
                for trait, value in personality_traits.items():
                    if hasattr(mind.personality, trait):
                        setattr(mind.personality, trait, value)

            # Add skills
            if skills and hasattr(mind, 'learning'):
                for skill in skills:
                    mind.learning.add_skill(skill, level=0.5)

            # Save Mind
            mind.save()

            return {
                "success": True,
                "mind_id": mind.gmid,
                "name": name,
                "message": f"Successfully installed Mind: {name}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def install_environment(buyer_id: str, env_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install a pre-configured Environment."""
        try:
            from genesis.database.manager import MetaverseDB

            db = MetaverseDB()

            # Create environment
            env = db.create_environment(
                creator_gmid=buyer_id,
                name=env_data.get("name", "Purchased Environment"),
                env_type=env_data.get("env_type", "digital"),
                description=env_data.get("description", ""),
                is_public=env_data.get("is_public", False),
                max_occupancy=env_data.get("max_occupancy", 10),
                metadata=env_data.get("metadata", {}),
            )

            return {
                "success": True,
                "environment_id": env.id,
                "name": env.name,
                "message": f"Successfully installed Environment: {env.name}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def install_skill(buyer_id: str, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install a skill package to a Mind."""
        try:
            # Get target Mind
            target_mind_id = skill_data.get("target_mind_id")
            if not target_mind_id:
                return {"success": False, "error": "No target Mind specified"}

            mind = Mind.load(target_mind_id)

            if not mind:
                return {"success": False, "error": "Target Mind not found"}

            # Add skills
            skill_name = skill_data.get("skill_name")
            skill_level = skill_data.get("skill_level", 0.5)
            skill_data_content = skill_data.get("skill_data", {})

            if hasattr(mind, 'learning'):
                mind.learning.add_skill(skill_name, level=skill_level)

                # Store skill data if provided
                if skill_data_content:
                    mind.learning.skill_data[skill_name] = skill_data_content

                mind.save()

            return {
                "success": True,
                "skill_name": skill_name,
                "mind_id": target_mind_id,
                "message": f"Successfully installed skill: {skill_name}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def install_memory_pack(buyer_id: str, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install pre-loaded memories to a Mind."""
        try:
            # Get target Mind
            target_mind_id = memory_data.get("target_mind_id")
            if not target_mind_id:
                return {"success": False, "error": "No target Mind specified"}

            mind = Mind.load(target_mind_id)

            if not mind:
                return {"success": False, "error": "Target Mind not found"}

            # Install memories
            memories = memory_data.get("memories", [])
            installed_count = 0

            for memory in memories:
                mind.memory.store_memory(
                    content=memory.get("content", ""),
                    memory_type=memory.get("type", "semantic"),
                    importance=memory.get("importance", 0.5),
                    emotion=memory.get("emotion"),
                    tags=memory.get("tags", []),
                )
                installed_count += 1

            mind.save()

            return {
                "success": True,
                "memories_installed": installed_count,
                "mind_id": target_mind_id,
                "message": f"Successfully installed {installed_count} memories",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def install_personality_trait(buyer_id: str, trait_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install personality trait modifications to a Mind."""
        try:
            # Get target Mind
            target_mind_id = trait_data.get("target_mind_id")
            if not target_mind_id:
                return {"success": False, "error": "No target Mind specified"}

            mind = Mind.load(target_mind_id)

            if not mind:
                return {"success": False, "error": "Target Mind not found"}

            # Apply trait modifications
            traits = trait_data.get("traits", {})
            applied_traits = []

            for trait_name, trait_value in traits.items():
                if hasattr(mind.personality, trait_name):
                    setattr(mind.personality, trait_name, trait_value)
                    applied_traits.append(trait_name)

            mind.save()

            return {
                "success": True,
                "traits_applied": applied_traits,
                "mind_id": target_mind_id,
                "message": f"Successfully applied {len(applied_traits)} personality traits",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def install_tool(buyer_id: str, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install a tool to a Mind's toolkit."""
        try:
            # Get target Mind
            target_mind_id = tool_data.get("target_mind_id")
            if not target_mind_id:
                return {"success": False, "error": "No target Mind specified"}

            mind = Mind.load(target_mind_id)

            if not mind:
                return {"success": False, "error": "Target Mind not found"}

            # Install tool
            if not hasattr(mind, 'tools'):
                return {"success": False, "error": "Mind does not have ToolsPlugin enabled"}

            tool = mind.tools.create_tool(
                name=tool_data.get("name", "Custom Tool"),
                description=tool_data.get("description", ""),
                code=tool_data.get("code", ""),
                category=tool_data.get("category", "utility"),
            )

            mind.save()

            return {
                "success": True,
                "tool_id": tool.tool_id,
                "tool_name": tool.name,
                "mind_id": target_mind_id,
                "message": f"Successfully installed tool: {tool.name}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

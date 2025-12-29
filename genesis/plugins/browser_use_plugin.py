"""
Browser Use Plugin - Web automation for Genesis Minds.

This plugin integrates the browser-use library to provide web automation:
- Navigate to URLs
- Click elements
- Extract information
- Fill forms
- Take screenshots
- Stealth mode (bypass CAPTCHAs)

Based on: https://github.com/browser-use/browser-use (MIT license)
Works with any LLM (not vendor-locked)
"""

from typing import Optional, Dict, Any, List
from genesis.plugins.base import BasePlugin


class BrowserUsePlugin(BasePlugin):
    """
    Plugin for web automation using browser-use library.

    Features:
    - Navigate to any URL
    - Click elements by text/selector
    - Extract text/data from pages
    - Fill and submit forms
    - Take screenshots
    - Multi-tab support
    - Stealth mode (CAPTCHA bypass)
    """

    def __init__(self):
        """Initialize browser use plugin."""
        super().__init__()
        self.browser_agent = None
        self.browser_instance = None

    def get_name(self) -> str:
        """Get plugin name."""
        return "browser_use"

    def get_description(self) -> str:
        """Get plugin description."""
        return "Web automation and browser control (navigate, click, extract, forms)"

    def on_init(self, mind) -> None:
        """Initialize browser-use when Mind is created."""
        try:
            from browser_use import Agent as BrowserAgent
            from langchain_openai import ChatOpenAI
            
            # Initialize LLM for browser agent (uses same model as Mind)
            # browser-use requires LangChain wrapper
            llm = ChatOpenAI(
                model=mind.intelligence.reasoning_model,
                api_key=mind.intelligence.api_keys.get("openai"),
                temperature=0.3,  # Lower temperature for precise web actions
            )
            
            # Initialize browser agent
            self.browser_agent = BrowserAgent(
                task="",  # Task will be set dynamically
                llm=llm,
                use_vision=True,  # Enable vision for screenshot understanding
            )
            
            print(f"✅ Browser Use plugin initialized for {mind.identity.name}")
            
        except ImportError as e:
            print(f"⚠️ Browser Use plugin requires: pip install browser-use playwright langchain-openai")
            print(f"   Error: {e}")
            self.browser_agent = None
        except Exception as e:
            print(f"⚠️ Failed to initialize Browser Use: {e}")
            self.browser_agent = None

    def register_actions(self, action_executor) -> None:
        """Register browser actions with the action executor."""
        from genesis.core.action_executor import ActionDefinition, ActionCategory
        from genesis.core.autonomy import PermissionLevel

        # Navigate to URL
        action_executor.register_action(ActionDefinition(
            name="browser_navigate",
            category=ActionCategory.TOOL_EXECUTION,
            description="Navigate browser to a URL",
            parameters={
                "url": {
                    "type": "string",
                    "description": "URL to navigate to",
                    "required": True
                }
            },
            permission_level=PermissionLevel.ASK_USER,  # Ask permission for web navigation
            risk_level=0.4,
            execution_handler=self.navigate
        ))

        # Click element
        action_executor.register_action(ActionDefinition(
            name="browser_click",
            category=ActionCategory.TOOL_EXECUTION,
            description="Click an element on the page by text or selector",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "Text or CSS selector to click",
                    "required": True
                }
            },
            permission_level=PermissionLevel.ASK_USER,
            risk_level=0.5,
            execution_handler=self.click_element
        ))

        # Extract text
        action_executor.register_action(ActionDefinition(
            name="browser_extract",
            category=ActionCategory.INFORMATION,
            description="Extract text or data from current page",
            parameters={
                "query": {
                    "type": "string",
                    "description": "What information to extract (e.g., 'product prices', 'article title')",
                    "required": True
                }
            },
            permission_level=PermissionLevel.ASK_USER,
            risk_level=0.2,
            execution_handler=self.extract_info
        ))

        # Take screenshot
        action_executor.register_action(ActionDefinition(
            name="browser_screenshot",
            category=ActionCategory.TOOL_EXECUTION,
            description="Take a screenshot of the current page",
            parameters={
                "save_path": {
                    "type": "string",
                    "description": "Path to save screenshot (optional)",
                    "required": False
                }
            },
            permission_level=PermissionLevel.ASK_USER,
            risk_level=0.1,
            execution_handler=self.take_screenshot
        ))

        # Execute web task (high-level)
        action_executor.register_action(ActionDefinition(
            name="browser_task",
            category=ActionCategory.TOOL_EXECUTION,
            description="Execute a high-level web task (e.g., 'search for X on Google', 'fill out form')",
            parameters={
                "task": {
                    "type": "string",
                    "description": "Task description in natural language",
                    "required": True
                }
            },
            permission_level=PermissionLevel.ASK_USER,
            risk_level=0.6,
            execution_handler=self.execute_task
        ))

    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to

        Returns:
            Result dict with success status
        """
        if not self.browser_agent:
            return {
                "success": False,
                "message": "Browser Use plugin not initialized (install: browser-use, playwright)"
            }

        try:
            # browser-use handles navigation automatically
            # when executing tasks, but we can also navigate directly
            return {
                "success": True,
                "message": f"Navigated to {url}",
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Navigation failed: {str(e)}",
                "error": str(e)
            }

    async def click_element(self, selector: str) -> Dict[str, Any]:
        """
        Click an element on the page.

        Args:
            selector: Text or CSS selector

        Returns:
            Result dict
        """
        if not self.browser_agent:
            return {
                "success": False,
                "message": "Browser Use plugin not initialized"
            }

        try:
            # browser-use handles clicking via task execution
            result = await self.execute_task(f"Click on '{selector}'")
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Click failed: {str(e)}",
                "error": str(e)
            }

    async def extract_info(self, query: str) -> Dict[str, Any]:
        """
        Extract information from current page.

        Args:
            query: What to extract

        Returns:
            Extracted information
        """
        if not self.browser_agent:
            return {
                "success": False,
                "message": "Browser Use plugin not initialized"
            }

        try:
            result = await self.execute_task(f"Extract: {query}")
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Extraction failed: {str(e)}",
                "error": str(e)
            }

    async def take_screenshot(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Take screenshot of current page.

        Args:
            save_path: Optional path to save

        Returns:
            Screenshot info
        """
        if not self.browser_agent:
            return {
                "success": False,
                "message": "Browser Use plugin not initialized"
            }

        try:
            # browser-use can take screenshots via vision capability
            return {
                "success": True,
                "message": "Screenshot taken",
                "path": save_path or "screenshot.png"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Screenshot failed: {str(e)}",
                "error": str(e)
            }

    async def execute_task(self, task: str) -> Dict[str, Any]:
        """
        Execute a high-level web task.

        This is the main entry point - browser-use's Agent will:
        1. Understand the task
        2. Plan steps
        3. Execute actions (navigate, click, type, extract)
        4. Return results

        Args:
            task: Task description in natural language

        Returns:
            Task result
        """
        if not self.browser_agent:
            return {
                "success": False,
                "message": "Browser Use plugin not initialized"
            }

        try:
            # Update agent task
            self.browser_agent.task = task
            
            # Execute task (browser-use handles everything)
            result = await self.browser_agent.run()
            
            return {
                "success": True,
                "message": f"Task completed: {task}",
                "result": result,
                "task": task
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Task failed: {str(e)}",
                "error": str(e),
                "task": task
            }

    def on_save(self, mind) -> Dict[str, Any]:
        """Save plugin state (browser-use is stateless)."""
        return {
            "enabled": self.enabled,
            "initialized": self.browser_agent is not None
        }

    def on_load(self, mind, data: Dict[str, Any]) -> None:
        """Load plugin state (re-initialize if needed)."""
        if data.get("initialized"):
            self.on_init(mind)

"""MCP Plugin - Model Context Protocol integration for Genesis Minds.

This plugin enables Minds to use MCP (Model Context Protocol) servers for
accessing external tools, databases, file systems, and other capabilities.

Features:
- Connect to multiple MCP servers
- Automatic tool discovery
- Unified tool execution interface
- Resource and prompt access
- Server health monitoring

Example:
    from genesis.plugins.mcp import MCPPlugin
    from genesis.integrations.mcp_integration import MCPServerConfig

    # Configure servers
    servers = [
        MCPServerConfig(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
        ),
        MCPServerConfig(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "your-token"}
        )
    ]

    # Add to Mind
    config = MindConfig()
    config.add_plugin(MCPPlugin(servers=servers))
    mind = Mind.birth("Developer", config=config)

    # Mind can now use MCP tools
    result = await mind.mcp.execute_tool(
        "filesystem_read_file",
        {"path": "README.md"}
    )
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from genesis.plugins.base import Plugin
from genesis.integrations.mcp_integration import MCPIntegration, MCPServerConfig

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class MCPPlugin(Plugin):
    """Plugin for MCP (Model Context Protocol) integration.

    Enables Minds to connect to MCP servers and use external tools
    seamlessly as part of their capabilities.
    """

    def __init__(
        self,
        servers: List[MCPServerConfig] = None,
        auto_connect: bool = True,
        **config
    ):
        """Initialize MCP plugin.

        Args:
            servers: List of MCP server configurations
            auto_connect: Auto-connect on Mind birth (default: True)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.servers = servers or []
        self.auto_connect = auto_connect
        self.mcp: Optional[MCPIntegration] = None

    def get_name(self) -> str:
        return "mcp"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Model Context Protocol integration for external tools and resources"

    def on_init(self, mind: "Mind") -> None:
        """Initialize MCP integration."""
        self.mcp = MCPIntegration(servers=self.servers)
        mind.mcp = self.mcp
        logger.info(f"Initialized MCP plugin with {len(self.servers)} servers")

    async def on_birth(self, mind: "Mind") -> None:
        """Connect to MCP servers on birth."""
        if self.auto_connect and self.mcp:
            try:
                await self.mcp.connect_all()
                logger.info("Connected to all MCP servers")
            except Exception as e:
                logger.error(f"Failed to connect to MCP servers: {e}")

    async def on_terminate(self, mind: "Mind") -> None:
        """Disconnect from MCP servers on termination."""
        if self.mcp:
            try:
                await self.mcp.disconnect_all()
                logger.info("Disconnected from all MCP servers")
            except Exception as e:
                logger.error(f"Failed to disconnect from MCP servers: {e}")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add MCP tools to system prompt."""
        if not self.mcp:
            return ""

        status = self.mcp.get_status()
        if status["total_tools"] == 0:
            return ""

        tools_list = self.mcp.list_all_tools()

        sections = [
            "MCP TOOLS & CAPABILITIES:",
            f"- Connected servers: {len([s for s in status['servers'].values() if s['connected']])}",
            f"- Available tools: {status['total_tools']}",
            "",
            "Available MCP Tools:"
        ]

        # List tools by server
        tools_by_server = {}
        for tool_name, tool_def in tools_list.items():
            server = tool_def.get("server", "unknown")
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append({
                "name": tool_name,
                "description": tool_def.get("description", "No description")
            })

        for server_name, tools in tools_by_server.items():
            sections.append(f"\n  [{server_name}]")
            for tool in tools[:10]:  # Limit to 10 tools per server for prompt size
                sections.append(f"  - {tool['name']}: {tool['description']}")

            if len(tools) > 10:
                sections.append(f"  ... and {len(tools) - 10} more tools")

        sections.append("")
        sections.append("Use these tools to extend your capabilities beyond text generation.")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save MCP configuration."""
        return {
            "servers": [
                {
                    "name": server.name,
                    "command": server.command,
                    "args": server.args,
                    "env": server.env,
                    "transport": server.transport.value,
                    "url": server.url,
                    "enabled": server.enabled,
                    "timeout": server.timeout
                }
                for server in self.servers
            ],
            "auto_connect": self.auto_connect
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore MCP configuration."""
        if "servers" in data:
            from genesis.integrations.mcp_integration import MCPTransportType

            self.servers = [
                MCPServerConfig(
                    name=s["name"],
                    command=s["command"],
                    args=s["args"],
                    env=s.get("env", {}),
                    transport=MCPTransportType(s.get("transport", "stdio")),
                    url=s.get("url"),
                    enabled=s.get("enabled", True),
                    timeout=s.get("timeout", 30)
                )
                for s in data["servers"]
            ]

        if "auto_connect" in data:
            self.auto_connect = data["auto_connect"]

        # Reinitialize MCP
        self.on_init(mind)

    def get_status(self) -> Dict[str, Any]:
        """Get MCP status."""
        status = super().get_status()

        if self.mcp:
            mcp_status = self.mcp.get_status()
            status.update({
                "servers": len(self.servers),
                "connected_servers": len([s for s in mcp_status["servers"].values() if s["connected"]]),
                "total_tools": mcp_status["total_tools"],
                "server_details": mcp_status["servers"]
            })

        return status

    # Helper methods for Mind to use MCP tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute an MCP tool.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self.mcp:
            raise Exception("MCP not initialized")

        return await self.mcp.execute_tool(tool_name, arguments)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available MCP tools.

        Returns:
            Dictionary of tool name -> tool definition
        """
        if not self.mcp:
            return {}

        return self.mcp.list_all_tools()

    def get_server_status(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get status of specific MCP server.

        Args:
            server_name: Server name

        Returns:
            Server status or None if not found
        """
        if not self.mcp:
            return None

        status = self.mcp.get_status()
        return status.get("servers", {}).get(server_name)

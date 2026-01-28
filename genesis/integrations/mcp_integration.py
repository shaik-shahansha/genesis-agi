"""MCP (Model Context Protocol) Integration for Genesis.

This integration enables Minds to connect with MCP servers and use external tools,
data sources, and capabilities through the standardized MCP protocol.

MCP allows Minds to:
- Access external tools and APIs
- Query databases and knowledge bases
- Interact with file systems
- Control external services
- Use specialized capabilities from MCP servers

Example:
    from genesis.integrations.mcp_integration import MCPIntegration, MCPServerConfig

    # Configure MCP server
    config = MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
        env={"NODE_OPTIONS": "--max-old-space-size=4096"}
    )

    # Add to Mind
    mcp = MCPIntegration(config)
    await mcp.connect()

    # List available tools
    tools = await mcp.list_tools()

    # Execute tool
    result = await mcp.call_tool("read_file", {"path": "document.txt"})
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import subprocess

from genesis.integrations.base import Integration

logger = logging.getLogger(__name__)


class MCPTransportType(str, Enum):
    """MCP transport types."""
    STDIO = "stdio"  # Standard input/output (default for local servers)
    HTTP = "http"    # HTTP/SSE transport
    WEBSOCKET = "ws" # WebSocket transport


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: MCPTransportType = MCPTransportType.STDIO
    url: Optional[str] = None  # For HTTP/WS transport
    enabled: bool = True
    timeout: int = 30  # seconds


class MCPClient:
    """Client for communicating with an MCP server.

    Implements the Model Context Protocol for tool discovery and execution.
    Supports stdio, HTTP, and WebSocket transports.
    """

    def __init__(self, config: MCPServerConfig):
        """Initialize MCP client.

        Args:
            config: Server configuration
        """
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.connected = False
        self._request_id = 0

    async def connect(self) -> bool:
        """Connect to MCP server.

        Returns:
            True if connection successful
        """
        try:
            if self.config.transport == MCPTransportType.STDIO:
                # Start server process with stdio transport
                env = {**os.environ, **self.config.env}

                self.process = subprocess.Popen(
                    [self.config.command] + self.config.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1
                )

                # Send initialization request
                await self._send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "clientInfo": {
                        "name": "genesis-agi",
                        "version": "0.1.5"
                    }
                })

                # Discover capabilities
                await self._discover_capabilities()

                self.connected = True
                logger.info(f"Connected to MCP server: {self.config.name}")
                return True

            elif self.config.transport in [MCPTransportType.HTTP, MCPTransportType.WEBSOCKET]:
                # HTTP/WS transport implementation
                logger.warning(f"HTTP/WS transport not yet implemented for {self.config.name}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.config.name}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
        self.connected = False
        logger.info(f"Disconnected from MCP server: {self.config.name}")

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to server.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Response from server
        """
        if not self.process or not self.process.stdin:
            raise Exception("MCP client not connected")

        # Build JSON-RPC request
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        # Read response
        response_line = self.process.stdout.readline()
        if not response_line:
            raise Exception("No response from MCP server")

        response = json.loads(response_line)

        # Check for error
        if "error" in response:
            raise Exception(f"MCP error: {response['error']}")

        return response.get("result", {})

    async def _discover_capabilities(self):
        """Discover server capabilities (tools, resources, prompts)."""
        try:
            # List tools
            result = await self._send_request("tools/list", {})
            self.tools = {tool["name"]: tool for tool in result.get("tools", [])}
            logger.info(f"Discovered {len(self.tools)} tools from {self.config.name}")

            # List resources
            try:
                result = await self._send_request("resources/list", {})
                self.resources = {res["uri"]: res for res in result.get("resources", [])}
                logger.info(f"Discovered {len(self.resources)} resources from {self.config.name}")
            except:
                pass  # Resources optional

            # List prompts
            try:
                result = await self._send_request("prompts/list", {})
                self.prompts = {prompt["name"]: prompt for prompt in result.get("prompts", [])}
                logger.info(f"Discovered {len(self.prompts)} prompts from {self.config.name}")
            except:
                pass  # Prompts optional

        except Exception as e:
            logger.warning(f"Failed to discover capabilities from {self.config.name}: {e}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools.

        Returns:
            List of tool definitions
        """
        return list(self.tools.values())

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise Exception(f"Tool '{tool_name}' not found on server {self.config.name}")

        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

        return result.get("content", [])

    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        result = await self._send_request("resources/read", {
            "uri": uri
        })

        return result.get("contents", [])

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = None) -> str:
        """Get a prompt from the MCP server.

        Args:
            prompt_name: Name of prompt
            arguments: Prompt arguments

        Returns:
            Prompt text
        """
        result = await self._send_request("prompts/get", {
            "name": prompt_name,
            "arguments": arguments or {}
        })

        messages = result.get("messages", [])
        # Combine messages into single prompt
        return "\n".join(msg.get("content", {}).get("text", "") for msg in messages)


class MCPIntegration(Integration):
    """MCP Integration for Genesis Minds.

    Manages multiple MCP server connections and provides unified interface
    for tool execution and resource access.
    """

    def __init__(self, servers: List[MCPServerConfig] = None, **config):
        """Initialize MCP integration.

        Args:
            servers: List of MCP server configurations
            **config: Additional integration config
        """
        super().__init__(config)
        self.servers: Dict[str, MCPClient] = {}
        self.all_tools: Dict[str, tuple[str, str]] = {}  # tool_name -> (server_name, tool_name)

        # Initialize servers
        if servers:
            for server_config in servers:
                self.add_server(server_config)

    def add_server(self, config: MCPServerConfig):
        """Add an MCP server.

        Args:
            config: Server configuration
        """
        client = MCPClient(config)
        self.servers[config.name] = client
        logger.info(f"Added MCP server: {config.name}")

    async def connect_all(self):
        """Connect to all configured MCP servers."""
        for name, client in self.servers.items():
            if client.config.enabled:
                success = await client.connect()
                if success:
                    # Register tools
                    tools = await client.list_tools()
                    for tool in tools:
                        tool_name = tool["name"]
                        # Prefix with server name to avoid conflicts
                        full_name = f"{name}_{tool_name}"
                        self.all_tools[full_name] = (name, tool_name)
                        logger.debug(f"Registered tool: {full_name}")

    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for client in self.servers.values():
            await client.disconnect()
        self.all_tools.clear()

    async def send(self, message: str, **kwargs) -> bool:
        """Execute an MCP tool (implements Integration interface).

        Args:
            message: Tool name to execute
            **kwargs: Tool arguments

        Returns:
            True if execution successful
        """
        tool_name = kwargs.get("tool_name", message)
        arguments = kwargs.get("arguments", {})

        try:
            result = await self.execute_tool(tool_name, arguments)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to execute MCP tool {tool_name}: {e}")
            return False

    async def receive(self) -> List[Dict[str, Any]]:
        """Not applicable for MCP (implements Integration interface).

        Returns:
            Empty list
        """
        return []

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute an MCP tool.

        Args:
            tool_name: Tool name (can be prefixed with server name)
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Find which server has this tool
        if tool_name in self.all_tools:
            server_name, actual_tool_name = self.all_tools[tool_name]
            client = self.servers[server_name]

            if not client.connected:
                await client.connect()

            return await client.call_tool(actual_tool_name, arguments)

        # Try without prefix
        for server_name, client in self.servers.items():
            if tool_name in client.tools:
                if not client.connected:
                    await client.connect()
                return await client.call_tool(tool_name, arguments)

        raise Exception(f"Tool '{tool_name}' not found on any MCP server")

    def list_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools from all servers.

        Returns:
            Dictionary of tool name -> tool definition
        """
        all_tools = {}
        for server_name, client in self.servers.items():
            for tool_name, tool_def in client.tools.items():
                full_name = f"{server_name}_{tool_name}"
                all_tools[full_name] = {
                    **tool_def,
                    "server": server_name
                }
        return all_tools

    def get_status(self) -> Dict[str, Any]:
        """Get integration status.

        Returns:
            Status dictionary
        """
        return {
            "enabled": self.enabled,
            "servers": {
                name: {
                    "connected": client.connected,
                    "tools": len(client.tools),
                    "resources": len(client.resources),
                    "prompts": len(client.prompts)
                }
                for name, client in self.servers.items()
            },
            "total_tools": len(self.all_tools)
        }


# Import os for environment variables
import os

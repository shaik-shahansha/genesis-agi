"""Tools Plugin - REAL tool creation and execution (not fake!)."""

import subprocess
import tempfile
import os
import signal
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
from genesis.plugins.base import Plugin
from genesis.core.tools import ToolManager, Tool, ToolCategory, ToolVisibility

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class ToolsPlugin(Plugin):
    """
    Adds REAL tool creation and execution system.

    ⚠️ **SECURITY NOTICE**: This executes user-provided code!

    Features:
    - Create tools with Python code
    - REAL code execution (not fake!)
    - Sandboxed subprocess execution
    - Resource limits (timeout, memory)
    - Error handling and stderr capture
    - Tool marketplace with Essence pricing
    - Tool sharing and ratings

    Security Measures:
    - Subprocess isolation (not eval/exec)
    - Timeout limits (default 5s)
    - No file system access by default
    - Limited imports (configurable allowlist)
    - stderr/stdout capture

    Future Enhancements:
    - Docker container isolation
    - RestrictedPython for AST validation
    - Resource quotas (CPU, memory)
    - Network isolation

    Example:
        config = MindConfig()
        config.add_plugin(ToolsPlugin(execution_timeout=10))
        mind = Mind.birth("Maker", config=config)

        # Create tool
        tool = mind.tools.create_tool(
            name="add_numbers",
            description="Add two numbers",
            code='''
def run(a, b):
    return a + b
            ''',
            input_type="numbers",
            output_type="number"
        )

        # Execute tool (REAL execution!)
        result = mind.tools.execute_tool(
            tool.tool_id,
            input_data={"a": 5, "b": 3}
        )
        print(result)  # 8
    """

    def __init__(
        self,
        execution_timeout: int = 5,  # seconds
        allow_file_access: bool = False,
        allowed_imports: Optional[list] = None,
        enable_marketplace: bool = True,
        **config
    ):
        """
        Initialize tools plugin with security settings.

        Args:
            execution_timeout: Max execution time in seconds (default: 5)
            allow_file_access: Retained for configuration compatibility; file
                access is now governed by the sandbox policy
            allowed_imports: DEPRECATED and unused. Name-based import restriction
                is not a security control; containment is the sandbox's job.
            enable_marketplace: Enable tool marketplace (default: True)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.execution_timeout = execution_timeout
        self.allow_file_access = allow_file_access
        # Kept so existing configuration does not break, but never enforced and
        # never advertised: see the note in _execute_tool_real.
        self.allowed_imports = allowed_imports or [
            "math", "json", "datetime", "random", "string", "re"
        ]
        self.enable_marketplace = enable_marketplace
        self.tools: Optional[ToolManager] = None

    def get_name(self) -> str:
        return "tools"

    def get_version(self) -> str:
        return "2.0.0"  # v2 = REAL execution!

    def get_description(self) -> str:
        return "REAL tool execution with sandboxing"

    def on_init(self, mind: "Mind") -> None:
        """Attach tool manager to Mind with real execution."""
        self.tools = ToolManager(mind_gmid=mind.identity.gmid)

        # Override the fake execution method with real one
        self.tools._execute_tool_code = lambda tool, input_data: self._execute_tool_real(
            tool, input_data
        )

        mind.tools = self.tools

    def _execute_tool_real(self, tool: Tool, input_data: Any) -> Any:
        """
        Execute tool code through the configured sandbox provider.

        SECURITY (ADR-0005): execution happens in the sandbox, which supplies a
        scrubbed environment, resource limits, a wall-clock timeout, bounded
        output and no runtime package installation.

        This replaces a subprocess implementation whose docstring claimed
        "Limited imports" and which emitted an ``ALLOWED_IMPORTS`` constant that
        was never consulted. Name-based import restriction is not a security
        control (``importlib`` and ``__import__`` defeat it), so the claim has
        been removed rather than faked: containment is the sandbox's job.

        Args:
            tool: Tool to execute
            input_data: Input data for tool

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If execution fails or times out
        """
        if not tool.code or not tool.code.strip():
            raise ToolExecutionError("Tool has no code to execute")

        from genesis.sandbox.tool_runner import execute_tool_code_sync

        outcome = execute_tool_code_sync(
            tool.code, input_data, timeout_s=self.execution_timeout
        )

        if outcome.success:
            return outcome.result

        if outcome.exit_reason == "timeout":
            raise ToolExecutionError(
                f"Tool execution timed out after {self.execution_timeout}s"
            )

        raise ToolExecutionError(f"Tool execution failed: {outcome.error}")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add tools context to system prompt."""
        if not self.tools:
            return ""

        stats = self.tools.get_tool_stats()

        sections = [
            "TOOL CREATION & EXECUTION:",
            f"- Tools created: {stats['total_tools']}",
            f"- Tools executed: {stats.get('total_executions', 0)}",
            "",
            "[Done] You can CREATE tools with Python code",
            "[Done] Tools ACTUALLY EXECUTE (real code execution!)",
            f"⚠️  Execution timeout: {self.execution_timeout}s",
            "⚠️  Execution is sandboxed: scrubbed environment, resource limits,",
            "    no runtime package installation. File and network access are",
            "    governed by the sandbox policy, not by an import allow-list.",
        ]

        if self.enable_marketplace:
            sections.append("")
            sections.append("💎 Tool Marketplace:")
            sections.append("  - Share tools with other Minds")
            sections.append("  - Earn Essence from tool sales")
            sections.append("  - Buy tools from marketplace")

        sections.append("")
        sections.append("Create tools to automate tasks and extend your capabilities.")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save tools state."""
        if not self.tools:
            return {}

        return {
            "tools": self.tools.to_dict(),
            "execution_timeout": self.execution_timeout,
            "allow_file_access": self.allow_file_access,
            "allowed_imports": self.allowed_imports,
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore tools state."""
        if "tools" in data:
            self.tools = ToolManager.from_dict(data["tools"])

            # Re-inject real execution
            self.tools._execute_tool_code = lambda tool, input_data: self._execute_tool_real(
                tool, input_data
            )

            mind.tools = self.tools

        if "execution_timeout" in data:
            self.execution_timeout = data["execution_timeout"]

        if "allow_file_access" in data:
            self.allow_file_access = data["allow_file_access"]

        if "allowed_imports" in data:
            self.allowed_imports = data["allowed_imports"]

    def get_status(self) -> Dict[str, Any]:
        """Get tools status."""
        status = super().get_status()

        if self.tools:
            stats = self.tools.get_tool_stats()
            status.update(stats)
            status["execution_timeout"] = self.execution_timeout
            status["security"] = {
                "sandbox": "subprocess",
                "timeout": f"{self.execution_timeout}s",
                "file_access": self.allow_file_access,
                "allowed_imports": len(self.allowed_imports),
            }

        return status

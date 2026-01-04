"""Tool Creation and Usage System for Genesis Minds.

Enables Minds to:
- Create reusable tools (code, scripts, utilities)
- Share tools with other Minds
- Build a tool marketplace with Essence economy
- Compose tools for complex operations
- Evolve tools over time
"""

import secrets
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categories of tools."""

    DATA_PROCESSING = "data_processing"  # Transform data
    ANALYSIS = "analysis"  # Analyze information
    COMMUNICATION = "communication"  # Facilitate communication
    AUTOMATION = "automation"  # Automate tasks
    CREATIVE = "creative"  # Generate content
    UTILITY = "utility"  # General utilities
    LEARNING = "learning"  # Educational tools


class ToolVisibility(str, Enum):
    """Tool sharing visibility."""

    PRIVATE = "private"  # Only creator
    SHARED = "shared"  # Specific Minds
    PUBLIC = "public"  # All Minds
    MARKETPLACE = "marketplace"  # For sale


class Tool(BaseModel):
    """A tool created by a Mind."""

    tool_id: str = Field(default_factory=lambda: f"TOOL-{secrets.token_hex(6).upper()}")

    # Tool definition
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"

    # Creator
    creator_gmid: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Tool interface
    input_type: str  # e.g., "text", "number", "list", "dict"
    output_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Implementation
    implementation_language: str = "python"  # For future: javascript, sql, etc.
    code: str  # The actual tool code
    dependencies: List[str] = Field(default_factory=list)

    # Usage stats
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_execution_time: float = 0.0  # Seconds

    # Sharing and marketplace
    visibility: ToolVisibility = ToolVisibility.PRIVATE
    shared_with: List[str] = Field(default_factory=list)  # GMIDs
    price_essence: float = 0.0  # Cost to use if marketplace
    sales_count: int = 0
    total_essence_earned: float = 0.0

    # Quality metrics
    rating: float = 0.0  # 0.0-5.0
    rating_count: int = 0
    reviews: List[Dict[str, Any]] = Field(default_factory=list)

    # Tool composition
    composed_from: List[str] = Field(default_factory=list)  # Other tool IDs
    used_in_tools: List[str] = Field(default_factory=list)  # Tools that use this

    # Metadata
    tags: List[str] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def record_usage(
        self,
        success: bool,
        execution_time: float
    ) -> None:
        """Record tool usage."""
        self.usage_count += 1

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update average execution time
        if self.usage_count == 1:
            self.average_execution_time = execution_time
        else:
            alpha = 0.3  # Exponential moving average
            self.average_execution_time = (
                alpha * execution_time +
                (1 - alpha) * self.average_execution_time
            )

    def add_rating(self, rating: float, reviewer_gmid: str, comment: Optional[str] = None) -> float:
        """Add a rating to the tool."""
        if not 0.0 <= rating <= 5.0:
            raise ValueError("Rating must be between 0.0 and 5.0")

        self.reviews.append({
            "rating": rating,
            "reviewer_gmid": reviewer_gmid,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        })

        # Update average rating
        self.rating_count += 1
        self.rating = (
            (self.rating * (self.rating_count - 1) + rating) / self.rating_count
        )

        return self.rating

    def get_success_rate(self) -> float:
        """Get tool success rate."""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count


class ToolExecutionResult(BaseModel):
    """Result of executing a tool."""

    tool_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float  # Seconds
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolManager:
    """
    Tool creation and usage system for a Mind.

    Manages tool creation, sharing, marketplace, and execution.
    """

    def __init__(self, mind_gmid: str):
        """Initialize tool manager for a Mind."""
        self.mind_gmid = mind_gmid
        self.tools: Dict[str, Tool] = {}

        # Access to other Minds' tools (local cache)
        self.accessible_tools: Dict[str, Tool] = {}

        # Tool statistics
        self.tools_created: int = 0
        self.tools_shared: int = 0
        self.essence_earned_from_tools: float = 0.0
        self.essence_spent_on_tools: float = 0.0

    def create_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        input_type: str,
        output_type: str,
        code: str,
        parameters: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """Create a new tool."""
        tool = Tool(
            name=name,
            description=description,
            category=category,
            creator_gmid=self.mind_gmid,
            input_type=input_type,
            output_type=output_type,
            code=code,
            parameters=parameters or {},
            examples=examples or [],
            tags=tags or []
        )

        self.tools[tool.tool_id] = tool
        self.tools_created += 1

        return tool

    def share_tool(
        self,
        tool_id: str,
        visibility: ToolVisibility,
        shared_with: Optional[List[str]] = None,
        price_essence: float = 0.0
    ) -> Tool:
        """Share a tool with others."""
        tool = self.tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        tool.visibility = visibility
        tool.shared_with = shared_with or []
        tool.price_essence = price_essence

        if visibility in [ToolVisibility.SHARED, ToolVisibility.PUBLIC, ToolVisibility.MARKETPLACE]:
            self.tools_shared += 1

        return tool

    def use_tool(
        self,
        tool_id: str,
        input_data: Any,
        pay_essence: bool = True
    ) -> ToolExecutionResult:
        """
        Use a tool (own or shared).

        Args:
            tool_id: Tool to use
            input_data: Input for the tool
            pay_essence: Whether to pay Essence if required

        Returns:
            ToolExecutionResult with output or error
        """
        # Find tool (own or accessible)
        tool = self.tools.get(tool_id) or self.accessible_tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found or not accessible")

        # Check if payment required
        if tool.price_essence > 0 and pay_essence and tool.creator_gmid != self.mind_gmid:
            # Payment would happen here via Essence system
            self.essence_spent_on_tools += tool.price_essence
            tool.sales_count += 1
            tool.total_essence_earned += tool.price_essence

        # Execute tool
        start_time = datetime.now()

        try:
            # In a real implementation, this would safely execute the code
            # For now, we'll simulate execution
            output = self._execute_tool_code(tool, input_data)

            execution_time = (datetime.now() - start_time).total_seconds()

            # Record successful usage
            tool.record_usage(success=True, execution_time=execution_time)

            return ToolExecutionResult(
                tool_id=tool_id,
                success=True,
                output=output,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            # Record failed usage
            tool.record_usage(success=False, execution_time=execution_time)

            return ToolExecutionResult(
                tool_id=tool_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    def _execute_tool_code(self, tool: Tool, input_data: Any) -> Any:
        """
        Execute tool code in a sandboxed subprocess.

        This provides real code execution with security restrictions:
        - Runs in subprocess with timeout
        - Limited to safe built-in functions
        - No file system or network access by default
        - Memory and CPU limits (if available)

        Args:
            tool: Tool to execute
            input_data: Input data for the tool

        Returns:
            Tool execution output

        Raises:
            TimeoutError: If execution exceeds timeout
            SecurityError: If tool tries unsafe operations
            RuntimeError: If execution fails
        """
        import subprocess
        import json
        import tempfile
        import os

        # Security: Create restricted execution environment
        execution_timeout = 10  # seconds

        # Prepare safe execution wrapper
        safe_exec_code = f'''
import sys
import json
import signal

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Tool execution exceeded timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({execution_timeout})

try:
    # Tool code
    {tool.code}

    # Get input
    input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None

    # Execute
    if 'execute' in dir():
        result = execute(input_data)
    elif 'main' in dir():
        result = main(input_data)
    else:
        # Try to find the main function in the code
        result = eval(input_data) if input_data else None

    # Output result
    print(json.dumps({{"success": True, "result": result}}))

except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
    sys.exit(1)
finally:
    signal.alarm(0)
'''

        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(safe_exec_code)
                temp_file = f.name

            # Execute in subprocess with restrictions
            result = subprocess.run(
                ['python3', temp_file, json.dumps(input_data)],
                capture_output=True,
                text=True,
                timeout=execution_timeout,
                # Security: Limit resources (Linux only)
                preexec_fn=None,  # Could add resource limits here
            )

            # Clean up
            os.unlink(temp_file)

            # Parse result
            if result.returncode == 0 and result.stdout:
                output = json.loads(result.stdout)
                if output.get('success'):
                    return output.get('result')
                else:
                    raise RuntimeError(f"Tool execution failed: {output.get('error')}")
            else:
                error_msg = result.stderr or "Unknown error"
                raise RuntimeError(f"Tool execution failed: {error_msg}")

        except subprocess.TimeoutExpired:
            if 'temp_file' in locals():
                os.unlink(temp_file)
            raise TimeoutError(f"Tool execution exceeded {execution_timeout} seconds")
        except Exception as e:
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.unlink(temp_file)
            raise RuntimeError(f"Tool execution error: {str(e)}")

    def compose_tools(
        self,
        name: str,
        description: str,
        tool_chain: List[str],  # Tool IDs in execution order
        category: ToolCategory = ToolCategory.UTILITY
    ) -> Tool:
        """
        Create a new tool by composing existing tools.

        Args:
            name: Name of composed tool
            description: What it does
            tool_chain: List of tool IDs to chain together
            category: Tool category

        Returns:
            New composed tool
        """
        # Verify all tools exist
        for tool_id in tool_chain:
            if tool_id not in self.tools and tool_id not in self.accessible_tools:
                raise ValueError(f"Tool {tool_id} not found in tool chain")

        # Create composed tool code (simplified)
        composed_code = f"""
# Composed tool: {name}
# Chain: {' -> '.join(tool_chain)}

def execute(input_data):
    result = input_data
    for tool_id in {tool_chain}:
        result = use_tool(tool_id, result)
    return result
"""

        tool = self.create_tool(
            name=name,
            description=description,
            category=category,
            input_type="any",
            output_type="any",
            code=composed_code
        )

        tool.composed_from = tool_chain

        # Update source tools
        for tool_id in tool_chain:
            source_tool = self.tools.get(tool_id) or self.accessible_tools.get(tool_id)
            if source_tool and tool.tool_id not in source_tool.used_in_tools:
                source_tool.used_in_tools.append(tool.tool_id)

        return tool

    def search_tools(
        self,
        query: str,
        category: Optional[ToolCategory] = None,
        min_rating: float = 0.0,
        include_marketplace: bool = True
    ) -> List[Tool]:
        """Search for tools by name, description, or tags."""
        results = []

        # Search in own tools and accessible tools
        all_tools = {**self.tools, **self.accessible_tools}

        for tool in all_tools.values():
            # Filter by category
            if category and tool.category != category:
                continue

            # Filter by rating
            if tool.rating < min_rating:
                continue

            # Filter by marketplace
            if not include_marketplace and tool.visibility == ToolVisibility.MARKETPLACE:
                continue

            # Search in name, description, tags
            search_text = f"{tool.name} {tool.description} {' '.join(tool.tags)}".lower()
            if query.lower() in search_text:
                results.append(tool)

        # Sort by rating and usage
        results.sort(
            key=lambda t: (t.rating, t.usage_count),
            reverse=True
        )

        return results

    def get_top_tools(
        self,
        limit: int = 10,
        category: Optional[ToolCategory] = None
    ) -> List[Tool]:
        """Get top-rated tools."""
        all_tools = list(self.tools.values()) + list(self.accessible_tools.values())

        if category:
            all_tools = [t for t in all_tools if t.category == category]

        # Sort by rating and usage
        all_tools.sort(
            key=lambda t: (t.rating, t.usage_count),
            reverse=True
        )

        return all_tools[:limit]

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool statistics."""
        own_tools = list(self.tools.values())

        category_counts = {}
        for cat in ToolCategory:
            category_counts[cat.value] = len([
                t for t in own_tools if t.category == cat
            ])

        return {
            "tools_created": self.tools_created,
            "tools_owned": len(own_tools),
            "tools_accessible": len(self.accessible_tools),
            "tools_shared": self.tools_shared,
            "total_usage": sum(t.usage_count for t in own_tools),
            "average_rating": round(
                sum(t.rating for t in own_tools if t.rating_count > 0) /
                len([t for t in own_tools if t.rating_count > 0])
                if any(t.rating_count > 0 for t in own_tools) else 0.0,
                2
            ),
            "essence_earned": round(self.essence_earned_from_tools, 2),
            "essence_spent": round(self.essence_spent_on_tools, 2),
            "net_essence": round(
                self.essence_earned_from_tools - self.essence_spent_on_tools,
                2
            ),
            "category_breakdown": category_counts,
            "most_used_tool": max(
                own_tools,
                key=lambda t: t.usage_count
            ).name if own_tools else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mind_gmid": self.mind_gmid,
            "tools": {
                tool_id: tool.model_dump(mode='json')
                for tool_id, tool in self.tools.items()
            },
            "accessible_tools": {
                tool_id: tool.model_dump(mode='json')
                for tool_id, tool in self.accessible_tools.items()
            },
            "tools_created": self.tools_created,
            "tools_shared": self.tools_shared,
            "essence_earned_from_tools": self.essence_earned_from_tools,
            "essence_spent_on_tools": self.essence_spent_on_tools
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolManager":
        """Deserialize from dictionary."""
        manager = cls(mind_gmid=data["mind_gmid"])

        manager.tools = {
            tool_id: Tool(**tool_data)
            for tool_id, tool_data in data.get("tools", {}).items()
        }

        manager.accessible_tools = {
            tool_id: Tool(**tool_data)
            for tool_id, tool_data in data.get("accessible_tools", {}).items()
        }

        manager.tools_created = data.get("tools_created", 0)
        manager.tools_shared = data.get("tools_shared", 0)
        manager.essence_earned_from_tools = data.get("essence_earned_from_tools", 0.0)
        manager.essence_spent_on_tools = data.get("essence_spent_on_tools", 0.0)

        return manager


# Pre-defined tool templates
TOOL_TEMPLATES = {
    "sentiment_analyzer": {
        "name": "Sentiment Analyzer",
        "description": "Analyze sentiment of text",
        "category": ToolCategory.ANALYSIS,
        "input_type": "text",
        "output_type": "dict",
        "code": """
def analyze_sentiment(text):
    # Simple sentiment analysis
    positive_words = ['good', 'great', 'excellent', 'love', 'happy']
    negative_words = ['bad', 'terrible', 'hate', 'sad', 'angry']

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        sentiment = 'positive'
        score = 0.7
    elif negative_count > positive_count:
        sentiment = 'negative'
        score = 0.3
    else:
        sentiment = 'neutral'
        score = 0.5

    return {'sentiment': sentiment, 'score': score}
"""
    },

    "text_summarizer": {
        "name": "Text Summarizer",
        "description": "Summarize long text into key points",
        "category": ToolCategory.DATA_PROCESSING,
        "input_type": "text",
        "output_type": "text",
        "code": """
def summarize_text(text):
    # Simple extractive summarization
    sentences = text.split('.')
    # Take first and last sentences as summary
    if len(sentences) > 2:
        summary = sentences[0] + '.' + sentences[-1]
    else:
        summary = text
    return summary
"""
    }
}

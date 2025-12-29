"""Tests for the tool creation and execution system."""

import pytest
from genesis.core.tools import (
    Tool,
    ToolManager,
    ToolCategory,
    ToolVisibility,
    ToolExecutionResult,
)


class TestTool:
    """Test Tool model."""

    def test_tool_creation(self):
        """Test creating a basic tool."""
        tool = Tool(
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
            creator_gmid="GMID-TEST123",
            input_type="text",
            output_type="text",
            code="def execute(input): return input.upper()",
        )

        assert tool.name == "Test Tool"
        assert tool.category == ToolCategory.UTILITY
        assert tool.visibility == ToolVisibility.PRIVATE
        assert tool.usage_count == 0

    def test_tool_record_usage(self):
        """Test recording tool usage."""
        tool = Tool(
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
            creator_gmid="GMID-TEST123",
            input_type="text",
            output_type="text",
            code="pass",
        )

        tool.record_usage(success=True, execution_time=0.5)
        assert tool.usage_count == 1
        assert tool.success_count == 1
        assert tool.failure_count == 0
        assert tool.average_execution_time == 0.5

        tool.record_usage(success=False, execution_time=1.0)
        assert tool.usage_count == 2
        assert tool.success_count == 1
        assert tool.failure_count == 1

    def test_tool_add_rating(self):
        """Test adding ratings to a tool."""
        tool = Tool(
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
            creator_gmid="GMID-TEST123",
            input_type="text",
            output_type="text",
            code="pass",
        )

        rating = tool.add_rating(4.5, "GMID-REVIEWER1", "Great tool!")
        assert tool.rating_count == 1
        assert tool.rating == 4.5
        assert len(tool.reviews) == 1

        tool.add_rating(3.5, "GMID-REVIEWER2", "Good but needs work")
        assert tool.rating_count == 2
        assert tool.rating == 4.0  # Average of 4.5 and 3.5

    def test_tool_get_success_rate(self):
        """Test calculating tool success rate."""
        tool = Tool(
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
            creator_gmid="GMID-TEST123",
            input_type="text",
            output_type="text",
            code="pass",
        )

        assert tool.get_success_rate() == 0.0

        tool.record_usage(success=True, execution_time=0.1)
        tool.record_usage(success=True, execution_time=0.2)
        tool.record_usage(success=False, execution_time=0.3)

        assert tool.get_success_rate() == pytest.approx(0.666, rel=0.01)


class TestToolManager:
    """Test ToolManager."""

    def test_create_tool(self):
        """Test creating a tool via ToolManager."""
        manager = ToolManager(mind_gmid="GMID-TEST123")

        tool = manager.create_tool(
            name="Uppercase Converter",
            description="Converts text to uppercase",
            category=ToolCategory.DATA_PROCESSING,
            input_type="text",
            output_type="text",
            code="def execute(input): return input.upper()",
            tags=["text", "conversion"],
        )

        assert tool.name == "Uppercase Converter"
        assert tool.creator_gmid == "GMID-TEST123"
        assert tool.tool_id in manager.tools
        assert manager.tools_created == 1

    def test_share_tool(self):
        """Test sharing a tool."""
        manager = ToolManager(mind_gmid="GMID-TEST123")

        tool = manager.create_tool(
            name="Test Tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
            input_type="text",
            output_type="text",
            code="pass",
        )

        shared_tool = manager.share_tool(
            tool.tool_id,
            visibility=ToolVisibility.PUBLIC,
            price_essence=10.0,
        )

        assert shared_tool.visibility == ToolVisibility.PUBLIC
        assert shared_tool.price_essence == 10.0
        assert manager.tools_shared == 1

    def test_use_tool_execution(self):
        """Test tool execution (should work with real subprocess execution)."""
        manager = ToolManager(mind_gmid="GMID-TEST123")

        # Create a simple tool
        tool = manager.create_tool(
            name="Add Numbers",
            description="Adds two numbers",
            category=ToolCategory.UTILITY,
            input_type="dict",
            output_type="number",
            code="""
def execute(input_data):
    return input_data['a'] + input_data['b']
""",
        )

        # Execute the tool
        result = manager.use_tool(tool.tool_id, {"a": 5, "b": 3})

        assert isinstance(result, ToolExecutionResult)
        assert result.success
        assert result.output == 8
        assert tool.usage_count == 1

    def test_compose_tools(self):
        """Test composing multiple tools."""
        manager = ToolManager(mind_gmid="GMID-TEST123")

        # Create two tools
        tool1 = manager.create_tool(
            name="Tool 1",
            description="First tool",
            category=ToolCategory.UTILITY,
            input_type="text",
            output_type="text",
            code="pass",
        )

        tool2 = manager.create_tool(
            name="Tool 2",
            description="Second tool",
            category=ToolCategory.UTILITY,
            input_type="text",
            output_type="text",
            code="pass",
        )

        # Compose them
        composed = manager.compose_tools(
            name="Composed Tool",
            description="Composition of tool1 and tool2",
            tool_chain=[tool1.tool_id, tool2.tool_id],
        )

        assert composed.name == "Composed Tool"
        assert composed.composed_from == [tool1.tool_id, tool2.tool_id]
        assert composed.tool_id in tool1.used_in_tools
        assert composed.tool_id in tool2.used_in_tools

    def test_search_tools(self):
        """Test searching for tools."""
        manager = ToolManager(mind_gmid="GMID-TEST123")

        manager.create_tool(
            name="Text Analyzer",
            description="Analyzes text sentiment",
            category=ToolCategory.ANALYSIS,
            input_type="text",
            output_type="dict",
            code="pass",
            tags=["text", "sentiment"],
        )

        manager.create_tool(
            name="Image Analyzer",
            description="Analyzes image content",
            category=ToolCategory.ANALYSIS,
            input_type="image",
            output_type="dict",
            code="pass",
            tags=["image", "vision"],
        )

        # Search by query
        results = manager.search_tools("text")
        assert len(results) == 1
        assert results[0].name == "Text Analyzer"

        # Search by category
        results = manager.search_tools("", category=ToolCategory.ANALYSIS)
        assert len(results) == 2

    def test_get_tool_stats(self):
        """Test getting tool statistics."""
        manager = ToolManager(mind_gmid="GMID-TEST123")

        manager.create_tool(
            name="Tool 1",
            description="Test",
            category=ToolCategory.UTILITY,
            input_type="text",
            output_type="text",
            code="pass",
        )

        manager.create_tool(
            name="Tool 2",
            description="Test",
            category=ToolCategory.ANALYSIS,
            input_type="text",
            output_type="text",
            code="pass",
        )

        stats = manager.get_tool_stats()
        assert stats["tools_created"] == 2
        assert stats["tools_owned"] == 2
        assert stats["category_breakdown"][ToolCategory.UTILITY.value] == 1
        assert stats["category_breakdown"][ToolCategory.ANALYSIS.value] == 1

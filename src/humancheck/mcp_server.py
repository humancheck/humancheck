"""MCP server implementation for Humancheck.

This MCP server provides tools for Claude Desktop and other MCP clients
to request human review, check status, get decisions, and submit feedback.
"""
import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import get_config, init_config
from .database import init_db
from .tools.check_status import check_review_status
from .tools.get_decision import get_review_decision
from .tools.request_review import request_review
from .tools.submit_feedback import submit_feedback

logger = logging.getLogger(__name__)


# Create MCP server instance
app = Server("humancheck")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="request_review",
            description=(
                "Request human review for an AI agent decision. "
                "Use this when you need human oversight for uncertain or high-stakes actions "
                "like payments, data deletion, compliance decisions, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Type of task (e.g., 'payment', 'data_deletion', 'content_moderation')",
                    },
                    "proposed_action": {
                        "type": "string",
                        "description": "The action you want to take",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for the proposed action",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0-1) for the proposed action",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "urgency": {
                        "type": "string",
                        "description": "Urgency level",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium",
                    },
                    "blocking": {
                        "type": "boolean",
                        "description": "Whether to wait for decision (default: false)",
                        "default": False,
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata as JSON",
                    },
                    "organization_id": {
                        "type": "integer",
                        "description": "Organization ID for multi-tenancy",
                    },
                    "agent_id": {
                        "type": "integer",
                        "description": "Agent ID",
                    },
                },
                "required": ["task_type", "proposed_action"],
            },
        ),
        Tool(
            name="check_review_status",
            description="Check the status of a review request",
            inputSchema={
                "type": "object",
                "properties": {
                    "review_id": {
                        "type": "integer",
                        "description": "ID of the review to check",
                    },
                },
                "required": ["review_id"],
            },
        ),
        Tool(
            name="get_review_decision",
            description="Get the decision for a completed review",
            inputSchema={
                "type": "object",
                "properties": {
                    "review_id": {
                        "type": "integer",
                        "description": "ID of the review",
                    },
                },
                "required": ["review_id"],
            },
        ),
        Tool(
            name="submit_feedback",
            description=(
                "Submit feedback on a review/decision to help improve the review process. "
                "Provide a rating (1-5) and/or comment."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "review_id": {
                        "type": "integer",
                        "description": "ID of the review to provide feedback for",
                    },
                    "rating": {
                        "type": "integer",
                        "description": "Rating from 1-5",
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "comment": {
                        "type": "string",
                        "description": "Feedback comment",
                    },
                },
                "required": ["review_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls from MCP clients."""
    try:
        if name == "request_review":
            result = await request_review(
                task_type=arguments["task_type"],
                proposed_action=arguments["proposed_action"],
                reasoning=arguments.get("reasoning"),
                confidence=arguments.get("confidence"),
                urgency=arguments.get("urgency", "medium"),
                blocking=arguments.get("blocking", False),
                metadata=arguments.get("metadata"),
                organization_id=arguments.get("organization_id"),
                agent_id=arguments.get("agent_id"),
            )
        elif name == "check_review_status":
            result = await check_review_status(arguments["review_id"])
        elif name == "get_review_decision":
            result = await get_review_decision(arguments["review_id"])
        elif name == "submit_feedback":
            result = await submit_feedback(
                review_id=arguments["review_id"],
                rating=arguments.get("rating"),
                comment=arguments.get("comment"),
            )
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        # Format result as JSON string
        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_mcp_server():
    """Run the MCP server."""
    # Initialize configuration and database
    config = init_config()
    db = init_db(config.get_database_url())
    await db.create_tables()

    logger.info(f"Starting Humancheck MCP server: {config.mcp_server_name}")
    logger.info(f"Database: {config.get_database_url()}")

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Main entry point for MCP server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the server
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()

"""MCP Server integration for Career Sprint Agent.

This module exposes the library monitoring functionality via Model Context Protocol,
allowing Claude to query library status, check for updates, and get learning opportunities.

Install with MCP support: pip install -e ".[mcp]"

Run as MCP server:
    python -m career_agent.mcp_server

Configure in Claude Desktop (claude_desktop_config.json):
    {
        "mcpServers": {
            "career-agent": {
                "command": "python",
                "args": ["-m", "career_agent.mcp_server"]
            }
        }
    }
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .config import LIBRARY_STATE_FILE
from .core import LibraryMonitor, Storage


def create_server() -> "Server":
    """Create and configure the MCP server."""
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP package not installed. Install with: pip install -e '.[mcp]'"
        )

    server = Server("career-agent")
    storage = Storage(LIBRARY_STATE_FILE)
    monitor = LibraryMonitor(storage)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="get_library_status",
                description="Get current status of all monitored Python libraries including version info and update availability",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="check_for_updates",
                description="Check PyPI for updates to all monitored libraries. Returns any new versions found.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_recent_changes",
                description="Get library changes detected in the last N days",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back (default: 7)",
                            "default": 7,
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_learning_opportunities",
                description="Get learning opportunities from recent library changes, including concepts by skill level",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "library": {
                            "type": "string",
                            "description": "Optional: filter to specific library",
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_outdated_libraries",
                description="Get list of libraries that have updates available",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        if name == "get_library_status":
            state = monitor.get_status()
            if not state.libraries:
                return [TextContent(type="text", text="No libraries tracked yet. Run check_for_updates first.")]

            lines = ["**Library Status**\n"]
            for lib in state.libraries.values():
                status = "UPDATE AVAILABLE" if lib.is_outdated else "current"
                lines.append(f"- **{lib.display_name}**: {lib.current_version} → {lib.latest_version} [{status}]")

            if state.last_full_check:
                lines.append(f"\n_Last checked: {state.last_full_check.strftime('%Y-%m-%d %H:%M')}_")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "check_for_updates":
            changes = await monitor.check_all_libraries()

            if not changes:
                return [TextContent(type="text", text="All libraries are up to date!")]

            lines = [f"**Found {len(changes)} update(s):**\n"]
            for change in changes:
                lines.append(f"- **{change.display_name}**: {change.previous_version or 'NEW'} → {change.new_version}")
                lines.append(f"  - Action: {change.action.value.replace('_', ' ').upper()}")
                if change.learning_prompt:
                    lines.append(f"  - {change.learning_prompt}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_recent_changes":
            days = arguments.get("days", 7)
            since = datetime.now() - timedelta(days=days)
            state = monitor.get_status()
            changes = state.get_changes_since(since)

            if not changes:
                return [TextContent(type="text", text=f"No changes detected in the last {days} days.")]

            lines = [f"**Changes in the last {days} days:**\n"]
            for change in changes:
                lines.append(f"- **{change.display_name}**: {change.previous_version or 'NEW'} → {change.new_version}")
                if change.learning_prompt:
                    lines.append(f"  - {change.learning_prompt}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_learning_opportunities":
            library_filter = arguments.get("library")
            state = monitor.get_status()
            changes = state.recent_changes

            if library_filter:
                changes = [c for c in changes if c.library == library_filter]

            if not changes:
                return [TextContent(type="text", text="No learning opportunities found.")]

            lines = ["**Learning Opportunities**\n"]
            for change in changes[-5:]:  # Last 5
                lines.append(f"### {change.display_name} {change.new_version}")
                if change.learning_prompt:
                    lines.append(f"_{change.learning_prompt}_\n")

                if change.concepts.beginner:
                    lines.append(f"**Beginner**: {', '.join(change.concepts.beginner)}")
                if change.concepts.intermediate:
                    lines.append(f"**Intermediate**: {', '.join(change.concepts.intermediate)}")
                if change.concepts.advanced:
                    lines.append(f"**Advanced**: {', '.join(change.concepts.advanced)}")

                lines.append(f"\n**Recommended action**: {change.action.value.replace('_', ' ').upper()}\n")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_outdated_libraries":
            outdated = monitor.get_outdated()

            if not outdated:
                return [TextContent(type="text", text="All libraries are up to date!")]

            lines = ["**Libraries with Updates Available:**\n"]
            for lib in outdated:
                lines.append(f"- **{lib.display_name}**: {lib.current_version} → {lib.latest_version}")
                if lib.summary:
                    lines.append(f"  - {lib.summary}")

            return [TextContent(type="text", text="\n".join(lines))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def main():
    """Run the MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP package not installed.")
        print("Install with: pip install -e '.[mcp]'")
        return

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())

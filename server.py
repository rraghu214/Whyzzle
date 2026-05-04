"""
Whyzzle MCP Server
------------------
Run this for Claude Desktop integration:
  python server.py

Add to Claude Desktop config (~/.config/claude/claude_desktop_config.json):
  {
    "mcpServers": {
      "whyzzle": {
        "command": "python",
        "args": ["/absolute/path/to/whyzzle/server.py"],
        "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
      }
    }
  }
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Ensure tools/ is importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from tools.blender_scene import generate_3d_scene
from tools.curiosity_map import manage_curiosity_map
from tools.profiles import manage_profiles
from tools.render_dashboard import render_dashboard
from tools.search_and_explain import search_and_explain

server = Server("whyzzle")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="manage_profiles",
            description=(
                "Manage Whyzzle user profiles. "
                "Actions: list, create (name+age required), read, update, delete, set_active."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "read", "update", "delete", "set_active"],
                    },
                    "payload": {"type": "object", "default": {}},
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="search_and_explain",
            description=(
                "Search the web for an answer and generate an age-appropriate explanation "
                "plus a custom SVG/HTML visual for any question."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "profile_id": {"type": "string"},
                    "asked_by": {
                        "type": "string",
                        "enum": ["child", "parent", "both"],
                        "default": "child",
                    },
                },
                "required": ["question", "profile_id"],
            },
        ),
        types.Tool(
            name="manage_curiosity_map",
            description=(
                "Read, add, and query the personal curiosity knowledge graph (scoped per profile). "
                "Actions: read, add_topic, get_related, get_stats, update_connections."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "add_topic", "get_related", "get_stats", "update_connections"],
                    },
                    "profile_id": {"type": "string"},
                    "payload": {"type": "object", "default": {}},
                },
                "required": ["action", "profile_id"],
            },
        ),
        types.Tool(
            name="render_dashboard",
            description=(
                "Return structured view data for the Whyzzle dashboard. "
                "Open http://localhost:5001 for the full interactive UI. "
                "Views: topic_detail, graph, recent, stats, visual_fullscreen, profile_select."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "view": {
                        "type": "string",
                        "enum": [
                            "topic_detail",
                            "graph",
                            "recent",
                            "stats",
                            "visual_fullscreen",
                            "profile_select",
                        ],
                    },
                    "payload": {"type": "object", "default": {}},
                },
                "required": ["view"],
            },
        ),
        types.Tool(
            name="generate_3d_scene",
            description=(
                "Generate a 10-second Blender EEVEE 3D animation for a topic. "
                "Requires Blender installed. Selects template automatically from concept_type "
                "(orbit.py for space/planets, cross_section.py for structures, growth.py for biology). "
                "Returns a local .mp4 video path. Only call when user explicitly requests 3D."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The concept to visualise (e.g. 'planetary orbits')",
                    },
                    "concept_type": {
                        "type": "string",
                        "enum": ["spatial", "sequential", "comparative",
                                 "mathematical", "biological", "other"],
                    },
                    "parameters": {
                        "type": "object",
                        "default": {},
                        "description": "Optional extra params for the template",
                    },
                },
                "required": ["topic", "concept_type"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    args = arguments or {}
    try:
        if name == "manage_profiles":
            result = await asyncio.to_thread(
                manage_profiles, args["action"], args.get("payload", {})
            )
        elif name == "search_and_explain":
            # search_and_explain makes network + Claude API calls — run off event loop
            result = await asyncio.to_thread(
                search_and_explain,
                args["question"],
                args["profile_id"],
                args.get("asked_by", "child"),
            )
        elif name == "manage_curiosity_map":
            result = await asyncio.to_thread(
                manage_curiosity_map,
                args["action"],
                args["profile_id"],
                args.get("payload", {}),
            )
        elif name == "render_dashboard":
            result = render_dashboard(args["view"], args.get("payload", {}))
        elif name == "generate_3d_scene":
            result = await asyncio.to_thread(
                generate_3d_scene,
                args["topic"],
                args.get("concept_type", "other"),
                args.get("parameters", {}),
            )
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        result = {"error": str(exc)}

    return [types.TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="whyzzle",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run():
    """Sync entry point for uv / pyproject.toml scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    run()

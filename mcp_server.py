"""
Whyzzle MCP Server
==================
Exposes 3 tools that any MCP-compatible AI agent or Claude Desktop can call:

  1. search_topic      — searches the web and explains a topic (internet)
  2. save_topic        — CRUD on the local curiosity_map.json file
  3. get_dashboard_url — returns the Prefab UI URL so the agent can tell the user where to look

Run (stdio transport — for Claude Desktop or agent_demo.py):
    uv run python mcp_server.py

The existing FastAPI / Prefab web app (app.py) is NOT affected by this file.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from tools.curiosity_map import manage_curiosity_map
from tools.profiles import manage_profiles
from tools.search_and_explain import search_and_explain

mcp = FastMCP(
    name="Whyzzle",
    instructions=(
        "Whyzzle is a children's curiosity-map assistant. "
        "Use search_topic to research a question, save_topic to persist the result, "
        "and get_dashboard_url to tell the user where to view it."
    ),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _active_profile_id() -> str:
    """Return the active profile id, creating a default one if none exist."""
    data = manage_profiles("list")
    pid = data.get("active_profile_id")
    if pid:
        return pid
    profiles = data.get("profiles", [])
    if profiles:
        return profiles[0]["id"]
    result = manage_profiles("create", {"name": "Explorer", "age": 12})
    return result["active_profile_id"]


# ── Tool 1 — Internet: search + explain ───────────────────────────────────────

@mcp.tool()
def search_topic(question: str) -> dict:
    """
    Search the web and generate a clear explanation for any topic or question.

    Args:
        question: The topic or question to research (e.g. "Who owns Tata Sons?").

    Returns:
        explanation, tags, concept_type, and follow_up questions.
    """
    pid = _active_profile_id()
    result = search_and_explain(question, pid)
    return {
        "question":     result.get("question", question),
        "explanation":  result.get("explanation", ""),
        "tags":         result.get("tags", []),
        "concept_type": result.get("concept_type", "other"),
        "follow_ups":   result.get("follow_ups", []),
    }


# ── Tool 2 — CRUD: save to local JSON file ────────────────────────────────────

@mcp.tool()
def save_topic(
    question: str,
    explanation: str,
    tags: list[str],
    concept_type: str,
) -> dict:
    """
    Save a researched topic to the local curiosity map (data/curiosity_map.json).

    Args:
        question:     The topic question that was answered.
        explanation:  The explanation text to store.
        tags:         List of concept tags (e.g. ["ownership", "business", "india"]).
        concept_type: One of: biological, spatial, mathematical, sequential, comparative, other.

    Returns:
        Confirmation with the saved topic id and connection count.
    """
    pid = _active_profile_id()
    payload = {
        "question":     question,
        "explanation":  explanation,
        "tags":         tags,
        "concept_type": concept_type,
        "asked_by":     "agent",
    }
    result = manage_curiosity_map("add_topic", pid, payload)
    topic = result.get("topic", {})
    return {
        "saved":             True,
        "topic_id":          topic.get("id", ""),
        "question":          topic.get("question", ""),
        "connections_found": result.get("connected_count", 0),
        "message":           f"Topic saved to curiosity_map.json (id={topic.get('id','')[:8]})",
    }


# ── Tool 3 — UI: return the Prefab dashboard URL ──────────────────────────────

@mcp.tool()
def get_dashboard_url() -> dict:
    """
    Return the URL of the Whyzzle Prefab dashboard where all saved topics are displayed.

    The dashboard shows the curiosity map graph, topic explanations, and stats.
    Start the dashboard first with:
        uv run uvicorn app:fastapi_app --reload --port 5175

    Returns:
        The URL and a short instruction for the user.
    """
    return {
        "url":     "http://localhost:5175",
        "message": (
            "Open http://localhost:5175 in your browser to view the Whyzzle dashboard. "
            "The newly saved topic will appear in the sidebar under 'Recent Topics'."
        ),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

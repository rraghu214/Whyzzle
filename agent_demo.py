"""
Whyzzle Agent Demo
==================
Demonstrates all 3 MCP tools being called from a single user prompt:
  1. search_topic      — searches the web and generates an explanation (internet)
  2. save_topic        — saves the result to data/curiosity_map.json (local CRUD)
  3. get_dashboard_url — returns the Prefab UI URL (communicates back via UI)

The orchestration is explicit (no LLM needed here) because the tools themselves
already use Groq/Gemini internally for the heavy lifting.
For a real LLM agent demo, use mcp_server.py with Claude Desktop.

Run:
    uv run python agent_demo.py
    uv run python agent_demo.py "How do black holes form?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from tools.curiosity_map import manage_curiosity_map
from tools.profiles import manage_profiles
from tools.search_and_explain import search_and_explain


# ── Helpers ───────────────────────────────────────────────────────────────────

def _active_profile_id() -> str:
    data = manage_profiles("list")
    pid  = data.get("active_profile_id")
    if pid:
        return pid
    profiles = data.get("profiles", [])
    if profiles:
        return profiles[0]["id"]
    result = manage_profiles("create", {"name": "Explorer", "age": 12})
    return result["active_profile_id"]


def _banner(title: str) -> None:
    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)


def _step(n: int, tool: str, desc: str) -> None:
    print(f"\n[Step {n}] Calling tool: {tool}")
    print(f"         {desc}")
    print("-" * 65)


# ── The 3 MCP tool calls ──────────────────────────────────────────────────────

def tool_search_topic(question: str) -> dict:
    """MCP Tool 1 — internet: search web + generate explanation via LLM."""
    pid    = _active_profile_id()
    result = search_and_explain(question, pid)
    return {
        "question":     result.get("question", question),
        "explanation":  result.get("explanation", ""),
        "tags":         result.get("tags", []),
        "concept_type": result.get("concept_type", "other"),
        "follow_ups":   result.get("follow_ups", []),
    }


def tool_save_topic(question: str, explanation: str, tags: list, concept_type: str) -> dict:
    """MCP Tool 2 — local CRUD: save topic to data/curiosity_map.json."""
    pid    = _active_profile_id()
    result = manage_curiosity_map("add_topic", pid, {
        "question":     question,
        "explanation":  explanation,
        "tags":         tags,
        "concept_type": concept_type,
        "asked_by":     "agent",
    })
    topic = result.get("topic", {})
    return {
        "saved":             True,
        "topic_id":          topic.get("id", ""),
        "connections_found": result.get("connected_count", 0),
        "file":              "data/curiosity_map.json",
    }


def tool_get_dashboard_url() -> dict:
    """MCP Tool 3 — UI: return the Prefab dashboard URL."""
    return {
        "url":     "http://localhost:5175",
        "message": (
            "Open http://localhost:5175 in your browser to view the Whyzzle dashboard. "
            "The saved topic will appear in the sidebar under 'Recent Topics'."
        ),
    }


# ── Agent orchestration ───────────────────────────────────────────────────────

def run_agent(user_prompt: str) -> None:
    _banner("WHYZZLE MCP AGENT DEMO")
    print(f"PROMPT : {user_prompt}")
    print(f"PROFILE: {_active_profile_id()[:8]}…")

    # ── Tool 1: search the internet ───────────────────────────────────────────
    _step(1, "search_topic", "Searching the web + generating explanation via LLM…")
    search_result = tool_search_topic(user_prompt)
    print(f"  Question    : {search_result['question']}")
    print(f"  Tags        : {search_result['tags']}")
    print(f"  Concept type: {search_result['concept_type']}")
    print(f"  Explanation : {search_result['explanation'][:200]}…")

    # ── Tool 2: save to local file ────────────────────────────────────────────
    _step(2, "save_topic", "Saving result to data/curiosity_map.json…")
    save_result = tool_save_topic(
        question     = search_result["question"],
        explanation  = search_result["explanation"],
        tags         = search_result["tags"],
        concept_type = search_result["concept_type"],
    )
    print(f"  Saved       : {save_result['saved']}")
    print(f"  Topic ID    : {save_result['topic_id'][:8]}…")
    print(f"  File        : {save_result['file']}")
    print(f"  Connections : {save_result['connections_found']} related topics linked")

    # ── Tool 3: return dashboard URL ──────────────────────────────────────────
    _step(3, "get_dashboard_url", "Fetching the Prefab UI dashboard URL…")
    url_result = tool_get_dashboard_url()
    print(f"  URL         : {url_result['url']}")
    print(f"  Instruction : {url_result['message']}")

    # ── Summary ───────────────────────────────────────────────────────────────
    _banner("AGENT COMPLETE — all 3 MCP tools used successfully")
    print(f"  Topic      : {search_result['question']}")
    print(f"  Saved to   : data/curiosity_map.json")
    print(f"  View at    : {url_result['url']}")
    print()

    if search_result.get("follow_ups"):
        print("Follow-up questions you can explore next:")
        for i, q in enumerate(search_result["follow_ups"], 1):
            print(f"  {i}. {q}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    default_prompt = (
        "Find out who owns Tata Sons and their ownership structure"
    )
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_prompt
    run_agent(prompt)

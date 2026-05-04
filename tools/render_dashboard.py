"""
render_dashboard — MCP tool that returns structured view data.
The full interactive UI is served by webapp.py at http://localhost:5001
"""


def render_dashboard(view: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    ui_url = "http://localhost:5001"

    if view == "topic_detail":
        topic = payload.get("topic", {})
        return {
            "view": "topic_detail",
            "question": topic.get("question", ""),
            "explanation_preview": (topic.get("explanation", "")[:200] + "…")
            if len(topic.get("explanation", "")) > 200
            else topic.get("explanation", ""),
            "visual_type": topic.get("visual_type", ""),
            "tags": topic.get("tags", []),
            "follow_ups": topic.get("follow_ups", []),
            "message": f"Full topic detail with visual → {ui_url}",
        }

    if view == "graph":
        topics = payload.get("topics", [])
        return {
            "view": "graph",
            "node_count": len(topics),
            "edge_count": sum(len(t.get("connected_to", [])) for t in topics) // 2,
            "message": f"Interactive knowledge graph → {ui_url} (click Graph tab)",
        }

    if view == "recent":
        topics = payload.get("topics", [])
        return {
            "view": "recent",
            "questions": [t["question"] for t in topics[-5:]],
            "message": f"Full recent list → {ui_url}",
        }

    if view == "stats":
        return {
            "view": "stats",
            "stats": payload,
            "message": f"Full stats dashboard → {ui_url} (click Stats tab)",
        }

    if view == "visual_fullscreen":
        return {
            "view": "visual_fullscreen",
            "message": f"Fullscreen visual → {ui_url}",
        }

    if view == "profile_select":
        profiles = payload.get("profiles", [])
        active = payload.get("active_profile_id")
        return {
            "view": "profile_select",
            "profiles": [{"name": p["name"], "age": p["age"], "active": p["id"] == active} for p in profiles],
            "message": f"Profile switcher → {ui_url}",
        }

    return {"view": view, "message": f"Open {ui_url} for the full dashboard"}

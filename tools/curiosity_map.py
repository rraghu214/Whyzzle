import json
import logging
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger("whyzzle.map")

DATA_DIR = Path(__file__).parent.parent / "data"
MAP_FILE = DATA_DIR / "curiosity_map.json"


def _read_map() -> list:
    if not MAP_FILE.exists():
        return []
    with open(MAP_FILE, encoding="utf-8") as f:
        return json.load(f)


def _write_map(topics: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2)


def _calc_streak(topics: list) -> int:
    if not topics:
        return 0
    dates = sorted({t["date"] for t in topics}, reverse=True)
    today = date.today()
    most_recent = date.fromisoformat(dates[0])
    # Streak only active if asked today or yesterday
    if most_recent < today - timedelta(days=1):
        return 0
    streak = 0
    expected = most_recent
    for d_str in dates:
        d = date.fromisoformat(d_str)
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak


def manage_curiosity_map(action: str, profile_id: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    all_topics = _read_map()
    profile_topics = [t for t in all_topics if t.get("profile_id") == profile_id]

    if action == "read":
        return {"topics": profile_topics}

    if action == "add_topic":
        topic_id = str(uuid.uuid4())
        new_tags = set(payload.get("tags", []))
        question = payload.get("question", "")
        logger.info("Saving topic to curiosity map: \"%s\"", question[:80])
        logger.info("Tags: %s", list(new_tags))

        # Deduplicate: if same question already exists for this profile, return it
        def _normalize(q: str) -> str:
            return re.sub(r"[^a-z0-9 ]", "", q.lower().strip())

        norm_q = _normalize(question)
        for existing_topic in profile_topics:
            if _normalize(existing_topic.get("question", "")) == norm_q:
                logger.info("Duplicate question detected — skipping save, returning existing id=%s",
                            existing_topic["id"][:8])
                return {"topic": existing_topic, "connected_count": len(existing_topic.get("connected_to", []))}


        # Auto-connect: find profile topics with overlapping tags
        connected = []
        for t in profile_topics:
            overlap = new_tags & set(t.get("tags", []))
            if overlap:
                connected.append(t["id"])
                logger.info("Auto-connected to \"%s\" (shared tags: %s)",
                            t.get("question", "")[:50], list(overlap))
                # Bidirectional: add back-reference to existing topic
                for existing in all_topics:
                    if existing["id"] == t["id"] and topic_id not in existing.get("connected_to", []):
                        existing.setdefault("connected_to", []).append(topic_id)

        if not connected:
            logger.info("No existing topics share tags — standalone node")

        new_topic = {
            "id": topic_id,
            "profile_id": profile_id,
            "question": question,
            "asked_by": payload.get("asked_by", "child"),
            "date": str(date.today()),
            "profile_age": payload.get("profile_age", 7),
            "explanation": payload.get("explanation", ""),
            "visual_code": payload.get("visual_code", ""),
            "visual_type": payload.get("visual_type", "svg"),
            "follow_ups": payload.get("follow_ups", []),
            "tags": list(new_tags),
            "concept_type": payload.get("concept_type", "other"),
            "connected_to": connected,
            "depth": len(connected),
        }
        all_topics.append(new_topic)
        _write_map(all_topics)
        logger.info("Topic saved (id=%s, connections=%d, total in map=%d)",
                    topic_id[:8], len(connected), len(all_topics))
        return {"topic": new_topic, "connected_count": len(connected)}

    if action == "get_related":
        tags = set(payload.get("tags", []))
        related = []
        for t in profile_topics:
            overlap = tags & set(t.get("tags", []))
            if overlap:
                related.append({"topic": t, "shared_tags": list(overlap)})
        related.sort(key=lambda x: -len(x["shared_tags"]))
        return {"related": related[:5]}

    if action == "get_stats":
        if not profile_topics:
            return {"total": 0, "streak": 0, "top_branch": None, "top_tags": [], "this_week": 0}

        all_tags = [tag for t in profile_topics for tag in t.get("tags", [])]
        tag_counts = Counter(all_tags)
        top_tags = tag_counts.most_common(8)

        top_tag, top_count = top_tags[0] if top_tags else (None, 0)
        top_branch = f"{top_tag} — {top_count} questions" if top_tag else None

        week_ago = str(date.today() - timedelta(days=7))
        this_week = sum(1 for t in profile_topics if t["date"] >= week_ago)

        return {
            "total": len(profile_topics),
            "streak": _calc_streak(profile_topics),
            "top_branch": top_branch,
            "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
            "this_week": this_week,
        }

    if action == "update_connections":
        for topic in all_topics:
            if topic.get("profile_id") != profile_id:
                continue
            topic_tags = set(topic.get("tags", []))
            connected = [
                other["id"]
                for other in profile_topics
                if other["id"] != topic["id"] and topic_tags & set(other.get("tags", []))
            ]
            topic["connected_to"] = connected
            topic["depth"] = len(connected)
        _write_map(all_topics)
        return {"updated": len(profile_topics)}

    raise ValueError(f"Unknown action: {action}")

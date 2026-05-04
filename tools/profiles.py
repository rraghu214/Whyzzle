import json
import uuid
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
PROFILES_FILE = DATA_DIR / "profiles.json"

AVATAR_COLORS = [
    "#7B5EA7", "#27AE9E", "#E8735A", "#3498DB",
    "#E91E63", "#FF9800", "#4CAF50", "#9C27B0",
]


def _read() -> dict:
    if not PROFILES_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {"profiles": [], "active_profile_id": None}
        _write(data)
        return data
    with open(PROFILES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _pick_color(existing_profiles: list) -> str:
    used = {p["avatar_color"] for p in existing_profiles}
    for color in AVATAR_COLORS:
        if color not in used:
            return color
    return AVATAR_COLORS[len(existing_profiles) % len(AVATAR_COLORS)]


def manage_profiles(action: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    data = _read()

    if action == "list":
        return {
            "profiles": data["profiles"],
            "active_profile_id": data["active_profile_id"],
        }

    if action == "create":
        name = payload.get("name", "").strip()
        age = payload.get("age")
        if not name:
            raise ValueError("name is required")
        if age is None:
            raise ValueError("age is required")
        profile = {
            "id": str(uuid.uuid4()),
            "name": name,
            "age": int(age),
            "avatar_color": payload.get("avatar_color") or _pick_color(data["profiles"]),
            "created_at": str(date.today()),
        }
        data["profiles"].append(profile)
        if data["active_profile_id"] is None:
            data["active_profile_id"] = profile["id"]
        _write(data)
        return {"profiles": data["profiles"], "active_profile_id": data["active_profile_id"]}

    if action == "read":
        pid = payload.get("profile_id")
        profile = next((p for p in data["profiles"] if p["id"] == pid), None)
        return {"profile": profile, "active_profile_id": data["active_profile_id"]}

    if action == "update":
        pid = payload.get("profile_id")
        for p in data["profiles"]:
            if p["id"] == pid:
                if "name" in payload:
                    p["name"] = payload["name"].strip()
                if "age" in payload:
                    p["age"] = int(payload["age"])
                if "avatar_color" in payload:
                    p["avatar_color"] = payload["avatar_color"]
                break
        _write(data)
        return {"profiles": data["profiles"], "active_profile_id": data["active_profile_id"]}

    if action == "delete":
        pid = payload.get("profile_id")
        data["profiles"] = [p for p in data["profiles"] if p["id"] != pid]
        if data["active_profile_id"] == pid:
            data["active_profile_id"] = data["profiles"][0]["id"] if data["profiles"] else None
        # Cascade-delete curiosity map entries for this profile
        from tools.curiosity_map import _read_map, _write_map
        topics = _read_map()
        _write_map([t for t in topics if t.get("profile_id") != pid])
        _write(data)
        return {"profiles": data["profiles"], "active_profile_id": data["active_profile_id"]}

    if action == "set_active":
        pid = payload.get("profile_id")
        if any(p["id"] == pid for p in data["profiles"]):
            data["active_profile_id"] = pid
            _write(data)
        return {"profiles": data["profiles"], "active_profile_id": data["active_profile_id"]}

    raise ValueError(f"Unknown action: {action}")

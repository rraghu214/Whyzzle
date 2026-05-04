"""
Whyzzle Web App
---------------
Run this to open the full dashboard UI in a browser:
  python webapp.py
  → Open http://localhost:5001
"""

import logging
import os
import sys
import uuid
from collections import deque
from contextvars import ContextVar
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# ─── Per-request interaction ID ──────────────────────────────────────────────
# Each API call sets this so every log line carries [req-XXXXX] prefix.
_req_id: ContextVar[str] = ContextVar("req_id", default="-")

class _ReqIdFilter(logging.Filter):
    """Inject the current request ID into every log record as record.reqid."""
    def filter(self, record):
        record.reqid = _req_id.get()
        return True

_req_filter = _ReqIdFilter()

# ─── Logging setup ───────────────────────────────────────────────────────────
# In-memory ring buffer so the browser can poll recent log lines
_LOG_BUFFER: deque = deque(maxlen=300)

class _BufHandler(logging.Handler):
    def emit(self, record):
        _LOG_BUFFER.append(self.format(record))

_fmt = logging.Formatter("%(asctime)s  [%(reqid)s] %(message)s", datefmt="%H:%M:%S")

_buf_h = _BufHandler()
_buf_h.setFormatter(_fmt)
_buf_h.addFilter(_req_filter)

_con_h = logging.StreamHandler()
_con_h.setFormatter(_fmt)
_con_h.addFilter(_req_filter)

# File handler — writes to logs/whyzzle.log (rotates at 1 MB, keeps 3 backups)
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
from logging.handlers import RotatingFileHandler as _RFH
_file_h = _RFH(_LOG_DIR / "whyzzle.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
_file_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s  [%(reqid)s] %(message)s"))
_file_h.addFilter(_req_filter)

_wz = logging.getLogger("whyzzle")
_wz.setLevel(logging.DEBUG)
_wz.addHandler(_buf_h)
_wz.addHandler(_con_h)
_wz.addHandler(_file_h)
_wz.propagate = False

# ─── Imports that use the logger ─────────────────────────────────────────────
from tools.curiosity_map import _read_map, manage_curiosity_map
from tools.profiles import manage_profiles
from tools.search_and_explain import search_and_explain

app = Flask(__name__, static_folder="ui")
_wz.info("Whyzzle webapp starting up")


# ─── Static ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("ui", "index.html")


# ─── Profiles ────────────────────────────────────────────────────────────────

@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    return jsonify(manage_profiles("list"))


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    data = request.get_json(force=True) or {}
    return jsonify(manage_profiles("create", data))


@app.route("/api/profiles/<profile_id>/activate", methods=["POST"])
def activate_profile(profile_id):
    return jsonify(manage_profiles("set_active", {"profile_id": profile_id}))


@app.route("/api/profiles/<profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    return jsonify(manage_profiles("delete", {"profile_id": profile_id}))


# ─── Logs ────────────────────────────────────────────────────────────────────

@app.route("/api/logs")
def get_logs():
    """Return recent agent log lines for the UI log panel."""
    since = request.args.get("since", type=int, default=0)
    buf = list(_LOG_BUFFER)
    return jsonify({"logs": buf[since:], "total": len(buf)})


# ─── Ask ─────────────────────────────────────────────────────────────────────

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    asked_by = data.get("asked_by", "child")

    if not question:
        return jsonify({"error": "question is required"}), 400

    profiles_data = manage_profiles("list")
    active_id = profiles_data.get("active_profile_id")
    if not active_id:
        return jsonify({"error": "No active profile — create one first."}), 400

    _req_id.set(f"ask-{uuid.uuid4().hex[:5]}")
    _wz.info("--- /api/ask: \"%s\" (by %s) ---", question[:80], asked_by)

    # Core pipeline: search + explain + generate visual
    result = search_and_explain(question, active_id, asked_by)

    # Save to curiosity map
    _wz.info("Storing result in curiosity map...")
    topic_data = manage_curiosity_map("add_topic", active_id, result)
    topic = topic_data.get("topic", result)

    # Fetch related topics for the response
    related_result = manage_curiosity_map("get_related", active_id, {"tags": topic.get("tags", [])})
    related = [r for r in related_result.get("related", []) if r["topic"]["id"] != topic["id"]]
    _wz.info("Found %d related topic(s) in curiosity map", len(related))

    return jsonify({"topic": topic, "related": related})


# ─── 3D Blender scene ────────────────────────────────────────────────────────

@app.route("/api/3d", methods=["POST"])
def render_3d():
    data     = request.get_json(force=True) or {}
    topic_id = data.get("topic_id", "").strip()
    if not topic_id:
        return jsonify({"error": "topic_id is required"}), 400

    all_topics = _read_map()
    topic = next((t for t in all_topics if t["id"] == topic_id), None)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    from tools.blender_scene import generate_3d_scene
    _req_id.set(f"3d-{uuid.uuid4().hex[:5]}")
    _wz.info("3D render requested for topic: %s", topic.get("question", "")[:60])
    result = generate_3d_scene(
        topic       = topic.get("question", ""),
        concept_type= topic.get("concept_type", "other"),
        parameters  = {},
    )
    return jsonify(result)


@app.route("/api/regenerate-visual", methods=["POST"])
def regenerate_visual():
    """Re-generate visualization for an existing topic (Canvas 2D animation).
    Updates the visual in the UI without creating a new topic entry.
    """
    data     = request.get_json(force=True) or {}
    topic_id = data.get("topic_id", "").strip()
    if not topic_id:
        return jsonify({"error": "topic_id is required"}), 400

    all_topics = _read_map()
    topic = next((t for t in all_topics if t["id"] == topic_id), None)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    from tools.search_and_explain import generate_canvas_visual
    _req_id.set(f"vis-{uuid.uuid4().hex[:5]}")
    _wz.info("Regenerating visual for: %s", topic.get("question", "")[:60])
    result = generate_canvas_visual(
        question     = topic.get("question", ""),
        concept_type = topic.get("concept_type", "other"),
    )
    return jsonify(result)


@app.route("/output/<path:filename>")
def serve_output(filename):
    """Serve rendered Blender animations."""
    return send_from_directory("output", filename)


# ─── Map & stats ─────────────────────────────────────────────────────────────

@app.route("/api/map/<profile_id>", methods=["GET"])
def get_map(profile_id):
    return jsonify(manage_curiosity_map("read", profile_id))


@app.route("/api/stats/<profile_id>", methods=["GET"])
def get_stats(profile_id):
    return jsonify(manage_curiosity_map("get_stats", profile_id))


@app.route("/api/topic/<topic_id>", methods=["GET"])
def get_topic(topic_id):
    all_topics = _read_map()
    topic = next((t for t in all_topics if t["id"] == topic_id), None)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    # Also return related topics (same profile, shared tags)
    profile_id = topic.get("profile_id")
    related_result = manage_curiosity_map(
        "get_related", profile_id, {"tags": topic.get("tags", [])}
    )
    related = [r for r in related_result.get("related", []) if r["topic"]["id"] != topic_id]
    return jsonify({"topic": topic, "related": related})


# ─── Error handler ───────────────────────────────────────────────────────────

@app.errorhandler(Exception)
def handle_error(exc):
    return jsonify({"error": str(exc)}), 500


# ─── Run ─────────────────────────────────────────────────────────────────────

def main():
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Whyzzle dashboard -> http://localhost:{port}\n")
    app.run(debug=True, port=port, use_reloader=False)


if __name__ == "__main__":
    main()

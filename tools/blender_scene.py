"""
Tool 4 — generate_3d_scene
Runs Blender headlessly to produce a 10-second EEVEE animation.

Blender must be installed (blender.org).  The tool auto-detects the
executable across Windows / macOS / Linux and selects the best script
template based on concept_type + topic keywords.
"""

import glob
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger("whyzzle.blender")

OUTPUT_DIR  = Path(__file__).parent.parent / "output"
SCRIPTS_DIR = Path(__file__).parent.parent / "blender_scripts"


# ─── Blender discovery ────────────────────────────────────────────────────────

def _find_blender() -> str | None:
    """Return path to the Blender executable, or None if not found."""
    # 1 — Explicit override via BLENDER_PATH in .env
    env_path = os.environ.get("BLENDER_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return str(p)
        # Treat as directory — look for blender.exe inside (any depth)
        hits = sorted(p.rglob("blender.exe"), reverse=True)
        if hits:
            return str(hits[0])
        logger.warning("BLENDER_PATH set to '%s' but blender.exe not found there", env_path)

    # 2 — PATH (works if user added Blender to system PATH)
    found = shutil.which("blender")
    if found:
        return found

    if sys.platform == "win32":
        patterns = [
            r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe",
            r"C:\Users\*\AppData\Roaming\Blender Foundation\Blender\*\blender.exe",
        ]
        for pat in patterns:
            hits = sorted(glob.glob(pat), reverse=True)   # newest version first
            if hits:
                return hits[0]

    if sys.platform == "darwin":
        for cand in [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender 4.0/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender 3.6/Blender.app/Contents/MacOS/Blender",
        ]:
            if Path(cand).exists():
                return cand

    return None


# ─── Template selection ───────────────────────────────────────────────────────

_ORBIT_WORDS       = {"planet", "orbit", "solar", "space", "star", "moon", "earth",
                      "mars", "saturn", "jupiter", "mercury", "venus", "rotate", "revolve"}
_CROSS_WORDS       = {"volcano", "interior", "layer", "crust", "mantle", "core",
                      "cross", "section", "inside", "atom", "cell", "nucleus"}
_GROWTH_WORDS      = {"grow", "seed", "plant", "tree", "life cycle", "flower",
                      "sprout", "root", "leaf", "biology", "germinate"}

def _select_template(concept_type: str, topic: str) -> str:
    words = set(topic.lower().split())
    if words & _ORBIT_WORDS:
        return "orbit.py"
    if words & _CROSS_WORDS:
        return "cross_section.py"
    if words & _GROWTH_WORDS:
        return "growth.py"
    # Fallback by concept_type
    if concept_type in ("biological", "sequential"):
        return "growth.py"
    if concept_type in ("spatial", "comparative", "mathematical"):
        return "orbit.py"
    return "orbit.py"


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_3d_scene(topic: str, concept_type: str, parameters: dict | None = None) -> dict:
    """
    Render a 10-second Blender EEVEE animation for the given topic.

    Returns:
      {video_url, video_path, duration, error}
    """
    parameters = parameters or {}
    logger.info("3D scene request: topic='%s' concept_type=%s", topic[:60], concept_type)

    blender_exe = _find_blender()
    if not blender_exe:
        msg = (
            "Blender is not installed or not found in PATH. "
            "Download it from blender.org, install, then try again."
        )
        logger.warning(msg)
        return {"error": msg, "video_url": None, "video_path": None, "duration": 0}

    logger.info("Blender found at: %s", blender_exe)

    template = _select_template(concept_type, topic)
    script_path = SCRIPTS_DIR / template
    if not script_path.exists():
        err = f"Blender script template not found: {script_path}"
        logger.error(err)
        return {"error": err, "video_url": None, "video_path": None, "duration": 0}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
    output_file = OUTPUT_DIR / f"scene_{safe}.mp4"

    # Temp directory for PNG frame sequence (Blender 5.x removed FFMPEG render output)
    frames_dir = Path(tempfile.mkdtemp(prefix="whyzzle_frames_"))

    # Pass parameters to the Blender script via a temp JSON file
    params_data = {"topic": topic, "concept_type": concept_type,
                   "frames_dir": str(frames_dir), **parameters}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(params_data, f)
        params_file = f.name

    try:
        cmd = [blender_exe, "--background", "--python", str(script_path),
               "--", "--params", params_file]
        logger.info("Running: %s", " ".join(cmd[:4]) + " ... --params <json>")

        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )

        if proc.returncode != 0:
            tail = (proc.stderr or "")[-600:]
            logger.error("Blender exited %d: %s", proc.returncode, tail)
            return {
                "error": f"Blender render failed (exit {proc.returncode}): {tail[-200:]}",
                "video_url": None, "video_path": None, "duration": 0,
            }

        # Check PNG frames were written
        frame_files = sorted(frames_dir.glob("frame_*.png"))
        if not frame_files:
            stderr_tail = (proc.stderr or "").strip()[-800:]
            logger.error("Blender ran but wrote no frames. Stderr: %s", stderr_tail)
            return {
                "error": f"Blender ran but produced no frames. Error: {stderr_tail[-300:]}",
                "video_url": None, "video_path": None, "duration": 0,
            }

        logger.info("Blender rendered %d PNG frames — combining with ffmpeg...", len(frame_files))

        # Combine PNG frames → MP4 using bundled ffmpeg
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        frame_pattern = str(frames_dir / "frame_%04d.png")
        ff_proc = subprocess.run([
            ffmpeg_exe, "-y",
            "-framerate", "24",
            "-start_number", "1",
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_file),
        ], capture_output=True, text=True, timeout=120)

        if ff_proc.returncode != 0 or not output_file.exists():
            logger.error("ffmpeg failed: %s", ff_proc.stderr[-300:])
            return {
                "error": f"ffmpeg video assembly failed: {ff_proc.stderr[-200:]}",
                "video_url": None, "video_path": None, "duration": 0,
            }

        logger.info("3D scene rendered: %s (%.1f KB)",
                    output_file.name, output_file.stat().st_size / 1024)
        return {
            "video_url": f"/output/{output_file.name}",
            "video_path": str(output_file),
            "duration": 10,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        logger.error("Blender render timed out after 300s")
        return {
            "error": "Blender render timed out (>5 minutes).",
            "video_url": None, "video_path": None, "duration": 0,
        }

    finally:
        try:
            os.unlink(params_file)
        except OSError:
            pass
        # Clean up temp frames dir
        import shutil
        shutil.rmtree(frames_dir, ignore_errors=True)

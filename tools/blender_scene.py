"""
Tool 4 — generate_3d_scene
Runs Blender headlessly to produce a short CYCLES (CPU) animation.

Flow:
  1. Ask an LLM (Groq → Gemini → Ollama) to pick a template and return
     scene parameters as JSON — no code generation, no crashes.
  2. Merge those parameters into the params file passed to Blender.
  3. The template script reads the parameters and builds the scene.
  4. If LLM fails, fall back to keyword-based template selection with defaults.
"""

import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("whyzzle.blender")

OUTPUT_DIR  = Path(__file__).parent.parent / "output"
SCRIPTS_DIR = Path(__file__).parent.parent / "blender_scripts"


def _cfg() -> dict:
    """Read render config from .env — tune without touching code."""
    return {
        "samples":          int(os.environ.get("BLENDER_SAMPLES",          "4")),
        "frames":           int(os.environ.get("BLENDER_FRAMES",           "60")),
        "width":            int(os.environ.get("BLENDER_WIDTH",            "480")),
        "height":           int(os.environ.get("BLENDER_HEIGHT",           "270")),
        "llm_timeout":      int(os.environ.get("BLENDER_LLM_TIMEOUT",      "90")),
        "template_timeout": int(os.environ.get("BLENDER_TEMPLATE_TIMEOUT", "300")),
    }


# ─── Blender discovery ────────────────────────────────────────────────────────

def _find_blender() -> str | None:
    env_path = os.environ.get("BLENDER_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return str(p)
        hits = sorted(p.rglob("blender.exe"), reverse=True)
        if hits:
            return str(hits[0])
        logger.warning("BLENDER_PATH='%s' but blender.exe not found", env_path)

    found = shutil.which("blender")
    if found:
        return found

    if sys.platform == "win32":
        for pat in [
            r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe",
        ]:
            hits = sorted(glob.glob(pat), reverse=True)
            if hits:
                return hits[0]

    if sys.platform == "darwin":
        for cand in ["/Applications/Blender.app/Contents/MacOS/Blender"]:
            if Path(cand).exists():
                return cand

    return None


# ─── LLM: generate scene parameters (JSON, not code) ─────────────────────────

_ORBIT_SCHEMA = '''{
  "template": "orbit",
  "background_color": [R, G, B],
  "central_body": {"label": "Name", "color": [R, G, B], "radius": 1.0},
  "orbiting_bodies": [
    {"label": "Name", "color": [R, G, B], "radius": 0.2, "orbit_r": 3.0, "speed": 1.5},
    {"label": "Name", "color": [R, G, B], "radius": 0.15, "orbit_r": 5.0, "speed": 0.8}
  ]
}'''

_CROSS_SCHEMA = '''{
  "template": "cross_section",
  "background_color": [R, G, B],
  "layers": [
    {"label": "Innermost", "radius": 0.6, "color": [R, G, B], "emit": 8.0, "alpha": 0.0},
    {"label": "Middle",    "radius": 1.4, "color": [R, G, B], "emit": 3.0, "alpha": 0.5},
    {"label": "Outer",     "radius": 2.2, "color": [R, G, B], "emit": 1.0, "alpha": 0.75}
  ]
}'''

_GROWTH_SCHEMA = '''{
  "template": "growth",
  "background_color": [R, G, B],
  "ground_color": [R, G, B],
  "stem_color":   [R, G, B],
  "leaf_color":   [R, G, B],
  "seed_color":   [R, G, B],
  "title": "Short animation title"
}'''


def _generate_scene_params(topic: str, concept_type: str) -> dict | None:
    """
    Ask the LLM to pick a template and return customised scene parameters as JSON.
    Returns a dict like {"template": "orbit", "orbiting_bodies": [...], ...}
    or None if the call fails.
    """
    try:
        from tools.search_and_explain import _call_llm
    except ImportError:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from tools.search_and_explain import _call_llm
        except ImportError as e:
            logger.warning("Cannot import _call_llm: %s", e)
            return None

    prompt = f"""You are choosing parameters for a 3D educational animation.

TOPIC: "{topic}"
CONCEPT TYPE: {concept_type}
AUDIENCE: children aged 8-14

Pick the best template and fill in creative, topic-appropriate parameters.

Templates:
• "orbit"         — objects revolving around a central body
                    Use for: solar system, atoms, satellites, moons, anything that orbits
• "cross_section" — nested concentric spheres that rotate to reveal layers
                    Use for: Earth's interior, cell structure, any layered system
• "growth"        — something sprouting and growing upward from the ground
                    Use for: plants, seeds, trees, anything that grows

Rules:
- orbit: 2–5 orbiting bodies; orbit_r 2.0–7.0; speed 0.5–5.0
- cross_section: 3–5 layers; innermost radius ~0.5, outermost ≤2.8; innermost alpha=0 (opaque), outermost alpha≤0.9
- All colors are [R, G, B] with floats 0.0–1.0. Make them vivid and child-friendly.
- Labels: short (1–3 words), descriptive, educational

Schemas (output ONLY the JSON for the chosen template, no markdown, no explanation):

orbit →
{_ORBIT_SCHEMA}

cross_section →
{_CROSS_SCHEMA}

growth →
{_GROWTH_SCHEMA}"""

    try:
        raw = _call_llm(prompt).strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw.rstrip())
        params = json.loads(raw)
        template = params.get("template")
        if template not in ("orbit", "cross_section", "growth"):
            logger.warning("LLM returned unknown template '%s'", template)
            return None
        logger.info("LLM chose template '%s' for: %s", template, topic[:60])
        return params
    except Exception as e:
        logger.warning("Scene params generation failed: %s", e)
        return None


# ─── Fallback: keyword-based template selection ───────────────────────────────

_ORBIT_WORDS  = {"planet", "orbit", "solar", "space", "star", "moon", "earth",
                 "mars", "saturn", "jupiter", "mercury", "venus", "rotate",
                 "revolve", "gravity", "float", "floating", "atom", "electron"}
_CROSS_WORDS  = {"volcano", "interior", "layer", "crust", "mantle", "core",
                 "cross", "section", "inside", "cell", "nucleus", "structure"}
_GROWTH_WORDS = {"grow", "seed", "plant", "tree", "flower", "sprout", "root",
                 "leaf", "biology", "germinate", "photosynthesis", "lifecycle"}

def _fallback_template(concept_type: str, topic: str) -> str:
    words = set(topic.lower().split())
    if words & _ORBIT_WORDS:  return "orbit"
    if words & _CROSS_WORDS:  return "cross_section"
    if words & _GROWTH_WORDS: return "growth"
    if concept_type in ("biological", "sequential"): return "growth"
    if concept_type in ("spatial",):                 return "cross_section"
    return "orbit"


# ─── Run Blender + assemble MP4 ───────────────────────────────────────────────

def _run_blender(blender_exe: str, script_path: Path, params_file: str,
                 frames_dir: Path, output_file: Path, timeout: int = 300) -> dict:
    cmd = [blender_exe, "--background", "--factory-startup",
           "--python", str(script_path),
           "--", "--params", params_file]
    logger.info("Blender (timeout=%ds): %s", timeout, script_path.name)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"Blender timed out (>{timeout}s).",
                "video_url": None, "video_path": None, "duration": 0}

    if proc.stdout:
        logger.info("Blender stdout: %s", proc.stdout[-300:])
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-600:]
        logger.error("Blender exit %d: %s", proc.returncode, tail)
        return {"error": f"Blender failed (exit {proc.returncode}): {tail[-200:]}",
                "video_url": None, "video_path": None, "duration": 0}

    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        tail = (proc.stderr or "").strip()[-600:]
        logger.error("No frames written. stderr: %s", tail)
        return {"error": f"No frames produced: {tail[-200:]}",
                "video_url": None, "video_path": None, "duration": 0}

    logger.info("%d frames rendered — assembling MP4", len(frames))
    import imageio_ffmpeg
    ff = subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-framerate", "24", "-start_number", "1",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_file),
    ], capture_output=True, text=True, timeout=120)

    if ff.returncode != 0 or not output_file.exists():
        logger.error("ffmpeg failed: %s", ff.stderr[-300:])
        return {"error": f"ffmpeg failed: {ff.stderr[-200:]}",
                "video_url": None, "video_path": None, "duration": 0}

    logger.info("Done: %s (%.1f KB)", output_file.name, output_file.stat().st_size / 1024)
    return {"video_url": f"/output/{output_file.name}",
            "video_path": str(output_file),
            "duration": len(frames) // 24,
            "error": None}


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_3d_scene(topic: str, concept_type: str, parameters: dict | None = None) -> dict:
    parameters = parameters or {}
    cfg = _cfg()
    logger.info("3D scene: '%s' | %dx%d %df %ds",
                topic[:60], cfg["width"], cfg["height"], cfg["frames"], cfg["samples"])

    blender_exe = _find_blender()
    if not blender_exe:
        return {"error": "Blender not found. Install from blender.org and set BLENDER_PATH in .env",
                "video_url": None, "video_path": None, "duration": 0}
    logger.info("Blender: %s", blender_exe)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe        = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
    output_file = OUTPUT_DIR / f"scene_{safe}.mp4"
    frames_dir  = Path(tempfile.mkdtemp(prefix="whyzzle_frames_"))

    # ── Ask LLM for scene parameters ─────────────────────────────────────────
    scene_params = _generate_scene_params(topic, concept_type)
    if scene_params:
        template_name = scene_params["template"]
    else:
        template_name = _fallback_template(concept_type, topic)
        logger.info("LLM params unavailable — fallback template: %s", template_name)

    script_path = SCRIPTS_DIR / f"{template_name}.py"
    if not script_path.exists():
        return {"error": f"Template not found: {script_path}",
                "video_url": None, "video_path": None, "duration": 0}

    # Merge render config + scene params into the params file for Blender
    params_data = {
        "topic": topic,
        "concept_type": concept_type,
        "frames_dir": str(frames_dir),
        # render tuning (templates read these)
        "samples": cfg["samples"],
        "frames":  cfg["frames"],
        "width":   cfg["width"],
        "height":  cfg["height"],
        # scene parameters from LLM (or empty — templates use their own defaults)
        **(scene_params or {}),
        # caller overrides last
        **parameters,
    }

    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(params_data, f, indent=2)
        params_file = f.name

    # Save params for debugging
    (OUTPUT_DIR / "debug_last_params.json").write_text(
        json.dumps(params_data, indent=2), encoding="utf-8")

    try:
        timeout = cfg["llm_timeout"] if scene_params else cfg["template_timeout"]
        logger.info("Running template '%s' (timeout=%ds)", template_name, timeout)
        return _run_blender(blender_exe, script_path, params_file,
                            frames_dir, output_file, timeout=timeout)
    finally:
        try:
            os.unlink(params_file)
        except OSError:
            pass
        shutil.rmtree(frames_dir, ignore_errors=True)

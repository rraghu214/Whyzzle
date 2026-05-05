"""
Tool 4 — generate_3d_scene
Runs Blender headlessly to produce a 5-second CYCLES (CPU) animation.

PRIMARY path: asks an LLM (Groq → Gemini → Ollama, same waterfall as
search_and_explain) to write a Blender Python script tailored to the topic —
works for any subject: planets, chemistry, maths, history, biology…
FALLBACK: static hand-crafted templates (orbit / cross_section / growth).
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
    """Read render config from env — all tunable in .env without code changes."""
    return {
        "samples":          int(os.environ.get("BLENDER_SAMPLES",          "4")),
        "frames":           int(os.environ.get("BLENDER_FRAMES",           "60")),
        "width":            int(os.environ.get("BLENDER_WIDTH",            "480")),
        "height":           int(os.environ.get("BLENDER_HEIGHT",           "270")),
        "llm_timeout":      int(os.environ.get("BLENDER_LLM_TIMEOUT",      "90")),
        "template_timeout": int(os.environ.get("BLENDER_TEMPLATE_TIMEOUT", "300")),
    }


# Boilerplate that MUST appear at the top of every generated script.
_BOILERPLATE = '''\
import bpy, json, math, sys, os

params = {}
argv = sys.argv
if "--" in argv:
    extra = argv[argv.index("--") + 1:]
    if "--params" in extra:
        idx = extra.index("--params") + 1
        if idx < len(extra):
            with open(extra[idx], encoding="utf-8") as f:
                params = json.load(f)

frames_dir = params.get("frames_dir", os.path.join(os.path.dirname(__file__), "frames"))
os.makedirs(frames_dir, exist_ok=True)
'''

# Blender 4.x / 5.x compatible keyframe-interpolation helper.
_INTERP_HELPER = '''\
def _set_interp(obj, mode="LINEAR"):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    fcurves = []
    try:
        fcurves = list(action.fcurves)
    except AttributeError:
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in getattr(strip, "channelbags", []):
                        fcurves.extend(bag.fcurves)
        except (AttributeError, TypeError):
            pass
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = mode
'''


def _render_settings_block(cfg: dict) -> str:
    """Render the mandatory scene-setup block with live config values."""
    return f'''\
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = {cfg["frames"]}
scene.render.fps  = 24
scene.render.image_settings.file_format = "PNG"
scene.render.filepath     = os.path.join(frames_dir, "frame_####")
scene.render.resolution_x = {cfg["width"]}
scene.render.resolution_y = {cfg["height"]}
scene.render.engine  = "CYCLES"
scene.cycles.samples = {cfg["samples"]}
scene.cycles.device  = "CPU"

# Minimise bounce depth — biggest single speedup for simple scenes
scene.cycles.max_bounces             = 2
scene.cycles.diffuse_bounces         = 1
scene.cycles.glossy_bounces          = 1
scene.cycles.transmission_bounces    = 1
scene.cycles.volume_bounces          = 0
scene.cycles.transparent_max_bounces = 2

# World — always created here so scene.world is never None
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
_bg_node = world.node_tree.nodes["Background"]
_bg_node.inputs[0].default_value = (0.01, 0.01, 0.05, 1)
_bg_node.inputs[1].default_value = 1.0
'''


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
        logger.warning("BLENDER_PATH set to '%s' but blender.exe not found there", env_path)

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
            hits = sorted(glob.glob(pat), reverse=True)
            if hits:
                return hits[0]

    if sys.platform == "darwin":
        for cand in [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender 4.0/Blender.app/Contents/MacOS/Blender",
        ]:
            if Path(cand).exists():
                return cand

    return None


# ─── LLM-generated script ────────────────────────────────────────────────────

def _generate_script_via_llm(topic: str, concept_type: str) -> str | None:
    """
    Ask an LLM (Groq → Gemini → Ollama waterfall) to write the *scene content*
    of a Blender script. The boilerplate, render settings, and fcurve helper are
    prepended by us — the LLM never touches that critical infrastructure.
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

    cfg = _cfg()

    scene_prompt = f"""You are writing the scene-building section of a Blender Python script.
The script header is already written. Do NOT add import statements, do NOT call
bpy.ops.wm.read_factory_settings, and do NOT touch render or cycles settings.

Pre-defined — do NOT redefine or reassign any of these:
  scene, world, frames_dir, _set_interp, bpy, math, os

Set background colour with exactly:
  world.node_tree.nodes["Background"].inputs[0].default_value = (R, G, B, 1)

TOPIC: "{topic}"   CONCEPT TYPE: {concept_type}   AUDIENCE: children 8-14

STRICT PERFORMANCE RULES — every rule is mandatory:
1. Maximum 5 mesh objects total
2. ALWAYS specify segments/ring_count explicitly — NEVER use defaults (Blender defaults to 32 which is too slow):
     uv_sphere  → segments=12, ring_count=8
     cylinder   → vertices=8
     torus      → major_segments=16, minor_segments=4
     cone/circle → vertices=8
   Example: bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=12, ring_count=8, location=(0,0,0))
3. MATERIALS — use Emission shader ONLY (not Principled BSDF — Emission skips expensive light bounces):
     m = bpy.data.materials.new("Name")
     m.use_nodes = True
     m.node_tree.nodes.clear()
     em = m.node_tree.nodes.new("ShaderNodeEmission")
     out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
     em.inputs["Color"].default_value = (R, G, B, 1)
     em.inputs["Strength"].default_value = 2.0
     m.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
     obj.data.materials.append(m)
4. NEVER use: Principled BSDF, blend_method, shadow_method, modifier_add, subdivision_set, shade_smooth
5. At most 2 keyframes per object (frame 1 and frame {cfg["frames"]})
6. Write each object explicitly — no loops that create many objects

Write in this exact order (all 8 steps required):
1. world.node_tree.nodes["Background"].inputs[0].default_value = (R, G, B, 1)
2. Create each mesh object with EXPLICIT segments as shown above
3. Assign an Emission material to each object using the pattern above
4. Add 1 text label: bpy.ops.object.text_add(location=(0,3,0)); t=bpy.context.active_object; t.data.body="KEY CONCEPT"; t.data.size=0.4; t.rotation_euler=(1.2,0,0)
5. Animate: obj.rotation_euler=(0,0,0); obj.keyframe_insert("rotation_euler", frame=1); obj.rotation_euler.z=6.28; obj.keyframe_insert("rotation_euler", frame={cfg["frames"]}); _set_interp(obj,"LINEAR")
6. bpy.ops.object.light_add(type="SUN", location=(5,5,8)); bpy.context.active_object.data.energy=3
7. bpy.ops.object.camera_add(location=(0,-8,4)); cam=bpy.context.active_object; cam.rotation_euler=(1.1,0,0); scene.camera=cam
8. bpy.ops.render.render(animation=True)

Output ONLY Python code. No markdown fences, no explanation text."""

    try:
        scene_code = _call_llm(scene_prompt)
        scene_code = scene_code.strip()
        scene_code = re.sub(r"^```[a-z]*\n?", "", scene_code)
        scene_code = re.sub(r"\n?```\s*$", "", scene_code.rstrip())

        # Sanitize: strip lines that conflict with the mandatory header
        _STRIP_PATTERNS = [
            r"bpy\.data\.worlds\.new\(",                          # world already created
            r"(scene|bpy\.context\.scene)\.world\s*=",           # world already assigned
            r"import\s+bpy",                                      # already imported
            r"bpy\.ops\.wm\.read_factory",                        # already called
            r"(scene|bpy\.context\.scene)\.frame_(start|end)\s*=",
            r"(scene|bpy\.context\.scene)\.render\.(engine|resolution|fps|filepath|image_settings)",
            r"(scene|bpy\.context\.scene)\.cycles\.",             # samples/device already set
            r"bpy\.ops\.object\.modifier_add",                    # no subdivision modifiers
            r"\.modifier_set\b",
            r"ops\.object\.subdivision_set",
        ]
        clean_lines = []
        for line in scene_code.splitlines():
            s = line.strip()
            if any(re.search(p, s) for p in _STRIP_PATTERNS):
                clean_lines.append(f"# [sanitized] {line.rstrip()}")
            else:
                clean_lines.append(line)
        scene_code = "\n".join(clean_lines)

        # Prepend the mandatory header ourselves — LLM never touches it
        render_block = _render_settings_block(cfg)
        full_script = _BOILERPLATE + "\n" + render_block + "\n" + _INTERP_HELPER + "\n" + scene_code

        # Save for debugging — inspect output/debug_last_llm_script.py on failures
        debug_path = OUTPUT_DIR / "debug_last_llm_script.py"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(full_script, encoding="utf-8")
        logger.info("LLM script saved to %s (%d chars, timeout=%ds)",
                    debug_path.name, len(full_script), cfg["llm_timeout"])
        return full_script
    except Exception as e:
        logger.warning("LLM script generation failed: %s", e)
        return None


# ─── Fallback static template selection ──────────────────────────────────────

_ORBIT_WORDS  = {"planet", "orbit", "solar", "space", "star", "moon", "earth",
                 "mars", "saturn", "jupiter", "mercury", "venus", "rotate", "revolve", "gravity"}
_CROSS_WORDS  = {"volcano", "interior", "layer", "crust", "mantle", "core",
                 "cross", "section", "inside", "atom", "cell", "nucleus", "electron"}
_GROWTH_WORDS = {"grow", "seed", "plant", "tree", "flower", "sprout", "root",
                 "leaf", "biology", "germinate", "photosynthesis", "lifecycle"}

def _select_fallback_template(concept_type: str, topic: str) -> str:
    words = set(topic.lower().split())
    if words & _ORBIT_WORDS:
        return "orbit.py"
    if words & _CROSS_WORDS:
        return "cross_section.py"
    if words & _GROWTH_WORDS:
        return "growth.py"
    if concept_type in ("biological", "sequential"):
        return "growth.py"
    if concept_type in ("spatial",):
        return "cross_section.py"
    return "orbit.py"


# ─── Shared render helper ─────────────────────────────────────────────────────

def _run_blender(blender_exe: str, script_path: Path, params_file: str,
                 frames_dir: Path, output_file: Path, timeout: int = 600) -> dict:
    """Run Blender, assemble frames → MP4. Returns the result dict."""
    cmd = [blender_exe, "--background", "--factory-startup",
           "--python", str(script_path),
           "--", "--params", params_file]
    logger.info("Running Blender (timeout=%ds): %s … --params <json>", timeout, " ".join(cmd[:5]))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"Blender render timed out (>{timeout}s).",
                "video_url": None, "video_path": None, "duration": 0}

    if proc.stdout:
        logger.info("Blender stdout (tail): %s", proc.stdout[-400:])
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-600:]
        logger.error("Blender exited %d: %s", proc.returncode, tail)
        return {"error": f"Blender render failed (exit {proc.returncode}): {tail[-200:]}",
                "video_url": None, "video_path": None, "duration": 0}

    frame_files = sorted(frames_dir.glob("frame_*.png"))
    if not frame_files:
        tail = (proc.stderr or "").strip()[-600:]
        logger.error("Blender wrote no frames. stderr: %s", tail)
        return {"error": f"Blender produced no frames: {tail[-200:]}",
                "video_url": None, "video_path": None, "duration": 0}

    logger.info("Blender rendered %d frames — assembling MP4…", len(frame_files))

    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ff = subprocess.run([
        ffmpeg_exe, "-y",
        "-framerate", "24",
        "-start_number", "1",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_file),
    ], capture_output=True, text=True, timeout=120)

    if ff.returncode != 0 or not output_file.exists():
        logger.error("ffmpeg failed: %s", ff.stderr[-300:])
        return {"error": f"ffmpeg assembly failed: {ff.stderr[-200:]}",
                "video_url": None, "video_path": None, "duration": 0}

    logger.info("Scene ready: %s (%.1f KB)",
                output_file.name, output_file.stat().st_size / 1024)
    return {"video_url": f"/output/{output_file.name}",
            "video_path": str(output_file), "duration": 5, "error": None}


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_3d_scene(topic: str, concept_type: str, parameters: dict | None = None) -> dict:
    """
    Render a 5-second Blender CYCLES animation for any topic.

    1. Ask Claude to generate a topic-specific Blender script.
    2. If that fails or errors, fall back to a static template.
    """
    parameters = parameters or {}
    logger.info("3D scene request: topic='%s' concept_type=%s", topic[:60], concept_type)

    blender_exe = _find_blender()
    if not blender_exe:
        msg = ("Blender not found. Install from blender.org and set BLENDER_PATH in .env")
        logger.warning(msg)
        return {"error": msg, "video_url": None, "video_path": None, "duration": 0}
    logger.info("Blender: %s", blender_exe)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe        = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
    output_file = OUTPUT_DIR / f"scene_{safe}.mp4"
    frames_dir  = Path(tempfile.mkdtemp(prefix="whyzzle_frames_"))

    params_data = {"topic": topic, "concept_type": concept_type,
                   "frames_dir": str(frames_dir), **parameters}
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(params_data, f)
        params_file = f.name

    cfg = _cfg()
    logger.info("Render config: %dx%d, %d frames, %d samples, llm_timeout=%ds, template_timeout=%ds",
                cfg["width"], cfg["height"], cfg["frames"], cfg["samples"],
                cfg["llm_timeout"], cfg["template_timeout"])

    try:
        # ── 1. Try LLM-generated script ───────────────────────────────────────
        script_content = _generate_script_via_llm(topic, concept_type)
        if script_content:
            with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, encoding="utf-8") as sf:
                sf.write(script_content)
                generated_script = Path(sf.name)
            try:
                result = _run_blender(blender_exe, generated_script, params_file,
                                      frames_dir, output_file, timeout=cfg["llm_timeout"])
                if result["error"] is None:
                    logger.info("LLM-generated script succeeded for: %s", topic[:50])
                    return result
                logger.warning("LLM script failed (%s) — falling back to template",
                               result["error"][:80])
            finally:
                generated_script.unlink(missing_ok=True)
                for f in frames_dir.glob("*.png"):
                    f.unlink()
        else:
            logger.info("LLM generation skipped/failed — using static template")

        # ── 2. Fallback: static template ──────────────────────────────────────
        template    = _select_fallback_template(concept_type, topic)
        script_path = SCRIPTS_DIR / template
        if not script_path.exists():
            return {"error": f"Template not found: {script_path}",
                    "video_url": None, "video_path": None, "duration": 0}
        logger.info("Using fallback template: %s", template)
        return _run_blender(blender_exe, script_path, params_file, frames_dir, output_file,
                            timeout=cfg["template_timeout"])

    finally:
        try:
            os.unlink(params_file)
        except OSError:
            pass
        shutil.rmtree(frames_dir, ignore_errors=True)

"""
Tier 1 — Manim video generation.
LLM generates a Manim Scene class; we render it locally.
Fast (~10-15s), deterministic, always has labels and structure.

Install:  pip install manim
"""

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

logger = logging.getLogger("whyzzle.manim")

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Topics that work well in Manim vs topics better handled by Blender
_BLENDER_TOPICS = {
    "planet", "orbit", "solar", "space", "star", "moon", "mars", "saturn",
    "jupiter", "mercury", "venus", "galaxy", "comet", "asteroid",
    "volcano", "interior", "crust", "mantle", "core",
    "grow", "seed", "plant", "tree", "flower", "sprout", "root", "leaf",
}


def _manim_exe() -> str | None:
    """Return path to the manim executable, checking venv Scripts dir first."""
    # When running inside a uv/venv environment the Scripts dir may not be on PATH
    venv_manim = Path(sys.executable).parent / ("manim.exe" if sys.platform == "win32" else "manim")
    if venv_manim.exists():
        return str(venv_manim)
    return shutil.which("manim")


def is_available() -> bool:
    return _manim_exe() is not None


def _route_to_blender(topic: str, concept_type: str) -> bool:
    """Return True if this topic is better served by Blender than Manim.
    Uses keyword matching only — concept_type alone is not trusted because
    LLMs sometimes label molecular/biological topics as 'spatial'."""
    words = set(topic.lower().split())
    return bool(words & _BLENDER_TOPICS)


def _plan_visual(topic: str, concept_type: str, call_llm) -> str:
    """
    Stage 1 — Ask the LLM how the animation should look.
    Returns a short visual plan (3-6 sentences) that Stage 2 uses as a spec.
    Falls back to a generic plan on failure.
    """
    plan_prompt = f"""You are designing a short educational animation for children aged 8-14.

TOPIC: "{topic}"
CONCEPT TYPE: {concept_type}

Describe EXACTLY what the Manim animation should look like, step by step.
Be specific about shapes, patterns, colours, and how many objects to use.
Think structurally — e.g., "show 12 blue dots and 12 orange dots along two sine curves,
connected by 12 short white line rungs between them" rather than "show a helix".

Rules:
- 3-6 sentences, plain English, no code
- Mention exact shapes (Dot, Circle, Line, Arrow, Rectangle)
- Mention counts when relevant (e.g., "12 pairs of dots")
- Mention colours (Manim names: BLUE, ORANGE, RED, GREEN, TEAL, YELLOW, WHITE)
- Describe how objects animate (appear one by one, fade in, grow from centre)
- End with: what text labels appear on the scene

Reply with ONLY the visual plan, nothing else."""

    try:
        plan = call_llm(plan_prompt).strip()
        logger.info("Manim visual plan: %s", plan[:200])
        return plan
    except Exception as e:
        logger.warning("Visual planning failed (%s), using generic plan", e)
        return (
            f"Show a clear, labelled diagram of '{topic}' using simple shapes. "
            "Use for-loops to build any repeating structure (e.g., chains, rings, grids). "
            "Label every key part with small Text objects. Animate each part appearing in sequence."
        )


def _generate_code(topic: str, concept_type: str) -> str | None:
    try:
        from tools.search_and_explain import _call_llm
    except ImportError:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from tools.search_and_explain import _call_llm
        except ImportError as e:
            logger.warning("Cannot import _call_llm: %s", e)
            return None

    # Stage 1: ask LLM to design the visual
    visual_plan = _plan_visual(topic, concept_type, _call_llm)

    # Stage 2: ask LLM to write Manim code that implements the plan
    prompt = f"""Write Manim Community Edition (v0.18+) Python code that implements this animation:

VISUAL PLAN:
{visual_plan}

TOPIC: "{topic}"
AUDIENCE: children aged 8-14

Hard rules — follow ALL of them:
1. First two lines must be exactly:
   from manim import *
   import math
2. Class name exactly: WhyzzleScene(Scene)
3. Only method: def construct(self):
4. Use Text() only — NEVER MathTex, Tex, DecimalNumber, ValueTracker, or LaTeX
5. Title: Text("{topic[:45]}").scale(0.5).to_edge(UP)  — animate with self.play(Write(title))
6. Colors: BLUE, RED, GREEN, YELLOW, ORANGE, PURPLE, TEAL, PINK, WHITE (Manim constants)
7. Shapes: Circle, Square, Rectangle, Arrow, Dot, Line, VGroup
8. Every object must be animated (Create, Write, FadeIn, or GrowFromCenter)
9. Label every key part with Text().scale(0.35) placed near the object
10. Total runtime: 6-8 seconds — end with self.wait(1)
11. Use Python for-loops freely; build as many objects as the plan requires
12. Dot/Line positions use np.array([x, y, 0]) — never plain tuples
13. NEVER use += on Animation, AnimationGroup, or Succession objects — they don't support +=.
    To combine: collect in a plain Python list, then pass to AnimationGroup() or Succession():
        anims = []
        for obj in objects:
            anims.append(FadeIn(obj))
        self.play(AnimationGroup(*anims))
14. NEVER call self.play() with a list — always unpack: self.play(*anims) or self.play(anim1, anim2)

Output ONLY the Python code. No markdown fences, no explanation."""

    try:
        code = _call_llm(prompt).strip()
        code = re.sub(r"^```[a-z]*\n?", "", code)
        code = re.sub(r"\n?```\s*$", "", code.rstrip())
        return code
    except Exception as e:
        logger.warning("Manim code generation failed: %s", e)
        return None


def generate_manim_video(topic: str, concept_type: str) -> dict:
    """
    Generate an educational animation using Manim.
    Returns {video_url, video_path, duration, error, renderer}
    """
    manim_bin = _manim_exe()
    if not manim_bin:
        return {"error": "Manim not installed. Run: uv add manim",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}

    if _route_to_blender(topic, concept_type):
        return {"error": "Topic better suited for Blender (spatial/3D)",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}

    logger.info("Manim: generating code for '%s'", topic[:60])
    code = _generate_code(topic, concept_type)
    if not code:
        return {"error": "Failed to generate Manim scene code",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}

    # Ensure WhyzzleScene class exists — patch common LLM mistakes
    if "WhyzzleScene" not in code:
        code = re.sub(r"class\s+\w+\s*\(Scene\)", "class WhyzzleScene(Scene)", code)
    if "WhyzzleScene" not in code:
        return {"error": "Generated code missing WhyzzleScene class",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe        = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
    output_file = OUTPUT_DIR / f"manim_{safe}.mp4"
    media_dir   = Path(tempfile.mkdtemp(prefix="whyzzle_manim_"))

    # Save debug copy as .txt so uvicorn --reload doesn't trigger on it
    (OUTPUT_DIR / "debug_last_manim_script.txt").write_text(code, encoding="utf-8")
    logger.info("Manim script saved to output/debug_last_manim_script.txt")

    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        script_path = f.name

    try:
        cmd = [
            manim_bin, "-ql",         # low quality — 480p, fast
            "--format=mp4",
            "--media_dir", str(media_dir),
            "--disable_caching",
            script_path, "WhyzzleScene",
        ]
        logger.info("Running: manim -ql WhyzzleScene (timeout=120s)")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if proc.stdout:
            logger.info("Manim stdout: %s", proc.stdout[-300:])
        if proc.returncode != 0:
            logger.error("Manim failed (exit %d):\n%s", proc.returncode, proc.stderr[-500:])
            return {"error": f"Manim render failed: {proc.stderr[-200:]}",
                    "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}

        mp4_files = sorted(media_dir.rglob("WhyzzleScene.mp4"))
        if not mp4_files:
            mp4_files = sorted(media_dir.rglob("*.mp4"))
        if not mp4_files:
            return {"error": "Manim produced no MP4 output",
                    "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}

        shutil.copy2(mp4_files[0], output_file)
        size_kb = output_file.stat().st_size / 1024
        logger.info("Manim done: %s (%.1f KB)", output_file.name, size_kb)
        return {"video_url": f"/output/{output_file.name}",
                "video_path": str(output_file),
                "duration": 5, "error": None, "renderer": "manim"}

    except subprocess.TimeoutExpired:
        logger.error("Manim timed out")
        return {"error": "Manim render timed out (>120s)",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "manim"}
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
        shutil.rmtree(media_dir, ignore_errors=True)

"""
Three-tier video pipeline for Whyzzle educational animations.

Tier 1 — Manim     : LLM-generated Python scene, rendered locally.
                     Fast (~15s), deterministic, great for math/science diagrams.
                     Skipped for spatial/3D topics (planets, plants, Earth layers).

Tier 2 — Blender   : Parameter-driven static templates (orbit, cross_section, growth).
                     Richer 3D visuals; needs Blender installed locally.

Tier 3 — CogVideoX : HuggingFace Inference API (free tier, no GPU needed locally).
                     Artistic text-to-video; fallback when local renderers fail.

The pipeline tries each tier in order and returns the first success.
"""

import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("whyzzle.pipeline")

# Topics that map well to one of the three Blender static templates.
# Topics NOT in this set should skip Blender entirely and fall to CogVideoX,
# because forcing a planet/growth/cross-section template onto them (e.g. DNA,
# photosynthesis, circuits) produces misleading visuals.
_BLENDER_SPATIAL_WORDS = {
    # orbit template
    "planet", "orbit", "solar", "space", "star", "moon", "earth",
    "mars", "saturn", "jupiter", "mercury", "venus", "galaxy", "comet",
    "asteroid", "satellite", "atom", "electron", "rotate", "revolve", "gravity",
    # cross_section template (spherical layered structures only)
    "volcano", "interior", "layer", "crust", "mantle", "core",
    "inside", "cross", "section",
    # growth template
    "grow", "seed", "plant", "tree", "flower", "sprout", "root",
    "leaf", "germinate", "photosynthesis", "biology", "lifecycle",
}


def _blender_fits(topic: str, concept_type: str) -> bool:
    """Return True only for topics that match a Blender static template well.
    Uses keyword matching only — concept_type alone is not trusted because
    LLMs sometimes label molecular/biological topics as 'spatial'."""
    words = set(topic.lower().split())
    return bool(words & _BLENDER_SPATIAL_WORDS)


def generate_video(topic: str, concept_type: str) -> dict:
    """
    Try Manim → Blender → CogVideoX in order.
    Returns the first successful result dict, or an error dict if all fail.
    Each result dict has: video_url, video_path, duration, error, renderer
    """
    errors = []

    # ── Tier 1: Manim ─────────────────────────────────────────────────────────
    try:
        from tools.video_manim import generate_manim_video, is_available as manim_ok
        if manim_ok():
            logger.info("Pipeline: trying Manim for '%s'", topic[:60])
            result = generate_manim_video(topic, concept_type)
            if result.get("video_url"):
                logger.info("Pipeline: Manim succeeded")
                return result
            errors.append(f"Manim: {result.get('error', 'unknown')}")
            logger.info("Pipeline: Manim failed — %s", errors[-1])
        else:
            errors.append("Manim: not installed")
            logger.info("Pipeline: Manim not available, skipping")
    except Exception as e:
        errors.append(f"Manim: exception — {e}")
        logger.warning("Pipeline: Manim exception: %s", e)

    # ── Tier 2: Blender ───────────────────────────────────────────────────────
    try:
        from tools.blender_scene import generate_3d_scene, _find_blender
        if not _blender_fits(topic, concept_type):
            errors.append("Blender: topic doesn't match any spatial template (orbit/cross_section/growth)")
            logger.info("Pipeline: Blender skipped — topic '%s' not spatial/3D", topic[:60])
        elif _find_blender():
            logger.info("Pipeline: trying Blender for '%s'", topic[:60])
            result = generate_3d_scene(topic=topic, concept_type=concept_type)
            if result.get("video_url"):
                logger.info("Pipeline: Blender succeeded")
                return {**result, "renderer": "blender"}
            errors.append(f"Blender: {result.get('error', 'unknown')}")
            logger.info("Pipeline: Blender failed — %s", errors[-1])
        else:
            errors.append("Blender: not installed")
            logger.info("Pipeline: Blender not available, skipping")
    except Exception as e:
        errors.append(f"Blender: exception — {e}")
        logger.warning("Pipeline: Blender exception: %s", e)

    # ── Tier 3: CogVideoX ─────────────────────────────────────────────────────
    try:
        from tools.video_cogvideo import generate_cogvideo, is_available as cog_ok
        if cog_ok():
            logger.info("Pipeline: trying CogVideoX for '%s'", topic[:60])
            result = generate_cogvideo(topic, concept_type)
            if result.get("video_url"):
                logger.info("Pipeline: CogVideoX succeeded")
                return result
            errors.append(f"CogVideoX: {result.get('error', 'unknown')}")
            logger.info("Pipeline: CogVideoX failed — %s", errors[-1])
        else:
            errors.append("CogVideoX: HF_TOKEN not set or huggingface_hub not installed")
            logger.info("Pipeline: CogVideoX not available, skipping")
    except Exception as e:
        errors.append(f"CogVideoX: exception — {e}")
        logger.warning("Pipeline: CogVideoX exception: %s", e)

    summary = " | ".join(errors)
    logger.error("Pipeline: all tiers failed — %s", summary)
    return {
        "error": f"All video tiers failed: {summary}",
        "video_url": None,
        "video_path": None,
        "duration": 0,
        "renderer": "none",
    }

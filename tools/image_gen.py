"""
Educational image generation for Whyzzle visuals.

Tier 1 — HuggingFace Inference API  (FLUX.1-schnell; needs HF_TOKEN in .env)
Tier 2 — Pollinations.ai            (completely free; no key; uses FLUX)

Returns an HTML <img> fragment suitable for use as visual_code.
Images are saved locally under output/ (HF tier) or linked externally (Pollinations).
"""

import hashlib
import logging
import os
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("whyzzle.imagegen")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ─── Prompt templates per concept type ───────────────────────────────────────

_BASE_STYLE = (
    "educational infographic illustration, vivid saturated colors, "
    "cartoon style, child-friendly, clean background, "
    "detailed labeled diagram, digital art, no watermarks, high quality"
)

_CONCEPT_SUBJECT = {
    "biological": (
        "colorful biology education poster of {topic}, "
        "showing detailed anatomical structure with labeled parts, "
        "cross-section diagram, bright bold colors, cute cartoon style"
    ),
    "mathematical": (
        "mathematics infographic explaining {topic}, "
        "colorful numbered steps, geometric shapes, arrows showing relationships, "
        "bright educational poster"
    ),
    "chemical": (
        "chemistry education illustration of {topic}, "
        "colorful molecular structure, labeled atoms and bonds, "
        "bright cartoon chemistry poster"
    ),
    "spatial": (
        "space science educational illustration of {topic}, "
        "colorful labeled diagram, scale comparison, vivid cosmic colors, "
        "educational poster style"
    ),
    "sequential": (
        "step-by-step process infographic explaining {topic}, "
        "numbered stages with arrows, colorful boxes, educational flow diagram"
    ),
    "comparative": (
        "side-by-side comparison educational infographic about {topic}, "
        "two-column layout, colorful, labeled differences and similarities"
    ),
    "other": (
        "colorful educational diagram explaining {topic}, "
        "labeled parts, vivid illustration, infographic style"
    ),
}


def _build_prompt(topic: str, concept_type: str) -> str:
    template = _CONCEPT_SUBJECT.get(concept_type, _CONCEPT_SUBJECT["other"])
    subject = template.format(topic=topic[:70])
    return f"{subject}, {_BASE_STYLE}"


def _deterministic_seed(topic: str) -> int:
    """Same topic → same seed → same Pollinations image on re-render."""
    return int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) % 99999


# ─── HuggingFace tier ─────────────────────────────────────────────────────────

def _try_huggingface(prompt: str, output_path: Path) -> bool:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        return False
    try:
        from huggingface_hub import InferenceClient
        logger.info("ImageGen: HuggingFace FLUX.1-schnell...")
        client = InferenceClient(api_key=token)
        image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-schnell",
            width=512,
            height=384,
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        image.save(str(output_path), format="PNG")
        logger.info("ImageGen: HF saved %s (%.1f KB)",
                    output_path.name, output_path.stat().st_size / 1024)
        return True
    except Exception as e:
        logger.warning("ImageGen: HuggingFace failed (%s)", str(e)[:120])
        return False


# ─── Pollinations.ai tier (no key) ───────────────────────────────────────────

def _pollinations_url(prompt: str, seed: int) -> str:
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=800&height=600&model=flux&nologo=true&seed={seed}"
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_educational_image(topic: str, concept_type: str) -> str | None:
    """
    Generate an educational image for the topic.
    Returns an HTML <img> string (visual_code-compatible), or None on total failure.
    """
    prompt = _build_prompt(topic, concept_type)
    seed   = _deterministic_seed(topic)
    logger.info("ImageGen: prompt=%s", prompt[:100])

    safe        = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
    output_path = OUTPUT_DIR / f"img_{safe}_{seed}.png"

    img_style = (
        "width:100%;max-width:600px;border-radius:14px;"
        "display:block;margin:0 auto;box-shadow:0 4px 16px rgba(0,0,0,.12)"
    )

    # Return cached HF image if it exists from a previous run
    if output_path.exists():
        logger.info("ImageGen: serving cached image %s", output_path.name)
        return f'<img src="/output/{output_path.name}" alt="{topic}" style="{img_style}" />'

    # Tier 1: HuggingFace
    if _try_huggingface(prompt, output_path):
        return f'<img src="/output/{output_path.name}" alt="{topic}" style="{img_style}" />'

    # Tier 2: Pollinations.ai (always free, no key)
    logger.info("ImageGen: falling back to Pollinations.ai (FLUX, no key required)")
    pol_url = _pollinations_url(prompt, seed)
    return (
        f'<img src="{pol_url}" alt="{topic}" '
        f'style="{img_style}" loading="lazy" '
        f'onerror="this.style.display=\'none\'" />'
    )

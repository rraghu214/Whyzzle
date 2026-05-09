"""
Educational image generation for Whyzzle visuals.

Tier 1 — Gemini Flash image generation  (free; needs GEMINI_API_KEY)
Tier 2 — HuggingFace Inference API      (free; needs HF_TOKEN)
Tier 3 — Pollinations.ai                (free; no key; FLUX)

Images are downloaded and cached locally under output/.
Returns an HTML <img> fragment, or None on total failure (caller falls to SVG).
"""

import base64
import hashlib
import logging
import os
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("whyzzle.imagegen")
OUTPUT_DIR = Path(__file__).parent.parent / "output"

IMG_STYLE = (
    "width:100%;max-width:600px;border-radius:14px;"
    "display:block;margin:0 auto;box-shadow:0 4px 16px rgba(0,0,0,.12)"
)


# ─── Prompt builder ───────────────────────────────────────────────────────────
# Each template describes the VISUAL ELEMENTS precisely, not just the topic name.
# Gemini image gen follows detailed instructions far better than FLUX.

_CONCEPT_PROMPT = {
    "biological": (
        "A detailed, colorful, child-friendly educational diagram of {topic}. "
        "Draw the actual physical structure with labeled parts: show cross-sections, "
        "membranes, components as distinct colored shapes. Use bold outlines, bright "
        "contrasting colors for each part, and clear text labels pointing to each element. "
        "Include a title bar at the top. Clean white background. Scientific poster style."
    ),
    "mathematical": (
        "A precise, colorful educational math diagram explaining {topic}. "
        "Draw the exact geometric or algebraic concept with correctly proportioned shapes, "
        "clearly labeled variables (a, b, c etc.), formulas written in large readable text, "
        "and arrows showing relationships. Use a different bold color for each element. "
        "Clean white background. Include a title. No decorative clutter — only what explains the concept."
    ),
    "chemical": (
        "A colorful chemistry education poster of {topic}. "
        "Draw molecules as colored circles connected by lines for bonds "
        "(H=white, O=red, C=black, N=blue). Show the reaction or structure clearly. "
        "Label every atom and bond type. Bold title at top. Clean white background."
    ),
    "spatial": (
        "A vivid, detailed educational science illustration of {topic}. "
        "Show objects at relative scale with labeled arrows indicating forces, distances, "
        "or motion paths. Use a space or Earth background appropriate to the topic. "
        "Bold text labels on every key element. Colorful and dramatic. Educational poster style."
    ),
    "sequential": (
        "A clear step-by-step educational infographic of {topic}. "
        "Show numbered stages (1, 2, 3...) as distinct colored boxes connected by large arrows. "
        "Each box contains a small illustration and a short label of that step. "
        "Left-to-right or top-to-bottom flow. Bold title at top. Clean background."
    ),
    "comparative": (
        "A side-by-side comparison educational poster about {topic}. "
        "Divide the image into two clearly labeled halves with a dividing line. "
        "Each side shows matching colored illustrations of the contrasting concepts. "
        "Bold headers for each side. Highlight key differences with callout labels. "
        "Clean background."
    ),
    "other": (
        "A colorful, precise educational infographic explaining {topic}. "
        "Identify the key components and draw each as a distinct labeled shape. "
        "Use a different bold color for each part. Include arrows showing relationships. "
        "Bold title at top. Clean white background. Child-friendly illustration style."
    ),
}


def _build_prompt(topic: str, concept_type: str) -> str:
    template = _CONCEPT_PROMPT.get(concept_type, _CONCEPT_PROMPT["other"])
    return template.format(topic=topic[:80])


def _safe_name(topic: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])


def _deterministic_seed(topic: str) -> int:
    return int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) % 99999


def _img_tag(path_name: str, topic: str) -> str:
    return f'<img src="/output/{path_name}" alt="{topic}" style="{IMG_STYLE}" />'


# ─── Tier 1: Gemini Flash image generation ───────────────────────────────────

def _try_gemini(prompt: str, output_path: Path) -> bool:
    if not os.environ.get("GEMINI_API_KEY"):
        return False
    try:
        from google import genai
        from google.genai import types
        logger.info("ImageGen: Gemini Flash image generation...")
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img_bytes = base64.b64decode(part.inline_data.data)
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(img_bytes)
                logger.info("ImageGen: Gemini saved %s (%.1f KB)",
                            output_path.name, len(img_bytes) / 1024)
                return True
        logger.warning("ImageGen: Gemini returned no image part")
    except Exception as exc:
        logger.warning("ImageGen: Gemini image gen failed (%s)", str(exc)[:150])
    return False


# ─── Tier 2: HuggingFace FLUX.1-schnell ──────────────────────────────────────

def _try_huggingface(prompt: str, output_path: Path) -> bool:
    if not os.environ.get("HF_TOKEN", "").strip():
        return False
    try:
        from huggingface_hub import InferenceClient
        logger.info("ImageGen: HuggingFace FLUX.1-schnell...")
        client = InferenceClient(api_key=os.environ["HF_TOKEN"])
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
    except Exception as exc:
        logger.warning("ImageGen: HuggingFace failed (%s)", str(exc)[:120])
        return False


# ─── Tier 3: Pollinations.ai (no key, download & cache) ──────────────────────

def _try_pollinations(prompt: str, seed: int, output_path: Path) -> bool:
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=800&height=600&model=flux&nologo=true&seed={seed}"
    )
    try:
        logger.info("ImageGen: Pollinations.ai (FLUX, no key)...")
        r = httpx.get(url, timeout=25, follow_redirects=True)
        if r.status_code == 200 and "image/" in r.headers.get("content-type", ""):
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(r.content)
            logger.info("ImageGen: Pollinations cached → %s (%.1f KB)",
                        output_path.name, len(r.content) / 1024)
            return True
        logger.warning("ImageGen: Pollinations returned %d", r.status_code)
    except Exception as exc:
        logger.warning("ImageGen: Pollinations failed (%s)", str(exc)[:120])
    return False


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_educational_image(topic: str, concept_type: str) -> str | None:
    """
    Try each image tier in order. Returns an HTML <img> tag, or None (caller uses SVG).
    """
    prompt = _build_prompt(topic, concept_type)
    seed   = _deterministic_seed(topic)
    safe   = _safe_name(topic)
    logger.info("ImageGen: topic=%s concept=%s", topic[:60], concept_type)

    # Serve cached copy if already generated
    for ext in ("png", "jpg"):
        for prefix in ("gem", "hf", "pol"):
            cached = OUTPUT_DIR / f"{prefix}_{safe}_{seed}.{ext}"
            if cached.exists():
                logger.info("ImageGen: cache hit → %s", cached.name)
                return _img_tag(cached.name, topic)

    # Tier 1: Gemini Flash image generation (free, best quality)
    gem_path = OUTPUT_DIR / f"gem_{safe}_{seed}.png"
    if _try_gemini(prompt, gem_path):
        return _img_tag(gem_path.name, topic)

    # Tier 2: HuggingFace FLUX (free with token)
    hf_path = OUTPUT_DIR / f"hf_{safe}_{seed}.png"
    if _try_huggingface(prompt, hf_path):
        return _img_tag(hf_path.name, topic)

    # Tier 3: Pollinations.ai (no key, download & cache)
    pol_path = OUTPUT_DIR / f"pol_{safe}_{seed}.jpg"
    if _try_pollinations(prompt, seed, pol_path):
        return _img_tag(pol_path.name, topic)

    return None  # caller falls through to LLM SVG

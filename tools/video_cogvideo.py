"""
Tier 3 — CogVideoX via HuggingFace Inference API.
Free text-to-video model; artistic quality rather than educational diagrams.
Used as a cloud fallback when Manim and Blender are unavailable or fail.

Requires:
    pip install huggingface_hub
    HF_TOKEN=<your token> in .env  (free account at huggingface.co)
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("whyzzle.cogvideo")

OUTPUT_DIR = Path(__file__).parent.parent / "output"

MODEL_ID = "THUDM/CogVideoX-5b"


def is_available() -> bool:
    try:
        from huggingface_hub import InferenceClient  # noqa: F401
        return bool(os.environ.get("HF_TOKEN", "").strip())
    except ImportError:
        return False


def _build_prompt(topic: str, concept_type: str) -> str:
    style = "educational animation, bright colors, child-friendly, clear labels"
    if concept_type == "spatial":
        style = "3D animation, space exploration, vivid colors, educational"
    elif concept_type in ("biological", "sequential"):
        style = "nature documentary style, vivid colors, slow motion, educational"
    elif concept_type in ("mathematical", "logical"):
        style = "geometric animation, bright colors, abstract, educational"
    return (
        f"Short educational animation explaining '{topic}' for children aged 8-14. "
        f"{style}. High quality, visually engaging, simple to understand."
    )


def generate_cogvideo(topic: str, concept_type: str) -> dict:
    """
    Generate a short video via HuggingFace CogVideoX Inference API.
    Returns {video_url, video_path, duration, error, renderer}
    """
    if not is_available():
        return {"error": "CogVideoX unavailable: missing HF_TOKEN or huggingface_hub package",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "cogvideo"}

    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        return {"error": "huggingface_hub not installed. Run: pip install huggingface_hub",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "cogvideo"}

    prompt = _build_prompt(topic, concept_type)
    logger.info("CogVideoX: generating for '%s'", topic[:60])
    logger.info("Prompt: %s", prompt)

    try:
        client = InferenceClient(
            provider="fal-ai",
            api_key=os.environ["HF_TOKEN"],
        )
        video = client.text_to_video(
            prompt,
            model=MODEL_ID,
        )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe        = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
        output_file = OUTPUT_DIR / f"cogvideo_{safe}.mp4"

        # video may be bytes or a file-like object
        if isinstance(video, bytes):
            output_file.write_bytes(video)
        else:
            with open(output_file, "wb") as f:
                shutil.copyfileobj(video, f)

        size_kb = output_file.stat().st_size / 1024
        logger.info("CogVideoX done: %s (%.1f KB)", output_file.name, size_kb)
        return {"video_url": f"/output/{output_file.name}",
                "video_path": str(output_file),
                "duration": 6, "error": None, "renderer": "cogvideo"}

    except Exception as e:
        logger.error("CogVideoX failed: %s", e)
        return {"error": f"CogVideoX failed: {e}",
                "video_url": None, "video_path": None, "duration": 0, "renderer": "cogvideo"}

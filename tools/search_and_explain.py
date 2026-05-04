"""
LLM waterfall (tried in this order):
  1. Groq / Llama 3.3 70B  — free tier, ~2s latency, best quality
  2. Google Gemini Flash    — free tier, throttled to stay under 15 RPM
  3. Ollama / Gemma 4 4B   — local, no key, fully offline (uses lite prompt)
  4. Anthropic Claude       — fallback if key is present

Set keys / options in .env:
  GEMINI_API_KEY=...          # enables Gemini (free tier at Google AI Studio)
  OLLAMA_HOST=http://localhost:11434   # default; change if Ollama runs elsewhere
  OLLAMA_MODEL=gemma4:e4b               # any model you have pulled in Ollama
  ANTHROPIC_API_KEY=...       # enables Claude fallback
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logger = logging.getLogger("whyzzle.search")

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from tools.profiles import manage_profiles

# ─── Gemini throttle + session state ─────────────────────────────────────────
_GEMINI_MIN_INTERVAL = 8.0          # 8s between calls → well under 15 RPM
_gemini_last_call_at: float = 0.0
_gemini_fail_streak: int = 0        # consecutive 429s; skip Gemini after 2


# ─── LLM backends ────────────────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str:
    """Google Gemini Flash — free tier with throttle."""
    global _gemini_last_call_at
    elapsed = time.monotonic() - _gemini_last_call_at
    wait = _GEMINI_MIN_INTERVAL - elapsed
    if wait > 0:
        logger.info("Gemini throttle: waiting %.1fs to stay under rate limit", wait)
        time.sleep(wait)

    logger.info("Calling Gemini Flash (gemini-2.0-flash)...")
    from google import genai  # lazy import — only needed if key present
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    _gemini_last_call_at = time.monotonic()
    chars = len(response.text or "")
    logger.info("Gemini responded: %d chars", chars)
    return response.text


def _call_ollama(prompt: str) -> str:
    """Local Ollama — no key required, works fully offline."""
    host  = os.environ.get("OLLAMA_HOST",  "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
    logger.info("Calling Ollama at %s (model: %s) — timeout 90s...", host, model)
    r = httpx.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=90,   # 90s — enough for text-only lite prompt; fail fast to Claude
    )
    r.raise_for_status()
    resp = r.json()["response"]
    logger.info("Ollama responded: %d chars", len(resp))
    return resp


def _call_groq(prompt: str) -> str:
    """Groq — free tier, Llama 3.3 70B, ~2s response time."""
    logger.info("Calling Groq (llama-3.3-70b-versatile)...")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        },
        timeout=60,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    logger.info("Groq responded: %d chars", len(text))
    return text


def _call_claude(prompt: str) -> str:
    """Anthropic Claude Sonnet — requires ANTHROPIC_API_KEY."""
    logger.info("Calling Anthropic Claude (claude-sonnet-4-6)...")
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    logger.info("Claude responded: %d chars", len(text))
    return text


def _call_llm(prompt: str, prompt_lite: str | None = None) -> str:
    """
    Try each backend in order.
    prompt_lite is a shorter, simpler prompt used for Ollama (4B models struggle
    with very long JSON generation requests).
    """
    global _gemini_fail_streak

    # 1 — Groq (free, fast, Llama 3.3 70B — best free option)
    if os.environ.get("GROQ_API_KEY"):
        try:
            return _call_groq(prompt)
        except Exception as exc:
            reason = str(exc)
            if "429" in reason or "rate_limit" in reason.lower():
                logger.warning("Groq rate limit hit — falling through to Gemini")
            else:
                logger.warning("Groq failed (%s) — falling through to Gemini", reason[:120])

    # 2 — Gemini (free, throttled, 1500 req/day)
    if os.environ.get("GEMINI_API_KEY") and _gemini_fail_streak < 2:
        try:
            result = _call_gemini(prompt)
            _gemini_fail_streak = 0   # reset on success
            return result
        except Exception as exc:
            reason = str(exc)
            _gemini_fail_streak += 1
            if "429" in reason or "RESOURCE_EXHAUSTED" in reason:
                if _gemini_fail_streak >= 2:
                    logger.warning(
                        "Gemini 429 x2 in a row — skipping Gemini for this session; "
                        "daily quota likely exhausted"
                    )
                else:
                    logger.warning("Gemini 429 — quota hit; falling through to Ollama")
            else:
                logger.warning("Gemini failed (%s) — falling through to Ollama", reason[:120])
    elif _gemini_fail_streak >= 2:
        logger.info("Gemini quota exhausted this session — skipping")

    # 3 — Ollama / Gemma (local) — uses lite text-only prompt; SVG generated from template
    ollama_err = None
    ollama_prompt = prompt_lite if prompt_lite else prompt
    try:
        return _call_ollama(ollama_prompt)
    except Exception as exc:
        ollama_err = exc
        logger.warning("Ollama unavailable (%s) — falling through to Claude", exc)

    # 3 — Claude (paid fallback)
    has_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    logger.info("ANTHROPIC_API_KEY present: %s", has_claude)
    if has_claude:
        return _call_claude(prompt)

    # Build a clear, actionable error for the UI
    lines = ["No LLM is reachable. Fix at least one of these:"]
    lines.append("* GROQ (recommended free): get a free key at console.groq.com → add GROQ_API_KEY to .env")
    if os.environ.get("GEMINI_API_KEY"):
        lines.append("* GEMINI: daily quota exhausted — wait for reset at midnight PT, or get a new key")
    else:
        lines.append("* GEMINI: add GEMINI_API_KEY to .env (free at aistudio.google.com)")
    if ollama_err:
        lines.append(f"* OLLAMA: not responding ({ollama_err}) — run: ollama serve")
    else:
        lines.append("* OLLAMA: run: ollama serve && ollama pull gemma4:e4b")
    lines.append("* CLAUDE: add ANTHROPIC_API_KEY to .env (paid, always reliable)")
    raise RuntimeError("\n".join(lines))


# ─── JSON extraction ──────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Strip markdown fences and parse the first JSON object found in the text."""
    text = raw.strip()

    # Remove ```json ... ``` or ``` ... ``` wrappers
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost { ... } block
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(f"No JSON object found in LLM response:\n{raw[:300]}")


# ─── Age instruction ──────────────────────────────────────────────────────────

def _age_instruction(age: int) -> str:
    if age <= 6:
        return (
            "Write 1-2 sentences using the simplest possible words. "
            "Use one concrete real-world analogy (like comparing to a toy or food). "
            "Absolutely no jargon."
        )
    if age <= 10:
        return (
            "Write 2-3 short paragraphs. "
            "Use relatable comparisons a kid would enjoy. "
            "Introduce at most one new word, and explain it immediately."
        )
    if age <= 14:
        return (
            "Write 2-3 paragraphs. "
            "Introduce proper scientific terms but define each one briefly. "
            "Use cause-and-effect reasoning."
        )
    if age <= 17:
        return (
            "Write 3-4 paragraphs at near-adult depth. "
            "Use formal vocabulary with brief in-line definitions where needed. "
            "Include some abstraction and systemic thinking."
        )
    return (
        "Write a thorough explanation without any simplification. "
        "Use domain vocabulary freely. Include nuance and edge cases where relevant."
    )


# ─── Template SVG (used when Ollama skips visual generation) ─────────────────

_CONCEPT_ICONS = {
    "spatial":      ("🌍", "#4A90D9", "#E8F4FD"),
    "sequential":   ("🔗", "#27AE60", "#E8F8F0"),
    "comparative":  ("⚖️",  "#8E44AD", "#F5EEF8"),
    "mathematical": ("➗", "#E67E22", "#FEF9E7"),
    "biological":   ("🌱", "#16A085", "#E8F8F5"),
    "other":        ("💡", "#7B3FBD", "#F0E8FF"),
}

def _template_svg(concept_type: str, question: str, tags: list | None = None) -> str:
    """
    Generate a clean placeholder SVG when the LLM didn't produce one.
    Displays the question, concept type, and tag pills.
    """
    icon, accent, bg = _CONCEPT_ICONS.get(concept_type, _CONCEPT_ICONS["other"])
    tags = tags or []

    # Wrap question at ~50 chars per line
    words, lines, cur = question.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 50:
            lines.append(cur.strip())
            cur = w
        else:
            cur += (" " if cur else "") + w
    if cur:
        lines.append(cur.strip())

    q_y_start = 130
    q_lines_svg = "\n".join(
        f'<text x="240" y="{q_y_start + i * 26}" text-anchor="middle" '
        f'font-size="16" fill="#2D2040">{line}</text>'
        for i, line in enumerate(lines[:4])
    )

    tag_pills = ""
    tx = 40
    for t in tags[:5]:
        w = len(t) * 8 + 20
        tag_pills += (
            f'<rect x="{tx}" y="240" width="{w}" height="22" rx="11" fill="{accent}" opacity="0.18"/>'
            f'<text x="{tx + w//2}" y="255" text-anchor="middle" font-size="11" fill="{accent}">#{t}</text>'
        )
        tx += w + 8

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 290">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{bg}"/>
      <stop offset="100%" stop-color="#FFFFFF"/>
    </linearGradient>
  </defs>
  <rect width="480" height="290" rx="16" fill="url(#bg)"/>
  <rect x="20" y="20" width="440" height="250" rx="12"
        fill="none" stroke="{accent}" stroke-width="1.5" opacity="0.3"/>
  <text x="240" y="72" text-anchor="middle" font-size="48">{icon}</text>
  <text x="240" y="102" text-anchor="middle" font-size="12" font-weight="700"
        fill="{accent}" letter-spacing="2" text-transform="uppercase"
        style="text-transform:uppercase">{concept_type.upper()}</text>
  {q_lines_svg}
  {tag_pills}
  <text x="240" y="278" text-anchor="middle" font-size="10" fill="#AAA">
    Visual generated by local model — ask again with Gemini for a richer diagram
  </text>
</svg>"""


# ─── Interactive Canvas visual (regenerate in-place) ─────────────────────────

def generate_canvas_visual(question: str, concept_type: str) -> dict:
    """Generate a self-contained Canvas 2D animation for an existing topic.
    Called from /api/regenerate-visual; does NOT save a new topic.
    Falls back to template SVG if all LLMs fail.
    """
    logger.info("generate_canvas_visual: '%s' (concept=%s)", question[:60], concept_type)

    prompt = f"""Create a self-contained HTML page (NO external libraries, no CDN) with a smooth Canvas 2D animation that visually explains: "{question}"

Requirements:
- Vanilla JS + HTML Canvas 2D API only (ctx.fillRect, ctx.arc, ctx.lineTo, ctx.fillText, etc.)
- Set canvas.width = 600; canvas.height = 420; center it in the page; body background #FAF7FF
- Use requestAnimationFrame for a smooth, continuously looping animation
- Color palette: purple #7B3FBD, teal #00B4A2, yellow #FFD43B, coral #FF6B6B, green #40C057
- Draw clear text labels so a child can understand each part
- Show meaningful movement that illustrates the concept (orbiting, growing, pulsing, flowing, etc.)
- Draw a bold title at the top in purple (font 16px)
- Keep code simple and robust — no ES6 classes, no modules

Output ONLY the complete HTML from <!DOCTYPE html> to </html>. No markdown fences, no explanation outside the HTML."""

    raw = None

    # Try Groq first (free, fast, supports 6k output tokens)
    if os.environ.get("GROQ_API_KEY"):
        try:
            model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
            r = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 6000},
                timeout=60,
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
            logger.info("Canvas visual from Groq: %d chars", len(raw))
        except Exception as exc:
            logger.warning("Groq failed for canvas visual (%s) — trying Gemini", exc)

    # Try Gemini
    if not raw and os.environ.get("GEMINI_API_KEY") and _gemini_fail_streak < 2:
        try:
            raw = _call_gemini(prompt)
            logger.info("Canvas visual from Gemini: %d chars", len(raw))
        except Exception as exc:
            logger.warning("Gemini failed for canvas visual (%s) — trying Claude", exc)

    # Try Claude
    if not raw and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            raw = _call_claude(prompt)
            logger.info("Canvas visual from Claude: %d chars", len(raw))
        except Exception as exc:
            logger.warning("Claude failed for canvas visual (%s)", exc)

    # Extract and validate HTML
    if raw:
        text = raw.strip()
        # Strip markdown fences if LLM wrapped the HTML
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:])
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()
        if ("<!DOCTYPE" in text or "<html" in text.lower()) and "<canvas" in text:
            logger.info("Canvas visual generation successful (%d chars)", len(text))
            return {"visual_code": text, "visual_type": "html_interactive"}
        logger.warning("LLM response doesn't look like valid Canvas HTML — falling back to SVG")

    # Fallback: template SVG
    logger.info("Falling back to template SVG for regenerated visual")
    return {"visual_code": _template_svg(concept_type, question), "visual_type": "svg"}


# ─── Web search ───────────────────────────────────────────────────────────────

def _search_web(query: str) -> str:
    """No API key needed. Two attempts before giving up."""
    logger.info("Web search: \"%s\"", query)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Whyzzle/1.0)"}

    # Attempt 1: DuckDuckGo Instant Answer API (keyless)
    try:
        r = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers=headers,
            timeout=8,
            follow_redirects=True,
        )
        data = r.json()
        text = data.get("AbstractText", "")
        if text:
            logger.info("DuckDuckGo Instant Answer: %d chars", len(text))
            return text[:3000]
        parts = [
            item["Text"]
            for item in data.get("RelatedTopics", [])[:4]
            if isinstance(item, dict) and item.get("Text")
        ]
        if parts:
            combined = " ".join(parts)[:3000]
            logger.info("DuckDuckGo related topics: %d chars", len(combined))
            return combined
        logger.info("DuckDuckGo Instant: no abstract, trying HTML snippets")
    except Exception as e:
        logger.warning("DuckDuckGo Instant failed: %s", e)

    # Attempt 2: DuckDuckGo HTML search snippets (keyless)
    try:
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
            timeout=10,
            follow_redirects=True,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        snippets = [el.get_text(" ", strip=True) for el in soup.select(".result__snippet")[:5]]
        if snippets:
            combined = " ".join(snippets)[:3000]
            logger.info("DuckDuckGo HTML snippets: %d chars from %d results", len(combined), len(snippets))
            return combined
    except Exception as e:
        logger.warning("DuckDuckGo HTML search failed: %s", e)

    logger.info("No web context found — LLM will use its own knowledge")
    return ""  # LLM will answer from its own training knowledge


# ─── Main entry point ─────────────────────────────────────────────────────────

def search_and_explain(question: str, profile_id: str, asked_by: str = "child") -> dict:
    logger.info("=== New question (profile=%s, asked_by=%s) ===", profile_id, asked_by)
    logger.info("Question: \"%s\"", question)
    profile = (manage_profiles("read", {"profile_id": profile_id}).get("profile") or {})
    age     = int(profile.get("age", 7))
    logger.info("Profile age: %d — applying age-adaptive explanation depth", age)

    web_context = _search_web(question)
    age_instr   = _age_instruction(age)

    context_block = (
        f"Web context (use for factual accuracy, rewrite in your own words):\n{web_context}"
        if web_context
        else "No web context available — rely on your own knowledge."
    )

    # Full prompt — for cloud models (Gemini, Claude)
    prompt = f"""You are Whyzzle, a visual curiosity coach.
A user aged {age} asked: "{question}"

{context_block}

Your tasks:
1. EXPLANATION — {age_instr}
2. VISUAL — Generate a BEAUTIFUL, COLOURFUL, self-contained visual that clearly illustrates the concept.
   - Prefer SVG: use gradients, shapes, labels, CSS animations where they add clarity.
   - Use HTML + JS only if interactivity genuinely helps (e.g. a draggable curve, a slider, Three.js 3D).
   - The visual must be completely self-contained (no external URLs, no CDN links).
   - Make it large enough to be readable (viewBox or width/height >= 480px wide).
3. FOLLOW-UPS — 3 natural follow-up questions the user might ask next.
4. TAGS — 2-5 lowercase concept tags (e.g. ["light", "atmosphere", "physics"]).
5. CONCEPT_TYPE — one of: spatial | sequential | comparative | mathematical | biological | other
6. VISUAL_TYPE — "svg" if pure SVG, "html_interactive" if HTML with JS.

Respond ONLY with a valid JSON object. No markdown fences, no explanation outside the JSON.

{{
  "explanation": "...",
  "visual_code": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 380'>...</svg>",
  "visual_type": "svg",
  "follow_ups": ["...", "...", "..."],
  "tags": ["...", "..."],
  "concept_type": "spatial",
  "related_search": ""
}}"""

    # Lite prompt — TEXT ONLY for local small models (Ollama 4B).
    # Asking a 4B model to generate JSON + full SVG reliably is too slow.
    # We ask for text fields only and generate the visual from a template.
    ctx_short = web_context[:500] if web_context else ""
    ctx_line  = f"Context: {ctx_short}" if ctx_short else ""
    prompt_lite = f"""You are Whyzzle, a curiosity coach for kids.
A {age}-year-old asked: "{question}"
{ctx_line}

{age_instr}

Reply with ONLY a JSON object (no markdown fences, no extra text):
{{
  "explanation": "2-3 paragraph explanation suitable for age {age}",
  "follow_ups": ["follow-up 1?", "follow-up 2?", "follow-up 3?"],
  "tags": ["tag1", "tag2"],
  "concept_type": "spatial"
}}

concept_type must be one of: spatial, sequential, comparative, mathematical, biological, other"""

    logger.info("Building prompt (%d chars web context) and calling LLM...", len(web_context))
    raw    = _call_llm(prompt, prompt_lite=prompt_lite)
    logger.info("LLM response received, extracting JSON...")
    result = _extract_json(raw)

    # If the model didn't produce a visual (e.g. Ollama lite prompt), generate a template SVG
    if not result.get("visual_code"):
        concept = result.get("concept_type", "other")
        tags_list = result.get("tags", [])
        logger.info("No visual_code in response — generating template SVG (concept=%s)", concept)
        result["visual_code"] = _template_svg(concept, question, tags_list)
        result["visual_type"] = "svg"

    tags   = result.get("tags", [])
    vtype  = result.get("visual_type", "svg")
    logger.info("Parsed response: concept_type=%s, visual_type=%s, tags=%s",
                result.get("concept_type"), vtype, tags)
    result.update(
        asked_by=asked_by,
        profile_age=age,
        question=question,
        profile_id=profile_id,
    )
    logger.info("=== Pipeline complete ===")
    return result

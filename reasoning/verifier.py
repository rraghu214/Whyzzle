"""
Self Verification Layer
Validates LLM output quality and computes a confidence score.
All checks are heuristic — no additional LLM call needed.

Checks performed:
  1. length        — explanation is substantive (> 100 chars)
  2. relevance     — explanation words overlap with question words
  3. hallucination — no known AI-refusal phrases present
  4. completeness  — multiple complete sentences (≥ 2 sentence-ending punctuation)
  5. follow_ups    — at least one follow-up question generated
  6. tags          — at least one concept tag present
  7. web_grounded  — whether web context was available
"""

import logging

logger = logging.getLogger("whyzzle.verifier")

# Known phrases that indicate the model refused or admitted uncertainty
_REFUSAL_PHRASES = [
    "as an ai",
    "i cannot",
    "i'm not able",
    "i am not able",
    "i don't know",
    "i do not know",
    "i'm not sure",
    "i am not sure",
    "as a language model",
    "i lack the ability",
]


def _mk(check: str, passed: bool, note: str) -> dict:
    """Build a check result dict with a pre-computed display icon."""
    return {
        "check":      check,
        "passed":     passed,
        "check_icon": "✅" if passed else "❌",
        "note":       note,
    }


def _check_length(explanation: str) -> dict:
    passed = len(explanation) > 100
    return _mk("length", passed,
               "Explanation is substantive" if passed else "Explanation seems too short")


def _check_relevance(explanation: str, question: str) -> dict:
    q_words = {w for w in question.lower().split() if len(w) > 3}
    exp_words = set(explanation.lower().split())
    overlap = len(q_words & exp_words) / max(len(q_words), 1)
    passed = overlap > 0.15
    return _mk("relevance", passed,
               f"Explanation covers question topic ({overlap:.0%} word overlap)"
               if passed else "Explanation may not address the question directly")


def _check_hallucination(explanation: str) -> dict:
    has_markers = any(p in explanation.lower() for p in _REFUSAL_PHRASES)
    return _mk("hallucination_risk", not has_markers,
               "No AI-refusal markers detected"
               if not has_markers else "Possible AI-refusal or uncertainty markers found")


def _check_completeness(explanation: str) -> dict:
    sentence_count = (
        explanation.count(".") + explanation.count("!") + explanation.count("?")
    )
    passed = sentence_count >= 2
    return _mk("completeness", passed,
               f"Contains {sentence_count} sentences — looks complete"
               if passed else "May be incomplete — fewer than 2 sentences")


def _check_follow_ups(follow_ups: list) -> dict:
    passed = len(follow_ups) >= 1
    return _mk("follow_ups", passed,
               f"{len(follow_ups)} follow-up question(s) generated"
               if passed else "No follow-up questions generated")


def _check_tags(tags: list) -> dict:
    passed = len(tags) >= 1
    return _mk("tags", passed,
               f"Concept tags: {', '.join(tags[:5])}"
               if passed else "No concept tags generated")


def _check_web_grounded(has_web_context: bool) -> dict:
    return _mk("web_grounded", has_web_context,
               "Answer grounded in web search results"
               if has_web_context else "No web context — answer from LLM training knowledge only")


def calculate_confidence(
    has_web_context: bool,
    explanation_len: int,
    tags_count: int,
    follow_ups_count: int,
    has_visual: bool,
    checks_passed: int,
    checks_total: int,
) -> float:
    """
    Compute a 0.0–1.0 confidence score from multiple quality signals.
    Weights are designed so a solid web-backed answer with visuals scores ~0.90.
    """
    score = 0.0

    # Web grounding (20 pts)
    score += 0.20 if has_web_context else 0.0

    # Explanation length (20 pts)
    if explanation_len > 500:
        score += 0.20
    elif explanation_len > 200:
        score += 0.15
    elif explanation_len > 100:
        score += 0.08

    # Tags (10 pts)
    score += 0.10 if tags_count >= 3 else (0.05 if tags_count >= 1 else 0.0)

    # Follow-ups (10 pts)
    score += 0.10 if follow_ups_count >= 3 else (0.05 if follow_ups_count >= 1 else 0.0)

    # Visual present (15 pts)
    score += 0.15 if has_visual else 0.0

    # Verification checks pass ratio (25 pts)
    if checks_total > 0:
        score += 0.25 * (checks_passed / checks_total)

    return min(round(score, 2), 1.0)


def verify_response(question: str, result: dict, has_web_context: bool) -> dict:
    """
    Run all verification checks on the LLM result and return a full report.

    Returns dict with:
      checks           — list of individual check results
      passed           — number of checks passed
      total            — total checks
      confidence       — float 0.0–1.0
      confidence_label — "high" / "medium" / "low"
      confidence_pct   — formatted string e.g. "87%"
      fallback_note    — human-readable warning when confidence is low
    """
    explanation  = result.get("explanation", "")
    tags         = result.get("tags", [])
    follow_ups   = result.get("follow_ups", [])
    visual_code  = result.get("visual_code", "")

    checks = [
        _check_length(explanation),
        _check_relevance(explanation, question),
        _check_hallucination(explanation),
        _check_completeness(explanation),
        _check_follow_ups(follow_ups),
        _check_tags(tags),
        _check_web_grounded(has_web_context),
    ]

    passed = sum(1 for c in checks if c["passed"])
    total  = len(checks)

    confidence = calculate_confidence(
        has_web_context=has_web_context,
        explanation_len=len(explanation),
        tags_count=len(tags),
        follow_ups_count=len(follow_ups),
        has_visual=bool(visual_code),
        checks_passed=passed,
        checks_total=total,
    )

    if confidence >= 0.80:
        label = "high"
    elif confidence >= 0.55:
        label = "medium"
    else:
        label = "low"

    fallback_note = ""
    if not has_web_context:
        fallback_note = "No web context — answer based on LLM training knowledge"
    if confidence < 0.55:
        if fallback_note:
            fallback_note += "; "
        fallback_note += "Low confidence — consider verifying with additional sources"

    logger.info(
        "Verification: %d/%d checks passed, confidence=%.2f (%s)",
        passed, total, confidence, label,
    )

    return {
        "checks":           checks,
        "passed":           passed,
        "total":            total,
        "confidence":       confidence,
        "confidence_label": label,
        "confidence_pct":   f"{confidence:.0%}",
        "fallback_note":    fallback_note,
    }

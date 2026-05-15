"""
Reasoning Type Classifier
Classifies a question into one of the supported reasoning types using
keyword rules (fast, no LLM call required).
"""

# Supported reasoning types
REASONING_TYPES = [
    "arithmetic",
    "logical",
    "causal",
    "research",
    "planning",
    "comparison",
    "educational",
    "visual",
    "exploratory",
    "multi-step",
]

# Rules: (keywords_list, reasoning_type) — first match wins
_RULES: list[tuple[list[str], str]] = [
    (
        # Comparison must come before arithmetic so "difference between" wins
        ["compare", "difference between", " vs ", "versus", "better than",
         "which is more", "similar to", "unlike", "contrast", "same as",
         "how are", "what is the difference"],
        "comparison",
    ),
    (
        ["how much", "calculate", "how many", "how far", "percent", "ratio",
         "equation", "solve", "sum", "total", "average", "formula", "multiply",
         "divide", "add", "subtract", "what is the value", "compute"],
        "arithmetic",
    ),
    (
        ["why does", "why do", "why is", "why are", "why did", "cause of",
         "because of", "reason for", "result in", "lead to", "effect of",
         "what causes", "what makes"],
        "causal",
    ),
    (
        ["how to", "steps to", "how do i", "how can i", "process of",
         "procedure for", "plan for", "create a", "build a", "make a",
         "design a", "instructions for", "guide to"],
        "planning",
    ),
    (
        ["show me", "draw", "diagram", "picture", "illustrate", "visualize",
         "what does it look like", "image of", "sketch of"],
        "visual",
    ),
    (
        ["if", "would", "could", "imagine", "what if", "suppose", "assume",
         "is it possible", "can a", "logical", "true or false", "prove"],
        "logical",
    ),
    (
        ["step by step", "sequence of", "order of", "first then", "after that",
         "next step", "process", "stages of", "phases of", "how does .* work",
         "lifecycle"],
        "multi-step",
    ),
    (
        ["latest", "recent", "news", "current events", "today", "2024", "2025",
         "search for", "find information", "who invented", "when was"],
        "research",
    ),
    (
        ["what is", "who is", "where is", "when did", "define", "explain",
         "tell me about", "what are", "describe", "meaning of", "history of"],
        "educational",
    ),
]


def classify_reasoning_type(question: str) -> str:
    """
    Classify the question into one of the supported reasoning types.
    Uses keyword matching — fast and deterministic, no LLM needed.
    Returns 'exploratory' when no rule matches.
    """
    q = question.lower()
    for keywords, rtype in _RULES:
        if any(kw in q for kw in keywords):
            return rtype
    return "exploratory"


def describe_reasoning_type(rtype: str) -> str:
    """Human-readable description of each reasoning type."""
    _DESCRIPTIONS = {
        "arithmetic":  "Numerical calculation or quantitative reasoning",
        "logical":     "Deductive or conditional reasoning",
        "causal":      "Understanding cause-and-effect relationships",
        "research":    "Fact lookup or current-events retrieval",
        "planning":    "Step-by-step procedural planning",
        "comparison":  "Comparing two or more concepts",
        "educational": "Learning or defining a concept",
        "visual":      "Requesting a diagram or visual representation",
        "exploratory": "Open-ended curiosity question",
        "multi-step":  "Sequential process with ordered stages",
    }
    return _DESCRIPTIONS.get(rtype, "General reasoning")

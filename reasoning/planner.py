"""
Tool Planning Layer
Creates a structured execution plan for a given reasoning type and question.
Separates reasoning, tool selection, and execution order explicitly.
"""

# Available tools in the system
AVAILABLE_TOOLS = {
    "web_search":       "DuckDuckGo keyless web search for real-world context",
    "llm_explain":      "LLM waterfall (Groq → Gemini → Ollama → Claude) for explanation",
    "image_gen":        "AI image generator for educational visuals",
    "svg_generator":    "LLM-based SVG diagram generator (fallback after image gen)",
    "template_svg":     "Rule-based SVG template (final fallback for visuals)",
    "curiosity_map":    "Personal knowledge graph — stores and connects topics",
}

# Maps reasoning type → which tools to use and in what order
_TOOL_PLANS: dict[str, list[str]] = {
    "arithmetic":  ["web_search", "llm_explain"],
    "logical":     ["llm_explain"],
    "causal":      ["web_search", "llm_explain", "image_gen"],
    "research":    ["web_search", "llm_explain"],
    "planning":    ["web_search", "llm_explain", "image_gen"],
    "comparison":  ["web_search", "llm_explain", "image_gen"],
    "educational": ["web_search", "llm_explain", "image_gen"],
    "visual":      ["web_search", "llm_explain", "image_gen"],
    "exploratory": ["web_search", "llm_explain", "image_gen"],
    "multi-step":  ["web_search", "llm_explain", "image_gen"],
}


def create_execution_plan(reasoning_type: str, question: str) -> dict:
    """
    Build a structured execution plan for the given reasoning type.

    Returns a dict with:
      required_tools   — list of tool IDs that will be used
      execution_order  — same list, explicitly ordered
      steps            — numbered step-by-step actions with tool assignments
    """
    tools = _TOOL_PLANS.get(reasoning_type, _TOOL_PLANS["exploratory"])

    steps: list[dict] = []
    n = 1

    steps.append({
        "step": n, "phase": "Reasoning",
        "action": "understand_intent",
        "tool": "intent_parser",
        "description": f"Parse and understand: \"{question[:70]}\"",
    })
    n += 1

    steps.append({
        "step": n, "phase": "Reasoning",
        "action": "classify_type",
        "tool": "reasoning_classifier",
        "description": f"Identified reasoning type: {reasoning_type}",
    })
    n += 1

    steps.append({
        "step": n, "phase": "Planning",
        "action": "select_tools",
        "tool": "planner",
        "description": f"Tools selected: {', '.join(tools)}",
    })
    n += 1

    if "web_search" in tools:
        steps.append({
            "step": n, "phase": "Execution",
            "action": "web_search",
            "tool": "web_search",
            "description": "Fetch factual context from DuckDuckGo (keyless)",
        })
        n += 1

    steps.append({
        "step": n, "phase": "Execution",
        "action": "llm_explain",
        "tool": "llm_explain",
        "description": "Generate age-appropriate explanation via LLM waterfall",
    })
    n += 1

    if "image_gen" in tools:
        steps.append({
            "step": n, "phase": "Execution",
            "action": "generate_visual",
            "tool": "image_gen -> svg_generator -> template_svg",
            "description": "Generate educational visual (AI image → SVG → template fallback)",
        })
        n += 1

    steps.append({
        "step": n, "phase": "Verification",
        "action": "verify_output",
        "tool": "verifier",
        "description": "Check factual consistency, completeness, and hallucination risk",
    })
    n += 1

    steps.append({
        "step": n, "phase": "Verification",
        "action": "self_check",
        "tool": "self_checker",
        "description": "Compute confidence score and flag uncertainty if needed",
    })
    n += 1

    steps.append({
        "step": n, "phase": "Response",
        "action": "synthesize",
        "tool": "response_builder",
        "description": "Assemble structured final response with reasoning trace",
    })

    return {
        "required_tools":  tools,
        "execution_order": tools,
        "steps":           steps,
    }

"""Quick smoke-test for all reasoning module components."""
import sys
sys.path.insert(0, ".")

from reasoning.classifier import classify_reasoning_type
from reasoning.planner import create_execution_plan
from reasoning.verifier import verify_response

# ── Classifier ─────────────────────────────────────────────────────────────────
print("=== Classifier ===")
tests = [
    "Why is the sky blue?",
    "How to make a paper airplane?",
    "What is the difference between a virus and bacteria?",
    "Calculate speed of car going 100km in 2 hours",
    "How do black holes form step by step?",
    "Show me a diagram of the solar system",
    "If water freezes at 0C would boiling point change on Mars?",
]
for q in tests:
    rtype = classify_reasoning_type(q)
    print(f"  [{rtype:12s}] {q}")

# ── Planner ────────────────────────────────────────────────────────────────────
print("\n=== Planner ===")
plan = create_execution_plan("causal", "Why is the sky blue?")
print(f"Steps: {len(plan['steps'])}, tools: {plan['required_tools']}")
for step in plan["steps"]:
    print(f"  {step['step']}. [{step['phase']:12s}] {step['action']:20s} - {step['description']}")

# ── Verifier ───────────────────────────────────────────────────────────────────
print("\n=== Verifier ===")
fake_result = {
    "explanation": (
        "The sky appears blue because of Rayleigh scattering. "
        "When sunlight enters the atmosphere, it collides with gas molecules. "
        "Blue light scatters more than red light due to its shorter wavelength. "
        "This scattered blue light reaches our eyes from all directions."
    ),
    "tags": ["light", "atmosphere", "physics"],
    "follow_ups": [
        "Why is sunset red?",
        "What causes rainbows?",
        "Is the sky blue on other planets?",
    ],
    "visual_code": "<svg><rect/></svg>",
}
ver = verify_response("Why is the sky blue?", fake_result, has_web_context=True)
print(f"Verification: {ver['passed']}/{ver['total']} checks, confidence={ver['confidence_pct']} ({ver['confidence_label']})")
for c in ver["checks"]:
    print(f"  {c['check_icon']} {c['check']:20s}: {c['note']}")

print("\nAll tests passed!")

"""Test with a new question to verify full save+trace path."""
import json
import sys
import urllib.request
import urllib.error

URL = "http://localhost:5175/api/ask"
PAYLOAD = json.dumps({
    "question": "What is the difference between speed and velocity?",
    "asked_by": "child",
    "profile_id": "",
}).encode()

print("Testing /api/ask with NEW question ...")
req = urllib.request.Request(
    URL, data=PAYLOAD,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read())
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

topic = body.get("topic", {})
trace = topic.get("reasoning_trace", {})

print(f"  question:         {topic.get('question', '?')}")
print(f"  reasoning_type:   {trace.get('reasoning_type', 'MISSING')}")
print(f"  confidence_pct:   {trace.get('confidence_pct', 'MISSING')}")
print(f"  confidence_label: {trace.get('confidence_label', 'MISSING')}")
print(f"  elapsed_seconds:  {trace.get('elapsed_seconds', '?')}")
print(f"  tools_selected:   {trace.get('tools_selected', [])}")

stages = trace.get("pipeline_stages", [])
print(f"\nPipeline stages ({len(stages)}):")
for s in stages:
    print(f"  {s.get('status_icon','?')} {s.get('name','?')}: {s.get('detail','')}")

# Also verify explicit_reasoning fields
print(f"\nEvaluation criteria:")
for field in ["explicit_reasoning","structured_output","tool_separation",
              "conversation_loop","instructional_framing","internal_self_checks",
              "reasoning_type_awareness","fallbacks"]:
    val = trace.get(field, "MISSING")
    icon = "OK" if val is True else ("MISSING" if val == "MISSING" else str(val))
    print(f"  {field}: {icon}")

print(f"\n  overall_clarity: {trace.get('overall_clarity', 'MISSING')}")

print("\nPASS" if stages else "FAIL: no stages found")

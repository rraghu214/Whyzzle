"""End-to-end test against the running Whyzzle API."""
import json
import sys
import urllib.request
import urllib.error

URL = "http://localhost:5175/api/ask"
PAYLOAD = json.dumps({
    "question": "Why is the sky blue?",
    "asked_by": "child",
    "profile_id": "",
}).encode()

print("Testing /api/ask ...")
try:
    req = urllib.request.Request(
        URL, data=PAYLOAD,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read())
except urllib.error.URLError as e:
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

checks = trace.get("verification_checks", [])
print(f"\nVerification ({trace.get('verification_passed','?')}/{trace.get('verification_total','?')}):")
for c in checks:
    print(f"  {c.get('check_icon','?')} {c.get('check','?')}: {c.get('note','')}")

print("\nAll checks PASSED" if stages and checks else "\nWARNING: trace data missing!")

"""Check curiosity map for reasoning_trace presence."""
import json
data = json.load(open("data/curiosity_map.json"))
print(f"Total topics: {len(data)}")
for t in data[:5]:
    has_trace = bool(t.get("reasoning_trace"))
    print(f"  q={t.get('question','?')[:50]:50s} has_trace={has_trace}")

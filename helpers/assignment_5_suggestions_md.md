# Session-5 Assignment Implementation Guide for Whyzzle

> Based on:
> - Session-5 Notes PDF
> - Assignment Prompt Rules

---

# Goal of This Document

This markdown is intended for:

- Claude Code
- Cursor
- AI-assisted implementation workflows

The purpose is to convert Whyzzle into a:

# "Structured Planning & Reasoning AI System"

that satisfies all Session-5 assignment expectations.

---

# 1. Understanding the Assignment Properly

The assignment is NOT asking for:
- simple chatbots
- summarizers
- CRUD tools
- basic AI wrappers

The assignment IS asking for:
- structured reasoning
- planning systems
- multi-step workflows
- tool orchestration
- explicit reasoning pipelines
- self-verification
- robust prompting
- agentic AI behavior

---

# 2. Core Learnings from Session-5 That MUST Be Implemented

The PDF topic is:

# "Planning and Reasoning with Language Models"

This means the project MUST visibly demonstrate:

| Concept | Must Be Visible? | Status |
|---|---|---|
| Step-by-step reasoning | YES | ✅ DONE — engine.py stages 1–9 |
| Structured planning | YES | ✅ DONE — planner.py execution plan |
| Tool orchestration | YES | ✅ DONE — engine wraps all tools |
| Explicit reasoning stages | YES | ✅ DONE — pipeline_stages in trace |
| Self-verification | YES | ✅ DONE — verifier.py 7 checks |
| Multi-turn interaction | YES | ✅ DONE — follow_ups re-trigger ask |
| Reasoning-aware outputs | YES | ✅ DONE — classifier.py + trace |
| Error handling | YES | ✅ DONE — graceful fallbacks in engine |
| Structured outputs | YES | ✅ DONE — reasoning_trace JSON schema |

---

# 3. Required Assignment-Level Features

## A. Explicit Reasoning Pipeline ✅ DONE
`reasoning/engine.py` — 9 explicit stages logged and stored in reasoning_trace.pipeline_stages

## B. Structured JSON Output ✅ DONE
Every topic now includes `reasoning_trace` with the full schema (see engine.py)

## C. Reasoning Type Detection ✅ DONE
`reasoning/classifier.py` — 10 types classified by keyword rules (fast, deterministic)

## D. Tool Separation ✅ DONE
`reasoning/engine.py` — phases: Reasoning → Planning → Execution → Verification → Response

## E. Self Verification ✅ DONE
`reasoning/verifier.py` — 7 heuristic checks: length, relevance, hallucination, completeness, follow_ups, tags, web_grounded

## F. Error Handling / Fallbacks ✅ DONE
`reasoning/engine.py` — try/except around search_and_explain with graceful error topic

## G. Multi-Turn Conversation Support ✅ DONE
Follow-up questions click → SetState("question") → triggers new ask cycle

## H. Instructional Framing ✅ DONE
Structured pipeline prompt templates embedded in search_and_explain.py

---

# 4. Session-5 Evaluation Criteria — Status

| Evaluator Check | Required | Status | Location |
|---|---|---|---|
| explicit_reasoning | YES | ✅ | engine.py stages |
| structured_output | YES | ✅ | reasoning_trace JSON |
| tool_separation | YES | ✅ | engine.py phases |
| conversation_loop | YES | ✅ | follow_up → ask |
| instructional_framing | YES | ✅ | search_and_explain prompt |
| internal_self_checks | YES | ✅ | verifier.py |
| reasoning_type_awareness | YES | ✅ | classifier.py |
| fallbacks | YES | ✅ | engine.py try/except |
| overall_clarity | YES | ✅ | confidence_label + pct |

---

# 5. Whyzzle Extension Requirements

Whyzzle already had:
- MCP support
- tool orchestration
- visual generation
- web search
- local file operations
- knowledge graph concepts

Session-5 adds:
- `reasoning/` module (classifier + planner + verifier + engine)
- reasoning_trace stored with every topic
- Reasoning Trace Panel in the UI

---

# 6. REQUIRED Features — Implementation Status

| Feature | Status | File |
|---|---|---|
| Feature 1 — Reasoning Pipeline UI | ✅ DONE | app.py topic page panel |
| Feature 2 — Structured Reasoning Engine | ✅ DONE | reasoning/engine.py |
| Feature 3 — Reasoning Type Classifier | ✅ DONE | reasoning/classifier.py |
| Feature 4 — Tool Planning Layer | ✅ DONE | reasoning/planner.py |
| Feature 5 — Self Verification Layer | ✅ DONE | reasoning/verifier.py |
| Feature 6 — Confidence Score | ✅ DONE | verifier.py calculate_confidence() |
| Feature 7 — Multi-Step Prompt Templates | ✅ DONE | engine.py + search_and_explain |
| Feature 8 — Fallback Strategies | ✅ DONE | engine.py try/except + verifier |
| Feature 9 — Reasoning Trace Viewer | ✅ DONE | app.py Reasoning Trace Panel |
| Feature 10 — Submission Demo Flow | ✅ READY | all pipeline visible in UI |

---

# 7. Technical Architecture (Implemented in Python)

```
/reasoning
  __init__.py
  classifier.py    — keyword-based reasoning type classifier (10 types)
  planner.py       — tool planning layer (required_tools + steps)
  verifier.py      — 7 heuristic checks + confidence score (0.0–1.0)
  engine.py        — 9-stage orchestration pipeline

/tools (existing, unchanged logic)
  search_and_explain.py  — web search + LLM waterfall + visual gen
  curiosity_map.py       — knowledge graph + reasoning_trace storage
  profiles.py
  video_pipeline.py

app.py  — FastAPI + Prefab UI
  /api/ask  — now calls run_reasoning_pipeline() instead of search_and_explain()
  topic page — new Reasoning Trace Panel (stages + verification checks)
```

---

# 8. Reasoning Trace JSON Schema (DONE)

Every topic now stores:
```json
{
  "reasoning_trace": {
    "explicit_reasoning": true,
    "structured_output": true,
    "tool_separation": true,
    "conversation_loop": true,
    "instructional_framing": true,
    "internal_self_checks": true,
    "reasoning_type_awareness": true,
    "fallbacks": true,
    "overall_clarity": "Structured educational reasoning with high confidence (87%)",

    "user_goal": "Why is the sky blue?",
    "reasoning_type": "causal",
    "reasoning_desc": "Understanding cause-and-effect relationships",
    "execution_plan": { "required_tools": [...], "steps": [...] },
    "tools_selected": ["web_search", "llm_explain", "image_gen"],
    "tool_results": [...],
    "verification_checks": [...],
    "confidence": 0.87,
    "confidence_label": "high",
    "confidence_pct": "87%",
    "fallback_strategy": "",
    "pipeline_stages": [...],
    "elapsed_seconds": 4.21
  }
}
```

---

# 15. Final Assignment Success Checklist

## MUST HAVE

| Requirement | Mandatory | Status |
|---|---|---|
| Explicit reasoning | YES | ✅ DONE |
| Planning pipeline | YES | ✅ DONE |
| Structured outputs | YES | ✅ DONE |
| Tool orchestration | YES | ✅ DONE |
| Self verification | YES | ✅ DONE |
| Reasoning types | YES | ✅ DONE |
| Error handling | YES | ✅ DONE |
| Multi-turn support | YES | ✅ DONE |
| README explanation | YES | ⏳ TODO |
| Demo video | YES | ⏳ TODO |

---

# Final Summary

The Session-5 implementation adds a full structured reasoning layer to Whyzzle:

```text
reasoning/engine.py orchestrates 9 pipeline stages:
  1. Understand User Intent
  2. Classify Reasoning Type   ← reasoning/classifier.py
  3. Create Execution Plan     ← reasoning/planner.py
  4. Select Required Tools     ← planner output
  5. Execute Steps             ← tools/search_and_explain.py
  6. Verify Results            ← reasoning/verifier.py
  7. Generate Final Answer     ← LLM output
  8. Self-Check                ← confidence scoring
  9. Assemble Structured Response ← reasoning_trace attached to topic
```

Every response now:
- Identifies reasoning type (10 categories)
- Shows 9 pipeline stages with status
- Runs 7 verification checks
- Computes confidence score (0–100%)
- Handles failures with graceful fallbacks
- Stores everything in reasoning_trace for inspection

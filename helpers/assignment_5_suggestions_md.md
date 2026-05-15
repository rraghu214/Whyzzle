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

# “Structured Planning & Reasoning AI System”

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

# “Planning and Reasoning with Language Models”

This means the project MUST visibly demonstrate:

| Concept | Must Be Visible? | Why |
|---|---|---|
| Step-by-step reasoning | YES | Core session theme |
| Structured planning | YES | Main assignment expectation |
| Tool orchestration | YES | Agentic workflow |
| Explicit reasoning stages | YES | Prompt engineering quality |
| Self-verification | YES | Reliability |
| Multi-turn interaction | YES | Conversational reasoning |
| Reasoning-aware outputs | YES | Advanced prompting |
| Error handling | YES | Robustness |
| Structured outputs | YES | Validation & evaluation |

---

# 3. Required Assignment-Level Features

The following MUST be clearly visible in the implementation.

---

# A. Explicit Reasoning Pipeline

The system must visibly reason in stages.

## Required Flow

```text
1. Understand User Intent
2. Identify Reasoning Type
3. Create Execution Plan
4. Select Required Tools
5. Execute Steps
6. Verify Intermediate Results
7. Generate Final Answer
8. Perform Self-Check
9. Return Structured Response
```

---

# B. Structured JSON Output

Every major AI response should internally follow a structure like:

```json
{
  "user_goal": "",
  "reasoning_type": "",
  "execution_plan": [],
  "tools_selected": [],
  "tool_results": [],
  "verification_steps": [],
  "confidence_level": "",
  "final_response": ""
}
```

This is VERY important for Session-5 evaluation.

---

# C. Reasoning Type Detection

The system should classify the reasoning category.

## Supported Types

```text
- arithmetic
- logical
- causal
- research
- planning
- comparison
- educational
- visual
- exploratory
- multi-step
```

---

# D. Tool Separation

Reasoning and tool execution must be separated.

## Correct Structure

```text
[Reasoning Phase]
Determine what needs to be done.

[Planning Phase]
Select tools and order of execution.

[Execution Phase]
Run tools.

[Verification Phase]
Validate outputs.

[Response Phase]
Generate final explanation.
```

---

# E. Self Verification

The system MUST verify outputs before finalizing.

## Required Checks

```text
- factual consistency
- hallucination risk
- missing steps
- contradictory statements
- logical consistency
- incomplete reasoning
```

---

# F. Error Handling / Fallbacks

The system must gracefully handle failures.

## Examples

```text
If web search fails:
- fallback to local KB

If image generation fails:
- continue with textual explanation

If confidence is low:
- explicitly say uncertainty exists
```

---

# G. Multi-Turn Conversation Support

The system should:
- remember previous reasoning
- continue workflows
- refine outputs iteratively

## Example

```text
User:
Explain black holes.

System:
Provides beginner explanation.

User:
Now explain mathematically.

System:
Continues from previous context.
```

---

# H. Instructional Framing

The AI should provide:
- structured explanations
- guided workflows
- predictable formatting

---

# 4. Session-5 Evaluation Criteria That MUST Be Demonstrated

The assignment rules evaluate prompts using the following criteria:

---

# 1. Explicit Reasoning Instructions

Must include instructions like:

```text
Think step-by-step.
Analyze before answering.
Explain intermediate reasoning.
```

---

# 2. Structured Output Format

Must produce:

- JSON
- numbered steps
- function-call style outputs
- predictable formatting

---

# 3. Separation of Reasoning and Tools

Must distinguish:
- reasoning
- planning
- tool usage
- verification

---

# 4. Conversation Loop Support

Must support:
- follow-up questions
- iterative refinement
- contextual continuation

---

# 5. Instructional Framing

Must define:
- output structure
- response style
- expected formatting

---

# 6. Internal Self Checks

Must verify:
- consistency
- correctness
- completeness

---

# 7. Reasoning Type Awareness

Must identify:
- what type of reasoning is being performed

---

# 8. Error Handling / Fallbacks

Must define:
- uncertainty handling
- fallback behaviors
- failure responses

---

# 9. Overall Robustness

Must reduce:
- hallucination
- drift
- inconsistent outputs

---

# 5. Whyzzle Extension Requirements

Whyzzle already has:
- MCP support
- tool orchestration
- visual generation
- web search
- local file operations
- knowledge graph concepts

The assignment requires Whyzzle to evolve into:

# “A Structured Multi-Agent Reasoning System”

---

# 6. REQUIRED Features To Add to Whyzzle

---

# Feature 1 — Reasoning Pipeline UI

Add a visible pipeline:

```text
🧠 Understanding Query
📋 Creating Plan
🛠 Selecting Tools
🔍 Gathering Information
✅ Verifying Results
🎨 Generating Visuals
📦 Preparing Final Response
```

This is one of the MOST important features.

---

# Feature 2 — Structured Reasoning Engine

Create a reasoning controller that manages:

```text
- planning
- tool sequencing
- memory
- verification
- final synthesis
```

Suggested module:

```text
reasoning-engine/
```

---

# Feature 3 — Reasoning Type Classifier

Add classifier logic:

```ts
type ReasoningType =
  | "logical"
  | "causal"
  | "research"
  | "comparison"
  | "educational"
  | "visual"
  | "planning"
  | "multi-step";
```

---

# Feature 4 — Tool Planning Layer

Before executing tools:

Generate a plan like:

```json
{
  "required_tools": [
    "web_search",
    "image_generator",
    "knowledge_graph"
  ],
  "execution_order": [
    "web_search",
    "knowledge_graph",
    "image_generator"
  ]
}
```

---

# Feature 5 — Self Verification Layer

Add a verification stage:

```text
- validate reasoning
- verify factual consistency
- detect hallucination risk
- confidence scoring
```

---

# Feature 6 — Confidence Score

Every response should include:

```json
{
  "confidence": 0.91
}
```

Based on:
- number of tool confirmations
- consistency
- source reliability

---

# Feature 7 — Multi-Step Prompt Templates

Add prompts like:

```text
1. Understand the problem
2. Break into smaller steps
3. Decide required tools
4. Execute carefully
5. Verify results
6. Generate final response
```

---

# Feature 8 — Fallback Strategies

Required fallback examples:

```text
If search unavailable:
→ use local KB

If visual generation unavailable:
→ provide textual visualization

If confidence low:
→ explicitly mention uncertainty
```

---

# Feature 9 — Reasoning Trace Viewer

Allow users to inspect:

```text
- reasoning type
- planning
- tools used
- intermediate outputs
- verification status
```

This strongly aligns with assignment expectations.

---

# Feature 10 — Submission Demonstration Flow

The final demo MUST clearly show:

## Example Demo Flow

```text
1. User asks complex question
2. System identifies reasoning type
3. System creates execution plan
4. System selects tools
5. System executes tools
6. System verifies outputs
7. System generates visuals
8. System returns structured response
9. User asks follow-up
10. System continues reasoning chain
```

---

# 7. Recommended Technical Architecture

## Suggested Modules

```text
/src
  /reasoning
    planner.ts
    verifier.ts
    reasoning-types.ts
    confidence.ts

  /tools
    web-search.ts
    image-generator.ts
    local-files.ts

  /memory
    context-manager.ts

  /ui
    reasoning-panel.tsx
```

---

# 8. Suggested Prompt Template

This prompt template is EXTREMELY IMPORTANT.

The assignment evaluator itself checks whether the prompt satisfies:

- explicit reasoning
- structured outputs
- tool separation
- conversation support
- self checks
- reasoning awareness
- fallbacks
- robustness

The implementation MUST therefore explicitly contain all of these.

---

## REQUIRED Master Prompt Structure

```text
You are a structured reasoning AI assistant.

Follow these steps strictly:

1. Understand the user goal
2. Identify the reasoning type
3. Break the task into substeps
4. Create an execution plan
5. Select required tools
6. Execute steps carefully
7. Verify intermediate outputs
8. Detect contradictions or hallucinations
9. Perform self-checks
10. Generate structured final output
11. Provide confidence score
12. If uncertain, explicitly mention limitations
13. If a tool fails, use fallback strategies

Separate:
- reasoning
- planning
- execution
- verification
- final response

Support multi-turn continuation using previous context.

Always explain intermediate reasoning.
```

---

# 9. REQUIRED Structured JSON Response Format

The assignment evaluator explicitly checks whether outputs are structured and machine-readable.

The system MUST therefore support outputs using the following structure:

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": true,
  "conversation_loop": true,
  "instructional_framing": true,
  "internal_self_checks": true,
  "reasoning_type_awareness": true,
  "fallbacks": true,
  "overall_clarity": "Clear structured reasoning with verification and fallback support."
}
```

---

# 10. REQUIRED Internal Reasoning JSON Schema

The actual reasoning engine inside Whyzzle should internally maintain a richer JSON structure like:

```json
{
  "user_goal": "",
  "reasoning_type": "",
  "execution_plan": [],
  "tools_selected": [],
  "tool_results": [],
  "verification_steps": [],
  "fallback_strategy": "",
  "confidence_level": 0.0,
  "final_response": ""
}
```

---

# 11. Assignment Evaluator Mapping

The evaluator prompt checks the following:

| Evaluator Check | Must Exist in Whyzzle |
|---|---|
| explicit_reasoning | Step-by-step reasoning pipeline |
| structured_output | JSON response formats |
| tool_separation | Separate planning/execution/verification |
| conversation_loop | Multi-turn continuation |
| instructional_framing | Strict response templates |
| internal_self_checks | Verification layer |
| reasoning_type_awareness | Reasoning classifier |
| fallbacks | Failure handling logic |
| overall_clarity | Predictable structured outputs |

---

# 12. What MUST Be Clearly Visible in README

The README should explicitly mention:

## A. Planning

```text
Whyzzle performs structured planning before execution.
```

---

## B. Multi-Step Reasoning

```text
Whyzzle breaks complex tasks into reasoning stages.
```

---

## C. Tool Orchestration

```text
Whyzzle dynamically selects and orchestrates tools.
```

---

## D. Verification

```text
Whyzzle performs self-verification before final responses.
```

---

## E. Reasoning Awareness

```text
Whyzzle identifies reasoning types for each task.
```

---

## F. Fallback Handling

```text
Whyzzle gracefully handles uncertainty and tool failures.
```

---

# 13. Recommended Submission Positioning

The project should be presented as:

# “Whyzzle — A Multi-Agent Planning and Reasoning System”

NOT:
- chatbot
- summarizer
- AI wrapper

BUT:
- reasoning engine
- planning system
- intelligent orchestration framework
- visual learning AI

---

# 14. Important Notes for Claude Code

## Priority Order

### Highest Priority
- reasoning pipeline
- planning visibility
- verification layer
- structured outputs

### Medium Priority
- UI polish
- animations

### Lower Priority
- advanced styling

---

# 15. Final Assignment Success Checklist

## MUST HAVE

| Requirement | Mandatory |
|---|---|
| Explicit reasoning | YES |
| Planning pipeline | YES |
| Structured outputs | YES |
| Tool orchestration | YES |
| Self verification | YES |
| Reasoning types | YES |
| Error handling | YES |
| Multi-turn support | YES |
| README explanation | YES |
| Demo video | YES |

---

# Final Summary

The assignment is fundamentally testing:

```text
Can you design an AI system that:
- reasons explicitly
- plans before acting
- uses tools intelligently
- verifies itself
- handles uncertainty
- supports iterative workflows
- exposes structured reasoning
```

Whyzzle already has a strong foundation.

The Session-5 implementation should focus on:

# “Making the reasoning process explicit, structured, and verifiable.”


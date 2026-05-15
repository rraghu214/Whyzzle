# Whyzzle
### *Ask anything. See everything.*

> An AI-powered curiosity coach that turns every question into an instant visual explanation — and grows a personal knowledge map for everyone who uses it.

---

## Session-5: Planning & Reasoning with Language Models

Whyzzle now includes a full **structured reasoning engine** that proves, at every step, that the LLM is following prompt-engineering best practices.

### What was added

| Feature | Where |
|---|---|
| 9-stage reasoning pipeline | `reasoning/engine.py` |
| Keyword-based reasoning classifier | `reasoning/classifier.py` |
| Execution planner (tool selection) | `reasoning/planner.py` |
| 7-check heuristic verifier | `reasoning/verifier.py` |
| Live reasoning sidebar (right panel) | `app.py` — right Column |
| Chain of Thought expand button | `app.py` — right sidebar |
| Prompt capture + raw response capture | `tools/search_and_explain.py` |

### Right sidebar — live reasoning panel

While a question is being processed, the right sidebar shows all 9 pipeline stages animating live. Once the answer arrives, it switches to showing:

- **Reasoning type badge** — e.g. `comparison`, `causal`, `educational`
- **Confidence badge** — e.g. `95%` (computed from 7 verification checks)
- **Pipeline stages** — each with a status icon (✅ / ❌ / ⚠️) and detail
- **Verification checks** — 7 heuristic checks on the response quality
- **Chain of Thought button** — expands to show the actual prompt sent to the LLM and the raw LLM response

### Chain of Thought — prompt qualification

Click **"🔍 Chain of Thought"** in the right sidebar to expand and see:

1. **PROMPT EVALUATION** — proof that every Session-5 prompt standard is met (all 8 criteria show `OK`)
2. **PROMPT SENT TO LLM** — the actual prompt string that was sent, including the reasoning framework preamble
3. **LLM RESPONSE** — the first 800 characters of the raw LLM response

### How the prompt qualifies the test output

The LLM prompt (`tools/search_and_explain.py`) is structured so that every response satisfies all 9 Session-5 evaluation criteria:

| Criterion | How the prompt enforces it |
|---|---|
| **Explicit Reasoning** | The prompt opens with `## REASONING FRAMEWORK` listing 8 explicit reasoning steps the model must follow before answering |
| **Structured Output** | The prompt requires JSON output with fixed keys: `explanation`, `tags`, `follow_ups`, `concept_type`, `visual_code`, `visual_type` |
| **Tool Separation** | Web search (`DuckDuckGo`) runs first and its results are injected into the prompt under `## WEB CONTEXT`; the LLM only calls the explain tool |
| **Conversation Loop** | `follow_ups` (3 clickable chips) let the user re-enter the pipeline for a new question |
| **Instructional Framing** | `## USER CONTEXT` section gives the LLM the asker's age and role; `## TASKS` lists the exact output expectations |
| **Internal Self-Checks** | The prompt ends with `## SELF-CHECK` requiring the model to verify: reasoning matches question type, explanation matches age level, JSON is valid |
| **Reasoning Type Awareness** | The classifier (`reasoning/classifier.py`) detects the reasoning type before the LLM is called; it's injected as `REASONING_TYPE` into the prompt |
| **Error Fallbacks** | The LLM waterfall (Groq → Gemini → Ollama → Claude) is built into `search_and_explain.py`; a graceful error response is returned if all tiers fail |
| **Overall Clarity** | The verification engine (`reasoning/verifier.py`) scores confidence 0–100% across 7 heuristic checks; result is shown in the sidebar |

### Sample test output (from `helpers/test_api2.py`)

```
question:         What is the difference between speed and velocity?
reasoning_type:   comparison
confidence_pct:   95%
confidence_label: high
elapsed_seconds:  5.04
tools_selected:   ['web_search', 'llm_explain', 'image_gen']

Pipeline stages (9):
  ✅ Understanding Query: "What is the difference between speed and velocity?"
  ✅ Classifying Reasoning: type=comparison — Comparing two or more concepts
  ✅ Creating Execution Plan: 9 steps, tools=['web_search', 'llm_explain', 'image_gen']
  ✅ Selecting Tools: execution_order=['web_search', 'llm_explain', 'image_gen']
  ✅ Gathering Information: explanation=266 chars, visual_type=html_interactive
  ✅ Verifying Results: 7/7 checks passed, confidence=95%
  ✅ Generating Response: 266 char explanation
  ✅ Self-Check: High confidence (95%) — response approved
  ✅ Assembling Response: pipeline completed in 5.04s

Evaluation criteria:
  explicit_reasoning:       OK
  structured_output:        OK
  tool_separation:          OK
  conversation_loop:        OK
  instructional_framing:    OK
  internal_self_checks:     OK
  reasoning_type_awareness: OK
  fallbacks:                OK (triggered when needed)

overall_clarity: Structured comparison reasoning with high confidence (95%) and verification.
```

Run this test yourself:
```bash
uv run python helpers/test_api2.py
```

---

## What is Whyzzle?

Whyzzle is a locally-run app where you (or your child) ask any question — *"Why is the sky blue?", "How do planets orbit?", "What is 6 × 7?"* — and get back:

- **A clear explanation** tuned to the asker's age (a 6-year-old and a 38-year-old get very different answers)
- **A custom visual** — SVG diagram or interactive HTML canvas — generated fresh for that exact question
- **Three follow-up questions** to keep curiosity alive
- **A growing knowledge graph** that connects everything you've ever asked

Every profile has its own private curiosity map. Switch between family members and the entire view — graph, stats, recent history — switches too.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Whyzzle                              │
│                                                             │
│  ┌─────────────────┐      ┌──────────────────────────────┐  │
│  │  Prefab UI      │      │  MCP Server (mcp_server.py)  │  │
│  │  app.py         │      │                              │  │
│  │  FastAPI+Prefab │      │  Tool 1: search_topic        │  │
│  │  port 5175      │      │  Tool 2: save_topic          │  │
│  └────────┬────────┘      │  Tool 3: get_dashboard_url   │  │
│           │               └──────────────┬───────────────┘  │
│           │                              │                   │
│  ┌────────▼──────────────────────────────▼───────────────┐  │
│  │              Reasoning Engine (Session-5)              │  │
│  │  classifier.py → planner.py → engine.py → verifier.py │  │
│  │  9-stage pipeline · reasoning type · confidence score  │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │                    Tools Layer                         │  │
│  │  profiles.py · curiosity_map.py · search_and_explain  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  data/  (plain JSON, nothing leaves your machine)      │ │
│  │  profiles.json          curiosity_map.json             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         ▲
         │  Claude Desktop connects here via MCP (stdio)
         │  agent_demo.py calls the same tools directly
```

---

## Sample Screens

### 1 · Main Dashboard (3-panel layout)

```
┌──────────────────┬─────────────────────────────────────┬──────────────────────────┐
│  LEFT SIDEBAR    │         MAIN CONTENT                 │  RIGHT SIDEBAR (new!)    │
│                  │                                      │                          │
│  🧠 Whyzzle      │  Why is the sky blue?                │  🧠 Reasoning            │
│  ──────────────  │                                      │  ────────────────────── │
│  PROFILES        │  [interactive SVG visual]            │  comparison  95%         │
│  ●Aarav  [+New]  │                                      │  Comparing two concepts  │
│                  │  When sunlight enters the            │                          │
│  ──────────────  │  atmosphere, it bumps into           │  PIPELINE                │
│  🔍 Ask          │  tiny air particles. Blue light      │  ✅ Understanding Query   │
│  ┌────────────┐  │  bounces around much more            │  ✅ Classifying Reasoning │
│  │ Why is the │  │  than other colours.                 │  ✅ Creating Plan         │
│  │ sky blue?  │  │                                      │  ✅ Selecting Tools       │
│  └────────────┘  │  #light  #atmosphere  #physics       │  ✅ Gathering Info        │
│  [Ask Whyzzle ✨] │                                      │  ✅ Verifying Results     │
│                  │  🔗 Explore Further                  │  ✅ Generating Response   │
│  ──────────────  │  [Why is the sunset red?]            │  ✅ Self-Check            │
│  📚 Recent       │  [What is UV light?]                 │  ✅ Assembling Response   │
│  • sky blue?     │                                      │                          │
│  • planets orbit │  🎬 3D Animation                     │  VERIFICATION            │
│  • 6 × 7?        │  [Render 3D Scene]                   │  ✅ has explanation       │
│                  │                                      │  ✅ has visual code       │
│                  │                                      │  ✅ has tags              │
│                  │                                      │  ✅ has follow-ups        │
│                  │                                      │  ✅ explanation length    │
│                  │                                      │  ✅ question echoed       │
│                  │                                      │  ✅ web context found     │
│                  │                                      │                          │
│                  │                                      │  [🔍 Chain of Thought]   │
└──────────────────┴─────────────────────────────────────┴──────────────────────────┘
```

### 2 · Chain of Thought Expanded

Click **"🔍 Chain of Thought"** to expand and see exactly what was sent to the LLM and what it returned:

```
┌──────────────────────────────────────────────────┐
│  PROMPT EVALUATION                               │
│  OK  Explicit Reasoning                          │
│  OK  Structured Output                           │
│  OK  Tool Separation                             │
│  OK  Conversation Loop                           │
│  OK  Instructional Framing                       │
│  OK  Internal Self-Checks                        │
│  OK  Reasoning Type Aware                        │
│  OK  Error Fallbacks                             │
│                                                  │
│  PROMPT SENT TO LLM                              │
│  ┌──────────────────────────────────────────┐   │
│  │ ## REASONING FRAMEWORK                   │   │
│  │ REASONING_TYPE: comparison               │   │
│  │ Step 1: Understand the question type ... │   │
│  │ ## USER CONTEXT                          │   │
│  │ ## WEB CONTEXT                           │   │
│  │ ## TASKS                                 │   │
│  │ ## SELF-CHECK                            │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  LLM RESPONSE                                    │
│  ┌──────────────────────────────────────────┐   │
│  │ {"explanation": "Speed measures how      │   │
│  │  fast you move, while velocity also      │   │
│  │  includes direction...", "tags": [...]}  │   │
│  └──────────────────────────────────────────┘   │
│  [▲ Collapse]                                    │
└──────────────────────────────────────────────────┘
```

### 2 · Knowledge Graph View

Every topic you ask becomes a node. Topics with shared tags auto-connect. Click any node to jump to that explanation.

### 3 · Age-Adaptive Explanations

| Profile | Age | Answer to "Why is the sky blue?" |
|---|---|---|
| **Tobi** | 5 | *"Air has tiny invisible helpers that grab blue light and throw it everywhere!"* |
| **Aarav** | 8 | *"Sunlight hits tiny air particles. Blue bounces around much more than red."* |
| **Priya** | 13 | *"Rayleigh scattering causes blue light (≈450 nm) to scatter ~10× more than red..."* |
| **Dad** | 38 | *"Scattering intensity is inversely proportional to λ⁴, meaning blue scatters ~9.4× more..."* |

---

## Features

| Feature | Detail |
|---|---|
| Multi-profile | Up to 8 colour-coded profiles, each with their own map |
| Age-adaptive answers | 5 depth tiers: 4–6 · 7–10 · 11–14 · 15–17 · 18+ |
| Live web search | DuckDuckGo → HTML scrape fallback → LLM knowledge |
| Custom visuals | SVG or interactive HTML canvas, generated per question |
| Curiosity map | Personal knowledge graph; topics auto-connect by shared tags |
| Cross-session memory | "This links to your sky question from last week" |
| Follow-up chips | Clickable chips auto-ask the next question |
| Stats | Day streak, top branch, weekly count, tag cloud |
| MCP server | Full Claude Desktop integration — 3 tools available to the AI agent |

---

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager (`pip install uv` or see uv docs)
- A [Groq API key](https://console.groq.com/) (free) — for the LLM waterfall
- Optionally: [Gemini API key](https://aistudio.google.com/) (free) for fallback

### 1 · Clone and install

```bash
git clone <repo-url>
cd whyzzle
uv sync
```

### 2 · Set your API keys

```bash
# Copy the example and fill in your keys
copy .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIza_your_gemini_key_here   # optional fallback
ANTHROPIC_API_KEY=                          # leave blank if using free tiers
```

### 3 · Start the dashboard

```bash
uv run uvicorn app:fastapi_app --reload --port 5175
```

Open **http://localhost:5175** in your browser.

That's it. No database, no Docker, no build step.

---

## First-Time Flow

```
1. Open http://localhost:5175
        ↓
2. Click  [+ Add Profile]
   → Enter name + age  (e.g. "Aarav", 7)
        ↓
3. Type a question in the sidebar ask-box
   → e.g. "Why do stars twinkle?"
        ↓
4. Watch the explanation + visual appear in the main panel
        ↓
5. Click a follow-up chip to go deeper
        ↓
6. Click  Graph  tab to see your growing curiosity map
        ↓
7. Add a second profile (e.g. "Dad", 38) — same question,
   completely different depth of answer
```

---

## MCP Server + Claude Desktop Integration

Whyzzle exposes **3 MCP tools** via `mcp_server.py` that any MCP-compatible AI agent can call:

| Tool | Category | What it does |
|---|---|---|
| `search_topic` | Internet | Web search + LLM explanation for a question |
| `save_topic` | Local CRUD | Save the result to `data/curiosity_map.json` |
| `get_dashboard_url` | UI | Return the Prefab dashboard URL so the agent can point you there |

### Wiring Claude Desktop (Windows)

> **Note:** The Windows Store version of Claude Desktop uses a virtualized path — the config is NOT at the usual `%APPDATA%\Claude` location.

**Config file location (Windows Store app):**
```
C:\Users\<YourName>\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json
```

**Config content** — use the full path to `uv.exe` and the `--directory` flag (the Windows Store app does not honour the `cwd` field):

```json
{
  "mcpServers": {
    "whyzzle": {
      "command": "C:\\path\\to\\your\\uv.exe",
      "args": [
        "run",
        "--directory",
        "C:\\absolute\\path\\to\\whyzzle",
        "python",
        "mcp_server.py"
      ]
    }
  }
}
```

Replace `C:\\path\\to\\your\\uv.exe` with the actual path (find it with `where uv` in a terminal) and `C:\\absolute\\path\\to\\whyzzle` with your project folder.

**Wiring Claude Desktop (Mac / standard Windows install):**

Config file: `~/.config/claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows non-Store)

```json
{
  "mcpServers": {
    "whyzzle": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "cwd": "/absolute/path/to/whyzzle"
    }
  }
}
```

After editing the config, **quit and reopen Claude Desktop**. The whyzzle server should show as connected in Settings → Developer.

**Test prompt for Claude Desktop:**
```
Search for "How does a rainbow form?" and explain it, then save it to my curiosity map, then tell me where I can view my dashboard.
```

---

## Agent Demo (no Claude Desktop required)

`agent_demo.py` shows all 3 MCP tools firing sequentially from Python — no LLM orchestrator needed since the tools call Groq/Gemini internally for the heavy lifting.

```bash
uv run python agent_demo.py
# or with a custom question:
uv run python agent_demo.py "How does a rainbow form?"
```

Expected output:
```
=================================================================
WHYZZLE MCP AGENT DEMO
=================================================================
PROMPT : How does a rainbow form?
PROFILE: abc12345…

[Step 1] Calling tool: search_topic
         Searching the web + generating explanation via LLM…
-----------------------------------------------------------------
  Question    : How does a rainbow form?
  Tags        : ['light', 'water', 'refraction', 'weather']
  Concept type: spatial
  Explanation : Rainbows form when sunlight enters water droplets…

[Step 2] Calling tool: save_topic
         Saving result to data/curiosity_map.json…
-----------------------------------------------------------------
  Saved       : True
  Topic ID    : def67890…
  Connections : 2 related topics linked

[Step 3] Calling tool: get_dashboard_url
         Fetching the Prefab UI dashboard URL…
-----------------------------------------------------------------
  URL         : http://localhost:5175
```

---

## Project Structure

```
whyzzle/
├── app.py                  Main web app — FastAPI + Prefab UI (port 5175)
├── mcp_server.py           MCP server — 3 tools for Claude Desktop / agents
├── agent_demo.py           CLI demo — calls all 3 MCP tools from one Python script
│
├── reasoning/              Session-5: Structured reasoning engine
│   ├── __init__.py
│   ├── engine.py           9-stage pipeline orchestrator
│   ├── classifier.py       Keyword-based reasoning type classifier (no LLM call)
│   ├── planner.py          Maps reasoning type to tool execution plan
│   └── verifier.py         7-check heuristic verifier + confidence scorer
│
├── tools/
│   ├── profiles.py         Profile CRUD (data/profiles.json)
│   ├── curiosity_map.py    Knowledge map CRUD + auto-connect + stats
│   ├── search_and_explain.py  Web search + LLM waterfall + visual generation
│   ├── image_gen.py        Educational image generation (Gemini → HF → Pollinations)
│   ├── video_pipeline.py   Video generation (Manim → Blender → CogVideoX)
│   ├── video_manim.py      Manim-based animated explainers
│   ├── blender_scene.py    Blender headless 3D rendering
│   └── video_cogvideo.py   CogVideoX cloud fallback
│
├── helpers/
│   ├── test_reasoning.py   Unit tests: classifier, planner, verifier
│   └── test_api2.py        End-to-end API test showing full reasoning trace
│
├── blender_scripts/        Blender template Python scripts
│
├── data/                   Auto-created on first run — stays local
│   ├── profiles.json
│   └── curiosity_map.json
│
├── output/                 Generated media cache (auto-created, gitignored)
├── .env.example            Copy to .env and fill in your API keys
├── pyproject.toml          Dependencies managed by uv
└── requirements.txt        Equivalent pip requirements list
```

---

## How the Intelligence Loop Works

```
You type a question
       │
       ▼
① reasoning/classifier.py
  → keyword match → reasoning_type (e.g. "comparison", "causal", "educational")
  → no LLM call — instant and deterministic
       │
       ▼
② reasoning/planner.py
  → selects tool execution plan based on reasoning_type
  → e.g. comparison → [web_search, llm_explain, image_gen]
       │
       ▼
③ tools/search_and_explain.py
  → DuckDuckGo search injects web context into prompt
  → Structured prompt with REASONING_TYPE, USER CONTEXT, TASKS, SELF-CHECK
  → LLM waterfall: Groq → Gemini → Ollama → Claude
  → returns explanation + SVG/HTML visual + tags + follow-ups
  → captures prompt_used and llm_response_raw for CoT viewer
       │
       ▼
④ reasoning/verifier.py
  → 7 heuristic checks (has explanation, has visual, has tags, length, etc.)
  → computes confidence score 0–100%
       │
       ▼
⑤ curiosity_map.add_topic
  → saves to curiosity_map.json for this profile
  → stores reasoning_trace alongside the topic
  → auto-connects to related topics by tag overlap (bidirectional)
       │
       ▼
⑥ Dashboard updates
  → main panel: explanation + visual + follow-up chips
  → right sidebar: 9-stage pipeline trace + verification checks + CoT
  → left sidebar: recent list + updated stats
  → graph tab: new node with edges to connected topics
```

---

## LLM Waterfall (free-tier friendly)

All heavy AI work goes through a 4-tier waterfall — the app falls through to the next tier only on rate-limit or failure:

| Tier | Provider | Model | Cost |
|---|---|---|---|
| 1 | Groq | llama-3.3-70b-versatile | Free (rate limited) |
| 2 | Gemini | gemini-2.0-flash | Free (rate limited) |
| 3 | Ollama | local model | Free (requires GPU/CPU locally) |
| 4 | Claude | claude-sonnet-4-6 | Paid (fallback only) |

Image generation follows a similar cascade: Gemini Flash → HuggingFace FLUX → Pollinations (no key required).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web app | FastAPI + Prefab UI |
| MCP server | FastMCP |
| Web search | DuckDuckGo instant API · httpx + BeautifulSoup fallback |
| LLM | Groq (Llama) → Gemini → Ollama → Claude |
| Image gen | Gemini Flash · HuggingFace FLUX · Pollinations.ai |
| Video gen | Manim · Blender (headless) · CogVideoX |
| Data | Plain JSON files — no database required |
| Knowledge graph | vis-network (CDN) |

---

## Data Storage

All data lives in `data/`. Nothing is sent to external servers except the LLM API calls.

**`data/profiles.json`**
```json
{
  "profiles": [
    { "id": "uuid", "name": "Aarav", "age": 7, "avatar_color": "#7B5EA7", "created_at": "2026-05-02" }
  ],
  "active_profile_id": "uuid"
}
```

**`data/curiosity_map.json`** — flat list of topics per profile
```json
[
  {
    "id": "uuid",
    "profile_id": "uuid",
    "question": "Why is the sky blue?",
    "asked_by": "child",
    "date": "2026-05-02",
    "profile_age": 7,
    "explanation": "...",
    "visual_code": "<svg>...</svg>",
    "visual_type": "svg",
    "follow_ups": ["Why is the sunset red?", "What is UV light?", "How do rainbows form?"],
    "tags": ["light", "atmosphere", "physics"],
    "concept_type": "spatial",
    "connected_to": ["topic-id-1"],
    "depth": 1
  }
]
```

---

## Explanation Depth Reference

| Profile age | Style |
|---|---|
| 4 – 6 | 1–2 sentences · one concrete analogy · zero jargon |
| 7 – 10 | 2–3 paragraphs · relatable comparisons · at most one new word |
| 11 – 14 | 2–3 paragraphs · proper terms with brief definitions · cause-and-effect |
| 15 – 17 | 3–4 paragraphs · near-adult depth · formal vocabulary |
| 18 + | Full explanation · no simplification · domain vocabulary free |

---

*Built by Raghu · May 2026*

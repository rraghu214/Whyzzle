# Whyzzle 🔍
### "Ask anything. See everything."
*An AI-powered curiosity coach for kids and parents — turns every question into an instant visual explanation.*

---

## The idea in one paragraph

Kids ask too many questions — and that's a gift. Whyzzle is an MCP-powered agent that takes any question a child (or parent) asks, fetches a real explanation from the web, and instantly generates a **custom visual** (SVG diagram, interactive HTML canvas, or illustrated timeline) tailored to that specific question. Every question is saved to a local **curiosity map** that grows into a personal knowledge graph over time. For deeply spatial concepts (planetary motion, volcanic eruptions), the user can optionally request a **Blender 3D animation**. The result: a tool that makes curiosity feel rewarding, instantaneous, and visually alive.

---

## Assignment constraints (EAG v4 — MCP session)

| Requirement | How Whyzzle satisfies it |
|---|---|
| MCP server with 3+ tools | 4 Python MCP tools (see below) |
| Internet-related tool | `search_and_explain` — fetches real web explanation for every question |
| Local file CRUD | `manage_curiosity_map` — reads/writes `curiosity_map.json` locally |
| Prefab UI | Knowledge graph dashboard + topic detail cards + visual player |
| Agent prompt that uses all tools | Single prompt exercises all 4 tools in sequence |
| YouTube demo | 60-second walkthrough: 3 questions, 3 visual types, graph grows live |

---

## Product name

**Whyzzle** — "Why" + puzzle. Every question unravels a new piece of the world.
Tagline: *"Ask anything. See everything."*

---

## Target users

- **Primary:** Children aged 5–12 who ask frequent questions
- **Secondary:** Parents who want to answer well, not just quickly
- **Tertiary:** Anyone curious — the profile system makes Whyzzle age-agnostic
- **Demo persona:** A family with 2-3 profiles, each with their own curiosity map

---

## Profiles

A profile is a lightweight JSON record that personalises every part of the pipeline — explanation depth, curiosity map segmentation, and UI presence — for any person, any age.

### Profile schema (`profiles.json`)
```json
{
  "profiles": [
    {
      "id": "uuid4",
      "name": "Aarav",
      "age": 7,
      "avatar_color": "#7B5EA7",
      "created_at": "2026-05-02"
    },
    {
      "id": "uuid4",
      "name": "Dad",
      "age": 38,
      "avatar_color": "#2D9CDB",
      "created_at": "2026-05-02"
    }
  ],
  "active_profile_id": "uuid4"
}
```

### Explanation depth by age
| Age range | Explanation style |
|---|---|
| 4–6 | One sentence, concrete analogy, no jargon |
| 7–10 | 2–3 paragraphs, relatable comparisons, gentle vocabulary |
| 11–14 | Slightly technical, introduces proper terms with definitions |
| 15–17 | Near-adult depth, cause-and-effect chains, some abstraction |
| 18+ | Full explanation, no simplification |

The pipeline reads age from the active profile and passes it to Claude — so "Claude simplifies for child's level" is now just one point on a continuous spectrum, not a hardcoded mode.

---

## The core intelligence loop

```
Profile selected → pipeline reads age + profile_id
         │
Child/Parent asks a question
         │
         ▼
1. manage_curiosity_map("get_related", profile_id)
   → finds connected topics for THIS profile already in the map
   → agent says "this links to rainbows you asked about last week"
         │
         ▼
2. search_and_explain(question, profile_id)
   → fetches real web explanation (accuracy)
   → reads age from profile → Claude adjusts explanation depth accordingly
   → Claude generates custom SVG/HTML visual code for THIS question
   → generates 3 follow-up questions
   → tags concept type: spatial | sequential | comparative | mathematical | biological
   → decides visual mode: diagram | interactive | timeline | image_search
         │
         ▼
3. manage_curiosity_map("add_topic", profile_id)
   → saves question, explanation, visual code, tags, connections, profile_id
   → writes to curiosity_map.json (entry keyed under profile_id)
         │
         ▼
4. render_dashboard("topic_detail" + "graph", profile_id)
   → Prefab UI shows: explanation + generated visual + follow-up chips
   → knowledge graph node appears for active profile's map only
   → switching profiles switches the entire graph view
```

---

## MCP Tools (Python)

### Tool 0 — `manage_profiles`
```
Input:
  action: str            — "create" | "read" | "update" | "delete" | "set_active" | "list"
  payload: dict          — depends on action

Actions:
  list          → returns all profiles from profiles.json (id, name, age, avatar_color)
  create        → adds new profile; name + age required; avatar_color auto-assigned if absent
  update        → edits name, age, or avatar_color for an existing profile_id
  delete        → removes profile by id; also removes all curiosity_map entries for that profile_id
  set_active    → sets active_profile_id in profiles.json; pipeline reads this on each request
  read          → returns single profile by id

Output:
  profiles: list[dict]   — current profiles list (after mutation, or full list for list/read)
  active_profile_id: str — currently active profile id
```

### Tool 1 — `search_and_explain`
```
Input:
  question: str          — the curiosity question
  profile_id: str        — active profile id; tool reads age from profiles.json
  asked_by: str          — "child" | "parent" | "both"  (kept for color-coding in graph)

Process:
  1. Resolve age from profiles.json using profile_id
  2. Web search for accurate explanation
  3. Fetch top result page content
  4. Claude synthesizes explanation calibrated to profile age (see depth table above)
  5. Claude generates custom SVG or HTML visual code
  6. Claude generates 3 follow-up questions
  7. Claude tags concept type and visual mode

Output:
  explanation: str        — explanation text (depth matched to profile age)
  visual_code: str        — raw SVG or HTML string to render
  visual_type: str        — "svg" | "html_interactive"
  follow_ups: list[str]   — 3 deeper questions
  tags: list[str]         — concept tags e.g. ["space", "light", "physics"]
  concept_type: str       — "spatial" | "sequential" | "comparative" | "mathematical" | "biological"
  related_search: str     — suggested image search if real photo needed
```

### Tool 2 — `manage_curiosity_map`
```
Input:
  action: str            — "read" | "add_topic" | "get_related" | "get_stats" | "update_connections"
  profile_id: str        — all actions are scoped to this profile; required
  payload: dict          — depends on action

Actions:
  read          → returns curiosity_map entries for this profile_id only
  add_topic     → appends new topic entry (tagged with profile_id), auto-connects by tag overlap within same profile
  get_related   → given a question/tags, returns topics sharing tags for this profile_id
  get_stats     → total topics, most explored branch, current streak, unique tags — for this profile
  update_connections → re-draw edges between topics within this profile's entries

Topic schema in curiosity_map.json:
{
  "id": "uuid4",
  "profile_id": "uuid4",
  "question": "Why do stars twinkle?",
  "asked_by": "child",
  "date": "2026-05-02",
  "profile_age": 7,
  "explanation": "...",
  "visual_code": "<svg>...</svg>",
  "visual_type": "svg",
  "follow_ups": ["...", "...", "..."],
  "tags": ["light", "atmosphere", "stars", "space"],
  "concept_type": "spatial",
  "connected_to": ["topic_id_abc", "topic_id_xyz"],
  "depth": 1
}

Storage structure:
  curiosity_map.json holds a flat list of topics.
  All reads/writes filter by profile_id — profiles never see each other's maps.
```

### Tool 3 — `render_dashboard`
```
Input:
  view: str              — "topic_detail" | "graph" | "recent" | "stats" | "visual_fullscreen"
  payload: dict          — data to render

Views:
  topic_detail    → shows explanation + generated visual + follow-up chips (scoped to active profile)
  graph           → full knowledge graph for active profile (nodes + edges)
  recent          → last 5 questions for active profile as cards
  stats           → streak, total topics, most explored branch — for active profile
  visual_fullscreen → plays visual at full panel width
  profile_select  → renders the profile strip in sidebar (all profiles + active indicator + +/- controls)
```

### Tool 4 — `generate_3d_scene` *(optional, on user request only)*
```
Input:
  topic: str             — e.g. "planetary orbits"
  concept_type: str      — "orbit" | "structure" | "force" | "cross_section" | "scale"
  parameters: dict       — topic-specific params (planet names, sizes, etc.)

Process:
  1. Selects matching Blender Python script template
  2. Fills in parameters
  3. Runs Blender headlessly (blender --background --python script.py)
  4. Renders 10-second EEVEE animation → saves to /output/scene.mp4

Output:
  video_path: str        — local path to rendered .mp4
  duration: int          — seconds
```

---

## Visual generation strategy

Claude generates visuals **on the fly** for every question — no pre-built templates needed.

| Question type | Visual Claude generates |
|---|---|
| "Why is the sky blue?" | SVG — light rays hitting atmosphere, scattering illustrated |
| "What is differentiation?" | Interactive HTML canvas — draggable point on curve, live tangent line + slope |
| "What is integration?" | Interactive HTML — area under curve fills as you drag |
| "How does a seed grow?" | SVG timeline — seed → roots → sprout → sapling → tree |
| "Why do we live on Earth?" | SVG comparison strip — all planets, Earth highlighted in goldilocks zone |
| "How do planets rotate?" | SVG orbital animation (CSS) — or Blender on request |
| "Why is milk white?" | SVG — light scattering off fat globules |
| "What is 6 × 7?" | SVG — animated dot grid, 6 rows × 7 columns |
| "How does a volcano erupt?" | SVG cross-section — or Blender on request |

**Fallback:** If the question needs a real photograph (rare plant, specific animal), the agent uses image search and renders a photo card instead.

---

## Visual mode decision logic

```
Any question →
  ├── Has clear structural/conceptual visual → Generate SVG/HTML (90% of cases)
  ├── Needs real photograph → Image search fallback
  └── Needs 3D motion/depth → Suggest Blender ("Want to see this in 3D?")
                                → Only generate if user confirms
```

---

## Prefab UI — screens

### Main layout
```
┌──────────────┬─────────────────────────────────────┐
│   SIDEBAR    │         MAIN PANEL                  │
│              │                                     │
│ Profiles     │  Active view (see below)            │
│ ●Aarav  ○Dad │                                     │
│   [+]        │                                     │
│              │                                     │
│ [Ask box]    │                                     │
│              │                                     │
│ Recent       │                                     │
│ • Stars...   │                                     │
│ • Mango...   │                                     │
│ • Earth...   │                                     │
│              │                                     │
│ Knowledge    │                                     │
│ Graph (mini) │                                     │
│              │                                     │
│ Stats        │                                     │
│ 23 questions │                                     │
│ 4-day streak │                                     │
└──────────────┴─────────────────────────────────────┘
```
All sidebar content (recent, graph, stats) reflects the **active profile** only.

### View 0 — Profile strip (top of sidebar, always visible)
- Row of avatar chips (colored circle + first name), one per profile
- Active profile is highlighted with a ring
- Clicking a chip switches the active profile → entire sidebar + main panel re-renders for that profile's map
- `+` button at end of row → opens "New profile" inline form (name + age, avatar color auto-picked)
- `-` button on any non-active chip → confirms deletion (removes profile + all its curiosity_map entries)

### View 1 — Topic detail (default after a question)
- Big friendly question heading
- Explanation text (depth matched to active profile's age — see depth table)
- Generated visual (SVG inline or HTML iframe)
- 3 follow-up question chips (clickable → asks that question)
- "Show me in 3D" button (triggers Blender tool)
- Connected topics strip at bottom (from active profile's map only)

### View 2 — Knowledge graph
- Nodes = topics for the **active profile only** (circle, labelled with short question)
- Node color: purple = child asked, teal = parent asked, coral = both
- Node size: proportional to number of connections
- Edges: lines between connected topics
- Click node → switches to topic detail view
- Animates when new node is added
- Switches instantly when active profile changes

### View 3 — Stats
- All stats scoped to the active profile
- Total questions asked
- Current daily streak
- Most explored branch (e.g. "Space — 8 questions")
- Questions this week (sparkline)
- Top tags cloud

---

## Demo script (60 seconds)

**Setup:** Claude Desktop open, Whyzzle MCP server running, Prefab dashboard open in browser.

**Question 1** (parent asks):
> "Why do we live on Earth and not Mars?"

Agent: searches web → generates SVG comparison of Earth vs Mars → saves to map → graph shows first node.

**Question 2** (child asks):
> "How do all the planets rotate together?"

Agent: finds "Earth", "space" already in map → generates orbital SVG animation → connects to Q1 node → graph now has 2 connected nodes.

**Question 3** (together):
> "How does a mango seed grow into a tree?"

Agent: different domain (biology) → generates SVG growth timeline → new node, new branch in graph.

**Zoom out:** Show knowledge graph — 3 nodes, 2 connections, two branches (space + biology). The map is alive.

**Optional closer:** Ask "Show me the planets in 3D" → Blender animation plays.

---

## Tech stack

| Layer | Technology |
|---|---|
| MCP Server | Python 3.10+, `mcp` SDK, `httpx`, `beautifulsoup4` |
| Web fetch | `httpx` + `beautifulsoup4` for scraping |
| Local storage | JSON file (`curiosity_map.json`) in project root |
| Visual generation | Claude API (claude-sonnet-4-20250514) generates SVG/HTML |
| Prefab UI | Prefab (web app or Chrome extension) |
| 3D (optional) | Blender 3.x with Python scripting, EEVEE renderer |
| MCP Client | Claude Desktop |

---

## File structure

```
whyzzle/
├── WHYZZLE.md                  ← this file (paste at start of every Claude Code session)
├── server.py                   ← MCP server entry point
├── tools/
│   ├── profiles.py             ← Tool 0: profile CRUD + set_active
│   ├── search_and_explain.py   ← Tool 1
│   ├── curiosity_map.py        ← Tool 2
│   ├── render_dashboard.py     ← Tool 3
│   └── blender_scene.py        ← Tool 4 (optional)
├── blender_scripts/
│   ├── orbit.py                ← planetary orbit template
│   ├── cross_section.py        ← volcano / earth interior template
│   └── growth.py               ← plant growth template
├── data/
│   ├── profiles.json           ← profile store (auto-created, includes active_profile_id)
│   └── curiosity_map.json      ← local knowledge store (auto-created, entries tagged with profile_id)
├── output/                     ← rendered Blender animations saved here
├── prefab/                     ← Prefab UI config and components
└── requirements.txt
```

---

## Build order (tackle in this sequence)

- [ ] **Step 1:** Scaffold `server.py` with 5 tool stubs (including `manage_profiles`), confirm Claude Desktop sees the server
- [ ] **Step 2:** Build `profiles.py` — create/read/update/delete/set_active, auto-init `profiles.json` with a default profile on first run
- [ ] **Step 3:** Build `curiosity_map.py` — full CRUD scoped by profile_id, auto-connection logic, stats
- [ ] **Step 4:** Build `search_and_explain.py` — web fetch + age-aware Claude summarization + visual generation
- [ ] **Step 5:** Wire Steps 2+3+4, test end-to-end with Claude Desktop (no UI yet); test switching profiles
- [ ] **Step 6:** Build Prefab UI — profile strip (avatar chips + +/- controls) + topic detail view + visual renderer
- [ ] **Step 7:** Build knowledge graph view in Prefab (scoped to active profile)
- [ ] **Step 8:** Connect `render_dashboard` tool to Prefab
- [ ] **Step 9:** Full end-to-end demo dry run (2+ profiles, show maps are separate)
- [ ] **Step 10 (bonus):** Blender tool + 2-3 script templates
- [ ] **Step 11:** Record YouTube demo + write LinkedIn post

---

## How to start each Claude Code session

Paste this at the top of your first message in Claude Code:

```
I'm building Whyzzle — an MCP-powered curiosity coach for kids.
Full spec is in WHYZZLE.md in the project root. Please read it first.
Today's goal: [INSERT CURRENT STEP FROM BUILD ORDER ABOVE]
```

---

## Key design principles (don't lose these)

1. **Visual first** — every question gets a visual, not just text
2. **Domain agnostic** — no hardcoded topic list; Claude generates the right visual for any question
3. **Memory matters** — the curiosity map makes every session smarter than the last
4. **Age-adaptive language** — explanation depth is set by the profile's age, not a hardcoded "kids mode"; the primary audience is still children but the system works for any age
5. **Profile-scoped maps** — each person's curiosity map is their own; profiles never bleed into each other
6. **Parent + child together** — the tool serves both; `asked_by` still tracks who asked; switching profiles switches the whole context
7. **Blender is a bonus** — the core product works beautifully without it

---

## Competitive landscape — does this already exist?

**Short answer: pieces exist, but Whyzzle as a whole doesn't.**

### What already exists (the individual pieces)

| What exists | Product | Gap vs Whyzzle |
|---|---|---|
| Kids Q&A with AI | ChatGPT, Socratic, TeachBetter.ai | Text answers only, no generated visuals, no memory across sessions |
| AI visual generation from text | Napkin.ai | Not for kids, not question-driven, no knowledge graph, no MCP |
| Knowledge graphs from documents | Taskade, Graphiti, ai-knowledge-graph (GitHub) | Built from documents, not from a child's questions; no visual generation |
| Multimodal AI education | Coursera, Virtual Anatomy | Institutional, pre-built content — not generative per question |
| Curiosity-driven AI research | Inria Flowers team | Academic research only, not a consumer product |

### What doesn't exist anywhere

The specific combination that makes Whyzzle original:

1. **Question → instant custom-generated visual** (SVG/HTML, not a stock image or pre-built template) for *any* domain
2. **Personal curiosity map** that grows from a specific child's questions over time — not from documents
3. **Cross-session memory** that connects "stars twinkle" to "rainbows" the kid asked last Tuesday
4. **Parent + child together** as a shared learning unit, tracked separately
5. **MCP-native** — the whole thing orchestrated by an AI agent, not a traditional app

No product combines all five. That's the whitespace Whyzzle occupies.

### Why this matters for the demo

The judges aren't checking Product Hunt for prior art — they're watching a 60-second demo. A knowledge graph growing live, with a custom visual appearing instantly for any question asked, will look like nothing else in the room. Originality of execution beats originality of concept every time.

---

*Last updated: 2026-05-02 (profiles expansion) | EAG v4 Assignment | Built by Raghu*

"""
Whyzzle — Prefab web app
========================
Run:  uv run uvicorn app:fastapi_app --reload --port 5175
"""

import asyncio
import logging
import sys
from pathlib import Path
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge, Button, Card, CardContent, CardHeader, CardTitle,
    Column, Combobox, ComboboxOption, Embed, ForEach,
    H2, H3, If, Else, Input, ITEM, Loader, Markdown, Mermaid,
    Metric, Muted, Page, Pages, Row,
    Separator, Small, Svg, Text, Textarea, Video, Rx, RESULT,
)
from prefab_ui.actions import AppendState, Fetch, SetState, ShowToast

from tools.curiosity_map import manage_curiosity_map
from tools.profiles import manage_profiles
from tools.video_pipeline import generate_video
from reasoning.engine import run_reasoning_pipeline

# ── FastAPI app ───────────────────────────────────────────────────────────────

fastapi_app = FastAPI()

_OUTPUT_DIR = Path(__file__).parent / "output"
_OUTPUT_DIR.mkdir(exist_ok=True)
fastapi_app.mount("/output", StaticFiles(directory=str(_OUTPUT_DIR)), name="output")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_mermaid(topics: list) -> str:
    if not topics:
        return ""
    id_map = {t["id"]: t["question"][:30].replace('"', "'") for t in topics}
    edges, seen = [], set()
    for t in topics:
        for cid in t.get("connected_to", []):
            pair = tuple(sorted([t["id"], cid]))
            if pair not in seen and cid in id_map:
                shared = set(t.get("tags", [])) & set(
                    next((x.get("tags", []) for x in topics if x["id"] == cid), [])
                )
                label = list(shared)[0] if shared else ""
                edges.append(
                    f'  {t["id"][:8]}["{id_map[t["id"]]}"] -- {label} --> '
                    f'{cid[:8]}["{id_map[cid]}"]'
                )
                seen.add(pair)
    if not edges:
        lines = [f'  {t["id"][:8]}["{id_map[t["id"]]}"]' for t in topics[:8]]
        return "graph LR\n" + "\n".join(lines)
    return "graph LR\n" + "\n".join(edges)


# ── Initial state — load real data synchronously so Select has options ────────

def _load_init_state() -> dict:
    profiles_data = manage_profiles("list")
    profiles = profiles_data.get("profiles", [])
    active_id = profiles_data.get("active_profile_id") or (
        profiles[0]["id"] if profiles else ""
    )
    topics = (
        manage_curiosity_map("read", active_id).get("topics", [])
        if active_id else []
    )
    stats = (
        manage_curiosity_map("get_stats", active_id)
        if active_id
        else {"total": 0, "streak": 0, "this_week": 0, "top_tags": [], "top_branch": None}
    )
    topics_sorted = sorted(topics, key=lambda t: t.get("date", ""), reverse=True)
    active_name = next((p["name"] for p in profiles if p["id"] == active_id), "")
    return {
        "profiles":            profiles,
        "active_profile_id":   active_id,
        "active_profile_name": active_name,
        "show_create_profile": False,
        "new_name":            "",
        "new_age":             "",
        "topics":              topics_sorted,
        "current_topic":       None,
        "question":            "",
        "asking":              False,
        "page":                "home",
        "stats":               stats,
        "graph_chart":         _build_mermaid(topics),
        "video_url":           "",
        "rendering_3d":        False,
        "render_error":        "",
        "selected_topic_id":   "",
        "show_cot":            False,
        "show_raw_prompt":     False,
    }


INIT_STATE = _load_init_state()

# ── Build Prefab UI ───────────────────────────────────────────────────────────

with PrefabApp(
    title="Whyzzle — Curiosity Map",
    state=INIT_STATE,
    css_class="min-h-screen bg-gradient-to-br from-purple-50 via-white to-teal-50",
) as _prefab:

    with Row(
        on_mount=Fetch.get(
            "/api/init",
            on_success=[
                SetState("profiles",            RESULT["profiles"]),
                SetState("active_profile_id",   RESULT["active_profile_id"]),
                SetState("active_profile_name", RESULT["active_profile_name"]),
                SetState("topics",              RESULT["topics"]),
                SetState("stats",               RESULT["stats"]),
                SetState("graph_chart",         RESULT["graph_chart"]),
            ],
        ),
    ):

        # ══════════════════════════════════════════════════════════════════════
        # SIDEBAR
        # ══════════════════════════════════════════════════════════════════════
        with Column(
            css_class=(
                "w-72 shrink-0 min-h-screen border-r border-purple-100 "
                "bg-white/80 backdrop-blur flex flex-col p-4 gap-3 shadow-sm"
            )
        ):
            H2("🧠 Whyzzle",
               css_class="text-purple-700 font-extrabold text-2xl tracking-tight")
            Muted("Your personal curiosity map ✨")

            Separator(css_class="border-purple-100")

            # ── Profile card ─────────────────────────────────────────────────
            with Card(css_class="border-purple-100 bg-purple-50/50"):
                with CardHeader(css_class="pb-2"):
                    with Row(css_class="items-center justify-between"):
                        CardTitle("👧 Profile")
                        Button(
                            "+ New Kid",
                            variant="outline",
                            size="xs",
                            css_class="text-purple-600 border-purple-300 hover:bg-purple-100",
                            on_click=SetState("show_create_profile", True),
                        )
                with CardContent(css_class="pt-0 flex flex-col gap-2"):
                    with Row(css_class="items-center gap-2 px-1 py-1"):
                        Text("👤", css_class="text-purple-500 text-sm")
                        Text(
                            Rx("active_profile_name"),
                            css_class="font-semibold text-purple-700 text-sm",
                        )
                    with ForEach("profiles"):
                        with Row(css_class="items-center gap-1"):
                            Button(
                                ITEM["name"],
                                variant="ghost",
                                size="sm",
                                css_class=(
                                    "flex-1 justify-start text-left text-xs "
                                    "hover:bg-purple-100 hover:text-purple-700 rounded-lg"
                                ),
                                on_click=Fetch.post(
                                    "/api/activate-profile",
                                    body={"profile_id": ITEM["id"]},
                                    on_success=[
                                        SetState("active_profile_id",   RESULT["active_profile_id"]),
                                        SetState("active_profile_name", RESULT["active_profile_name"]),
                                        SetState("topics",              RESULT["topics"]),
                                        SetState("stats",               RESULT["stats"]),
                                        SetState("graph_chart",         RESULT["graph_chart"]),
                                        SetState("current_topic",       None),
                                        SetState("video_url",           ""),
                                        SetState("page",                "home"),
                                    ],
                                ),
                            )
                            Button(
                                "🗑️",
                                variant="ghost",
                                size="sm",
                                css_class=(
                                    "text-red-400 hover:text-red-600 "
                                    "hover:bg-red-50 rounded-lg px-1.5"
                                ),
                                on_click=Fetch.post(
                                    "/api/profiles/delete",
                                    body={"profile_id": ITEM["id"]},
                                    on_success=[
                                        SetState("profiles",            RESULT["profiles"]),
                                        SetState("active_profile_id",   RESULT["active_profile_id"]),
                                        SetState("active_profile_name", RESULT["active_profile_name"]),
                                        SetState("topics",              RESULT["topics"]),
                                        SetState("stats",               RESULT["stats"]),
                                        SetState("graph_chart",         RESULT["graph_chart"]),
                                        SetState("current_topic",       None),
                                        SetState("video_url",           ""),
                                        SetState("page",                "home"),
                                    ],
                                    on_error=[
                                        ShowToast(
                                            "Cannot delete the last profile",
                                            variant="error",
                                        ),
                                    ],
                                ),
                            )

                    with If("show_create_profile"):
                        Separator(css_class="border-dashed border-purple-200 my-1")
                        Input(
                            name="new_name",
                            placeholder="Child's name 🌟",
                            css_class="border-purple-200",
                        )
                        Input(
                            name="new_age",
                            placeholder="Age 🎂",
                            css_class="border-purple-200 mt-1",
                        )
                        with Row(css_class="gap-2 mt-2"):
                            Button(
                                "Create ✅",
                                size="sm",
                                css_class="bg-purple-600 text-white flex-1",
                                on_click=Fetch.post(
                                    "/api/profiles",
                                    body={
                                        "name": "{{ new_name }}",
                                        "age":  "{{ new_age }}",
                                    },
                                    on_success=[
                                        SetState("profiles",            RESULT["profiles"]),
                                        SetState("active_profile_id",   RESULT["active_profile_id"]),
                                        SetState("active_profile_name", RESULT["active_profile_name"]),
                                        SetState("show_create_profile", False),
                                        SetState("new_name", ""),
                                        SetState("new_age",  ""),
                                        ShowToast("Profile created! 🎉", variant="success"),
                                    ],
                                    on_error=[
                                        ShowToast(
                                            "Could not create profile — check name and age",
                                            variant="error",
                                        ),
                                    ],
                                ),
                            )
                            Button(
                                "Cancel",
                                variant="ghost",
                                size="sm",
                                css_class="flex-1",
                                on_click=SetState("show_create_profile", False),
                            )

            Separator(css_class="border-purple-100")

            # ── Ask form ─────────────────────────────────────────────────────
            with Card(css_class="border-teal-100 bg-teal-50/40"):
                with CardHeader(css_class="pb-2"):
                    CardTitle("🔍 Ask a Question")
                with CardContent(css_class="flex flex-col gap-3 pt-0"):
                    Textarea(
                        name="question",
                        placeholder="What do you wonder about? 🌍🚀🦕",
                        rows=3,
                        css_class="border-teal-200 rounded-xl resize-none",
                    )
                    Button(
                        "Ask Whyzzle ✨",
                        disabled=Rx("asking"),
                        css_class=(
                            "w-full bg-gradient-to-r from-purple-600 to-teal-500 "
                            "hover:from-purple-700 hover:to-teal-600 "
                            "text-white font-bold rounded-xl shadow-md"
                        ),
                        on_click=[
                            SetState("asking",       True),
                            SetState("render_error", ""),
                            SetState("video_url",    ""),
                            Fetch.post(
                                "/api/ask",
                                body={
                                    "question":   "{{ question }}",
                                    "asked_by":   "child",
                                    "profile_id": "{{ active_profile_id }}",
                                },
                                on_success=[
                                    SetState("asking",        False),
                                    SetState("current_topic", RESULT["topic"]),
                                    SetState("page",          "topic"),
                                    AppendState("topics", RESULT["topic"], index=0),
                                ],
                                on_error=[
                                    SetState("asking", False),
                                    ShowToast(
                                        "Something went wrong — check the server log",
                                        variant="error",
                                    ),
                                ],
                            ),
                        ],
                    )
                    with If("asking"):
                        with Row(css_class="items-center gap-2"):
                            Loader()
                            Muted("Researching your question…")

            Separator(css_class="border-purple-100")

            # ── Navigation ───────────────────────────────────────────────────
            with Row(css_class="gap-1 flex-wrap"):
                Button(
                    "🏠 Home", variant="ghost", size="sm",
                    css_class="hover:bg-purple-100 hover:text-purple-700",
                    on_click=SetState("page", "home"),
                )
                Button(
                    "🌐 Graph", variant="ghost", size="sm",
                    css_class="hover:bg-teal-100 hover:text-teal-700",
                    on_click=SetState("page", "graph"),
                )
                Button(
                    "📊 Stats", variant="ghost", size="sm",
                    css_class="hover:bg-orange-100 hover:text-orange-700",
                    on_click=SetState("page", "stats"),
                )

            Separator(css_class="border-purple-100")

            H3("📚 Recent Topics",
               css_class="font-bold text-sm text-purple-700")
            with Card(css_class="overflow-hidden border-purple-100"):
                with CardContent(
                    css_class="flex flex-col gap-0.5 p-2 max-h-60 overflow-y-auto"
                ):
                    with If("topics"):
                        with ForEach("topics"):
                            Button(
                                ITEM["question"],
                                variant="ghost",
                                size="sm",
                                css_class=(
                                    "justify-start h-auto py-1.5 text-left "
                                    "text-xs w-full hover:bg-purple-50 "
                                    "hover:text-purple-700 rounded-lg"
                                ),
                                on_click=[
                                    SetState("current_topic", ITEM),
                                    SetState("video_url",    ""),
                                    SetState("render_error", ""),
                                    SetState("page",         "topic"),
                                ],
                            )
                    with Else():
                        Muted("Ask your first question! 🌱")

        # ══════════════════════════════════════════════════════════════════════
        # MAIN CONTENT
        # ══════════════════════════════════════════════════════════════════════
        with Column(css_class="flex-1 p-6 overflow-y-auto"):
            with Pages(name="page"):

                # ── HOME ─────────────────────────────────────────────────────
                with Page(value="home", title="Home"):
                    H2("Welcome to Whyzzle! 🌟",
                       css_class="text-3xl font-extrabold text-purple-700 mb-1")
                    Muted(
                        "Every question you ask becomes a node in your "
                        "personal knowledge graph. What are you curious about today?"
                    )
                    Separator(css_class="my-4 border-purple-100")

                    with Row(css_class="gap-4 flex-wrap mb-6"):
                        with Card(css_class="flex-1 min-w-32 border-purple-100 bg-purple-50/50"):
                            with CardContent(css_class="pt-4"):
                                Metric(label="🧩 Topics Explored",
                                       value=Rx("stats.total"))
                        with Card(css_class="flex-1 min-w-32 border-orange-100 bg-orange-50/50"):
                            with CardContent(css_class="pt-4"):
                                Metric(label="🔥 Day Streak",
                                       value=Rx("stats.streak"),
                                       description="consecutive days")
                        with Card(css_class="flex-1 min-w-32 border-teal-100 bg-teal-50/50"):
                            with CardContent(css_class="pt-4"):
                                Metric(label="⚡ This Week",
                                       value=Rx("stats.this_week"),
                                       description="new topics")

                    with If("stats.top_tags"):
                        H3("🌈 Your Curiosity Themes",
                           css_class="font-bold text-purple-700 mb-3")
                        with Row(css_class="flex-wrap gap-2 mb-4"):
                            with ForEach("stats.top_tags"):
                                Badge(
                                    ITEM["tag"],
                                    css_class="bg-purple-100 text-purple-700 border-purple-200",
                                )

                    with If(Rx("stats.total") == 0):
                        Separator(css_class="my-6 border-purple-100")
                        with Row(css_class="gap-4 flex-wrap"):
                            with Card(css_class="flex-1 min-w-48 border-yellow-200 bg-yellow-50"):
                                with CardContent(css_class="pt-4"):
                                    H3("🦕 Try asking:",
                                       css_class="font-bold text-yellow-800 mb-2")
                                    Muted('"Why is the sky blue?"')
                            with Card(css_class="flex-1 min-w-48 border-teal-200 bg-teal-50"):
                                with CardContent(css_class="pt-4"):
                                    H3("🚀 Or maybe:",
                                       css_class="font-bold text-teal-800 mb-2")
                                    Muted('"How do black holes form?"')
                            with Card(css_class="flex-1 min-w-48 border-pink-200 bg-pink-50"):
                                with CardContent(css_class="pt-4"):
                                    H3("🌊 Or even:",
                                       css_class="font-bold text-pink-800 mb-2")
                                    Muted('"Why do volcanoes erupt?"')

                # ── TOPIC ────────────────────────────────────────────────────
                with Page(value="topic", title="Topic"):
                    with If("current_topic"):
                        H2(Rx("current_topic.question"),
                           css_class="text-2xl font-extrabold text-purple-700 mb-4")

                        with Card(css_class="mb-4 border-purple-100 overflow-hidden"):
                            with CardContent(css_class="p-0"):
                                with If(
                                    Rx("current_topic.visual_type") == "html_interactive"
                                ):
                                    Embed(
                                        html="{{ current_topic.visual_code }}",
                                        height="460px",
                                        sandbox="allow-scripts allow-same-origin",
                                        css_class="w-full",
                                    )
                                with Else():
                                    Svg(
                                        content="{{ current_topic.visual_code }}",
                                        css_class="w-full p-4",
                                    )

                        with Card(css_class="mb-4 border-teal-100 bg-teal-50/30"):
                            with CardHeader(css_class="pb-2"):
                                CardTitle("📖 Explanation")
                            with CardContent():
                                Markdown(content=Rx("current_topic.explanation"))

                        with If("current_topic.tags"):
                            with Row(css_class="flex-wrap gap-2 mb-4"):
                                with ForEach("current_topic.tags"):
                                    Badge(
                                        ITEM,
                                        css_class="bg-teal-100 text-teal-700 border-teal-200",
                                    )

                        Separator(css_class="my-4 border-purple-100")
                        H3("🎬 3D Animation",
                           css_class="font-bold text-purple-700 mb-2")
                        Muted(
                            "Tries Manim → Blender → CogVideoX in order.",
                            css_class="mb-3 text-xs",
                        )
                        with If(Rx("video_url") == ""):
                            with If(Rx("rendering_3d") == False):
                                Button(
                                    "🌀 Render 3D Scene",
                                    variant="outline",
                                    css_class=(
                                        "border-purple-300 text-purple-700 "
                                        "hover:bg-purple-100 font-semibold"
                                    ),
                                    on_click=[
                                        SetState("rendering_3d", True),
                                        SetState("render_error", ""),
                                        Fetch.post(
                                            "/api/render-3d",
                                            body={
                                                "topic":        "{{ current_topic.question }}",
                                                "concept_type": "{{ current_topic.concept_type }}",
                                            },
                                            on_success=[
                                                SetState("rendering_3d", False),
                                                SetState("video_url",    RESULT["video_url"]),
                                                SetState("render_error", RESULT["error"]),
                                            ],
                                            on_error=[
                                                SetState("rendering_3d", False),
                                                SetState("render_error", "Render failed — check server logs"),
                                                ShowToast("3D render failed", variant="error"),
                                            ],
                                        ),
                                    ],
                                )
                            with Else():
                                with Row(css_class="items-center gap-3"):
                                    Loader()
                                    Muted("Rendering… (~2 min) 🎨")
                        with Else():
                            Video(
                                src="{{ video_url }}",
                                controls=True,
                                css_class="w-full rounded-xl shadow-lg mt-2",
                            )
                        with If("render_error"):
                            Badge(
                                Rx("render_error"),
                                css_class="bg-red-100 text-red-700 border-red-200 mt-2",
                            )

                        with If("current_topic.follow_ups"):
                            Separator(css_class="my-4 border-teal-100")
                            H3("🔗 Explore Further",
                               css_class="font-bold text-teal-700 mb-2")
                            with Row(css_class="flex-wrap gap-2"):
                                with ForEach("current_topic.follow_ups"):
                                    Button(
                                        ITEM,
                                        variant="outline",
                                        size="sm",
                                        css_class=(
                                            "border-teal-200 text-teal-700 "
                                            "hover:bg-teal-100"
                                        ),
                                        on_click=[
                                            SetState("question", ITEM),
                                            SetState("page",     "home"),
                                        ],
                                    )

                    with Else():
                        with Card(css_class="border-dashed border-purple-200 bg-purple-50/40 mt-8"):
                            with CardContent(
                                css_class="py-16 flex flex-col items-center gap-3"
                            ):
                                H2("🤔", css_class="text-6xl")
                                Muted(
                                    "Select a topic from the sidebar "
                                    "or ask a new question!"
                                )

                # ── GRAPH ────────────────────────────────────────────────────
                with Page(value="graph", title="Knowledge Graph"):
                    H2("🌐 Your Curiosity Map",
                       css_class="text-2xl font-extrabold text-purple-700 mb-1")
                    Muted("Topics connected by shared themes.")
                    Separator(css_class="my-3 border-purple-100")

                    with Card(css_class="mb-4 border-purple-100 bg-purple-50/30"):
                        with CardContent(css_class="pt-4"):
                            H3("🔍 Jump to Topic",
                               css_class="font-bold text-purple-700 mb-2")
                            with Combobox(
                                name="selected_topic_id",
                                placeholder="Search your topics…",
                                on_change=SetState("page", "topic"),
                            ):
                                with ForEach("topics"):
                                    ComboboxOption(
                                        ITEM["question"],
                                        value=ITEM["id"],
                                    )

                    with Card(css_class="border-purple-100"):
                        with CardContent(css_class="p-4"):
                            with If("graph_chart"):
                                Mermaid(chart=Rx("graph_chart"))
                            with Else():
                                with Column(css_class="items-center py-12 gap-3"):
                                    H2("🌐", css_class="text-5xl")
                                    Muted(
                                        "Ask some questions to grow "
                                        "your curiosity map!"
                                    )

                # ── STATS ────────────────────────────────────────────────────
                with Page(value="stats", title="Stats"):
                    H2("📊 Your Curiosity Stats",
                       css_class="text-2xl font-extrabold text-purple-700 mb-4")

                    with Row(css_class="gap-4 flex-wrap mb-6"):
                        with Card(css_class="flex-1 min-w-32 border-purple-100 bg-purple-50/50"):
                            with CardContent(css_class="pt-4"):
                                Metric(label="🧩 Total Topics",
                                       value=Rx("stats.total"))
                        with Card(css_class="flex-1 min-w-32 border-orange-100 bg-orange-50/50"):
                            with CardContent(css_class="pt-4"):
                                Metric(label="🔥 Day Streak",
                                       value=Rx("stats.streak"),
                                       description="days in a row")
                        with Card(css_class="flex-1 min-w-32 border-teal-100 bg-teal-50/50"):
                            with CardContent(css_class="pt-4"):
                                Metric(label="⚡ This Week",
                                       value=Rx("stats.this_week"),
                                       description="new topics")

                    with If("stats.top_branch"):
                        with Card(css_class="mb-4 border-yellow-200 bg-yellow-50"):
                            with CardHeader():
                                CardTitle("🌟 Top Knowledge Branch")
                            with CardContent():
                                Text(
                                    Rx("stats.top_branch"),
                                    bold=True,
                                    css_class="text-yellow-800",
                                )

                    with If("stats.top_tags"):
                        H3("🏷️ All Tags",
                           css_class="font-bold text-purple-700 mb-3")
                        with Row(css_class="flex-wrap gap-2"):
                            with ForEach("stats.top_tags"):
                                Badge(
                                    ITEM["tag"],
                                    css_class="bg-purple-100 text-purple-700 border-purple-200",
                                )

        # ══════════════════════════════════════════════════════════════════════
        # RIGHT SIDEBAR — Live Reasoning Panel
        # ══════════════════════════════════════════════════════════════════════
        with Column(
            css_class=(
                "wz-rsidebar w-72 shrink-0 min-h-screen border-l border-purple-100 "
                "bg-white/70 backdrop-blur flex flex-col shadow-sm"
            )
        ):
            with Column(
                css_class=(
                    "p-4 gap-2 flex flex-col overflow-y-auto "
                    "sticky top-0 max-h-screen"
                )
            ):
                # ── Header ────────────────────────────────────────────────────
                with Row(css_class="items-center gap-2 mb-1"):
                    H3("🧠 Reasoning",
                       css_class="font-extrabold text-purple-700 text-base tracking-tight")
                Separator(css_class="border-purple-100")

                # ── While asking: animated placeholder stages ─────────────────
                with If("asking"):
                    Muted("Thinking step by step…",
                          css_class="text-xs mb-2 italic text-purple-500")
                    _LOADING_STAGES = [
                        "Understanding Query",
                        "Classifying Reasoning",
                        "Creating Execution Plan",
                        "Selecting Tools",
                        "Gathering Information",
                        "Verifying Results",
                        "Generating Response",
                        "Self-Check",
                        "Assembling Response",
                    ]
                    for _sn in _LOADING_STAGES:
                        with Row(css_class="items-center gap-2 py-1"):
                            Loader()
                            Text(_sn, css_class="text-xs text-slate-500")

                # ── Trace panel (shown when a topic with trace is active) ──────
                with If("current_topic.reasoning_trace"):
                    # Type + confidence badges
                    with Row(css_class="flex-wrap gap-1.5 mb-1 mt-1"):
                        Badge(
                            Rx("current_topic.reasoning_trace.reasoning_type"),
                            css_class=(
                                "bg-purple-100 text-purple-700 "
                                "border-purple-200 capitalize text-xs"
                            ),
                        )
                        Badge(
                            Rx("current_topic.reasoning_trace.confidence_pct"),
                            css_class="bg-teal-100 text-teal-700 border-teal-200 text-xs",
                        )
                    Muted(
                        Rx("current_topic.reasoning_trace.reasoning_desc"),
                        css_class="text-xs italic mb-2",
                    )

                    # Pipeline stages ─────────────────────────────────────────
                    Small("PIPELINE",
                          css_class="font-bold text-purple-500 tracking-widest text-xs")
                    with ForEach("current_topic.reasoning_trace.pipeline_stages"):
                        with Row(css_class=(
                            "items-start gap-1.5 py-1 "
                            "border-b border-purple-50 last:border-0"
                        )):
                            Text(content=ITEM["status_icon"],
                                 css_class="text-xs shrink-0 mt-0.5")
                            with Column(css_class="gap-0 min-w-0"):
                                Text(content=ITEM["name"],
                                     css_class="text-xs font-semibold text-purple-800 leading-tight")
                                Muted(ITEM["detail"],
                                      css_class="text-xs leading-tight truncate")

                    Separator(css_class="border-purple-100 my-2")

                    # Verification checks ─────────────────────────────────────
                    Small("VERIFICATION",
                          css_class="font-bold text-teal-500 tracking-widest text-xs")
                    with ForEach("current_topic.reasoning_trace.verification_checks"):
                        with Row(css_class="items-start gap-1.5 py-0.5"):
                            Text(content=ITEM["check_icon"], css_class="text-xs shrink-0")
                            Text(content=ITEM["check"],
                                 css_class="text-xs text-slate-600 capitalize")

                    Separator(css_class="border-purple-100 my-2")

                    # ── Chain of Thought — pop-out window ────────────────────
                    Button(
                        "🔍 Chain of Thought ↗",
                        size="sm",
                        variant="outline",
                        css_class=(
                            "w-full text-xs border-purple-200 "
                            "text-purple-700 hover:bg-purple-50"
                        ),
                        on_click=SetState("show_cot", True),
                    )

                    # Sentinel: JS watches for this to appear → opens window
                    with If("show_cot"):
                        Small("", css_class="wz-cot-sentinel")
                        # Hidden button JS clicks to reset Prefab state on close
                        Button(
                            "×",
                            on_click=SetState("show_cot", False),
                            css_class=(
                                "wz-cot-close-trigger opacity-0 absolute "
                                "w-0 h-0 overflow-hidden pointer-events-none"
                            ),
                        )

                    # Hidden data feeds — Prefab keeps these reactive
                    Text(Rx("current_topic.reasoning_trace.reasoning_type"),
                         css_class="wz-d-type hidden")
                    Text(Rx("current_topic.reasoning_trace.confidence_pct"),
                         css_class="wz-d-conf hidden")
                    Text(Rx("current_topic.reasoning_trace.reasoning_desc"),
                         css_class="wz-d-desc hidden")
                    Text(Rx("current_topic.reasoning_trace.prompt_used"),
                         css_class="wz-d-prompt hidden")
                    Text(Rx("current_topic.reasoning_trace.llm_response_summary"),
                         css_class="wz-d-resp hidden")
                    Text(Rx("current_topic.explanation"),
                         css_class="wz-d-expl hidden")

                # ── Empty state ───────────────────────────────────────────────
                with If(Rx("asking") == False):
                    with If(Rx("current_topic") == None):
                        Muted(
                            "Ask a question to see the live reasoning panel.",
                            css_class="text-xs italic mt-2",
                        )

# Render once at startup — bundled mode inlines all JS so no CDN is needed
_html = _prefab.html(renderer_mode="bundled")

# ── Avatar panel — injected directly into HTML ────────────────────────────────
# Web Speech API runs in the main page context (not an iframe) so it works
# across all browsers without permissions. HeyGen upgrade path is marked below.

_AVATAR_HTML = """
<style>
#wz-panel{
  position:fixed;bottom:24px;right:24px;z-index:9999;
  display:flex;flex-direction:column;align-items:center;gap:7px;
  background:white;border-radius:22px;padding:14px 10px 10px;
  box-shadow:0 8px 32px rgba(99,102,241,.22);
  border:2px solid #ede9fe;width:116px;user-select:none;font-family:sans-serif
}
/* ── face bubble ── */
#wz-bubble{
  width:74px;height:74px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-size:40px;
  border:3px solid transparent;cursor:pointer;transition:border-color .3s,box-shadow .3s;
  position:relative;
}
#wz-bubble.speaking{
  border-color:var(--wz-c,#7c3aed) !important;
  box-shadow:0 0 0 7px color-mix(in srgb,var(--wz-c,#7c3aed) 22%,transparent);
  animation:wz-throb .85s ease-in-out infinite !important;
}
/* ── idle animations per avatar ── */
@keyframes wz-float  {0%,100%{transform:translateY(0)}  50%{transform:translateY(-6px)}}
@keyframes wz-bounce {0%,100%{transform:translateY(0) scale(1)} 40%{transform:translateY(-8px) scale(1.1)} 70%{transform:translateY(-3px) scale(1.03)}}
@keyframes wz-tilt   {0%,100%{transform:rotate(-5deg)} 50%{transform:rotate(5deg)}}
@keyframes wz-wobble {0%,100%{transform:translateX(0)} 25%{transform:translateX(-4px) rotate(-3deg)} 75%{transform:translateX(4px) rotate(3deg)}}
@keyframes wz-flutter{0%,100%{transform:translateY(0) scale(1)} 30%{transform:translateY(-5px) scale(1.06)} 60%{transform:translateY(-2px) scale(1.01)}}
@keyframes wz-spin   {0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)}}
@keyframes wz-throb  {0%,100%{transform:scale(1)} 50%{transform:scale(1.12)}}
/* ── sparkle ring for Pixie / Sparkle ── */
#wz-bubble::after{
  content:var(--wz-ring,'');position:absolute;inset:-6px;border-radius:50%;
  background:conic-gradient(from 0deg,transparent 60%,var(--wz-c,#ec4899) 80%,transparent 100%);
  animation:wz-spin 2.5s linear infinite;opacity:var(--wz-ring-op,0);
}
/* ── name / status ── */
#wz-name  {font-size:11px;font-weight:700;color:var(--wz-c,#6366f1);text-align:center}
#wz-status{font-size:9px;color:#a78bfa;text-align:center;min-height:11px}
/* ── avatar picker ── */
.wz-avs{display:flex;gap:3px;flex-wrap:wrap;justify-content:center}
.wz-av{
  width:26px;height:26px;border-radius:8px;border:2px solid transparent;
  background:#f5f3ff;cursor:pointer;font-size:15px;
  display:flex;align-items:center;justify-content:center;
  transition:all .2s;line-height:1;
}
.wz-av.on {border-color:var(--av-c,#7c3aed);background:#ede9fe;transform:scale(1.12)}
.wz-av:hover{border-color:#c4b5fd;transform:scale(1.06)}
/* ── controls ── */
.wz-ctrl{display:flex;gap:5px}
.wz-btn{
  width:30px;height:27px;border-radius:8px;border:1.5px solid #e0e7ff;
  background:#f5f3ff;cursor:pointer;font-size:14px;
  display:flex;align-items:center;justify-content:center;
  transition:background .2s;color:#6366f1;
}
.wz-btn:hover{background:#ede9fe}
/* ── topbar (drag handle + minimize) ── */
#wz-topbar{
  width:100%;display:flex;justify-content:flex-end;gap:3px;
  margin-bottom:2px;cursor:grab;
}
#wz-topbar:active{cursor:grabbing}
#wz-min{
  width:20px;height:18px;border-radius:5px;border:1px solid #e0e7ff;
  background:#f5f3ff;cursor:pointer;font-size:13px;line-height:1;
  display:flex;align-items:center;justify-content:center;
  color:#7c3aed;padding:0;flex-shrink:0;
}
#wz-min:hover{background:#ede9fe}
/* ── minimized state ── */
#wz-panel.minimized{padding:6px 8px;width:auto;gap:4px}
#wz-panel.minimized #wz-body{display:none}
#wz-panel.minimized #wz-bubble{width:42px;height:42px;font-size:24px}
</style>

<div id="wz-panel">
  <div id="wz-topbar">
    <button id="wz-min" title="Minimize / Restore">─</button>
  </div>
  <div id="wz-bubble" title="Click to speak / stop">🦄</div>
  <div id="wz-body">
    <div id="wz-name">Sparkle</div>
    <div id="wz-status"></div>
    <div class="wz-avs" id="wz-avs"></div>
    <div class="wz-ctrl">
      <button class="wz-btn" id="wz-play" title="Play">&#9654;</button>
      <button class="wz-btn" id="wz-stop" title="Stop">&#9632;</button>
    </div>
  </div>
</div>

<script>
(function(){
  /* Each avatar: emoji, display name, CSS color, background, idle animation,
     animation duration, voice-gender hint, rate, pitch,
     sparkle ring (true = spinning ring behind face) */
  const AVS = [
    {e:'&#x1F984;', n:'Sparkle',  c:'#ec4899', bg:'#fdf2f8', anim:'wz-bounce',  dur:'1.1s', female:true,  young:true,  ring:true,  rate:1.05, pitch:1.45},
    {e:'&#x1F9DA;', n:'Pixie',    c:'#d97706', bg:'#fffbeb', anim:'wz-flutter', dur:'1.3s', female:true,  young:true,  ring:true,  rate:1.10, pitch:1.6 },
    {e:'&#x1F9B8;&#x200D;&#x2640;&#xFE0F;', n:'Nova', c:'#dc2626', bg:'#fff1f2', anim:'wz-tilt', dur:'2s', female:true, young:false, ring:false, rate:0.97, pitch:1.15},
    {e:'&#x1F9D9;', n:'Merlin',   c:'#7c3aed', bg:'#f5f3ff', anim:'wz-float',   dur:'2.5s', female:false, young:false, ring:false, rate:0.88, pitch:0.92},
    {e:'&#x1F9D1;&#x200D;&#x1F52C;', n:'Dr.Zara', c:'#0d9488', bg:'#f0fdfa', anim:'wz-tilt', dur:'2.2s', female:true, young:false, ring:false, rate:0.90, pitch:1.1},
    {e:'&#x1F916;', n:'Bolt',     c:'#475569', bg:'#f1f5f9', anim:'wz-wobble',  dur:'1.8s', female:false, young:false, ring:false, rate:1.15, pitch:0.5 },
  ];

  let sel = Math.min(parseInt(localStorage.getItem('wz_av')||'0',10), AVS.length-1);
  let lastText='', debounce, voices=[];

  const bubble = document.getElementById('wz-bubble');
  const nameEl = document.getElementById('wz-name');
  const status = document.getElementById('wz-status');
  const avsCon = document.getElementById('wz-avs');

  /* load voices — Chrome populates them async */
  function loadVoices(){ voices=window.speechSynthesis.getVoices(); }
  loadVoices();
  if('onvoiceschanged' in window.speechSynthesis)
    window.speechSynthesis.onvoiceschanged = loadVoices;

  function pickVoice(av){
    if(!voices.length) return null;
    const female = ['zira','hazel','sonia','aria','jenny','natasha','karen',
                    'susan','female','girl','woman','samantha','victoria','allison'];
    const male   = ['david','mark','george','rishi','male','man','fred','daniel'];
    const names  = av.female ? female : male;
    return voices.find(v=> names.some(n=>v.name.toLowerCase().includes(n))) || voices[0];
  }

  /* build picker */
  AVS.forEach((av,i)=>{
    const b=document.createElement('button');
    b.className='wz-av'+(i===sel?' on':'');
    b.style.setProperty('--av-c', av.c);
    b.innerHTML=av.e; b.title=av.n;
    b.onclick=()=>{ sel=i; localStorage.setItem('wz_av',i); refreshUI(); };
    avsCon.appendChild(b);
  });

  function refreshUI(){
    const av=AVS[sel];
    bubble.innerHTML=av.e;
    bubble.style.background=av.bg;
    bubble.style.setProperty('--wz-c', av.c);
    bubble.style.setProperty('--wz-ring', av.ring?'""':'none');
    bubble.style.setProperty('--wz-ring-op', av.ring?'0.55':'0');
    bubble.style.animation=`${av.anim} ${av.dur} ease-in-out infinite`;
    nameEl.textContent=av.n;
    nameEl.style.color=av.c;
    document.querySelectorAll('.wz-av').forEach((b,i)=>{
      b.style.setProperty('--av-c', AVS[i].c);
      b.className='wz-av'+(i===sel?' on':'');
    });
  }

  function speak(text){
    /* HeyGen upgrade: set window.HEYGEN_API_KEY to switch from browser TTS
       to a HeyGen talking-head video. Hook is here — implement the API call
       (POST /v2/video/generate, poll /v1/video_status.get) when ready. */
    if(window.HEYGEN_API_KEY){ status.textContent='HeyGen…'; return; }

    window.speechSynthesis.cancel();
    const utt=new SpeechSynthesisUtterance(text);
    const av=AVS[sel]; const v=pickVoice(av);
    if(v) utt.voice=v;
    utt.rate=av.rate; utt.pitch=av.pitch;
    utt.onstart=()=>{
      bubble.style.animation='';
      bubble.classList.add('speaking');
      status.textContent='Speaking…';
    };
    utt.onend=utt.onerror=()=>{
      bubble.classList.remove('speaking');
      status.textContent='';
      refreshUI();
    };
    window.speechSynthesis.speak(utt);
  }

  bubble.onclick=()=>{
    if(window.speechSynthesis.speaking){
      window.speechSynthesis.cancel();
      bubble.classList.remove('speaking'); status.textContent=''; refreshUI();
    } else if(lastText){ speak(lastText); }
  };
  document.getElementById('wz-play').onclick=()=>{ if(lastText) speak(lastText); };
  document.getElementById('wz-stop').onclick=()=>{
    window.speechSynthesis.cancel();
    bubble.classList.remove('speaking'); status.textContent=''; refreshUI();
  };

  /* detect explanation text */
  function getExplanation(){
    const hdrs=[...document.querySelectorAll('*')].filter(
      el=>el.children.length===0&&el.textContent.trim()==='📖 Explanation'
    );
    if(hdrs.length){
      let card=hdrs[0];
      for(let i=0;i<6;i++){
        card=card.parentElement; if(!card) break;
        const ps=[...card.querySelectorAll('p,li')].filter(p=>p.textContent.trim().length>40);
        if(ps.length) return ps.map(p=>p.textContent.trim()).join(' ');
      }
    }
    const ps=[...document.querySelectorAll('p')].filter(p=>p.textContent.length>120);
    return ps.length?ps.map(p=>p.textContent).join(' '):'';
  }

  const obs=new MutationObserver(()=>{
    clearTimeout(debounce);
    debounce=setTimeout(()=>{
      const text=getExplanation();
      if(text&&text!==lastText&&text.length>80){ lastText=text; speak(text); }
    },900);
  });
  obs.observe(document.body,{childList:true,subtree:true});

  /* ── Progressive stage reveal ──────────────────────────────────
     Stages 1-4 are pure Python (<5ms each). Stage 5 is web search
     + LLM (~5-20s). Stages 6-9 are fast again.
     While the backend is synchronous (returns only on full completion),
     we know stages 1-4 are done almost immediately, so we mark them
     done progressively in the UI — this is honest, not fabricated.
     Stage 5 stays spinning until Prefab gets the real response.     */
  (function(){
    const FAST=['Understanding Query','Classifying Reasoning',
                'Creating Execution Plan','Selecting Tools'];
    let active=false, timers=[];

    function markDone(name){
      const sidebar=document.querySelector('.wz-rsidebar');
      if(!sidebar) return;
      // Find the text leaf with this exact name
      const nameEl=[...sidebar.querySelectorAll('*')].find(
        el=>el.childElementCount===0&&el.textContent.trim()===name
      );
      if(!nameEl) return;
      // Walk up to the flex row (first ancestor with >1 child element)
      let row=nameEl.parentElement;
      for(let i=0;i<4;i++){
        if(!row) return;
        if(row.childElementCount>=2) break;
        row=row.parentElement;
      }
      if(!row) return;
      // Loader() is the first child; replace its content with a checkmark
      const loader=row.firstElementChild;
      if(loader&&loader!==nameEl&&!loader.dataset.wzDone){
        loader.dataset.wzDone='1';
        loader.innerHTML='✅';
        loader.style.cssText='font-size:11px;flex-shrink:0;line-height:1;animation:none';
      }
    }

    function start(){
      FAST.forEach((name,i)=>{
        timers.push(setTimeout(()=>markDone(name),(i+1)*320));
      });
    }
    function stop(){ timers.forEach(clearTimeout); timers=[]; active=false; }

    // Detect asking=True via "Thinking step by step…" sentinel
    const obs=new MutationObserver(()=>{
      const sidebar=document.querySelector('.wz-rsidebar');
      if(!sidebar) return;
      const thinking=[...sidebar.querySelectorAll('*')].find(
        el=>el.childElementCount===0&&el.textContent.trim().startsWith('Thinking step')
      );
      if(thinking&&!active){ active=true; start(); }
      else if(!thinking&&active){ stop(); }
    });
    obs.observe(document.body,{childList:true,subtree:true});
  })();

  /* ── Right sidebar: drag-resize ────────────────────────────────
     A 6-px invisible strip on the LEFT edge of .wz-rsidebar.
     Turns purple on hover to signal it's draggable.               */
  (function(){
    function setup(sb){
      if(sb.dataset.wzSbReady) return;
      sb.dataset.wzSbReady='1';
      sb.style.position='relative';

      const h=document.createElement('div');
      h.id='wz-sb-handle';
      h.style.cssText='position:absolute;left:0;top:0;width:6px;height:100%;'+
        'cursor:col-resize;z-index:500;border-left:3px solid transparent;'+
        'transition:border-color .15s;box-sizing:border-box';
      sb.prepend(h);

      let drag=false,sx=0,sw=0;
      h.addEventListener('mouseenter',()=>{ if(!drag) h.style.borderLeftColor='#a78bfa'; });
      h.addEventListener('mouseleave',()=>{ if(!drag) h.style.borderLeftColor='transparent'; });
      h.addEventListener('mousedown',e=>{
        drag=true; sx=e.clientX; sw=sb.offsetWidth;
        document.body.style.cursor='col-resize';
        document.body.style.userSelect='none';
        e.preventDefault();
      });
      document.addEventListener('mousemove',e=>{
        if(!drag) return;
        const w=Math.max(220,Math.min(700,sw-(e.clientX-sx)));
        sb.style.width=w+'px'; sb.style.minWidth=w+'px'; sb.style.flexShrink='0';
      });
      document.addEventListener('mouseup',()=>{
        if(drag){
          drag=false;
          document.body.style.cursor='';
          document.body.style.userSelect='';
          h.style.borderLeftColor='transparent';
          localStorage.setItem('wz_sb_w',sb.offsetWidth);
        }
      });
      // restore saved width
      const saved=parseInt(localStorage.getItem('wz_sb_w')||'0',10);
      if(saved>=220){ sb.style.width=saved+'px'; sb.style.minWidth=saved+'px'; sb.style.flexShrink='0'; }
    }

    // try immediately, then watch for Prefab to render the sidebar
    const existing=document.querySelector('.wz-rsidebar');
    if(existing) setup(existing);
    const sbObs=new MutationObserver(()=>{
      const el=document.querySelector('.wz-rsidebar');
      if(el) setup(el);
    });
    sbObs.observe(document.body,{childList:true,subtree:true});
  })();

  /* ── Chain of Thought: floating pop-out window ──────────────────
     Opens when Prefab state show_cot=True (detected via sentinel).
     Draggable title bar. position:fixed + resize:both = reliable
     native resize that works regardless of flex layout.           */
  (function(){
    const STEPS=[
      'Understand user goal',
      'Identify reasoning type',
      'Break into substeps',
      'Ground with web context',
      'Verify intermediate reasoning',
      'Check hallucination risk',
      'Self-check: complete + age-right?',
      'Generate structured JSON',
    ];
    const CRITERIA=[
      ['Explicit Reasoning',    '8 reasoning steps injected into prompt'],
      ['Structured Output',     'JSON schema with fixed keys enforced'],
      ['Tool Separation',       'web search → LLM explain → verifier'],
      ['Conversation Loop',     'follow-up chips re-enter the pipeline'],
      ['Instructional Framing', 'age + role context in USER CONTEXT block'],
      ['Internal Self-Checks',  'SELF-CHECK block at end of prompt'],
      ['Reasoning Type Aware',  'type detected pre-call, injected as REASONING_TYPE'],
      ['Error Fallbacks',       '4-tier LLM waterfall + graceful error response'],
    ];

    function get(cls){
      return (document.querySelector('.'+cls)||{}).textContent?.trim()||'';
    }
    function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function badge(txt,bg,clr){
      return `<span style="display:inline-block;padding:2px 9px;border-radius:20px;
        font-size:11px;font-weight:600;background:${bg};color:${clr};
        border:1px solid ${clr}44;margin:2px 3px 2px 0">${txt}</span>`;
    }
    function sec(label,clr){
      return `<div style="font-size:10px;font-weight:800;letter-spacing:.09em;
        color:${clr};margin:16px 0 6px;text-transform:uppercase;
        border-bottom:1px solid ${clr}33;padding-bottom:4px">${label}</div>`;
    }

    function buildHTML(){
      const type=get('wz-d-type')||'—';
      const conf=get('wz-d-conf')||'—';
      const desc=get('wz-d-desc')||'';
      const prompt=get('wz-d-prompt')||'';
      const resp=get('wz-d-resp')||'';
      const expl=get('wz-d-expl')||'';

      const steps=STEPS.map((s,i)=>
        `<div style="display:flex;gap:8px;padding:3px 0;align-items:flex-start">
          <b style="color:#a78bfa;font-size:12px;min-width:18px">${i+1}</b>
          <span style="font-size:12px;color:#4b5563;line-height:1.5">${s}</span>
        </div>`).join('');

      const criteria=CRITERIA.map(([n,w])=>
        `<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #f3f4f6;align-items:flex-start">
          <span style="color:#10b981;font-weight:800;font-size:13px;flex-shrink:0">✓</span>
          <div>
            <div style="font-size:12px;font-weight:700;color:#1f2937">${n}</div>
            <div style="font-size:11px;color:#9ca3af;margin-top:1px">${w}</div>
          </div>
        </div>`).join('');

      return `
        <div style="font-size:12px;color:#6b7280;font-style:italic;margin-bottom:4px">${desc}</div>

        ${sec('Prompt Components','#7c3aed')}
        <div>
          ${badge(type,'#ede9fe','#7c3aed')}
          ${badge('🌐 web searched','#dbeafe','#1d4ed8')}
          ${badge('📋 json output','#ffedd5','#c2410c')}
          ${badge('👶 age-adaptive','#d1fae5','#065f46')}
          ${badge('✓ '+conf+' confidence','#f0fdf4','#166534')}
        </div>

        ${sec('Framework Injected Into Prompt','#7c3aed')}
        <div style="background:#faf5ff;border-radius:8px;padding:10px 12px">${steps}</div>

        ${sec('Prompt Criteria Met','#0d9488')}
        <div style="background:#f9fafb;border-radius:8px;padding:6px 10px">${criteria}</div>

        ${sec('LLM Output — Parsed Explanation','#059669')}
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
          padding:10px 12px;font-size:12px;color:#1f2937;line-height:1.7;
          min-height:60px;max-height:180px;overflow-y:auto;
          resize:vertical;box-sizing:border-box">
          ${expl||'<span style="color:#9ca3af">No explanation captured yet</span>'}
        </div>

        ${sec('Raw Prompt Sent to LLM','#d97706')}
        <button onclick="
          var b=document.getElementById('wz-rpb');
          var open=b.style.display!=='none';
          b.style.display=open?'none':'block';
          this.textContent=open?'📋 View raw prompt ▾':'📋 Hide raw prompt ▲'
        " style="background:#fff7ed;border:1px solid #fed7aa;border-radius:7px;
          padding:5px 12px;cursor:pointer;font-size:11px;color:#92400e;
          margin-bottom:6px;font-weight:600">📋 View raw prompt ▾</button>
        <div id="wz-rpb" style="display:none;background:#fff7ed;border:1px solid #fed7aa;
          border-radius:8px;padding:10px 12px;font-family:monospace;font-size:11px;
          white-space:pre-wrap;word-break:break-all;line-height:1.6;color:#44403c;
          min-height:60px;max-height:260px;overflow-y:auto;
          resize:vertical;box-sizing:border-box">${esc(prompt)||'No prompt captured'}</div>

        ${resp?`
          ${sec('Raw LLM Response','#2563eb')}
          <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
            padding:10px 12px;font-family:monospace;font-size:11px;white-space:pre-wrap;
            word-break:break-all;line-height:1.6;color:#1e3a5f;
            min-height:60px;max-height:200px;overflow-y:auto;
            resize:vertical;box-sizing:border-box">${esc(resp)}</div>`:''}
      `;
    }

    function openWin(){
      if(document.getElementById('wz-cot-win')) return;

      const win=document.createElement('div');
      win.id='wz-cot-win';
      win.style.cssText=[
        'position:fixed','top:60px','left:50%','transform:translateX(-50%)',
        'width:520px','height:600px','min-width:320px','min-height:220px',
        'background:#fff','z-index:9997',
        'border:2px solid #ddd6fe','border-radius:16px',
        'box-shadow:0 24px 60px rgba(99,102,241,.3),0 4px 16px rgba(0,0,0,.08)',
        'display:flex','flex-direction:column',
        'resize:both','overflow:hidden',
        'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      ].join(';');

      // ── Title bar ─────────────────────────────────────────────────────────
      const bar=document.createElement('div');
      bar.id='wz-cot-bar';
      bar.style.cssText=[
        'display:flex','align-items:center','justify-content:space-between',
        'padding:10px 14px',
        'background:linear-gradient(135deg,#f5f3ff 0%,#ede9fe 100%)',
        'border-bottom:1px solid #ddd6fe','border-radius:14px 14px 0 0',
        'cursor:grab','flex-shrink:0','user-select:none',
      ].join(';');
      bar.innerHTML=`
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-size:16px">🧠</span>
          <span style="font-size:13px;font-weight:800;color:#7c3aed">Chain of Thought</span>
        </div>
        <div style="display:flex;gap:6px;align-items:center">
          <button id="wz-cot-ref" title="Refresh content" style="
            background:#f5f3ff;border:1px solid #ddd6fe;border-radius:6px;
            width:26px;height:26px;cursor:pointer;color:#7c3aed;font-size:14px;
            display:flex;align-items:center;justify-content:center;padding:0;
            line-height:1">↻</button>
          <button id="wz-cot-x" title="Close" style="
            background:#f5f3ff;border:1px solid #ddd6fe;border-radius:6px;
            width:26px;height:26px;cursor:pointer;color:#7c3aed;font-size:16px;
            display:flex;align-items:center;justify-content:center;padding:0;
            line-height:1">✕</button>
        </div>`;

      // ── Scrollable body ────────────────────────────────────────────────────
      const body=document.createElement('div');
      body.id='wz-cot-body';
      body.style.cssText='flex:1;overflow-y:auto;padding:14px 16px;';
      body.innerHTML=buildHTML();

      win.appendChild(bar);
      win.appendChild(body);
      document.body.appendChild(win);

      // Restore saved position/size
      try{
        const p=JSON.parse(localStorage.getItem('wz_cot_geom')||'null');
        if(p){
          win.style.transform='none';
          if(p.l) win.style.left=p.l;
          if(p.t) win.style.top=p.t;
          if(p.w) win.style.width=p.w;
          if(p.h) win.style.height=p.h;
        }
      }catch(e){}

      function saveGeom(){
        try{
          const r=win.getBoundingClientRect();
          localStorage.setItem('wz_cot_geom',JSON.stringify({
            l:win.style.left||r.left+'px', t:win.style.top||r.top+'px',
            w:win.offsetWidth+'px', h:win.offsetHeight+'px',
          }));
        }catch(e){}
      }

      document.getElementById('wz-cot-ref').onclick=()=>{ body.innerHTML=buildHTML(); };
      document.getElementById('wz-cot-x').onclick=closeWin;

      // Drag the title bar
      let drag=false,ox=0,oy=0;
      bar.addEventListener('mousedown',e=>{
        if(e.target.closest('button')) return;
        drag=true;
        const r=win.getBoundingClientRect();
        win.style.transform='none';
        win.style.left=r.left+'px'; win.style.top=r.top+'px';
        ox=e.clientX-r.left; oy=e.clientY-r.top;
        bar.style.cursor='grabbing'; e.preventDefault();
      });
      document.addEventListener('mousemove',e=>{
        if(!drag) return;
        win.style.left=Math.max(0,Math.min(e.clientX-ox,window.innerWidth-win.offsetWidth))+'px';
        win.style.top =Math.max(0,Math.min(e.clientY-oy,window.innerHeight-win.offsetHeight))+'px';
      });
      document.addEventListener('mouseup',()=>{
        if(drag){ drag=false; bar.style.cursor='grab'; saveGeom(); }
      });

      // Save geometry when user finishes resizing (mouseup on document)
      win.addEventListener('mouseup', saveGeom);
    }

    function closeWin(){
      const win=document.getElementById('wz-cot-win');
      if(win){
        try{
          const r=win.getBoundingClientRect();
          localStorage.setItem('wz_cot_geom',JSON.stringify({
            l:win.style.left||r.left+'px', t:win.style.top||r.top+'px',
            w:win.offsetWidth+'px', h:win.offsetHeight+'px',
          }));
        }catch(e){}
        win.remove();
      }
      // Reset Prefab show_cot state via hidden trigger button
      const btn=document.querySelector('.wz-cot-close-trigger');
      if(btn){ const b=btn.tagName==='BUTTON'?btn:btn.querySelector('button'); if(b) b.click(); }
    }

    // Watch for sentinel appearing/disappearing
    const obs=new MutationObserver(()=>{
      const sentinel=document.querySelector('.wz-cot-sentinel');
      const winOpen=!!document.getElementById('wz-cot-win');
      if(sentinel&&!winOpen) openWin();
      else if(!sentinel&&winOpen) document.getElementById('wz-cot-win')?.remove();
    });
    obs.observe(document.body,{childList:true,subtree:true});
  })();

  /* ── Minimize / Restore ─────────────────────────────────────── */
  const panel   = document.getElementById('wz-panel');
  const minBtn  = document.getElementById('wz-min');
  let minimized = localStorage.getItem('wz_min')==='1';
  function applyMinimized(){
    panel.classList.toggle('minimized', minimized);
    minBtn.textContent = minimized ? '+' : '─';
    minBtn.title       = minimized ? 'Restore' : 'Minimize';
  }
  applyMinimized();
  minBtn.onclick = e => {
    e.stopPropagation();
    minimized = !minimized;
    localStorage.setItem('wz_min', minimized?'1':'0');
    applyMinimized();
  };

  /* ── Drag to move ───────────────────────────────────────────── */
  const topbar = document.getElementById('wz-topbar');
  let dragging=false, dragOX=0, dragOY=0;

  function startDrag(e){
    if(e.target===minBtn) return;     // let minimize button click through
    dragging=true;
    // Convert from bottom/right anchoring to top/left before first drag
    const r=panel.getBoundingClientRect();
    panel.style.bottom='auto'; panel.style.right='auto';
    panel.style.top =r.top +'px';
    panel.style.left=r.left+'px';
    dragOX=e.clientX-r.left;
    dragOY=e.clientY-r.top;
    document.body.style.userSelect='none';
  }
  topbar.addEventListener('mousedown', startDrag);
  document.addEventListener('mousemove', e=>{
    if(!dragging) return;
    let nx=e.clientX-dragOX, ny=e.clientY-dragOY;
    // Clamp inside viewport
    nx=Math.max(0,Math.min(nx,window.innerWidth -panel.offsetWidth));
    ny=Math.max(0,Math.min(ny,window.innerHeight-panel.offsetHeight));
    panel.style.left=nx+'px'; panel.style.top=ny+'px';
  });
  document.addEventListener('mouseup',()=>{
    if(dragging){
      dragging=false;
      document.body.style.userSelect='';
      // Persist position
      localStorage.setItem('wz_pos',JSON.stringify({
        left:panel.style.left, top:panel.style.top
      }));
    }
  });
  // Restore saved position
  try{
    const pos=JSON.parse(localStorage.getItem('wz_pos')||'null');
    if(pos&&pos.left&&pos.top){
      panel.style.bottom='auto'; panel.style.right='auto';
      panel.style.left=pos.left; panel.style.top=pos.top;
    }
  }catch(e){}

  refreshUI();
})();
</script>
"""

_last_body = _html.rfind("</body>")
_html = _html[:_last_body] + _AVATAR_HTML + _html[_last_body:]


# ── FastAPI routes ────────────────────────────────────────────────────────────

@fastapi_app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return _html


@fastapi_app.get("/api/init")
async def api_init():
    profiles_data = await asyncio.to_thread(manage_profiles, "list")
    profiles = profiles_data.get("profiles", [])
    active_id = profiles_data.get("active_profile_id") or (
        profiles[0]["id"] if profiles else ""
    )
    topics = await asyncio.to_thread(
        manage_curiosity_map, "read", active_id
    ) if active_id else {"topics": []}
    topics_list = sorted(
        topics.get("topics", []),
        key=lambda t: t.get("date", ""),
        reverse=True,
    )
    stats = await asyncio.to_thread(
        manage_curiosity_map, "get_stats", active_id
    ) if active_id else {
        "total": 0, "streak": 0, "this_week": 0,
        "top_tags": [], "top_branch": None,
    }
    active_name = next((p["name"] for p in profiles if p["id"] == active_id), "")
    return {
        "profiles":            profiles,
        "active_profile_id":   active_id,
        "active_profile_name": active_name,
        "topics":              topics_list,
        "stats":               stats,
        "graph_chart":         _build_mermaid(topics_list),
    }


class ActivateProfileRequest(BaseModel):
    profile_id: str


@fastapi_app.post("/api/activate-profile")
async def api_activate_profile(body: ActivateProfileRequest):
    await asyncio.to_thread(
        manage_profiles, "set_active", {"profile_id": body.profile_id}
    )
    profiles_data = await asyncio.to_thread(manage_profiles, "list")
    profiles = profiles_data.get("profiles", [])
    active_name = next((p["name"] for p in profiles if p["id"] == body.profile_id), "")
    topics_data = await asyncio.to_thread(
        manage_curiosity_map, "read", body.profile_id
    )
    topics_list = sorted(
        topics_data.get("topics", []),
        key=lambda t: t.get("date", ""),
        reverse=True,
    )
    stats = await asyncio.to_thread(
        manage_curiosity_map, "get_stats", body.profile_id
    )
    return {
        "active_profile_id":   body.profile_id,
        "active_profile_name": active_name,
        "topics":              topics_list,
        "stats":               stats,
        "graph_chart":         _build_mermaid(topics_list),
    }


class ProfileCreateRequest(BaseModel):
    name: str
    age: str  # comes as string from Input; profiles.py does int() conversion


@fastapi_app.post("/api/profiles")
async def api_create_profile(body: ProfileCreateRequest):
    try:
        result = await asyncio.to_thread(
            manage_profiles, "create", {"name": body.name, "age": body.age}
        )
        active_id = result.get("active_profile_id", "")
        profiles = result.get("profiles", [])
        result["active_profile_name"] = next(
            (p["name"] for p in profiles if p["id"] == active_id), body.name
        )
        return result
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


class ProfileDeleteRequest(BaseModel):
    profile_id: str


@fastapi_app.post("/api/profiles/delete")
async def api_delete_profile(body: ProfileDeleteRequest):
    from fastapi import HTTPException
    profiles_data = await asyncio.to_thread(manage_profiles, "list")
    if len(profiles_data.get("profiles", [])) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last profile")
    result = await asyncio.to_thread(
        manage_profiles, "delete", {"profile_id": body.profile_id}
    )
    profiles = result.get("profiles", [])
    active_id = result.get("active_profile_id", "")
    active_name = next((p["name"] for p in profiles if p["id"] == active_id), "")
    topics_data = await asyncio.to_thread(manage_curiosity_map, "read", active_id) if active_id else {"topics": []}
    topics_list = sorted(topics_data.get("topics", []), key=lambda t: t.get("date", ""), reverse=True)
    stats = await asyncio.to_thread(manage_curiosity_map, "get_stats", active_id) if active_id else {
        "total": 0, "streak": 0, "this_week": 0, "top_tags": [], "top_branch": None,
    }
    return {
        "profiles":            profiles,
        "active_profile_id":   active_id,
        "active_profile_name": active_name,
        "topics":              topics_list,
        "stats":               stats,
        "graph_chart":         _build_mermaid(topics_list),
    }


class RenderRequest(BaseModel):
    topic: str
    concept_type: str = "spatial"


@fastapi_app.post("/api/render-3d")
async def api_render_3d(body: RenderRequest):
    logging.getLogger("whyzzle").info(
        '/api/render-3d "%s" (concept=%s)', body.topic[:80], body.concept_type
    )
    result = await asyncio.to_thread(generate_video, body.topic, body.concept_type)
    return {
        "video_url": result.get("video_url") or "",
        "error":     result.get("error") or "",
        "renderer":  result.get("renderer") or "",
    }


class AskRequest(BaseModel):
    question: str
    asked_by: str = "child"
    profile_id: str = ""


@fastapi_app.post("/api/ask")
async def api_ask(body: AskRequest):
    question = body.question.strip()
    if not question:
        return {"error": "question is required"}

    active_id = body.profile_id
    if not active_id:
        profiles_data = await asyncio.to_thread(manage_profiles, "list")
        active_id = profiles_data.get("active_profile_id")
    if not active_id:
        return {"error": "No active profile — create one first."}

    logging.getLogger("whyzzle").info(
        '/api/ask "%s" (profile=%s)', question[:80], active_id[:8]
    )

    # Run the full structured reasoning pipeline (classifier → planner →
    # search+explain → verifier → confidence scorer → trace assembler)
    result = await asyncio.to_thread(
        run_reasoning_pipeline, question, active_id, body.asked_by
    )

    # Wrap bare HTML fragments in a complete document for Embed
    if result.get("visual_type") == "html_interactive":
        frag = result.get("visual_code", "")
        result["visual_code"] = (
            "<!doctype html><html><body style='"
            "margin:0;padding:0;background:#EEF2FF;"
            "display:flex;align-items:center;justify-content:center;height:100vh'>"
            + frag
            + "</body></html>"
        )

    topic_data = await asyncio.to_thread(
        manage_curiosity_map, "add_topic", active_id, result
    )
    topic = topic_data.get("topic", result)

    related_result = await asyncio.to_thread(
        manage_curiosity_map, "get_related", active_id, {"tags": topic.get("tags", [])}
    )
    related = [
        r for r in related_result.get("related", [])
        if r["topic"]["id"] != topic["id"]
    ]

    return {"topic": topic, "related": related}

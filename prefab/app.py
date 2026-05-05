"""
Whyzzle — Prefab UI  v2
========================
Run this alongside webapp.py:

    Terminal 1:  python webapp.py            # Flask API  →  :5001
    Terminal 2:  prefab serve prefab/app.py  # Prefab UI  →  :5175

Prefab concepts used
─────────────────────
• PrefabApp(state, view, connect_domains, stylesheets)
• Rx("key") / Rx("a.b.c")  — reactive state references
• RESULT / EVENT / ITEM     — special Rx refs
• Fetch(url, method, body, onSuccess, onError)
• SetState / AppendState
• SetInterval(ms, while_="key", onTick=...)
• ForEach("key") / ITEM     — list rendering
• If(condition) / Else()    — conditional rendering
• Pages(name="page") / Page(value=...)  — navigation
• StatefulMixin: Textarea(name=...), Input(name=...), Select(name=...)
"""

from prefab_ui import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardFooter,
    CardHeader,
    CardTitle,
    Column,
    Embed,
    ForEach,
    H2,
    H3,
    If,
    Else,
    Input,
    Loader,
    Markdown,
    Metric,
    Muted,
    Page,
    Pages,
    Row,
    Select,
    SelectOption,
    Separator,
    Small,
    Svg,
    Text,
    Textarea,
    Video,
    ITEM,
)
from prefab_ui.actions import AppendState, Fetch, SetInterval, SetState
from prefab_ui.rx import EVENT, RESULT, Rx

# ─── Config ───────────────────────────────────────────────────────────────────
API = "http://localhost:5001"   # Flask backend URL

# ─── Initial state ────────────────────────────────────────────────────────────
INIT_STATE = {
    # Profiles
    "profiles":           [],
    "active_profile_id":  "",
    "show_create_profile": False,
    "new_name":           "",
    "new_age":            "",
    # Topics + curiosity map
    "topics":             [],
    "current_topic":      None,
    "related":            [],
    # Ask flow
    "question":           "",
    "asking":             False,
    # 3D render flow
    "rendering_3d":       False,
    "video_url":          "",
    "render_error":       "",
    # Navigation
    "page":               "home",
    # Logs
    "log_lines":          [],
    "on_logs_page":       False,
    # Stats
    "stats": {
        "total":      0,
        "streak":     0,
        "this_week":  0,
        "top_tags":   [],
        "top_branch": None,
    },
}

# ─── Shared action snippets ───────────────────────────────────────────────────
# Refresh stats for active profile  (used after ask AND after profile switch)
_refresh_stats = Fetch(
    f"{API}/api/stats/{{{{active_profile_id}}}}",  # {{…}} → reactive template
    onSuccess=SetState("stats", RESULT),
)

# Fetch latest log lines (used by log poller and Logs page)
_fetch_logs = Fetch(
    f"{API}/api/logs",
    onSuccess=SetState("log_lines", RESULT["logs"]),
)

# ─────────────────────────────────────────────────────────────────────────────
# BUILD THE UI
# ─────────────────────────────────────────────────────────────────────────────
with Row(
    cssClass="min-h-screen flex bg-gradient-to-br from-purple-50 via-white to-teal-50",
    onMount=Fetch(
        f"{API}/api/init",
        onSuccess=[
            SetState("profiles",          RESULT["profiles"]),
            SetState("active_profile_id", RESULT["active_profile_id"]),
            SetState("topics",            RESULT["topics"]),
            SetState("stats",             RESULT["stats"]),
        ],
    ),
) as root:

    # ═══════════════════════════════════════════════════════════════════════════
    # LEFT SIDEBAR
    # ═══════════════════════════════════════════════════════════════════════════
    with Column(
        cssClass=(
            "w-72 shrink-0 min-h-screen border-r border-purple-100 "
            "bg-white/70 backdrop-blur flex flex-col p-4 gap-3 shadow-sm"
        )
    ):
        # ── Brand ─────────────────────────────────────────────────────────────
        with Row(cssClass="items-center gap-2 mb-1"):
            H2("🧠 Whyzzle", cssClass="text-purple-700 font-extrabold text-2xl tracking-tight")
        Muted("Your personal curiosity map ✨")

        Separator(cssClass="border-purple-100")

        # ── Profile selector ──────────────────────────────────────────────────
        # Select with name= auto-syncs both ways with state["active_profile_id"].
        # value="{{ active_profile_id }}" provides an explicit template binding
        # so the displayed selection updates reactively after onMount.
        with Card(cssClass="border-purple-100 bg-purple-50/50"):
            with CardHeader(cssClass="pb-2"):
                with Row(cssClass="items-center justify-between"):
                    CardTitle("👧 Profile")
                    Button(
                        "+ New Kid",
                        variant="outline",
                        size="xs",
                        cssClass="text-purple-600 border-purple-300 hover:bg-purple-100",
                        onClick=SetState("show_create_profile", True),
                    )
            with CardContent(cssClass="pt-0 flex flex-col gap-2"):
                with Select(
                    name="active_profile_id",
                    value="{{ active_profile_id }}",
                    placeholder="Select a profile…",
                    onChange=Fetch(
                        f"{API}/api/activate-profile",
                        method="POST",
                        body={"profile_id": EVENT},
                        onSuccess=[
                            SetState("topics",        RESULT["topics"]),
                            SetState("stats",         RESULT["stats"]),
                            SetState("current_topic", None),
                            SetState("video_url",     ""),
                            SetState("page",          "home"),
                        ],
                    ),
                ):
                    # ForEach renders one SelectOption per profile in state
                    with ForEach("profiles"):
                        SelectOption(ITEM["name"], value=ITEM["id"])

                # ── Create-profile mini-form ─────────────────────────────────
                # Shown only when the "+ New Kid" button is clicked.
                # Input with name= is a StatefulMixin — auto-binds to state.
                with If("show_create_profile"):
                    Separator(cssClass="border-dashed border-purple-200 my-1")
                    Input(
                        name="new_name",
                        placeholder="Child's name 🌟",
                        cssClass="border-purple-200 focus:ring-purple-400",
                    )
                    Input(
                        name="new_age",
                        inputType="number",
                        placeholder="Age 🎂",
                        cssClass="border-purple-200 focus:ring-purple-400",
                    )
                    with Row(cssClass="gap-2 mt-1"):
                        Button(
                            "Create ✅",
                            size="sm",
                            cssClass="bg-purple-600 hover:bg-purple-700 text-white flex-1",
                            onClick=Fetch(
                                f"{API}/api/profiles",
                                method="POST",
                                body={
                                    "name": Rx("new_name"),
                                    "age":  Rx("new_age"),
                                },
                                onSuccess=[
                                    SetState("profiles",           RESULT["profiles"]),
                                    SetState("active_profile_id",  RESULT["active_profile_id"]),
                                    SetState("show_create_profile", False),
                                    SetState("new_name",           ""),
                                    SetState("new_age",            ""),
                                ],
                            ),
                        )
                        Button(
                            "Cancel",
                            variant="ghost",
                            size="sm",
                            cssClass="flex-1 text-muted-foreground",
                            onClick=SetState("show_create_profile", False),
                        )

        Separator(cssClass="border-purple-100")

        # ── Ask form ──────────────────────────────────────────────────────────
        # Textarea(name="question") uses StatefulMixin — typing auto-updates
        # state["question"]. The Ask button reads Rx("question") for the body.
        with Card(cssClass="border-teal-100 bg-teal-50/40"):
            with CardHeader(cssClass="pb-2"):
                CardTitle("🔍 Ask a Question")
            with CardContent(cssClass="flex flex-col gap-3 pt-0"):
                Textarea(
                    name="question",
                    placeholder="What do you wonder about? 🌍🚀🦕",
                    rows=3,
                    cssClass="border-teal-200 focus:ring-teal-400 rounded-xl resize-none",
                )
                Button(
                    "Ask Whyzzle ✨",
                    disabled=Rx("asking"),
                    cssClass=(
                        "w-full bg-gradient-to-r from-purple-600 to-teal-500 "
                        "hover:from-purple-700 hover:to-teal-600 text-white "
                        "font-bold rounded-xl shadow-md"
                    ),
                    onClick=[
                        SetState("asking",       True),
                        SetState("log_lines",    []),
                        SetState("video_url",    ""),
                        SetState("render_error", ""),
                        # SetInterval polls /api/logs every 1 s while asking=True.
                        # when state["asking"] becomes False, the timer stops.
                        SetInterval(
                            1000,
                            while_="asking",
                            onTick=_fetch_logs,
                        ),
                        Fetch(
                            f"{API}/api/ask",
                            method="POST",
                            body={
                                "question": Rx("question"),
                                "asked_by": "child",
                            },
                            onSuccess=[
                                SetState("asking",        False),
                                SetState("current_topic", RESULT["topic"]),
                                SetState("related",       RESULT["related"]),
                                SetState("page",          "topic"),
                                # Prepend new topic to sidebar list (index=0 = front)
                                AppendState("topics", RESULT["topic"], index=0),
                                _refresh_stats,
                            ],
                            onError=SetState("asking", False),
                        ),
                    ],
                )
                with If("asking"):
                    with Row(cssClass="items-center gap-2"):
                        Loader()
                        Muted("Researching your question…")

        Separator(cssClass="border-purple-100")

        # ── Navigation buttons ─────────────────────────────────────────────────
        with Row(cssClass="gap-1 flex-wrap"):
            Button(
                "🏠 Home", variant="ghost", size="sm",
                cssClass="hover:bg-purple-100 hover:text-purple-700",
                onClick=[
                    SetState("page",         "home"),
                    SetState("on_logs_page", False),
                ],
            )
            Button(
                "📊 Stats", variant="ghost", size="sm",
                cssClass="hover:bg-teal-100 hover:text-teal-700",
                onClick=[
                    SetState("page",         "stats"),
                    SetState("on_logs_page", False),
                    _refresh_stats,
                ],
            )
            Button(
                "📋 Logs", variant="ghost", size="sm",
                cssClass="hover:bg-yellow-100 hover:text-yellow-700",
                onClick=[
                    SetState("page",         "logs"),
                    SetState("on_logs_page", True),
                    _fetch_logs,
                    # SetInterval: poll logs every 2 s while on_logs_page=True
                    SetInterval(
                        2000,
                        while_="on_logs_page",
                        onTick=_fetch_logs,
                    ),
                ],
            )

        Separator(cssClass="border-purple-100")

        # ── Recent topics list ─────────────────────────────────────────────────
        H3("📚 Recent Topics", cssClass="font-bold text-sm text-purple-700")
        with Card(cssClass="overflow-hidden border-purple-100"):
            with CardContent(cssClass="flex flex-col gap-0.5 p-2 max-h-60 overflow-y-auto"):
                with If("topics"):
                    with ForEach("topics"):
                        Button(
                            ITEM["question"],
                            variant="ghost",
                            size="sm",
                            cssClass=(
                                "justify-start h-auto py-1.5 text-left text-xs "
                                "w-full hover:bg-purple-50 hover:text-purple-700 "
                                "rounded-lg line-clamp-1"
                            ),
                            onClick=[
                                SetState("current_topic", ITEM),
                                SetState("related",       []),
                                SetState("video_url",     ""),
                                SetState("render_error",  ""),
                                SetState("page",          "topic"),
                                SetState("on_logs_page",  False),
                            ],
                        )
                with Else():
                    Muted("Ask your first question! 🌱")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN CONTENT AREA  (Pages drives navigation via state["page"])
    # ═══════════════════════════════════════════════════════════════════════════
    with Column(cssClass="flex-1 p-6 overflow-y-auto"):
        with Pages(name="page"):

            # ── HOME ─────────────────────────────────────────────────────────
            with Page(value="home", title="Home"):
                H2(
                    "Welcome to Whyzzle! 🌟",
                    cssClass="text-3xl font-extrabold text-purple-700 mb-1",
                )
                Muted(
                    "Every question you ask becomes a node in your personal knowledge graph. "
                    "What are you curious about today?"
                )
                Separator(cssClass="my-4 border-purple-100")

                # KPI metrics row
                with Row(cssClass="gap-4 flex-wrap mb-6"):
                    with Card(cssClass="flex-1 min-w-32 border-purple-100 bg-purple-50/50"):
                        with CardContent(cssClass="pt-4"):
                            Metric(
                                label="🧩 Topics Explored",
                                value=Rx("stats.total"),
                            )
                    with Card(cssClass="flex-1 min-w-32 border-orange-100 bg-orange-50/50"):
                        with CardContent(cssClass="pt-4"):
                            Metric(
                                label="🔥 Day Streak",
                                value=Rx("stats.streak"),
                                description="consecutive days",
                            )
                    with Card(cssClass="flex-1 min-w-32 border-teal-100 bg-teal-50/50"):
                        with CardContent(cssClass="pt-4"):
                            Metric(
                                label="⚡ This Week",
                                value=Rx("stats.this_week"),
                                description="new topics",
                            )

                # Curiosity theme badges
                with If("stats.top_tags"):
                    H3("🌈 Your Curiosity Themes", cssClass="font-bold text-purple-700 mb-3")
                    with Row(cssClass="flex-wrap gap-2"):
                        with ForEach("stats.top_tags"):
                            Badge(
                                ITEM["tag"],
                                cssClass="bg-purple-100 text-purple-700 border-purple-200",
                            )

                # Quick tips when no topics yet
                with If(Rx("stats.total") == 0):
                    Separator(cssClass="my-6 border-purple-100")
                    with Row(cssClass="gap-4 flex-wrap"):
                        with Card(cssClass="flex-1 min-w-48 border-yellow-200 bg-yellow-50"):
                            with CardContent(cssClass="pt-4"):
                                H3("🦕 Try asking:", cssClass="font-bold text-yellow-800 mb-2")
                                Muted('"Why is the sky blue?"')
                        with Card(cssClass="flex-1 min-w-48 border-teal-200 bg-teal-50"):
                            with CardContent(cssClass="pt-4"):
                                H3("🚀 Or maybe:", cssClass="font-bold text-teal-800 mb-2")
                                Muted('"How do black holes form?"')
                        with Card(cssClass="flex-1 min-w-48 border-pink-200 bg-pink-50"):
                            with CardContent(cssClass="pt-4"):
                                H3("🌊 Or even:", cssClass="font-bold text-pink-800 mb-2")
                                Muted('"Why do volcanoes erupt?"')

            # ── TOPIC ────────────────────────────────────────────────────────
            with Page(value="topic", title="Topic"):
                with If("current_topic"):

                    # Question heading
                    H2(
                        Rx("current_topic.question"),
                        cssClass="text-2xl font-extrabold text-purple-700 mb-4",
                    )

                    # Visual ──────────────────────────────────────────────────
                    # Canvas 2D HTML → sandboxed iframe via Embed
                    # SVG fallback  → rendered inline via Svg
                    # Note: Embed.html / Svg.content are str fields; Prefab
                    # evaluates {{ expr }} template strings at render time.
                    with Card(cssClass="mb-4 border-purple-100 overflow-hidden"):
                        with CardContent(cssClass="p-0"):
                            with If(
                                Rx("current_topic.visual_type") == "html_interactive"
                            ):
                                Embed(
                                    html="{{ current_topic.visual_code }}",
                                    height="460px",
                                    sandbox="allow-scripts allow-same-origin",
                                    cssClass="w-full",
                                )
                            with Else():
                                Svg(
                                    content="{{ current_topic.visual_code }}",
                                    cssClass="w-full p-4",
                                )

                    # Explanation (LLM Markdown output) ───────────────────────
                    with Card(cssClass="mb-4 border-teal-100 bg-teal-50/30"):
                        with CardHeader(cssClass="pb-2"):
                            CardTitle("📖 Explanation")
                        with CardContent():
                            Markdown(content=Rx("current_topic.explanation"))

                    # Tags ────────────────────────────────────────────────────
                    with If("current_topic.tags"):
                        with Row(cssClass="flex-wrap gap-2 mb-4"):
                            with ForEach("current_topic.tags"):
                                Badge(
                                    ITEM,
                                    cssClass="bg-teal-100 text-teal-700 border-teal-200",
                                )

                    # 3D Blender animation ─────────────────────────────────────
                    # Clicking the button calls /api/3d which runs Blender
                    # headlessly and returns an MP4 video URL.
                    Separator(cssClass="my-4 border-purple-100")
                    H3("🎬 3D Animation", cssClass="font-bold text-purple-700 mb-2")
                    with If(Rx("video_url") == ""):
                        with If(Rx("rendering_3d") == False):
                            Button(
                                "Generate 3D Animation with Blender 🌀",
                                variant="outline",
                                cssClass=(
                                    "border-purple-300 text-purple-700 "
                                    "hover:bg-purple-100 font-semibold"
                                ),
                                onClick=[
                                    SetState("rendering_3d", True),
                                    SetState("render_error", ""),
                                    Fetch(
                                        f"{API}/api/3d",
                                        method="POST",
                                        # Rx("current_topic.id") reads nested state
                                        body={"topic_id": Rx("current_topic.id")},
                                        onSuccess=[
                                            SetState("rendering_3d", False),
                                            SetState("video_url",    RESULT["video_url"]),
                                        ],
                                        onError=[
                                            SetState("rendering_3d", False),
                                            SetState("render_error", RESULT["error"]),
                                        ],
                                    ),
                                ],
                            )
                        with Else():
                            with Row(cssClass="items-center gap-3"):
                                Loader()
                                Muted("Blender is rendering your 3D scene… (~2 min) 🎨")
                    with Else():
                        # video_url from Flask is "/output/scene_xxx.mp4"
                        # Prepend API base with template: {{video_url}} is reactive
                        Video(
                            src=f"{API}{{{{video_url}}}}",
                            controls=True,
                            cssClass="w-full rounded-xl shadow-lg mt-2",
                        )
                    with If("render_error"):
                        Badge(
                            Rx("render_error"),
                            cssClass="bg-red-100 text-red-700 border-red-200 mt-2",
                        )

                    # Related questions ───────────────────────────────────────
                    with If("related"):
                        Separator(cssClass="my-4 border-teal-100")
                        H3("🔗 Explore Further", cssClass="font-bold text-teal-700 mb-2")
                        with Row(cssClass="flex-wrap gap-2"):
                            with ForEach("related"):
                                Button(
                                    ITEM["topic"]["question"],
                                    variant="outline",
                                    size="sm",
                                    cssClass=(
                                        "border-teal-200 text-teal-700 "
                                        "hover:bg-teal-100"
                                    ),
                                    onClick=[
                                        SetState("current_topic", ITEM["topic"]),
                                        SetState("related",       []),
                                        SetState("video_url",     ""),
                                        SetState("render_error",  ""),
                                    ],
                                )

                    # Agent log (only visible during or after ask) ─────────────
                    with If("log_lines"):
                        Separator(cssClass="my-4")
                        H3(
                            "🤖 Agent Log",
                            cssClass="text-xs font-bold text-muted-foreground mb-2",
                        )
                        with Card(cssClass="border-slate-200"):
                            with CardContent(
                                cssClass="p-3 max-h-48 overflow-y-auto font-mono"
                            ):
                                with ForEach("log_lines"):
                                    Text(
                                        content=ITEM,
                                        cssClass="text-xs text-slate-500 block",
                                    )

                with Else():
                    with Card(
                        cssClass="border-dashed border-purple-200 bg-purple-50/40 mt-8"
                    ):
                        with CardContent(
                            cssClass="py-16 flex flex-col items-center gap-3"
                        ):
                            H2("🤔", cssClass="text-6xl")
                            Muted("Select a topic from the sidebar or ask a new question!")

            # ── STATS ────────────────────────────────────────────────────────
            with Page(value="stats", title="Stats"):
                H2(
                    "📊 Your Curiosity Map",
                    cssClass="text-2xl font-extrabold text-purple-700 mb-4",
                )

                with Row(cssClass="gap-4 flex-wrap mb-6"):
                    with Card(cssClass="flex-1 min-w-32 border-purple-100 bg-purple-50/50"):
                        with CardContent(cssClass="pt-4"):
                            Metric(
                                label="🧩 Total Topics",
                                value=Rx("stats.total"),
                            )
                    with Card(cssClass="flex-1 min-w-32 border-orange-100 bg-orange-50/50"):
                        with CardContent(cssClass="pt-4"):
                            Metric(
                                label="🔥 Day Streak",
                                value=Rx("stats.streak"),
                                description="days in a row",
                            )
                    with Card(cssClass="flex-1 min-w-32 border-teal-100 bg-teal-50/50"):
                        with CardContent(cssClass="pt-4"):
                            Metric(
                                label="⚡ This Week",
                                value=Rx("stats.this_week"),
                                description="new topics",
                            )

                with If("stats.top_branch"):
                    with Card(cssClass="mb-4 border-yellow-200 bg-yellow-50"):
                        with CardHeader():
                            CardTitle("🌟 Top Knowledge Branch")
                        with CardContent():
                            Text(
                                content=Rx("stats.top_branch"),
                                bold=True,
                                cssClass="text-yellow-800",
                            )

                with If("stats.top_tags"):
                    H3("🏷️ All Tags", cssClass="font-bold text-purple-700 mb-3")
                    with Row(cssClass="flex-wrap gap-2"):
                        with ForEach("stats.top_tags"):
                            Badge(
                                ITEM["tag"],
                                cssClass="bg-purple-100 text-purple-700 border-purple-200",
                            )

            # ── LOGS ─────────────────────────────────────────────────────────
            # SetInterval starts on the onClick of the "Logs" nav button.
            # It polls /api/logs every 2 s while state["on_logs_page"] is True.
            # Navigating away sets on_logs_page=False which stops the timer.
            with Page(value="logs", title="Logs"):
                with Row(cssClass="items-center justify-between mb-4"):
                    H2(
                        "📋 Agent Logs",
                        cssClass="text-2xl font-extrabold text-purple-700",
                    )
                    Button(
                        "🔄 Refresh",
                        variant="outline",
                        size="sm",
                        cssClass="border-purple-200 text-purple-600",
                        onClick=_fetch_logs,
                    )
                Muted(
                    "Live log feed — auto-refreshes every 2 s while this page is open."
                )
                Separator(cssClass="my-4 border-purple-100")

                with If("log_lines"):
                    with Card(cssClass="border-slate-200"):
                        with CardContent(
                            cssClass=(
                                "p-4 max-h-screen overflow-y-auto "
                                "font-mono bg-slate-950 rounded-xl"
                            )
                        ):
                            with ForEach("log_lines"):
                                Text(
                                    content=ITEM,
                                    cssClass=(
                                        "text-xs text-green-400 block "
                                        "py-0.5 border-b border-slate-800"
                                    ),
                                )
                with Else():
                    with Card(cssClass="border-dashed border-slate-300 mt-4"):
                        with CardContent(cssClass="py-12 text-center"):
                            Muted("No logs yet — ask a question to see agent activity!")


# ─── Assemble the app ─────────────────────────────────────────────────────────
app = PrefabApp(
    title="Whyzzle — Curiosity Map",
    view=root,
    state=INIT_STATE,
    connect_domains=[API],
    # Nunito gives the UI a rounded, friendly feel for kids
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap",
        (
            "* { font-family: 'Nunito', sans-serif !important; } "
            "body { background: transparent; }"
        ),
    ],
)

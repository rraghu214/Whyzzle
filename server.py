"""
Whyzzle — FastMCP + Prefab server  (Step 2 stub)
=================================================
One FastMCP server replaces both the old server.py (raw MCP) and
webapp.py (Flask). The UI renders inside Claude Desktop via Prefab.

Claude Desktop config  (~AppData/Roaming/Claude/claude_desktop_config.json):
{
  "mcpServers": {
    "whyzzle": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "C:/Raghu/MyLearnings/EAG_V3/S4-25042026/Whyzzle"
    }
  }
}
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Card, CardHeader, CardTitle, CardContent, Muted,
)

mcp = FastMCP("Whyzzle")


# ── Step 2: minimal dashboard stub ────────────────────────────────────────────

@mcp.tool(app=True)
def whyzzle_dashboard() -> PrefabApp:
    """Open the Whyzzle curiosity dashboard."""
    with Card() as card:
        with CardHeader():
            CardTitle("🧠 Whyzzle")
        with CardContent():
            Muted("Ask anything. See everything.")

    return PrefabApp(view=card, state={})


if __name__ == "__main__":
    mcp.run()

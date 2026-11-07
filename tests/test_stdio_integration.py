"""Integration test: real MCP client talks to the server over stdio.

Spawns a fresh ``python -m boardgame_mcp.server`` process and performs an
actual JSON-RPC handshake, so we know the server works with stdio MCP
clients, not just as a library.
"""

import sys

import pytest

from mcp.client import Client
from mcp.client.client import StdioServerParameters


def stdio_params(log_path):
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "boardgame_mcp.server", "--log", str(log_path)],
    )


@pytest.mark.anyio
async def test_stdio_roundtrip(tmp_path):
    params = stdio_params(tmp_path / "boardgames.json")
    async with Client(params) as client:
        result = await client.list_tools()
        tools = result.tools if hasattr(result, "tools") else (
            result[0] if isinstance(result, tuple) else result
        )
        names = {t.name for t in tools}
        assert {
            "add_game", "list_games", "search_games", "remove_game",
            "record_play", "recent_plays", "unplayed_games",
            "weeknight_picks", "collection_summary",
        } <= names

        added = await client.call_tool("add_game", {
            "title": "Wingspan", "min_players": 1,
            "max_players": 5, "play_minutes": 60,
        })
        assert "Added **Wingspan**" in added.content[0].text

        played = await client.call_tool("record_play", {
            "query": "wingspan", "date": "2026-11-06",
            "players": ["Dana", "Sam"], "winner": "Dana",
        })
        assert "Friday 2026-11-06" in played.content[0].text

        picks = await client.call_tool("weeknight_picks", {"player_count": 5})
        assert "Wingspan" in picks.content[0].text

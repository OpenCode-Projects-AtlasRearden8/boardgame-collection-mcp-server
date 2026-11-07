"""End-to-end tool tests: build_server + call_tool against a temp log file."""

import asyncio
import json

import pytest

from boardgame_mcp.server import build_server

LOG = None  # filled by fixture


@pytest.fixture()
def server_with_log(tmp_path):
    log_path = tmp_path / "boardgames.json"
    svc = build_server(log_path)

    async def call(name, args=None):
        result = await svc.call_tool(name, args or {})
        assert not result.is_error, result.content
        return result.content[0].text

    return call, svc, log_path


def test_full_agent_workflow(server_with_log):
    call, _, log_path = server_with_log

    async def run():
        added = await call("add_game", {
            "title": "The Crew: Mission Deep Sea",
            "min_players": 2, "max_players": 5, "play_minutes": 45,
            "weeknight": True, "notes": "co-op",
        })
        assert "**The Crew: Mission Deep Sea**" in added
        assert "`the-crew-mission-deep-sea`" in added

        added2 = await call("add_game", {
            "title": "Gloomhaven", "min_players": 1,
            "max_players": 4, "play_minutes": 120,
        })
        assert "Added" in added2

        played = await call("record_play", {
            "query": "The Crew", "date": "2026-11-06",
            "players": ["Dana", "Sam", "Alex"], "winner": "", "minutes": 44,
        })
        assert "Friday" in played and "The Crew" in played

        recent = await call("recent_plays", {"limit": 3})
        assert "**The Crew: Mission Deep Sea** on Friday 2026-11-06" in recent

        shelf = await call("unplayed_games")
        assert "still on the shelf" in shelf and "Gloomhaven" in shelf
        assert "The Crew" not in shelf

        picks = await call("weeknight_picks", {"player_count": 5})
        assert "The Crew: Mission Deep Sea" in picks
        assert "Gloomhaven" not in picks

        listed = await call("list_games")
        assert "1 play · last played Friday 2026-11-06" in listed

        searched = await call("search_games", {"query": "crew"})
        assert "The Crew" in searched and "Gloomhaven" not in searched

        summary = await call("collection_summary")
        assert "2 games cataloged, 1 play recorded." in summary

        removed = await call("remove_game", {"query": "gloomhaven"})
        assert "Removed **Gloomhaven**" in removed

        # the log file exists, is plain JSON, and reflects remove + play
        data = json.loads(log_path.read_text(encoding="utf-8"))
        assert [g["id"] for g in data["games"]] == ["the-crew-mission-deep-sea"]
        assert data["plays"][0]["date"] == "2026-11-06"

    asyncio.run(run())


def test_duplicate_add_reports_error_in_chat(server_with_log):
    call, _, _ = server_with_log

    async def run():
        first = await call("add_game", {
            "title": "Wingspan", "min_players": 1,
            "max_players": 5, "play_minutes": 60,
        })
        dup = await call("add_game", {
            "title": "Wingspan", "min_players": 1,
            "max_players": 5, "play_minutes": 60,
        })
        assert "Sorry, that didn't work: a game with id 'wingspan' already exists" in dup
        assert not first.startswith("Sorry")

    asyncio.run(run())


def test_broken_tool_input_does_not_crash_server(server_with_log):
    call, _, _ = server_with_log

    async def run():
        await call("add_game", {
            "title": "Broken Box", "min_players": 5,
            "max_players": 2, "play_minutes": 30,
        })
        missing = await call("record_play", {"query": "does-not-exist", "date": "2026-11-06"})
        assert "no game matching" in missing

    asyncio.run(run())


def test_hand_edited_log_is_respected(server_with_log):
    call, _, log_path = server_with_log
    log_path.write_text(
        json.dumps({
            "games": [{"id": "handmade", "title": "Handmade", "min_players": 3,
                       "max_players": 6, "play_minutes": 30, "weeknight": True,
                       "notes": "typed by a human"}],
            "plays": [],
        }),
        encoding="utf-8",
    )

    async def run():
        return await call("unplayed_games")

    shelf = asyncio.run(run())
    assert "Handmade" in shelf and "typed by a human" not in shelf  # shelf is game text


def test_missing_log_starts_empty(server_with_log):
    call, _, log_path = server_with_log

    async def run():
        listed = await call("list_games")
        summary = await call("collection_summary")
        assert "No games in the catalog yet." in listed
        assert "catalog is empty" in summary

    asyncio.run(run())
    assert not log_path.exists()  # read-only tools never create files

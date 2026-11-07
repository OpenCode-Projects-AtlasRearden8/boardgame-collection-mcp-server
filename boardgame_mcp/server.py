"""MCP server exposing the board game log as agent tools.

Run with::

    python -m boardgame_mcp.server          # stdio (what MCP clients expect)

By default the log lives at ``./boardgames.json`` (created on first write);
point at another file with ``BOARDGAME_LOG=<path>`` or ``--log <path>``.

Copyright (c) 2026 Asdale Dynamics, LLC
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import stats, text
from .catalog import CatalogError, load_collection_or_empty, save_collection

DEFAULT_LOG = "boardgames.json"
DEFAULT_WEEKNIGHT_BUDGET_MINUTES = stats.DEFAULT_WEEKNIGHT_BUDGET_MINUTES

INSTRUCTIONS = """\
Board game collection helper over a plain JSON file on this machine.

Catalog games (title, player count, play time), record plays with winners,
and then ask for: recent plays, unplayed (shelf) games, or titles that fit
N players inside a weeknight time budget. All answers are chat-ready text.
"""


def _friendly_error(exc: Exception) -> str:
    return f"Sorry, that didn't work: {exc}"


class BoardGameService:
    """Loads the log file on every call so hand-edits are always respected."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)

    def _load(self):
        collection, _existed = load_collection_or_empty(self.log_path)
        return collection

    # -- catalog -------------------------------------------------------

    def add(
        self, title: str, min_players: int, max_players: int,
        play_minutes: int, weeknight: bool | None = None, notes: str = "",
    ) -> str:
        collection = self._load()
        game = collection.add_game(
            title, min_players, max_players, play_minutes,
            weeknight=weeknight, notes=notes,
        )
        save_collection(collection, self.log_path)
        if weeknight is None and game.play_minutes <= DEFAULT_WEEKNIGHT_BUDGET_MINUTES:
            hint = " It fits the default 90-minute weeknight budget."
        else:
            hint = ""
        return f"Added **{game.title}** (`{game.id}`).{hint}"

    def list(self) -> str:
        collection = self._load()
        counts = stats.play_counts(collection)
        last = {
            gid: p.date
            for gid in collection.games
            if (p := collection.most_recent_play_for(gid))
        }
        return text.format_games(
            collection.sorted_games(), play_counts=counts, last_played=last,
        )

    def search(self, query: str) -> str:
        collection = self._load()
        lowered = query.strip().lower()
        matches = [
            g for g in collection.sorted_games()
            if lowered in g.title.lower() or lowered in g.id
        ]
        if not matches:
            return f"No games in the catalog match {query!r}."
        return text.format_games(matches)

    def remove(self, query: str) -> str:
        collection = self._load()
        game = collection.remove_game(query)
        save_collection(collection, self.log_path)
        return (
            f"Removed **{game.title}** (`{game.id}`) and its play history."
        )

    # -- plays ---------------------------------------------------------

    def record_play(
        self, query: str, date_str: str = "", players: list[str] | None = None,
        winner: str = "", minutes: int | None = None,
    ) -> str:
        collection = self._load()
        game = collection.find(query)
        when = date_str or date.today().isoformat()
        play = collection.record_play(
            game.id, when, players=players, winner=winner, minutes=minutes,
        )
        save_collection(collection, self.log_path)
        day = text._weekday_name(play.date)
        return (
            f"Recorded a play of **{game.title}** on {day} {play.date}.\n"
            f"The log now has {len(collection.plays)} recorded plays."
        )

    def recent(self, limit: int = 5) -> str:
        collection = self._load()
        pairs = stats.recent_plays(collection, date.today(), limit)
        return text.format_plays(pairs)

    # -- reports -------------------------------------------------------

    def shelf(self) -> str:
        collection = self._load()
        return text.format_unplayed(stats.unplayed_games(collection))

    def picks(self, player_count: int = 5, max_minutes: int | None = None) -> str:
        budget = max_minutes or DEFAULT_WEEKNIGHT_BUDGET_MINUTES
        collection = self._load()
        picks = stats.weeknight_picks(collection, player_count, max_minutes=budget)
        return text.format_picks(picks, player_count, budget)

    def summary(self) -> str:
        collection = self._load()
        return text.format_summary(
            collection, stats.play_counts(collection),
            stats.winner_leaderboard(collection),
        )


def build_server(log_path: str | Path, name: str = "Board Game Collection") -> MCPServer:
    """Create the MCP server wired to a log file (handy for tests too)."""
    service = BoardGameService(log_path)
    mcp = MCPServer(
        name,
        title="Board Game Collection",
        description="Board game log tools for an LLM agent: local JSON in, chat-ready text out.",
        instructions=INSTRUCTIONS,
        version="0.1.0",
    )

    @mcp.tool()
    def add_game(
        title: str, min_players: int, max_players: int, play_minutes: int,
        weeknight: bool | None = None, notes: str = "",
    ) -> str:
        """Add a board game to the catalog: title, supported player count,
        typical play time in minutes. weeknight (optional) is a manual flag
        meaning "fine for a weeknight"; notes are free text."""
        try:
            return service.add(title, min_players, max_players, play_minutes,
                               weeknight=weeknight, notes=notes)
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def list_games() -> str:
        """List every game in the catalog with play counts and last-play dates."""
        try:
            return service.list()
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def search_games(query: str) -> str:
        """Find games whose title or id contains the given text."""
        try:
            return service.search(query)
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def remove_game(query: str) -> str:
        """Remove a game (by title or id) and its play history from the log."""
        try:
            return service.remove(query)
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def record_play(
        query: str, date: str = "", players: list[str] | None = None,
        winner: str = "", minutes: int | None = None,
    ) -> str:
        """Record one session of a game (title or id). date is YYYY-MM-DD
        (defaults to today). players is an optional list of names; winner
        (optional) must be on that list; minutes is actual table time."""
        try:
            return service.record_play(query, date, players, winner, minutes)
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def recent_plays(limit: int = 5) -> str:
        """The most recent plays, newest first, with players and winners."""
        try:
            return service.recent(limit)
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def unplayed_games() -> str:
        """Games in the catalog that have never been played (the shelf)."""
        try:
            return service.shelf()
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def weeknight_picks(player_count: int = 5, max_minutes: int | None = None) -> str:
        """Which titles fit a group size within a weeknight time budget
        (default: 5 players, 90 minutes). Quickest first."""
        try:
            return service.picks(player_count, max_minutes)
        except CatalogError as exc:
            return _friendly_error(exc)

    @mcp.tool()
    def collection_summary() -> str:
        """Quick totals: games cataloged, plays recorded, top game and top winner."""
        try:
            return service.summary()
        except CatalogError as exc:
            return _friendly_error(exc)

    return mcp


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - entry point
    parser = argparse.ArgumentParser(
        prog="boardgame-mcp",
        description="MCP server over a plain-file board game log.",
    )
    parser.add_argument(
        "--log", default=os.environ.get("BOARDGAME_LOG", DEFAULT_LOG),
        help="path to the JSON log file (default: %(default)s)",
    )
    parser.add_argument(
        "--transport", default="stdio", choices=["stdio", "streamable-http", "sse"],
        help="MCP transport (default: stdio)",
    )
    args = parser.parse_args(argv)
    server = build_server(args.log)
    server.run(transport=args.transport)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

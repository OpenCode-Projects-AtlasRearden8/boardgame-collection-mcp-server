"""Stats and queries over the board game log.

Pure functions: they take a :class:`~boardgame_mcp.catalog.Collection` and
plain values (today's date, limits) and return plain data. Formatting for
chat output lives in :mod:`boardgame_mcp.text`.

Copyright (c) 2026 Asdale Dynamics, LLC
"""

from __future__ import annotations

from datetime import date, timedelta

from .catalog import Collection, Game, Play

DEFAULT_WEEKNIGHT_BUDGET_MINUTES = 90


def recent_plays(
    collection: Collection, today: date, limit: int = 5
) -> list[tuple[Play, Game | None]]:
    """The ``limit`` most recent plays, newest first, paired with their game."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    max_date = today + timedelta(days=1)
    past = [p for p in collection.plays if date.fromisoformat(p.date) <= max_date]
    return [
        (play, collection.games.get(play.game_id))
        for play in sorted(past, key=lambda p: p.date, reverse=True)[:limit]
    ]


def unplayed_games(collection: Collection) -> list[Game]:
    """Shelf items that have never hit the table."""
    played = collection.titles_played()
    return [g for g in collection.sorted_games() if g.id not in played]


def weeknight_picks(
    collection: Collection,
    player_count: int = 5,
    *,
    max_minutes: int = DEFAULT_WEEKNIGHT_BUDGET_MINUTES,
    require_weeknight_flag: bool = False,
) -> list[Game]:
    """Games that fit ``player_count`` people inside a weeknight time budget.

    A game qualifies when:
      * its player range covers ``player_count``, and
      * its typical play time is at most ``max_minutes`` (default 90).

    By default the time budget alone decides; a manual ``weeknight: true``
    flag may be required instead with ``require_weeknight_flag=True``.
    Results are sorted by quickest first.
    """
    if player_count < 1:
        raise ValueError("player_count must be at least 1")
    if max_minutes < 1:
        raise ValueError("max_minutes must be at least 1")

    def fits(g: Game) -> bool:
        if require_weeknight_flag:
            return g.weeknight is True
        return g.play_minutes <= max_minutes

    return sorted(
        (g for g in collection.sorted_games()
         if g.supports(player_count) and fits(g)),
        key=lambda g: (g.play_minutes, g.title.lower()),
    )


def play_counts(collection: Collection) -> dict[str, int]:
    """Total recorded plays per game id, highest first, ties alphabetical."""
    counts: dict[str, int] = {}
    for play in collection.plays:
        counts[play.game_id] = counts.get(play.game_id, 0) + 1
    return dict(
        sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )


def winner_leaderboard(
    collection: Collection, limit: int = 10
) -> list[tuple[str, int]]:
    """Wins per player across all plays, highest first.

    Ties and co-op wins (empty ``winner``) don't count for anyone.
    """
    wins: dict[str, int] = {}
    for play in collection.plays:
        if play.winner:
            wins[play.winner] = wins.get(play.winner, 0) + 1
    ranked = sorted(wins.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    ranked = ranked[:max(1, limit)]
    return ranked

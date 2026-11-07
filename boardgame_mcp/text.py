"""Chat-ready text formatting for the board game log.

"Local files in, chat-ready text out": every tool result is a short,
friendly block of text an agent can paste straight into a conversation.

Copyright (c) 2026 Asdale Dynamics, LLC
"""

from __future__ import annotations

from datetime import date

WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday",
]


def _weekday_name(date_str: str) -> str:
    return WEEKDAY_NAMES[date.fromisoformat(date_str).weekday()]


def format_game(
    game,
    *,
    play_count: int | None = None,
    last_played: str | None = None,
) -> str:
    """One-line game summary, e.g. ``- Wingspan — 1-5 players, ~60 min``."""
    bits = [f"**{game.title}**", f"{game.min_players}-{game.max_players} players",
            f"~{game.play_minutes} min"]
    if play_count is not None:
        plural = "play" if play_count == 1 else "plays"
        bits.append(f"{play_count} {plural}")
    if last_played:
        bits.append(f"last played {_weekday_name(last_played)} {last_played}")
    return "- " + " · ".join(bits)


def format_games(
    games,
    *,
    play_counts: dict[str, int] | None = None,
    last_played: dict[str, str] | None = None,
) -> str:
    play_counts = play_counts or {}
    last_played = last_played or {}
    lines = [
        format_game(
            g,
            play_count=play_counts.get(g.id),
            last_played=last_played.get(g.id),
        )
        for g in games
    ]
    if not lines:
        return "No games in the catalog yet."
    header = f"{len(games)} game{'s' if len(games) != 1 else ''} in the catalog:"
    return header + "\n" + "\n".join(lines)


def format_plays(plays_with_games, *, today=None) -> str:
    """Format ``(play, game)`` pairs from ``stats.recent_plays``.

    ``today`` (optional ISO date) lets us mark future-dated plans distinctly.
    """
    if not plays_with_games:
        return "No plays recorded yet."
    lines = []
    for play, game in plays_with_games:
        title = game.title if game else play.game_id + " (not in catalog)"
        when = f"{_weekday_name(play.date)} {play.date}"
        bits = [f"- **{title}** on {when}"]
        if play.players:
            outcome = f"winner: {play.winner}" if play.winner else "no winner recorded"
            bits.append(f"players: {', '.join(play.players)}; {outcome}")
        else:
            bits.append("no players listed")
        if play.minutes:
            bits.append(f"took ~{play.minutes} min")
        lines.append(" — ".join(bits))
    count = len(plays_with_games)
    header = f"{count} play{'s' if count != 1 else ''}, most recent first:"
    return header + "\n" + "\n".join(lines)


def format_unplayed(games) -> str:
    if not games:
        return "Every game in the catalog has been played at least once!"
    lines = [f"{len(games)} game{'s' if len(games) != 1 else ''} still on the shelf:"]
    lines += [format_game(g) for g in games]
    return "\n".join(lines)


def format_picks(games, player_count: int, max_minutes: int) -> str:
    """Format picks for "which titles fit N players on a weeknight"."""
    if not games:
        return (
            f"No games fit {player_count} players in under {max_minutes} minutes."
        )
    lines = [
        f"{len(games)} title{'s' if len(games) != 1 else ''} fit {player_count} players "
        f"in under {max_minutes} minutes (quickest first):"
    ]
    lines += [format_game(g) for g in games]
    return "\n".join(lines)


def format_summary(
    collection,
    play_counts: dict[str, int],
    leaderboard: list[tuple[str, int]],
) -> str:
    total_games = len(collection.games)
    total_plays = len(collection.plays)
    if total_games == 0:
        return "The catalog is empty — add your first game with `add_game`."
    play_word = "play" if total_plays == 1 else "plays"
    lines = [f"{total_games} games cataloged, {total_plays} {play_word} recorded."]
    if play_counts:
        top_id, top_count = next(iter(play_counts.items()))
        top_title = getattr(collection.games.get(top_id), "title", top_id)
        word = "play" if top_count == 1 else "plays"
        lines.append(f"Most played: {top_title} ({top_count} {word})")
    if leaderboard:
        best_player, best_wins = leaderboard[0]
        word = "win" if best_wins == 1 else "wins"
        lines.append(f"Top winner: {best_player} ({best_wins} {word})")
    return "\n".join(lines)

"""Tests for chat-ready text formatting."""

from boardgame_mcp.catalog import Collection, Play
from boardgame_mcp.stats import recent_plays, unplayed_games, weeknight_picks
from boardgame_mcp.text import (
    format_games,
    format_plays,
    format_picks,
    format_summary,
    format_unplayed,
)

from datetime import date


def build():
    c = Collection()
    c.add_game("Wingspan", 1, 5, 60)
    c.add_game("Azul", 2, 4, 45)
    c.record_play("azul", "2026-11-06", ["Dana", "Sam"], "Dana", 47)  # a Friday
    return c


class TestFormatGames:
    def test_listing_shows_players_time_and_counts(self):
        c = build()
        out = format_games(c.sorted_games(), play_counts={"azul": 1})
        assert "2 games in the catalog:" in out
        assert "**Azul**" in out and "2-4 players" in out and "~45 min" in out
        assert "1 play" in out

    def test_empty_catalog_message(self):
        assert "No games" in format_games([])


class TestFormatPlays:
    def test_recent_plays_block(self):
        c = build()
        pairs = recent_plays(c, date(2026, 11, 7), limit=5)
        out = format_plays(pairs)
        assert "**Azul** on Friday 2026-11-06" in out
        assert "winner: Dana" in out
        assert "took ~47 min" in out

    def test_no_plays_message(self):
        assert "No plays" in format_plays([])

    def test_orphan_play_names_the_missing_game(self):
        play = Play(game_id="vanished", date="2026-11-06")
        out = format_plays([(play, None)])
        assert "vanished" in out and "not in catalog" in out


class TestFormatUnplayed:
    def test_shelf_listing(self):
        c = build()
        shelf = unplayed_games(c)
        out = format_unplayed(shelf)
        assert "1 game still on the shelf" in out
        assert "Wingspan" in out

    def test_no_shelf_left(self):
        assert "at least once" in format_unplayed([])


class TestFormatPicks:
    def test_weeknight_answer(self):
        c = build()
        picks = weeknight_picks(c, 5)
        out = format_picks(picks, 5, 90)
        assert "fit 5 players in under 90 minutes" in out
        assert "quickest first" in out

    def test_nothing_fits_message(self):
        out = format_picks([], 5, 90)
        assert "No games fit 5 players" in out


class TestFormatSummary:
    def test_totals_and_leaders(self):
        c = build()
        out = format_summary(c, {"azul": 1}, [("Dana", 1)])
        assert "2 games cataloged, 1 play recorded." in out
        assert "Most played: Azul (1 play)" in out
        assert "Top winner: Dana (1 win)" in out

    def test_empty_catalog_hint(self):
        assert "add your first game" in format_summary(Collection(), {}, [])

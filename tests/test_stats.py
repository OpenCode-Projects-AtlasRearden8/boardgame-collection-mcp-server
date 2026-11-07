"""Tests for stats/report logic: recent plays, shelf, weeknight picks."""

from datetime import date

import pytest

from boardgame_mcp.catalog import Collection
from boardgame_mcp.stats import (
    play_counts,
    recent_plays,
    unplayed_games,
    weeknight_picks,
    winner_leaderboard,
)

FRIDAY = date(2026, 11, 6)  # a Friday: perfect weeknight
SATURDAY = date(2026, 11, 7)


def make_collection() -> Collection:
    c = Collection()
    #        title                       min  max  minutes  weeknight flag
    c.add_game("Storybook Clan",          1,   4,     40, weeknight=True)
    c.add_game("Bazaar Royale",           2,   5,     60, weeknight=None)
    c.add_game("Empire of Candles",       3,   5,    240, weeknight=False)
    c.add_game("Duelist Crossing",        2,   2,     30, weeknight=None)
    c.add_game("Sixth Harbor",            5,   8,     75, weeknight=True)
    return c


class TestRecentPlays:
    def test_newest_first_with_limit(self):
        c = make_collection()
        c.record_play("bazaar-royale", "2026-10-01", ["Dana", "Sam"], "Dana")
        c.record_play("storybook-clan", "2026-11-03", ["Dana"], "Dana")
        c.record_play("duelist-crossing", "2026-11-05", ["Dana", "Sam"], "Dana")

        pairs = recent_plays(c, FRIDAY, limit=2)
        dates = [p.date for p, _ in pairs]
        assert dates == ["2026-11-05", "2026-11-03"]

    def test_unknown_game_id_still_shown(self):
        c = make_collection()
        c.add_game("Temp Box", 1, 2, 20)
        c.record_play("temp-box", "2026-11-03", ["Dana"], "Dana")
        c.remove_game("temp-box")  # removes history too; craft a stray play
        from boardgame_mcp.catalog import Play
        c.plays.append(Play(game_id="gone-game", date="2026-11-04"))
        pairs = recent_plays(c, FRIDAY)
        assert pairs == [(c.plays[-1], None)]

    def test_limit_must_be_positive(self):
        c = make_collection()
        with pytest.raises(ValueError):
            recent_plays(c, FRIDAY, limit=0)

    def test_future_plans_hidden_until_played(self):
        c = make_collection()
        c.record_play("bazaar-royale", "2026-12-25", ["Dana", "Sam"], "Dana")
        assert recent_plays(c, FRIDAY) == []
        assert [p.date for p, _ in recent_plays(c, date(2026, 12, 26))] == ["2026-12-25"]


class TestUnplayedGames:
    def test_only_never_played_shown(self):
        c = make_collection()
        c.record_play("bazaar-royale", "2026-10-01", ["Dana", "Sam"], "Dana")
        shelf = [g.id for g in unplayed_games(c)]
        assert shelf == ["duelist-crossing", "empire-of-candles",
                         "sixth-harbor", "storybook-clan"]

    def test_all_played_means_empty_shelf(self):
        c = Collection()
        c.add_game("Tiny Box", 1, 2, 20)
        c.record_play("tiny-box", "2026-11-02", ["Dana"], "Dana")
        assert unplayed_games(c) == []


class TestWeeknightPicks:
    def test_five_players_weeknight_default_budget(self):
        c = make_collection()
        picks = [g.id for g in weeknight_picks(c, 5)]
        # Bazaar Royale and Sixth Harbor seat 5 under 90 min; Empire of
        # Candles (240 min) and games that don't seat 5 are out.
        assert picks == ["bazaar-royale", "sixth-harbor"]

    def test_larger_budget_includes_long_games(self):
        c = make_collection()
        picks = [g.id for g in weeknight_picks(c, 5, max_minutes=300)]
        # quickest first: 60, 75, then 240
        assert picks == ["bazaar-royale", "sixth-harbor", "empire-of-candles"]

    def test_lone_player(self):
        c = make_collection()
        picks = [g.id for g in weeknight_picks(c, 1)]
        assert picks == ["storybook-clan"]

    def test_pair(self):
        c = make_collection()
        picks = [g.id for g in weeknight_picks(c, 2)]
        assert picks == ["duelist-crossing", "storybook-clan", "bazaar-royale"]

    def test_too_many_players(self):
        c = make_collection()
        assert weeknight_picks(c, 9) == []

    def test_manual_weeknight_flag_mode(self):
        c = make_collection()
        # Bazaar Royale fits at 60 min but has weeknight=None, so flag mode
        # excludes it even though the budget would allow it.
        picks = [g.id for g in weeknight_picks(
            c, 5, max_minutes=90, require_weeknight_flag=True)]
        assert picks == ["sixth-harbor"]

    def test_sorting_is_quickest_first_alphabetical_ties(self):
        c = make_collection()
        c.add_game("Alpha Rapid", 1, 5, 40, weeknight=True)
        c.add_game("Beta Rapid", 1, 5, 40, weeknight=True)
        picks = [g.id for g in weeknight_picks(c, 5)]
        assert picks == ["alpha-rapid", "beta-rapid", "bazaar-royale", "sixth-harbor"]

    def test_invalid_args(self):
        c = make_collection()
        with pytest.raises(ValueError):
            weeknight_picks(c, 0)
        with pytest.raises(ValueError):
            weeknight_picks(c, 5, max_minutes=0)


class TestPlayCountsAndWins:
    def test_play_counts_sorted(self):
        c = make_collection()
        c.record_play("bazaar-royale", "2026-10-01", ["Dana", "Sam"], "Dana")
        c.record_play("bazaar-royale", "2026-10-08", ["Dana", "Sam"], "Dana")
        c.record_play("storybook-clan", "2026-10-02", ["Dana"], "Dana")
        counts = play_counts(c)
        assert list(counts.items()) == [
            ("bazaar-royale", 2), ("storybook-clan", 1)
        ]

    def test_counts_alphabetical_on_ties(self):
        c = make_collection()
        c.add_game("Alpha Tray", 1, 2, 20)
        for gid in ("bazaar-royale", "alpha-tray", "alpha-tray", "bazaar-royale"):
            c.record_play(gid, "2026-10-01", ["Dana", "Sam"], "Dana")
        assert list(play_counts(c).items()) == [
            ("alpha-tray", 2), ("bazaar-royale", 2)
        ]

    def test_winner_leaderboard(self):
        c = make_collection()
        for _ in range(3):
            c.record_play("duelist-crossing", "2026-10-01", ["Dana", "Sam"], "Dana")
        c.record_play("bazaar-royale", "2026-10-08", ["Dana", "Priya"], "Priya")
        c.record_play("bazaar-royale", "2026-10-09", ["Dana", "Priya"], "")  # tie
        board = winner_leaderboard(c)
        assert board == [("Dana", 3), ("Priya", 1)]

    def test_leaderboard_limit(self):
        c = make_collection()
        c.record_play("duelist-crossing", "2026-10-01", ["Dana", "Sam"], "Dana")
        c.record_play("duelist-crossing", "2026-10-02", ["Dana", "Sam"], "Sam")
        c.record_play("duelist-crossing", "2026-10-03", ["Dana", "Sam"], "Dana")
        c.record_play("bazaar-royale", "2026-10-04", ["Dana", "Priya"], "Priya")
        c.record_play("bazaar-royale", "2026-10-05", ["Dana", "Priya"], "Priya")
        board = winner_leaderboard(c, limit=3)
        assert board == [("Dana", 2), ("Priya", 2), ("Sam", 1)]

    def test_coop_ties_never_count_as_wins(self):
        c = make_collection()
        c.record_play("bazaar-royale", "2026-10-01", ["Dana", "Sam"], "")
        assert winner_leaderboard(c) == []

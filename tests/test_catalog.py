"""Tests for the plain-file catalog (games, plays, load/save)."""

import json

import pytest

from boardgame_mcp.catalog import (
    CatalogError,
    Collection,
    is_weeknight,
    load_collection,
    save_collection,
    slugify,
)

GAME = dict(title="Wingspan", min_players=1, max_players=5, play_minutes=60)


def make_collection() -> Collection:
    c = Collection()
    c.add_game("Wingspan", 1, 5, 60)
    c.add_game("Azul", 2, 4, 45)
    return c


class TestSlugify:
    def test_simple_title(self):
        assert slugify("Wingspan") == "wingspan"

    def test_punctuation_and_case(self):
        assert slugify("Heat: Pedal to the Metal!") == "heat-pedal-to-the-metal"

    def test_blank_becomes_placeholder(self):
        assert slugify("   ") == "game"


class TestAddGame:
    def test_add_and_get(self):
        c = Collection()
        g = c.add_game(**GAME)
        assert g.id == "wingspan"
        assert c.get_game("wingspan") is g

    def test_duplicate_id_rejected(self):
        c = make_collection()
        # "Azul." slugs to "azul", which is already taken.
        with pytest.raises(CatalogError, match="already exists"):
            c.add_game("Azul.", 2, 4, 45)

    def test_reversed_player_range_rejected(self):
        c = Collection()
        with pytest.raises(CatalogError, match="max_players"):
            c.add_game("Broken", 5, 2, 30)

    def test_zero_players_rejected(self):
        c = Collection()
        with pytest.raises(CatalogError, match="min_players"):
            c.add_game("Solitaire Ghost", 0, 1, 20)

    def test_zero_minutes_rejected(self):
        c = Collection()
        with pytest.raises(CatalogError, match="play_minutes"):
            c.add_game("Instant Game", 1, 4, 0)

    def test_supports(self):
        g = Collection().add_game(**GAME)
        assert g.supports(1) and g.supports(5)
        assert not g.supports(6) and not g.supports(0)


class TestFind:
    def test_find_by_title_case_insensitive(self):
        c = make_collection()
        assert c.find("WINGSPAN").id == "wingspan"
        assert c.find("azul").id == "azul"

    def test_find_by_id_slug(self):
        c = make_collection()
        c.add_game("The Crew: Mission Deep Sea", 2, 5, 45)
        assert c.find("The Crew: Mission Deep Sea").id == "the-crew-mission-deep-sea"

    def test_find_by_slug_prefix(self):
        c = make_collection()
        c.add_game("The Crew: Mission Deep Sea", 2, 5, 45)
        assert c.find("the crew").title == "The Crew: Mission Deep Sea"

    def test_ambiguous_prefix_lists_matches(self):
        c = make_collection()
        c.add_game("Bazaar Relic", 2, 5, 45)
        c.add_game("Bazaar Royale", 2, 5, 60)
        with pytest.raises(CatalogError, match="several games match 'bazaar'"):
            c.find("bazaar")

    def test_empty_query_rejected(self):
        with pytest.raises(CatalogError, match="empty query"):
            make_collection().find("  ")

    def test_find_unknown(self):
        c = make_collection()
        with pytest.raises(CatalogError, match="no game matching"):
            c.find("Twilight Imperium")


class TestRecordPlay:
    def test_default_wins_sort_order(self):
        c = make_collection()
        p1 = c.record_play("wingspan", "2026-11-03", ["Dana"], "Dana")
        p2 = c.record_play("wingspan", "2026-11-01", ["Dana"], "Dana")
        assert c.plays == [p2, p1]  # sorted by date

    def test_winner_must_be_a_player(self):
        c = make_collection()
        with pytest.raises(CatalogError, match="must be one of the players"):
            c.record_play("wingspan", "2026-11-03", ["Dana", "Sam"], "Priya")

    def test_player_count_must_fit(self):
        c = make_collection()
        with pytest.raises(CatalogError, match="supports"):
            c.record_play("azul", "2026-11-03", ["P"] * 5)

    def test_coop_or_tie_has_empty_winner(self):
        c = make_collection()
        play = c.record_play("azul", "2026-11-03", ["Dana", "Sam"], "")
        assert play.winner == ""

    def test_bad_date_rejected(self):
        c = make_collection()
        with pytest.raises(CatalogError, match="YYYY-MM-DD"):
            c.record_play("wingspan", "Nov 3, 2026", ["Dana"])

    def test_proper_event_roundtrip(self):
        c = make_collection()
        c.record_play("wingspan", "2026-11-03", ["Dana", "Sam"], "Sam", 62)
        assert len(c.plays_for("wingspan")) == 1
        assert c.most_recent_play_for("azul") is None

    def test_minimum_players_for_log(self):
        c = make_collection()
        with pytest.raises(CatalogError, match="one player"):
            c.record_play("wingspan", "2026-11-03", [])

    def test_winner_requires_players_only_when_players_listed(self):
        c = make_collection()
        play = c.record_play("wingspan", "2026-11-03")  # no players at all
        assert play.winner == ""

    def test_negative_play_minutes_rejected(self):
        c = make_collection()
        with pytest.raises(CatalogError, match="minutes"):
            c.record_play("wingspan", "2026-11-03", ["Dana", "Sam"], "Dana", -5)


class TestRemoveGame:
    def test_remove_clears_history_too(self):
        c = make_collection()
        c.record_play("azul", "2026-11-03", ["Dana", "Sam"], "Dana")
        removed = c.remove_game("azul")
        assert removed.title == "Azul"
        assert "azul" not in c.games
        assert c.plays == []


class TestIsWeeknight:
    def test_weekdays(self):
        for d in ("2026-11-02", "2026-11-06"):  # Mon, Fri
            assert is_weeknight(d)

    def test_weekend(self):
        assert not is_weeknight("2026-11-07")  # Saturday


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        c = make_collection()
        c.add_game("The Crew: Mission Deep Sea", 2, 5, 45, weeknight=True,
                   notes="co-op")
        c.record_play("azul", "2026-11-03", ["Dana", "Sam"], "Dana", 45)
        path = tmp_path / "log.json"
        save_collection(c, path)

        loaded = load_collection(path)
        assert [g.title for g in loaded.sorted_games()] == ["Azul", "The Crew: Mission Deep Sea", "Wingspan"]
        assert len(loaded.plays) == 1
        assert loaded.find("the crew").notes == "co-op"

    def test_file_is_plain_readable_json(self, tmp_path):
        c = make_collection()
        path = tmp_path / "log.json"
        save_collection(c, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert {"games", "plays"} <= set(data)
        assert all(isinstance(g, dict) for g in data["games"])

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(CatalogError, match="not found"):
            load_collection(tmp_path / "nope.json")

    def test_load_corrupt_file_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(CatalogError, match="not valid JSON"):
            load_collection(path)

    def test_load_duplicate_ids_raise(self, tmp_path):
        path = tmp_path / "dup.json"
        path.write_text(
            json.dumps(
                {
                    "games": [dict(id="x", title="X", min_players=1,
                                   max_players=2, play_minutes=10)] * 2,
                    "plays": [],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(CatalogError, match="duplicate"):
            load_collection(path)

    def test_load_rejects_missing_sections(self, tmp_path):
        path = tmp_path / "thin.json"
        path.write_text(json.dumps({"games": []}), encoding="utf-8")
        with pytest.raises(CatalogError, match="'plays'"):
            load_collection(path)

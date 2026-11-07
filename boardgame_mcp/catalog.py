"""Plain-file catalog and play log for board games.

Everything lives in one human-readable JSON file so a person can open it,
edit it by hand, or keep it in version control. The file has two top-level
lists: ``games`` and ``plays``.

Copyright (c) 2026 Asdale Dynamics, LLC
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


class CatalogError(ValueError):
    """Raised for bad game or play data (ranges, duplicates, unknown ids...)."""


def slugify(text: str) -> str:
    """Turn a title into a friendly file-friendly id.

    >>> slugify("Wingspan")
    'wingspan'
    >>> slugify("Heat: Pedal to the Metal!")
    'heat-pedal-to-the-metal'
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return slug.strip("-") or "game"


def is_weeknight(date_str: str) -> bool:
    """True when an ISO date falls Monday through Friday."""
    return _parse_date(date_str).weekday() < 5


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except (TypeError, ValueError) as exc:
        raise CatalogError(
            f"date must be a calendar date in YYYY-MM-DD form, got {date_str!r}"
        ) from exc


def _as_int(value: Any, kind: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CatalogError(f"{kind} must be a whole number, got {value!r}")
    return value


@dataclass
class Game:
    """A board game in the collection (a box on the shelf)."""

    id: str
    title: str
    min_players: int
    max_players: int
    play_minutes: int
    weeknight: bool | None = None  # explicit manual flag, if you have one
    notes: str = ""

    def __post_init__(self) -> None:
        self.min_players = _as_int(self.min_players, "min_players")
        self.max_players = _as_int(self.max_players, "max_players")
        self.play_minutes = _as_int(self.play_minutes, "play_minutes")
        if self.min_players < 1:
            raise CatalogError("min_players must be at least 1")
        if self.max_players < self.min_players:
            raise CatalogError(
                f"max_players ({self.max_players}) can't be below "
                f"min_players ({self.min_players})"
            )
        if self.play_minutes <= 0:
            raise CatalogError("play_minutes must be greater than zero")
        if self.weeknight not in (None, True, False):
            raise CatalogError("weeknight must be true, false, or omitted")
        if self.notes is None:
            self.notes = ""
        self.title = str(self.title).strip()
        self.id = str(self.id).strip()

    def supports(self, player_count: int) -> bool:
        """True when ``player_count`` people can all play."""
        return self.min_players <= player_count <= self.max_players

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Play:
    """One recorded session of a game."""

    game_id: str
    date: str  # ISO YYYY-MM-DD
    players: list[str] = field(default_factory=list)
    winner: str = ""  # empty for ties, co-op wins, or "nobody special"
    minutes: int | None = None  # actual table time, if you tracked it

    def __post_init__(self) -> None:
        _parse_date(self.date)
        self.players = [str(p).strip() for p in (self.players or [])]
        self.winner = (self.winner or "").strip()
        if self.winner and self.players and self.winner not in self.players:
            raise CatalogError(
                f"winner {self.winner!r} must be one of the players {self.players}"
            )
        if self.minutes is not None:
            self.minutes = _as_int(self.minutes, "minutes")
            if self.minutes <= 0:
                raise CatalogError("minutes must be greater than zero when given")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Collection:
    """The whole board game log: games on the shelf + plays at the table."""

    games: dict[str, Game] = field(default_factory=dict)
    plays: list[Play] = field(default_factory=list)

    # -- games ---------------------------------------------------------

    def add_game(
        self,
        title: str,
        min_players: int,
        max_players: int,
        play_minutes: int,
        *,
        weeknight: bool | None = None,
        notes: str = "",
        game_id: str | None = None,
    ) -> Game:
        """Add a game; the id defaults to a slug of the title."""
        game_id = slugify(game_id or title)
        if game_id in self.games:
            raise CatalogError(
                f"a game with id {game_id!r} already exists "
                f"({self.games[game_id].title!r})"
            )
        game = Game(
            id=game_id,
            title=title,
            min_players=min_players,
            max_players=max_players,
            play_minutes=play_minutes,
            weeknight=weeknight,
            notes=notes,
        )
        self.games[game.id] = game
        return game

    def get_game(self, game_id: str) -> Game:
        game = self.games.get((game_id or "").strip())
        if game is None:
            raise CatalogError(
                f"no game with id {game_id!r}; ids are: "
                + ", ".join(sorted(self.games))
            )
        return game

    def find(self, query: str) -> Game:
        """Look up a game by exact id, slug-of-title, title, or a unique prefix.

        "the crew" finds ``The Crew: Mission Deep Sea``; a prefix that matches
        several games raises an error listing them, so nothing is guessed.
        """
        query = (query or "").strip()
        if not query:
            raise CatalogError("no game matching an empty query")
        lowered = query.lower()
        exact = [
            g for g in self.games.values()
            if g.id == lowered or g.id == slugify(query)
            or g.title.lower() == lowered
        ]
        if len(exact) == 1:
            return exact[0]
        prefix = [g for g in self.sorted_games() if g.id.startswith(slugify(query))]
        if len(prefix) == 1:
            return prefix[0]
        if len(exact) > 1 or len(prefix) > 1:
            titles = sorted(g.title for g in (exact or prefix))
            raise CatalogError(
                f"several games match {query!r}: " + ", ".join(titles)
            )
        raise CatalogError(f"no game matching {query!r}")

    def remove_game(self, query: str) -> Game:
        """Remove a game (matched like :meth:`find`) and its play history."""
        game = self.find(query)
        del self.games[game.id]
        self.plays = [p for p in self.plays if p.game_id != game.id]
        return game

    def sorted_games(self) -> list[Game]:
        return sorted(self.games.values(), key=lambda g: g.title.lower())

    # -- plays ---------------------------------------------------------

    def record_play(
        self,
        game_id: str,
        date: str,
        players: list[str] | None = None,
        winner: str = "",
        minutes: int | None = None,
    ) -> Play:
        """Record one session. ``date`` is ISO ``YYYY-MM-DD``.

        ``players`` is a list of names; ``winner`` (optional) must be one of
        them, and may be empty for ties, co-op games, or solo runs.
        """
        game = self.get_game(game_id)
        if players is not None:
            count = len(players)
            if count < 1:
                raise CatalogError("at least one player is required")
            if not game.supports(count):
                raise CatalogError(
                    f"{game.title!r} supports {game.min_players}-{game.max_players} "
                    f"players, but you recorded {count}"
                )
        play = Play(
            game_id=game.id,
            date=date,
            players=players or [],
            winner=winner,
            minutes=minutes,
        )
        self.plays.append(play)
        self.plays.sort(key=lambda p: p.date)
        return play

    def plays_for(self, game_id: str) -> list[Play]:
        game = self.get_game(game_id)
        return [p for p in self.plays if p.game_id == game.id]

    def most_recent_play_for(self, game_id: str) -> Play | None:
        plays = self.plays_for(game_id)
        return plays[-1] if plays else None

    def titles_played(self) -> set[str]:
        return {p.game_id for p in self.plays}

    # -- persistence ---------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "games": [g.to_dict() for g in self.sorted_games()],
            "plays": [p.to_dict() for p in self.plays],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Collection:
        if not isinstance(data, dict):
            raise CatalogError(
                "log file must contain a JSON object with 'games' and 'plays'"
            )
        for key in ("games", "plays"):
            if key not in data or not isinstance(data[key], list):
                raise CatalogError(f"log file must include a '{key}' list")

        games: dict[str, Game] = {}
        for raw in data["games"]:
            game = Game(**{k: raw.get(k) for k in Game.__dataclass_fields__})
            if game.id in games:
                raise CatalogError(f"duplicate game id {game.id!r} in log file")
            games[game.id] = game

        plays = [Play(**{k: p.get(k) for k in Play.__dataclass_fields__}) for p in data["plays"]]
        return cls(games=games, plays=plays)


def load_collection(path: str | Path) -> Collection:
    """Load the log from a JSON file. Raises ``CatalogError`` if unreadable."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CatalogError(f"log file not found: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"{path} is not valid JSON: {exc}") from exc
    return Collection.from_dict(data)


def load_collection_or_empty(path: str | Path) -> tuple[Collection, bool]:
    """Load the log, or return a fresh collection when no file exists yet.

    Returns ``(collection, existed)``. A corrupt file still raises
    ``CatalogError`` — never silently overwrite someone's data.
    """
    if not Path(path).exists():
        return Collection(), False
    return load_collection(path), True


def save_collection(collection: Collection, path: str | Path) -> Path:
    """Write the log to a JSON file (indented, stable order) and return it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_updated": datetime.now().isoformat(timespec="seconds"), **collection.to_dict()}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path

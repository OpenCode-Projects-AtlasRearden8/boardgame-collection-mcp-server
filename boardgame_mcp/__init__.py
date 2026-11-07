"""Board game collection MCP server.

A local-first MCP server over a plain JSON file: catalog board games with
player counts and play time, record plays with winners, and answer questions
like "what fits five players on a weeknight?".

Copyright (c) 2026 Asdale Dynamics, LLC
"""

from .catalog import (
    CatalogError,
    Collection,
    Game,
    Play,
    is_weeknight,
    load_collection,
    load_collection_or_empty,
    save_collection,
    slugify,
)
from .stats import (
    play_counts,
    recent_plays,
    unplayed_games,
    weeknight_picks,
    winner_leaderboard,
)
from .text import (
    format_game,
    format_games,
    format_plays,
    format_picks,
    format_unplayed,
)

__all__ = [
    "CatalogError",
    "Collection",
    "Game",
    "Play",
    "is_weeknight",
    "load_collection",
    "load_collection_or_empty",
    "save_collection",
    "slugify",
    "play_counts",
    "recent_plays",
    "unplayed_games",
    "weeknight_picks",
    "winner_leaderboard",
    "format_game",
    "format_games",
    "format_plays",
    "format_picks",
    "format_unplayed",
]

__version__ = "0.1.0"

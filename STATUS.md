STATUS.md

What was built
==============

A Python MCP server over a plain-file board game log, per the original goal:

- Catalog board games (title, player range, typical play time) in one
  human-readable JSON file.
- Record plays: date, players, optional winner, optional actual minutes,
  with validation (winners must be players; player counts must fit the box;
  dates must be real calendar dates).
- Agent-facing reports as chat-ready text: recent plays, unplayed (shelf)
  games, titles that fit N players in a weeknight time budget (default
  5 players / 90 minutes), plus a collection summary.
- Nine MCP tools over stdio: add_game, list_games, search_games,
  remove_game, record_play, recent_plays, unplayed_games, weeknight_picks,
  collection_summary.
- Scope kept distinct from the video-game backlog webapp and the offline
  party kit: this is about physical board games, MCP-driven, file-based.

Layout
------
boardgame_mcp/catalog.py  - Game, Play, Collection, JSON load/save, validation
boardgame_mcp/stats.py    - pure report logic (recent, shelf, picks, counts)
boardgame_mcp/text.py     - chat-ready text formatters
boardgame_mcp/server.py   - MCPServer wiring + CLI entry point
examples/example_collection.json - 8 games + 8 plays to explore (fictional names)
tests/                    - 69 pytest tests

How to run it
=============

    pip install -e .

    python -m boardgame_mcp.server            # stdio MCP server
    # or: boardgame-mcp
    # log path: --log PATH or BOARDGAME_LOG env; default ./boardgames.json

    python -m boardgame_mcp.server --log path/to/file.json --transport streamable-http

    # try it with example data:
    cp examples/example_collection.json boardgames.json && python -m boardgame_mcp.server

Connect from any MCP client by running that command as the server; config
sample is in README.md. There is no default network listener.

Verification results (2026-11-07)
=================================

- pytest: 69 passed (no failures, no skips).
- Live build check: `pip wheel --no-build-isolation .` builds a wheel.
- Entry point: `boardgame-mcp --help` runs (stdio default).
- Integration: a real MCP client performs a stdio JSON-RPC handshake with
  a spawned `python -m boardgame_mcp.server` process and calls tools
  end-to-end (tests/test_stdio_integration.py).

  Includes: catalog validation, load/save round-trips, corrupt-file and
  duplicate-id handling, weeknight/stats logic, text formatting, all nine
  tools through the MCP layer, empty-start behavior, and hand-edited log
  respect.

Bugs found and fixed during the re-review
-----------------------------------------
- stats.weeknight_picks referenced `g` outside its generator (NameError on
  the "weeknight fits" branch) -> reworked into a closure; caught by tests.
- Server failed on first-ever write because the log file did not exist ->
  added load_collection_or_empty(); read-only tools never create files.
- Collection.find only matched exact ids/titles -> added unique
  slug-prefix matching ("the crew" finds The Crew: Mission Deep Sea) while
  still refusing ambiguous guesses.
- Pluralization fixes ("1 plays recorded" etc.).

Known gaps
==========

- Report logic is heuristic, not learned: "weeknight" fit uses the
  recommended play time on the box (or the weeknight flag you stamp). A
  future version could average actual recorded minutes per game to tune
  the budget.
- No file locking: run one server per log file at a time.
- No pagination for huge catalogs (fine at human-collection scale).
- winner_leaderboard treats co-op wins and ties (empty winner) as no-op
  by design; there is no "team win" credit.
- Stdio integration test requires the mcp SDK installed in the test env
  (same package as the server, so it is available).

Status: working, tested, committed.

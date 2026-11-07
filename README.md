# boardgame-collection-mcp-server

A local-first **MCP server over a plain-file board game log**. Plain files in, chat-ready text out: catalog the games on your shelf, record plays with winners, and let an AI agent answer the questions you actually ask on game night — *what did we play lately, which boxes are still unplayed, and what fits five players on a weeknight?*

Built and published by **Asdale Dynamics, LLC** as part of a beginner-friendly collection of open-source tools and MCP servers. Written in plain English, step by step, never condescending.

> Physical board games only — this is not for video game backlogs, and it's not a party-game kit. If you want those, they live elsewhere.

## Why a plain file?

The whole database is one human-readable JSON file. You can:

- open it in any editor and fix a typo,
- keep it in git (it's your game history!),
- email it to a friend, or
- start fresh by deleting it.

No daemon, no cloud, no accounts, no secrets. The server just reads and writes that file.

## Quick start

```bash
pip install -e .

python -m boardgame_mcp.server            # stdio MCP server (what clients expect)
# or: boardgame-mcp
```

By default the log lives at `./boardgames.json`. Choose your own:

```bash
python -m boardgame_mcp.server --log ~/Documents/boardgames.json
# or: BOARDGAME_LOG=~/Documents/boardgames.json boardgame-mcp
```

On a weeknight when nobody has edited the file yet, it just starts empty.

### Try it with example data

```bash
cp examples/example_collection.json boardgames.json && python -m boardgame_mcp.server
```

### Connect it to an MCP client

Point any MCP-capable client (e.g. Claude Desktop, another agent host) at the command above. Example config entry:

```json
{
  "mcpServers": {
    "board-game-collection": {
      "command": "python",
      "args": ["-m", "boardgame_mcp.server", "--log", "/path/to/boardgames.json"]
    }
  }
}
```

There's no network listener by default; everything stays on your machine.

## The tools an agent gets

| Tool | What it does |
| --- | --- |
| `add_game` | Catalog a title: player range, typical play time, optional weeknight flag and notes |
| `list_games` | The whole catalog, with play counts and last-play dates |
| `search_games` | Loose text search over titles and ids |
| `remove_game` | Take a game (and its history) out of the log |
| `record_play` | One session: date (default today), players, optional winner, actual minutes |
| `recent_plays` | "What did we play recently?" — newest first, weekday and winner included |
| `unplayed_games` | "What's still on the shelf?" — never played |
| `weeknight_picks` | "What fits 5 people on a weeknight?" — player range + time budget (default 90 min), quickest first |
| `collection_summary` | Totals, most-played title, top winner |

"What fits a weeknight" means the game seats the group and its typical play time is within the default **90-minute** budget. If you stamp a game with `weeknight: true` yourself, that flag wins — and the catalog output will show every kind.

Game ids are friendly slugs (`Wingspan: Oceania` → `wingspan-oceania`), so the file is easy to read and edit by hand. Play records validate themselves: dates must be real calendar dates, winners must be among the recorded players, and a solo play of a 3-of-5-player game gets a polite no.

## Example: chat-ready answers

Ask an agent "what fits five players on a weeknight?" and it gets back text like:

```
4 titles fit 5 players in under 90 minutes (quickest first):
- **Tick Tock Brrr Baah** · 3-6 players · ~30 min
- **The Crew: Mission Deep Sea** · 2-5 players · ~45 min
- **Heat: Pedal to the Metal** · 1-7 players · ~60 min
- **Wingspan** · 1-5 players · ~60 min
```

## The log file

```json
{
  "_updated": "2026-11-07T13:20:00",
  "games": [
    {"id": "wingspan", "title": "Wingspan", "min_players": 1, "max_players": 5,
     "play_minutes": 60, "weeknight": null, "notes": "Europe expansion added."}
  ],
  "plays": [
    {"game_id": "wingspan", "date": "2026-10-20",
     "players": ["Dana", "Riley", "Priya"], "winner": "Priya", "minutes": null}
  ]
}
```

`winner` stays empty for co-op wins and honest ties. The example collection uses fictional player names only — put in whatever names you like; the file stays on your disk.

## Tests

```bash
pip install -e ".[dev]"
pytest            # 69 tests: catalog rules, stats, formatting, tools, live stdio round-trip
```

The suite covers validation (player ranges, dates, winners), load/save round-trips of hand-corruptible files, the report logic (recent plays, shelf, weeknight picks, leaderboards), every text formatter, all nine tools through the MCP layer, and a real subprocess stdio handshake with a genuine MCP client.

## Project layout

```
boardgame_mcp/
  catalog.py    # Game, Play, Collection, JSON load/save, validation
  stats.py      # recent plays, shelf, weeknight picks, counts, leaderboards
  text.py       # chat-ready formatting (local files in, chat text out)
  server.py     # nine MCP tools + stdio entry point
examples/
  example_collection.json   # ~8 games and plays to explore with
tests/          # pytest suite, incl. real stdio integration
```

## Known limits

- One file, one machine: no locking, so two servers on the same log could clobber each other (keep to one at a time).
- Weeknight fit is judged by the typical (often box-recommended) play time; it doesn't learn that your Avalon group takes twenty minutes to pick a leader — that's what the optional `minutes` field on each play is for, for later tuning.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Asdale Dynamics, LLC.

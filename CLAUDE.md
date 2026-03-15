# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
streamlit run main.py

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_advanced_stats.py

# Run a single test by name
python -m pytest tests/test_advanced_stats.py::test_function_name
```

## Architecture

This is a single-page **Streamlit** app (`main.py`) for analyzing League of Legends 5-stack team games. The app has two modes: **Single Match** (per-game deep dive) and **Team Trends** (aggregated across last 20 games).

### Data Flow

1. User enters Riot API key + 5 player `Name#Tag` identifiers in the sidebar
2. `RiotClient` (wraps `riotwatcher`) resolves names → PUUIDs via the Riot Account API
3. `MatchFetcher` finds games where all 5 players appeared on the same team
4. Match data and timelines are cached in SQLite (`data/cache.db`) via `MatchCache`
5. Analysis modules consume raw match/timeline JSON and return DataFrames
6. Plotly charts are rendered inline in Streamlit tabs

### Key Routing Detail

Riot API uses two routing tiers: **platform** (`na1`, `euw1`, `kr`, `br1`) for summoner lookups, and **regional** (`americas`, `europe`, `asia`) for match history and account lookups. `RiotClient._get_routing_value()` handles the mapping.

### Module Layout

- `src/api/riot_client.py` — Riot API wrapper (`riotwatcher`), handles both platform and regional routing
- `src/api/match_fetcher.py` — finds team games, fetches timelines (uses cache)
- `src/api/match_cache.py` — SQLite cache for match JSON and timeline JSON
- `src/config.py` — reads/writes `config.json` (API key, players, region, Discord webhook)
- `src/analysis/basic_stats.py` — KDA, DPM, CS/min, vision score, kill participation
- `src/analysis/advanced_stats.py` — timeline-derived metrics: harass score, greed index, jungle proximity, gank susceptibility, ward counts, spotted/unspotted gank deaths
- `src/analysis/team_trends.py` — aggregates stats across multiple games for trend charts
- `src/analysis/objectives.py` — dragon/baron tracking, throw detection
- `src/analysis/teamfights.py` — clusters kills by proximity/time to detect teamfights
- `src/analysis/jungle_pathing.py` — extracts jungler position/kill/elite events from timeline
- `src/analysis/game_summary.py` — generates natural language bullet-point match summaries
- `src/analysis/report_export.py` — renders a PNG report using Plotly + `kaleido`
- `src/discord_integration.py` — posts match summary + report image to a Discord webhook

### Timeline-Dependent Analysis

Most advanced stats require the match **timeline** (separate API call from match data). Timeline frames contain per-minute snapshots and events (kills, ward placements, champion positions). The advanced stats functions take `timeline`, a `participantId` (1-10 int, not PUUID), and sometimes the jungler's participant ID.

### Configuration

`config.json` is auto-created at the project root and persists API key, player names, region, and Discord webhook URL across sessions. The `.env` file (if present) can supply `RIOT_API_KEY` as a fallback.

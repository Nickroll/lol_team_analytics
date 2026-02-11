# LoL Team Analytics

A Streamlit-powered analytics dashboard for League of Legends team play. Track your 5-stack's performance across games with advanced stats, trend analysis, and Discord integration.

## Features

- **Match Analysis** — KDA, DPM, CS/M, Vision Score, Kill Participation, Damage/Gold share
- **Advanced Stats** — Harass Score, Greed Index, Jungle Proximity, Gank Susceptibility, Spotted/Unspotted Deaths
- **Laning Phase** — Gold/XP diff timelines, CS advantage charts
- **Vision Analysis** — Ward placement heatmaps, vision score tracking
- **Jungle Pathing** — Path visualization on map overlay
- **Objective Control** — Dragon/Baron tracking with throw detection
- **Teamfight Analysis** — Automatic teamfight detection and outcome breakdown
- **Player Trends** — Per-player stat trends across multiple games
- **Match Summary** — Auto-generated natural language game summaries
- **Image Export** — Export match reports as PNG images
- **Discord Integration** — Share match reports to Discord via webhook
- **SQLite Cache** — Fast match data caching with stats and management

## Quick Start (Windows)

### Prerequisites
- **Python 3.9+** — Download from [python.org](https://www.python.org/downloads/)
  - ⚠️ During installation, check **"Add Python to PATH"**
- **Riot API Key** — Get one from [developer.riotgames.com](https://developer.riotgames.com)

### Installation
1. Download/extract this folder to your PC
2. Double-click **`setup.bat`** — installs dependencies (one-time)
3. Double-click **`run.bat`** — starts the app

The app will open automatically in your default browser at `http://localhost:8501`.

### Configuration
1. Enter your **Riot API Key** in the sidebar
2. Enter **5 player names** in `Name#Tag` format (e.g., `Faker#KR1`)
3. Select your **region**
4. Click **Save Configuration** (persists across sessions)
5. *(Optional)* Add a **Discord Webhook URL** to enable match sharing

## Quick Start (Linux/Mac)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run main.py
```

## Project Structure

```
lol_team_analytics/
├── main.py                     # Streamlit app entry point
├── setup.bat                   # Windows setup script
├── run.bat                     # Windows launcher
├── requirements.txt            # Python dependencies
├── config.json                 # Saved configuration
├── src/
│   ├── api/
│   │   ├── riot_client.py      # Riot API wrapper
│   │   ├── match_fetcher.py    # Match data fetching
│   │   └── match_cache.py      # SQLite caching layer
│   ├── analysis/
│   │   ├── basic_stats.py      # KDA, DPM, CS, Vision
│   │   ├── advanced_stats.py   # Harass, Greed, Proximity
│   │   ├── team_trends.py      # Team + player trend analysis
│   │   ├── objectives.py       # Objective control & throws
│   │   ├── teamfights.py       # Teamfight detection
│   │   ├── jungle_pathing.py   # Jungle path extraction
│   │   ├── game_summary.py     # Natural language summaries
│   │   └── report_export.py    # PNG report generation
│   ├── discord_integration.py  # Discord webhook posting
│   └── config.py               # Configuration manager
└── data/
    ├── cache.db                # Match data cache
    └── exports/                # Exported report images
```

## Discord Setup

1. In Discord: **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**
2. Choose a channel and copy the webhook URL
3. Paste it into the app sidebar under "Discord Webhook URL"
4. Click "Save Configuration"
5. Use the **📤 Share to Discord** button on any match report

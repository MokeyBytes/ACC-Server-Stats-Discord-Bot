# ACC Server Stats Discord Bot

A Discord bot for Assetto Corsa Competizione servers that automatically tracks lap times, announces records, and provides detailed statistics.

---
<p align="center">
  <img
    src="https://github.com/user-attachments/assets/42c04e33-92bd-4c84-bf07-ab69c9f5ed32"
    alt="image"
    width="595"
    height="749"
  />
</p>

## 🎮 Features

### Automatic Announcements
- **🏆 Track Records** - Gold embed when someone sets a new track record
- **🎯 Personal Bests** - Green embed when a driver beats their personal best
- **🏁 Race Results** - Blue embed with full race standings after each race

### What gets announced (and what doesn’t)
- **Qualifying (`Q`) + Race (`R`)**: imported, tracked for records/PBs, and can generate announcements.
- **Free Practice (`FP`)**: imported and stored in the DB, **but never announced** and **does not update records**.

### On-Demand Commands
- View track leaderboards with top times
- Check any driver's personal bests with detailed sector breakdowns
- Compare times against track records
- See rank, session count, and improvement trends

---

## 📋 Commands

### `/records <track>`
Show the top 3 Qualifying and Race times for a specific track.

**Example Output:**
```
🏆 Track Records: Barcelona

🏁 Qualifying Times
🥇 1:42.123 — Mokey Bytes (BMW M4 GT3) • Today at 3:30 PM EST
🥈 2. 1:42.456 (+0.333) — Speed Demon (Ferrari 296 GT3)
🥉 3. 1:42.789 (+0.666) — Fast Larry (Porsche 992 GT3 R)

🏎️ Race Times
🥇 1:43.001 — Mokey Bytes (BMW M4 GT3) • Yesterday at 8:15 PM EST
🥈 2. 1:43.234 (+0.233) — Speed Demon (Ferrari 296 GT3)
🥉 3. 1:43.567 (+0.566) — Fast Larry (Porsche 992 GT3 R)
```

---

### `/pb <player> <track>`
Show a player's personal best for a specific track with detailed sector breakdown.

**Example Output:**
```
🎯 Personal Best: Mokey Bytes
🏁 Barcelona

🏁 Qualifying
⏱️ Time: 1:42.123
🚗 Car: BMW M4 GT3
📅 Set: Today at 3:30 PM EST
📊 Rank: 🥈 #2 of 15
🏆 vs Record: +0.234
🔄 Sessions: 8

⚡ Sector Breakdown (Q)
S1: 0:23.005 (-0.045) ✅
S2: 0:35.987 (+0.123)
S3: 0:51.180 (+0.089)

🏆 Strongest: S1 (0.045s faster than record)
💪 Weakest: S2 (0.123s slower than record)
```

---

### `/leaders`
Show the #1 Qualifying and Race time for every track.

**Example Output:**
```
🏆 Server Leaders - All Tracks

Barcelona
  🏁 Q: 1:42.123 — Mokey Bytes (BMW M4 GT3)
  🏎️ R: 1:43.001 — Mokey Bytes (BMW M4 GT3)

Spa-Francorchamps
  🏁 Q: 2:16.789 — Speed Demon (Ferrari 296 GT3)
  🏎️ R: 2:17.456 — Fast Larry (Porsche 992 GT3 R)
```

---

### `/tracks`
List all available tracks in the database.

---

### `/sync`
Manually sync slash commands with Discord (admin use).

---

## 🔔 Automatic Announcements

### New Track Record
When someone sets the fastest time ever on a track:

```
🏆 NEW TRACK RECORD! 🏆
🏁 Barcelona - Qualifying

🔥 Smashed the previous record by 0.234s!

👤 Driver: Mokey Bytes
⏱️ Time: 1:42.123
🚗 Car: BMW M4 GT3
📅 Set On: Today at 3:30 PM EST
```

### New Personal Best
When a driver beats their previous best (but not the track record):

```
🎯 PERSONAL BEST ACHIEVED! 🎯
🏎️ Barcelona - Race

🚀 Moved up 3 position(s) on the leaderboard!

👤 Driver: Speed Demon
⏱️ Time: 1:43.456
🚗 Car: Ferrari 296 GT3
📅 Set On: Today at 4:15 PM EST
```

### Race Results
Posted automatically after each race:

```
🏁 Race Results: Barcelona

🏆 Final Standings
🥇 Mokey Bytes — 25:34.123 (Best: 1:43.001 🔥)
🥈 Speed Demon — +12.456 (Best: 1:43.234)
🥉 Fast Larry — +23.789 (Best: 1:43.567)
4. Another Driver — +45.123 (Best: 1:44.012)
...
```

---

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- Discord Bot Token
- ACC Server with results output enabled

### 1. Install Dependencies
```bash
pip install discord.py pytz
```

### 2. Create Discord Bot

You need to create a Discord bot application and get a bot token.

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to the "Bot" section
4. Create a bot and copy the token
5. Invite the bot to your server with the following permissions:
   - **Send Messages**
   - **Embed Links**
   - **Attach Files**
   - **Read Message History**
   - **Use Slash Commands**

### 3. Set Discord Bot Token
```powershell
# Temporary (current session only)
$env:DISCORD_TOKEN = "your_token_here"

# Permanent (persists after restart)
[Environment]::SetEnvironmentVariable("DISCORD_TOKEN", "your_token_here", "User")
```

### 4. Configure ACC Server

**Important:** The ACC server must be configured to dump leaderboard data.

In your ACC server's configuration file `server/cfg/settings.json`, ensure:

```json
{
  "dumpLeaderboards": 1
}
```

This setting enables the server to generate the JSON result files that the bot imports. Without this, no race data will be available.

### 5. Configure Paths
Edit `config.py`:
```python
DB_PATH = r"C:\accserver\stats\acc_stats.sqlite"  # Your database path
CHANNEL_ID = 123456789012345678                    # Your Discord channel ID
IMG_DIR = r"C:\accserver\stats\img"               # Track images folder
```

### 6. Run the Bot
```bash
py run_bot.py
```

### 7. Run File Watcher (Separate Terminal)
```powershell
.\watch_results.ps1
```

This watches for new race result JSON files and automatically imports them.

---

## 📥 Importing an already-running server (backfill old JSON files)

If your ACC server has been running for a while, you can import **existing** result files so the bot has history.

- **Put old results in the results folder**: copy/move historical `*.json` into `RESULTS_DIR` (see `import_acc_results.py`).
- **Run the importer**:

```bash
py import_acc_results.py
```

- **Start the bot** (`py run_bot.py`): it will pick up any queued announcements.

Notes:
- The importer is **idempotent** based on `sessions.source_file` (full path). If you import files from one path and later move them and import again, they may be treated as “new” and create duplicates.
- Backfilling can create a backlog of TR/PB announcements; if you don’t want historical announcements, clear the queue tables before starting the bot (e.g., `record_announcements`, `race_results_announcements`).

---

## 📁 Project Structure

```
ACC-Stats/
├── config.py              # Configuration (paths, IDs, car models)
├── run_bot.py             # Bot entry point
├── import_acc_results.py  # Import race data from JSON files
├── watch_results.ps1      # File watcher for auto-import
│
├── db/
│   └── queries.py         # Database query functions
│
├── bot/
│   ├── client.py          # Main bot client and event loop
│   ├── embeds.py          # Embed builders (TR, PB, Race Results)
│   ├── autocomplete.py    # Autocomplete for player/track names
│   └── commands/
│       ├── records.py     # /records command
│       ├── pb.py          # /pb command
│       ├── leaders.py     # /leaders command
│       ├── tracks.py      # /tracks command
│       └── sync.py        # /sync command
│
├── utils/
│   ├── formatting.py      # Time/date/car formatting
│   └── images.py          # Track image matching
│
└── img/                   # Track images for embeds
```

---

## 🗄️ Database Schema

SQLite database with these main tables:

| Table | Purpose |
|-------|---------|
| `sessions` | Race session metadata (track, type, weather) |
| `entries` | Driver entries per session (times, sectors, car) |
| `records` | Current track records (Q/R per track) |
| `record_announcements` | Queue for TR/PB Discord posts |
| `race_results_announcements` | Queue for race result posts |

### Create Schema

Run this SQL to create the database schema:

```sql
PRAGMA foreign_keys = ON;

-- Session metadata
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL UNIQUE,
    session_type TEXT NOT NULL,
    track TEXT NOT NULL,
    server_name TEXT,
    is_wet INTEGER,
    session_index INTEGER,
    race_weekend_index INTEGER,
    file_mtime_utc TEXT NOT NULL
);

-- Driver entries per session
CREATE TABLE IF NOT EXISTS entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    car_id INTEGER,
    race_number INTEGER,
    car_model INTEGER,
    cup_category INTEGER,
    car_group TEXT,
    player_id TEXT,
    first_name TEXT,
    last_name TEXT,
    short_name TEXT,
    best_lap_ms INTEGER,
    total_time_ms INTEGER,
    lap_count INTEGER,
    missing_mandatory_pitstop INTEGER,
    best_splits_json TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

-- Track records (Q/R per track)
CREATE TABLE IF NOT EXISTS records (
    track TEXT NOT NULL,
    session_type TEXT NOT NULL,
    best_lap_ms INTEGER NOT NULL,
    player_id TEXT,
    first_name TEXT,
    last_name TEXT,
    short_name TEXT,
    car_model INTEGER,
    race_number INTEGER,
    cup_category INTEGER,
    set_session_id INTEGER,
    set_at_utc TEXT NOT NULL,
    PRIMARY KEY(track, session_type),
    FOREIGN KEY(set_session_id) REFERENCES sessions(session_id)
);

-- Queue for track record and personal best announcements
CREATE TABLE IF NOT EXISTS record_announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    track TEXT NOT NULL,
    session_type TEXT NOT NULL,
    best_lap_ms INTEGER NOT NULL,
    announced_at_utc TEXT NOT NULL,
    discord_message_id TEXT,
    announcement_type TEXT DEFAULT 'TR'
);

-- Queue for race result announcements
CREATE TABLE IF NOT EXISTS race_results_announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL UNIQUE,
    track TEXT NOT NULL,
    announced_at_utc TEXT NOT NULL,
    discord_message_id TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
```

### Import Data
```bash
py import_acc_results.py
```

This imports all JSON files from your ACC server's results folder.

Important:
- The importer will **run migrations** (e.g., add `entries.best_splits_json`, add `record_announcements.announcement_type`) and will create `race_results_announcements` if needed.
- The importer **assumes the base tables exist** (`sessions`, `entries`, `records`, `record_announcements`). Use the **Create Schema** SQL above when setting up a new DB.

---

## 📄 License

This project is licensed under a **Non-Commercial License**.

**Free to use, modify, and share - but commercial use is prohibited.**

See the [LICENSE](LICENSE) file for the full license text.

**Copyright (C) 2024 ACC Server Stats Discord Bot contributors**

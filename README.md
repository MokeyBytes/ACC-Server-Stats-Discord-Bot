# ACC Server Stats Discord Bot

A Discord bot for Assetto Corsa Competizione servers that automatically tracks lap times, announces records, and provides detailed statistics.

---

## 🎮 Features

### Automatic Announcements
- **🏆 Track Records** - Gold embed when someone sets a new track record
- **🎯 Personal Bests** - Green embed when a driver beats their personal best
- **🏁 Race Results** - Blue embed with full race standings after each race

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
- ACC Server with results output

### 1. Install Dependencies
```bash
pip install discord.py pytz
```

### 2. Set Discord Bot Token
```powershell
# Temporary (current session only)
$env:DISCORD_TOKEN = "your_token_here"

# Permanent (persists after restart)
[Environment]::SetEnvironmentVariable("DISCORD_TOKEN", "your_token_here", "User")
```

### 3. Configure Paths
Edit `config.py`:
```python
DB_PATH = r"C:\accserver\stats\acc_stats.sqlite"  # Your database path
CHANNEL_ID = 123456789012345678                    # Your Discord channel ID
IMG_DIR = r"C:\accserver\stats\img"               # Track images folder
```

### 4. Run the Bot
```bash
py run_bot.py
```

### 5. Run File Watcher (Separate Terminal)
```powershell
.\watch_results.ps1
```

This watches for new race result JSON files and automatically imports them.

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

### Import Data
```bash
py import_acc_results.py
```

This imports all JSON files from your ACC server's results folder.

---

## 📄 License

MIT

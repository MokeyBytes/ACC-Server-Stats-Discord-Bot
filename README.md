# ACC Server Stats Discord Bot

Discord bot for displaying Assetto Corsa Competizione server statistics, track records, personal bests, and race results.

## Features

- 🏁 **Track Records**: View current track records for Qualifying and Race sessions
- 🎯 **Personal Bests**: Check your personal best times across all tracks
- 📊 **Race Results**: Automatic posting of race results when races complete
- 🏆 **Leaderboards**: View top times for tracks and compare against leaders
- 🖼️ **Track Images**: Automatic track image matching and embedding

## Commands

- `/records <track>` - Show top 3 times for a specific track (Q and R)
- `/pb <first_name> <last_name>` - Show personal bests for a player across all tracks
- `/leaders` - Show top 1 Q and R time for all tracks
- `/tracks` - List all available tracks
- `/sync` - Manually sync slash commands (admin)

## Setup

1. Install dependencies:
   ```bash
   pip install discord.py pytz
   ```

2. Set your Discord bot token:
   ```powershell
   $env:DISCORD_TOKEN = "your_token_here"
   # Or permanently:
   [Environment]::SetEnvironmentVariable("DISCORD_TOKEN", "your_token_here", "User")
   ```

3. Configure paths in `config.py`:
   - `DB_PATH` - Path to your SQLite database
   - `CHANNEL_ID` - Discord channel ID for bot output
   - `IMG_DIR` - Directory containing track images

4. Run the bot:
   ```bash
   py run_bot.py
   ```

5. Run the file watcher (separate terminal):
   ```powershell
   .\watch_results.ps1
   ```

## Database

The bot uses SQLite database with the following main tables:
- `sessions` - Race session data
- `entries` - Driver entries per session
- `records` - Track records (Q/R)
- `record_announcements` - Queue for Discord announcements
- `race_results_announcements` - Queue for race result posts

Run `import_acc_results.py` to import race data from JSON files.

## Project Structure

```
ACC-Stats/
├── config.py              # Configuration constants
├── run_bot.py             # Bot entry point
├── import_acc_results.py  # Import race data from JSON
├── watch_results.ps1      # File watcher for auto-import
├── db/                    # Database query functions
├── bot/                   # Discord bot code
│   ├── client.py         # Main bot logic
│   ├── embeds.py         # Embed builders
│   ├── autocomplete.py   # Autocomplete handlers
│   └── commands/         # Slash commands
└── utils/                 # Utility functions
```

## License

MIT


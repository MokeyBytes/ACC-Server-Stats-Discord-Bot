"""Constants used throughout the bot application."""

# Discord API Limits
DISCORD_FIELD_VALUE_LIMIT = 1024  # Maximum characters in an embed field value
DISCORD_AUTOCOMPLETE_LIMIT = 25    # Maximum autocomplete choices Discord allows
DISCORD_EMBED_FIELD_LIMIT = 25     # Maximum fields per embed

# Display Limits
DEFAULT_TOP_TIMES_LIMIT = 3        # Default number of top times to show
TRACKS_PER_FIELD = 2               # Number of tracks to group per field in leaders command
MAX_RACE_RESULTS_DISPLAY = 10       # Maximum race results to display in embed

# Medal Positions
TOP_3_POSITIONS = {1, 2, 3}        # Positions that get medals
MEDAL_EMOJIS = {1: "🥇", 2: "🥈", 3: "🥉"}  # Medal emoji mapping

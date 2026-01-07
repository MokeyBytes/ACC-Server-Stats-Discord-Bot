import os
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

import discord
from discord import app_commands

DB_PATH = r"C:\accserver\stats\acc_stats.sqlite"
IMG_DIR = os.path.join(os.path.dirname(__file__), "img")

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = 1457747421764522106
ROLE_ID = 1457747594846671004

POLL_SECONDS = 5
BATCH_SIZE = 10

# Car model ID to name mapping
CAR_MODELS = {
    0: "Porsche 991 GT3 R",
    1: "Mercedes-AMG GT3",
    2: "Ferrari 488 GT3",
    3: "Audi R8 LMS",
    4: "Lamborghini Huracan GT3",
    5: "McLaren 650S GT3",
    6: "Nissan GT-R Nismo GT3 2018",
    7: "BMW M6 GT3",
    8: "Bentley Continental GT3 2018",
    9: "Porsche 991II GT3 Cup",
    10: "Nissan GT-R Nismo GT3 2017",
    11: "Bentley Continental GT3 2016",
    12: "Aston Martin V12 Vantage GT3",
    13: "Lamborghini Gallardo R-EX",
    14: "Jaguar G3",
    15: "Lexus RC F GT3",
    16: "Lamborghini Huracan Evo (2019)",
    17: "Honda NSX GT3",
    18: "Lamborghini Huracan SuperTrofeo",
    19: "Audi R8 LMS Evo (2019)",
    20: "AMR V8 Vantage (2019)",
    21: "Honda NSX Evo (2019)",
    22: "McLaren 720S GT3 (2019)",
    23: "Porsche 911II GT3 R (2019)",
    24: "Ferrari 488 GT3 Evo 2020",
    25: "Mercedes-AMG GT3 2020",
    26: "Ferrari 488 Challenge Evo",
    27: "BMW M2 CS Racing",
    28: "Porsche 911 GT3 Cup (Type 992)",
    29: "Lamborghini Huracán Super Trofeo EVO2",
    30: "BMW M4 GT3",
    31: "Audi R8 LMS GT3 evo II",
    32: "Ferrari 296 GT3",
    33: "Lamborghini Huracan Evo2",
    34: "Porsche 992 GT3 R",
    35: "McLaren 720S GT3 Evo 2023",
    36: "Ford Mustang GT3",
    50: "Alpine A110 GT4",
    51: "AMR V8 Vantage GT4",
    52: "Audi R8 LMS GT4",
    53: "BMW M4 GT4",
    55: "Chevrolet Camaro GT4",
    56: "Ginetta G55 GT4",
    57: "KTM X-Bow GT4",
    58: "Maserati MC GT4",
    59: "McLaren 570S GT4",
    60: "Mercedes-AMG GT4",
    61: "Porsche 718 Cayman GT4",
    80: "Audi R8 LMS GT2",
    82: "KTM XBOW GT2",
    83: "Maserati MC20 GT2",
    84: "Mercedes AMG GT2",
    85: "Porsche 911 GT2 RS CS Evo",
    86: "Porsche 935",
}

def fmt_car_model(car_model) -> str:
    """Convert car model ID to name, or return 'Unknown' if not found."""
    if car_model is None:
        return "Unknown"
    try:
        return CAR_MODELS.get(int(car_model), f"Unknown ({car_model})")
    except (ValueError, TypeError):
        return f"Unknown ({car_model})"

def fmt_ms(ms: int) -> str:
    # ms -> m:ss.mmm
    m, rem = divmod(ms, 60_000)
    s, ms2 = divmod(rem, 1000)
    return f"{m}:{s:02d}.{ms2:03d}"

def fmt_split_ms(ms: int) -> str:
    """Format split time (difference from leader). Positive = slower, shows as negative."""
    abs_ms = abs(ms)
    sign = "-" if ms > 0 else "+"
    m, rem = divmod(abs_ms, 60_000)
    s, ms2 = divmod(rem, 1000)
    return f"{sign}{m:02d}:{s:02d}.{ms2:03d}"

def fmt_dt(iso_utc: str) -> str:
    # expects "...Z" or ISO; display as YYYY-MM-DD HH:MM EST/EDT
    if iso_utc.endswith("Z"):
        iso_utc = iso_utc.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_utc).astimezone(timezone.utc)
    
    # Convert to Eastern Time (automatically handles EST/EDT)
    if HAS_PYTZ:
        eastern = pytz.timezone("America/New_York")
        et_dt = dt.astimezone(eastern)
        # Get timezone abbreviation (EST or EDT)
        tz_abbr = et_dt.strftime("%Z")
        return et_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")
    else:
        # Fallback: manual calculation (EST = UTC-5, EDT = UTC-4)
        # Simple approximation: assume EDT from March to November
        month = dt.month
        is_dst = 3 <= month <= 11  # Rough approximation
        offset_hours = -4 if is_dst else -5
        tz_abbr = "EDT" if is_dst else "EST"
        et_dt = dt + timedelta(hours=offset_hours)
        return et_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")

def fetch_queue(con: sqlite3.Connection):
    # Pull queued announcements and join to records for the extra fields
    # For TR: join with records table (which has the driver info)
    # For PB: get driver info from entries table matching the announcement
    return con.execute(
        """
        SELECT
          a.announcement_id,
          a.track,
          a.session_type,
          a.best_lap_ms,
          a.announced_at_utc,
          COALESCE(a.announcement_type, 'TR') as announcement_type,
          COALESCE(r.player_id, 
            (SELECT e2.player_id FROM entries e2 
             JOIN sessions s2 ON e2.session_id = s2.session_id 
             WHERE s2.track = a.track AND s2.session_type = a.session_type 
             AND e2.best_lap_ms = a.best_lap_ms 
             AND e2.player_id IS NOT NULL 
             LIMIT 1)) as player_id,
          COALESCE(r.first_name,
            (SELECT e2.first_name FROM entries e2 
             JOIN sessions s2 ON e2.session_id = s2.session_id 
             WHERE s2.track = a.track AND s2.session_type = a.session_type 
             AND e2.best_lap_ms = a.best_lap_ms 
             AND e2.player_id IS NOT NULL 
             LIMIT 1)) as first_name,
          COALESCE(r.last_name,
            (SELECT e2.last_name FROM entries e2 
             JOIN sessions s2 ON e2.session_id = s2.session_id 
             WHERE s2.track = a.track AND s2.session_type = a.session_type 
             AND e2.best_lap_ms = a.best_lap_ms 
             AND e2.player_id IS NOT NULL 
             LIMIT 1)) as last_name,
          COALESCE(r.short_name,
            (SELECT e2.short_name FROM entries e2 
             JOIN sessions s2 ON e2.session_id = s2.session_id 
             WHERE s2.track = a.track AND s2.session_type = a.session_type 
             AND e2.best_lap_ms = a.best_lap_ms 
             AND e2.player_id IS NOT NULL 
             LIMIT 1)) as short_name,
          COALESCE(r.car_model,
            (SELECT e2.car_model FROM entries e2 
             JOIN sessions s2 ON e2.session_id = s2.session_id 
             WHERE s2.track = a.track AND s2.session_type = a.session_type 
             AND e2.best_lap_ms = a.best_lap_ms 
             AND e2.player_id IS NOT NULL 
             LIMIT 1)) as car_model
        FROM record_announcements a
        LEFT JOIN records r
          ON r.track = a.track
         AND r.session_type = a.session_type
         AND r.best_lap_ms = a.best_lap_ms
        WHERE a.discord_message_id IS NULL
        ORDER BY a.announced_at_utc ASC
        LIMIT ?
        """,
        (BATCH_SIZE,),
    ).fetchall()

def mark_sent(con: sqlite3.Connection, announcement_id: int, message_id: int):
    con.execute(
        """
        UPDATE record_announcements
        SET discord_message_id = ?
        WHERE announcement_id = ?
        """,
        (str(message_id), announcement_id),
    )
    con.commit()

def normalize_track_name(track_name: str) -> str:
    """Normalize track name for matching (lowercase, handle spaces/underscores)."""
    return track_name.lower().strip().replace(" ", "_")

def find_track_image(track_name: str) -> tuple[str, discord.File] | tuple[None, None]:
    """Find matching image file for a track name. Returns (filename, File) or (None, None)."""
    if not os.path.exists(IMG_DIR):
        return None, None
    
    # Normalize track name for matching
    normalized_track = normalize_track_name(track_name)
    
    # Get all image files
    image_files = [f for f in os.listdir(IMG_DIR) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    
    # Try exact match first (case-insensitive)
    for img_file in image_files:
        normalized_img = normalize_track_name(os.path.splitext(img_file)[0])
        if normalized_track == normalized_img:
            file_path = os.path.join(IMG_DIR, img_file)
            return img_file, discord.File(file_path, filename=img_file)
    
    # Try partial match (track name contained in image name or vice versa)
    for img_file in image_files:
        normalized_img = normalize_track_name(os.path.splitext(img_file)[0])
        # Remove common prefixes/suffixes for matching
        img_clean = normalized_img.replace("circuit", "").replace("gp", "").replace("_", "").strip()
        track_clean = normalized_track.replace("_", "").strip()
        
        if track_clean in img_clean or img_clean in track_clean:
            file_path = os.path.join(IMG_DIR, img_file)
            return img_file, discord.File(file_path, filename=img_file)
    
    # Special case mappings for common variations
    special_mappings = {
        "spa": "Spa-Francochamps.jpg",
        "nurburgring": "Nürburgring.jpeg",
        "nurburgring_24h": "Nürburgring.jpeg",
        "paul_ricard": "Circuit Paul Ricard.jpg",
        "zandvoort": "Circuit Zandvoort.jpg",
        "zolder": "Circuit Zolder.jpg",
        "brands_hatch": "Brands Hatch GP.jpg",
        "cota": "Circuit of the Americas.jpg",
        "valencia": "Circuit Ricardo Tormo.jpg",
        "red_bull_ring": "Red Bull Ring.jpg",
        "mount_panorama": "Mount Panorama Circuit.jpg",
        "silverstone": "Silverstone GP Circuit.jpg",
        "donington": "Donington Park.jpg",
        "oulton_park": "Oulton Park.jpg",
        "watkins_glen": "Watkins Glen.jpg",
        "suzuka": "Suzuka Circuit.jpg",
    }
    
    if normalized_track in special_mappings:
        img_file = special_mappings[normalized_track]
        file_path = os.path.join(IMG_DIR, img_file)
        if os.path.exists(file_path):
            return img_file, discord.File(file_path, filename=img_file)
    
    return None, None

def find_track_match(con: sqlite3.Connection, track_input: str) -> str:
    """Find the actual track name in DB that matches the input (case-insensitive)."""
    # Try exact case-insensitive match first
    result = con.execute(
        """
        SELECT DISTINCT track 
        FROM sessions 
        WHERE LOWER(track) = LOWER(?)
        LIMIT 1
        """,
        (track_input,)
    ).fetchone()
    
    if result:
        return result[0]
    
    # Try partial match
    result = con.execute(
        """
        SELECT DISTINCT track 
        FROM sessions 
        WHERE LOWER(track) LIKE LOWER(?)
        LIMIT 1
        """,
        (f"%{track_input}%",)
    ).fetchone()
    
    if result:
        return result[0]
    
    return None

def fetch_track_top_times(con: sqlite3.Connection, track_name: str, limit: int = 3):
    """Get top N times for a specific track, for both Q and R session types."""
    # Get top times for Qualifying
    q_times = con.execute(
        """
        SELECT
          s.session_type,
          e.best_lap_ms,
          e.first_name,
          e.last_name,
          e.short_name,
          e.car_model,
          s.file_mtime_utc
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = 'Q'
          AND e.best_lap_ms IS NOT NULL
        ORDER BY e.best_lap_ms ASC
        LIMIT ?
        """,
        (track_name, limit)
    ).fetchall()
    
    # Get top times for Race
    r_times = con.execute(
        """
        SELECT
          s.session_type,
          e.best_lap_ms,
          e.first_name,
          e.last_name,
          e.short_name,
          e.car_model,
          s.file_mtime_utc
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = 'R'
          AND e.best_lap_ms IS NOT NULL
        ORDER BY e.best_lap_ms ASC
        LIMIT ?
        """,
        (track_name, limit)
    ).fetchall()
    
    return q_times, r_times

def fetch_available_tracks(con: sqlite3.Connection):
    """Get list of all tracks that have Q/R sessions with best lap times."""
    return con.execute(
        """
        SELECT DISTINCT s.track
        FROM sessions s
        JOIN entries e ON s.session_id = s.session_id
        WHERE UPPER(s.session_type) IN ('Q', 'R')
          AND e.best_lap_ms IS NOT NULL
        ORDER BY s.track ASC
        """
    ).fetchall()

def fetch_all_players(con: sqlite3.Connection):
    """Get list of all unique players (first_name, last_name) from entries."""
    return con.execute(
        """
        SELECT DISTINCT 
            COALESCE(first_name, '') as first_name,
            COALESCE(last_name, '') as last_name
        FROM entries
        WHERE (first_name IS NOT NULL OR last_name IS NOT NULL)
          AND player_id IS NOT NULL
        ORDER BY first_name, last_name
        """
    ).fetchall()

def fetch_player_pbs(con: sqlite3.Connection, first_name: str, last_name: str):
    """Get personal bests for a specific player across all tracks."""
    return con.execute(
        """
        WITH player_entries AS (
            SELECT 
                s.track,
                UPPER(s.session_type) as session_type,
                e.best_lap_ms,
                e.car_model,
                s.file_mtime_utc,
                ROW_NUMBER() OVER (PARTITION BY s.track, UPPER(s.session_type) ORDER BY e.best_lap_ms ASC) as rn
            FROM entries e
            JOIN sessions s ON e.session_id = s.session_id
            WHERE UPPER(s.session_type) IN ('Q', 'R')
              AND e.best_lap_ms IS NOT NULL
              AND e.first_name = ?
              AND e.last_name = ?
        )
        SELECT 
            track,
            session_type,
            best_lap_ms,
            car_model,
            file_mtime_utc
        FROM player_entries
        WHERE rn = 1
        ORDER BY track, session_type
        """
    , (first_name, last_name)).fetchall()

def get_player_rank(con: sqlite3.Connection, track: str, session_type: str, best_lap_ms: int, first_name: str, last_name: str) -> tuple[int, int]:
    """
    Get player's rank on a track. Returns (rank, total_drivers).
    Rank is 1-indexed (1 = first place).
    For ties, all players with the same time get the same rank.
    """
    # Get each player's best time on this track
    # Count how many players have a better (lower) best time
    rank_result = con.execute(
        """
        WITH player_bests AS (
            SELECT 
                e.first_name,
                e.last_name,
                MIN(e.best_lap_ms) as best_time
            FROM entries e
            JOIN sessions s ON e.session_id = s.session_id
            WHERE s.track = ?
              AND UPPER(s.session_type) = ?
              AND e.best_lap_ms IS NOT NULL
              AND e.player_id IS NOT NULL
            GROUP BY e.player_id, e.first_name, e.last_name
        )
        SELECT 
            COUNT(*) + 1 as rank
        FROM player_bests
        WHERE best_time < ?
        """,
        (track, session_type, best_lap_ms)
    ).fetchone()
    
    # Get total number of drivers with times on this track
    total_result = con.execute(
        """
        SELECT COUNT(DISTINCT e.player_id)
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = ?
          AND e.best_lap_ms IS NOT NULL
          AND e.player_id IS NOT NULL
        """,
        (track, session_type)
    ).fetchone()
    
    rank = rank_result[0] if rank_result else None
    total = total_result[0] if total_result else 0
    
    return rank, total

def get_track_record(con: sqlite3.Connection, track: str, session_type: str) -> int | None:
    """Get the track record (best lap time) for a track and session type. Returns None if no record exists."""
    result = con.execute(
        """
        SELECT best_lap_ms
        FROM records
        WHERE track = ? AND session_type = ?
        """,
        (track, session_type)
    ).fetchone()
    
    return result[0] if result else None

def get_session_count(con: sqlite3.Connection, track: str, session_type: str, first_name: str, last_name: str) -> int:
    """Get the number of sessions a player has completed on a track."""
    result = con.execute(
        """
        SELECT COUNT(DISTINCT s.session_id)
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = ?
          AND e.first_name = ?
          AND e.last_name = ?
          AND e.best_lap_ms IS NOT NULL
        """,
        (track, session_type, first_name, last_name)
    ).fetchone()
    
    return result[0] if result else 0

def get_previous_pb(con: sqlite3.Connection, track: str, session_type: str, current_pb_ms: int, first_name: str, last_name: str) -> int | None:
    """Get the previous PB (second best time) for a player on a track. Returns None if no previous PB exists."""
    result = con.execute(
        """
        SELECT MIN(e.best_lap_ms)
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = ?
          AND e.first_name = ?
          AND e.last_name = ?
          AND e.best_lap_ms IS NOT NULL
          AND e.best_lap_ms > ?
        """,
        (track, session_type, first_name, last_name, current_pb_ms)
    ).fetchone()
    
    return result[0] if result else None

def calculate_performance_percentage(player_time: int, track_record: int) -> float:
    """Calculate how close player is to track record as a percentage. 100% = equal to record, >100% = slower."""
    if track_record is None or track_record == 0:
        return None
    return (player_time / track_record) * 100

def fetch_all_tracks_top_times(con: sqlite3.Connection):
    """Get top 1 Q and R time for each track. Returns dict keyed by track name."""
    tracks_data = {}
    
    # Get all unique tracks
    all_tracks = con.execute(
        """
        SELECT DISTINCT s.track
        FROM sessions s
        JOIN entries e ON s.session_id = e.session_id
        WHERE UPPER(s.session_type) IN ('Q', 'R')
          AND e.best_lap_ms IS NOT NULL
        ORDER BY s.track ASC
        """
    ).fetchall()
    
    # For each track, get best Q and R times
    for (track,) in all_tracks:
        # Get best Q time
        q_result = con.execute(
            """
            SELECT
              e.best_lap_ms,
              e.first_name,
              e.last_name,
              e.short_name,
              e.car_model,
              s.file_mtime_utc
            FROM entries e
            JOIN sessions s ON e.session_id = s.session_id
            WHERE s.track = ?
              AND UPPER(s.session_type) = 'Q'
              AND e.best_lap_ms IS NOT NULL
            ORDER BY e.best_lap_ms ASC
            LIMIT 1
            """,
            (track,)
        ).fetchone()
        
        # Get best R time
        r_result = con.execute(
            """
            SELECT
              e.best_lap_ms,
              e.first_name,
              e.last_name,
              e.short_name,
              e.car_model,
              s.file_mtime_utc
            FROM entries e
            JOIN sessions s ON e.session_id = s.session_id
            WHERE s.track = ?
              AND UPPER(s.session_type) = 'R'
              AND e.best_lap_ms IS NOT NULL
            ORDER BY e.best_lap_ms ASC
            LIMIT 1
            """,
            (track,)
        ).fetchone()
        
        tracks_data[track] = {
            'q': q_result,
            'r': r_result
        }
    
    return tracks_data

def build_track_record_embed(track, stype, best_ms, when_utc, first, last, short, car_model):
    """Build a Discord embed for track record announcements."""
    session_label = "Qualifying" if stype == "Q" else "Race"
    who = "Unknown driver"
    if first or last:
        who = f"{(first or '').strip()} {(last or '').strip()}".strip()
    elif short:
        who = short

    car_name = fmt_car_model(car_model)
    
    embed = discord.Embed(
        title=f"🏆 New Track Record!",
        description=f"**{track}** - {session_label}",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="🏁 Driver",
        value=who,
        inline=True
    )
    
    embed.add_field(
        name="⏱️ Time",
        value=f"**{fmt_ms(best_ms)}**",
        inline=True
    )
    
    embed.add_field(
        name="🚗 Car",
        value=car_name,
        inline=True
    )
    
    embed.add_field(
        name="📅 Set On",
        value=fmt_dt(when_utc),
        inline=False
    )
    
    # Try to add track image thumbnail
    img_filename, img_file = find_track_image(track)
    if img_file:
        embed.set_thumbnail(url=f"attachment://{img_filename}")
        return embed, img_file
    
    return embed, None

def fetch_race_results_queue(con: sqlite3.Connection):
    """Fetch pending race results announcements."""
    return con.execute(
        """
        SELECT
          r.announcement_id,
          r.session_id,
          r.track,
          r.announced_at_utc
        FROM race_results_announcements r
        WHERE r.discord_message_id IS NULL
        ORDER BY r.announced_at_utc ASC
        LIMIT ?
        """,
        (BATCH_SIZE,),
    ).fetchall()

def fetch_race_session_data(con: sqlite3.Connection, session_id: int):
    """Fetch all data needed for race results embed."""
    # Get session info
    session = con.execute(
        """
        SELECT track, session_type, server_name, is_wet, session_index, 
               race_weekend_index, file_mtime_utc
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,)
    ).fetchone()
    
    if not session:
        return None, []
    
    # Get all entries ordered by position
    entries = con.execute(
        """
        SELECT 
            position,
            first_name,
            last_name,
            short_name,
            car_model,
            race_number,
            best_lap_ms,
            total_time_ms,
            lap_count,
            car_group
        FROM entries
        WHERE session_id = ?
        ORDER BY position ASC
        """,
        (session_id,)
    ).fetchall()
    
    return session, entries

def mark_race_results_sent(con: sqlite3.Connection, announcement_id: int, message_id: int):
    """Mark a race results announcement as sent."""
    con.execute(
        """
        UPDATE race_results_announcements
        SET discord_message_id = ?
        WHERE announcement_id = ?
        """,
        (str(message_id), announcement_id),
    )
    con.commit()

def build_race_results_embed(track, session_data, entries, when_utc):
    """Build a Discord embed for race results."""
    track_name, session_type, server_name, is_wet, session_index, race_weekend_index, file_mtime_utc = session_data
    
    # Determine conditions
    conditions = "🌧️ Wet" if is_wet else "☀️ Dry"
    
    # Get lap count from first entry (should be same for all finishers)
    lap_count = entries[0][10] if entries else 0
    
    # Create embed
    embed = discord.Embed(
        title=f"🏁 Race Results - {track.title().replace('_', ' ')}",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Add race info
    race_date = fmt_dt(when_utc) if when_utc else "Unknown"
    embed.description = f"📅 {race_date} | 🔄 {lap_count} Laps | {conditions}"
    
    # Try to add track image
    img_filename, img_file = find_track_image(track)
    if img_file:
        embed.set_thumbnail(url=f"attachment://{img_filename}")
    
    # Get leader's total time for gap calculations
    leader_total_ms = entries[0][9] if entries and entries[0][9] else None
    leader_best_ms = entries[0][8] if entries and entries[0][8] else None
    
    # Medals for top 3
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    # Build standings
    standings_lines = []
    for entry in entries[:10]:  # Limit to top 10 for embed space
        position, first_name, last_name, short_name, car_model, race_number, best_lap_ms, total_time_ms, entry_lap_count, car_group = entry
        
        # Format driver name
        if first_name or last_name:
            driver_name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
        elif short_name:
            driver_name = short_name
        else:
            driver_name = "Unknown"
        
        car_name = fmt_car_model(car_model)
        medal = medals.get(position, "")
        
        # Calculate gap to leader
        if position == 1:
            gap_str = "Leader"
        elif total_time_ms and leader_total_ms:
            gap_ms = total_time_ms - leader_total_ms
            gap_str = f"+{fmt_ms(gap_ms)}"
        else:
            gap_str = "N/A"
        
        # Best lap comparison
        if best_lap_ms and leader_best_ms:
            if position == 1:
                best_lap_str = f"**{fmt_ms(best_lap_ms)}** 🔥"
            else:
                lap_diff = best_lap_ms - leader_best_ms
                best_lap_str = f"{fmt_ms(best_lap_ms)} ({fmt_split_ms(lap_diff)})"
        elif best_lap_ms:
            best_lap_str = fmt_ms(best_lap_ms)
        else:
            best_lap_str = "No time"
        
        # Build the line
        if position <= 3:
            line = f"{medal} **{position}.** **{driver_name}**"
        else:
            line = f"**{position}.** {driver_name}"
        
        standings_lines.append(f"{line}\n   `{car_name}` #{race_number} | {gap_str} | Best: {best_lap_str}")
    
    # Add standings field
    if standings_lines:
        # Split into two fields if more than 5 entries
        if len(standings_lines) > 5:
            embed.add_field(
                name="📊 Final Standings (1-5)",
                value="\n".join(standings_lines[:5]),
                inline=False
            )
            embed.add_field(
                name="📊 Final Standings (6-10)",
                value="\n".join(standings_lines[5:10]),
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Final Standings",
                value="\n".join(standings_lines),
                inline=False
            )
    
    # Add fastest lap field
    if entries:
        # Find the fastest lap
        fastest_entry = min((e for e in entries if e[8]), key=lambda x: x[8], default=None)
        if fastest_entry:
            fl_position, fl_first, fl_last, fl_short, fl_car, fl_num, fl_best, _, _, _ = fastest_entry
            fl_driver = f"{(fl_first or '').strip()} {(fl_last or '').strip()}".strip() or fl_short or "Unknown"
            embed.add_field(
                name="⚡ Fastest Lap",
                value=f"**{fmt_ms(fl_best)}** — {fl_driver} ({fmt_car_model(fl_car)})",
                inline=False
            )
    
    # Set footer
    embed.set_footer(text=f"{server_name or 'ACC Server'}")
    
    if img_file:
        return embed, img_file
    return embed, None

def build_personal_best_embed(track, stype, best_ms, when_utc, first, last, short, car_model):
    """Build a Discord embed for personal best announcements."""
    session_label = "Qualifying" if stype == "Q" else "Race"
    who = "Unknown driver"
    if first or last:
        who = f"{(first or '').strip()} {(last or '').strip()}".strip()
    elif short:
        who = short

    car_name = fmt_car_model(car_model)
    
    embed = discord.Embed(
        title=f"🎯 New Personal Best!",
        description=f"**{track}** - {session_label}",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="🏁 Driver",
        value=who,
        inline=True
    )
    
    embed.add_field(
        name="⏱️ Time",
        value=f"**{fmt_ms(best_ms)}**",
        inline=True
    )
    
    embed.add_field(
        name="🚗 Car",
        value=car_name,
        inline=True
    )
    
    embed.add_field(
        name="📅 Set On",
        value=fmt_dt(when_utc),
        inline=False
    )
    
    # Try to add track image thumbnail
    img_filename, img_file = find_track_image(track)
    if img_file:
        embed.set_thumbnail(url=f"attachment://{img_filename}")
        return embed, img_file
    
    return embed, None

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

async def track_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for track names."""
    con = sqlite3.connect(DB_PATH)
    available = fetch_available_tracks(con)
    con.close()
    
    # Filter tracks based on current input
    current_lower = current.lower()
    matches = [
        app_commands.Choice(name=track[0], value=track[0])
        for track in available
        if current_lower in track[0].lower()
    ][:25]  # Discord limit is 25 choices
    
    return matches

async def player_first_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for player first names."""
    try:
        con = sqlite3.connect(DB_PATH)
        players = fetch_all_players(con)
        con.close()
        
        # Get unique first names (filter out empty strings)
        first_names = sorted(set([p[0] for p in players if p[0] and p[0].strip()]))
        
        if not first_names:
            return []
        
        current_lower = current.lower() if current else ""
        if current_lower:
            matches = [
                app_commands.Choice(name=name, value=name)
                for name in first_names
                if current_lower in name.lower()
            ][:25]
        else:
            # If no input, return first 25 names
            matches = [
                app_commands.Choice(name=name, value=name)
                for name in first_names[:25]
            ]
        
        return matches
    except Exception as e:
        print(f"[WARN] Error in first_name autocomplete: {e}")
        import traceback
        traceback.print_exc()
        return []

async def player_last_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for player last names."""
    try:
        # Get first_name from interaction if available
        first_name = None
        try:
            if hasattr(interaction.namespace, 'first_name'):
                first_name = interaction.namespace.first_name
        except:
            pass
        
        con = sqlite3.connect(DB_PATH)
        players = fetch_all_players(con)
        con.close()
        
        # Filter by first name if provided
        if first_name:
            matching_players = [p for p in players if p[0] == first_name]
            last_names = sorted(set([p[1] for p in matching_players if p[1]]))
        else:
            last_names = sorted(set([p[1] for p in players if p[1]]))
        
        current_lower = current.lower()
        matches = [
            app_commands.Choice(name=name, value=name)
            for name in last_names
            if current_lower in name.lower()
        ][:25]
        
        return matches
    except Exception as e:
        print(f"[WARN] Error in last_name autocomplete: {e}")
        return []

@tree.command(name="records", description="Show top 3 times for a specific track (Q and R)")
@app_commands.autocomplete(track=track_autocomplete)
async def records(interaction: discord.Interaction, track: str):
    # Only allow in your target channel (optional safety)
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message(
            f"Use this in <#{CHANNEL_ID}>.",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    con = sqlite3.connect(DB_PATH)
    
    # Try to find matching track name (case-insensitive)
    actual_track = find_track_match(con, track)
    if not actual_track:
        available = fetch_available_tracks(con)
        con.close()
        
        track_list = ", ".join([t[0] for t in available[:20]])  # Show first 20
        if len(available) > 20:
            track_list += f", ... ({len(available)} total)"
        
        await interaction.followup.send(
            f"No track found matching **{track}**.\n\n"
            f"Use `/tracks` to see all available tracks.\n"
            f"*Track names are case-insensitive and can use spaces or underscores.*"
        )
        return
    
    # Get top 4 times for both Q and R (leader + next 3)
    q_times, r_times = fetch_track_top_times(con, actual_track, limit=4)
    con.close()

    if not q_times and not r_times:
        await interaction.followup.send(
            f"No times found for track **{actual_track}** yet."
        )
        return

    # Create embed
    embed = discord.Embed(
        title=f"🏁 {actual_track}",
        color=discord.Color.blue()
    )
    
    # Try to find and attach track image as thumbnail (appears near top, under title)
    img_filename, img_file = find_track_image(actual_track)
    if img_file:
        embed.set_thumbnail(url=f"attachment://{img_filename}")
    
    # Helper function to format driver name
    def format_driver(first, last, short):
        if first or last:
            return f"{(first or '').strip()} {(last or '').strip()}".strip()
        elif short:
            return short
        return "Unknown"
    
    # Qualifying section
    if q_times:
        leader_q = q_times[0]
        stype, leader_ms, first, last, short, car_model, set_at_utc = leader_q
        who = format_driver(first, last, short)
        when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
        car_name = fmt_car_model(car_model)
        
        # Highlight leader
        q_leader_text = f"🥇 **{fmt_ms(leader_ms)}** — {who}\n`{car_name}` • {when}"
        embed.add_field(
            name="🏁 Qualifying Leader",
            value=q_leader_text,
            inline=False
        )
        
        # Next 3 times with splits
        if len(q_times) > 1:
            next_times = []
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            for idx, (stype, best_ms, first, last, short, car_model, set_at_utc) in enumerate(q_times[1:4], 2):
                who = format_driver(first, last, short)
                when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
                car_name = fmt_car_model(car_model)
                split_ms = best_ms - leader_ms  # Positive = slower
                split_str = fmt_split_ms(split_ms)
                medal = medals.get(idx, "")
                next_times.append(f"{medal} **{idx}.** **{fmt_ms(best_ms)}** ({split_str}) — {who} ({car_name})")
            
            if next_times:
                embed.add_field(
                    name="Qualifying Times",
                    value="\n".join(next_times),
                    inline=False
                )
    else:
        embed.add_field(
            name="🏁 Qualifying",
            value="No times recorded",
            inline=False
        )
    
    # Race section
    if r_times:
        leader_r = r_times[0]
        stype, leader_ms, first, last, short, car_model, set_at_utc = leader_r
        who = format_driver(first, last, short)
        when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
        car_name = fmt_car_model(car_model)
        
        # Highlight leader
        r_leader_text = f"🥇 **{fmt_ms(leader_ms)}** — {who}\n`{car_name}` • {when}"
        embed.add_field(
            name="🏎️ Race Leader",
            value=r_leader_text,
            inline=False
        )
        
        # Next 3 times with splits
        if len(r_times) > 1:
            next_times = []
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            for idx, (stype, best_ms, first, last, short, car_model, set_at_utc) in enumerate(r_times[1:4], 2):
                who = format_driver(first, last, short)
                when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
                car_name = fmt_car_model(car_model)
                split_ms = best_ms - leader_ms  # Positive = slower
                split_str = fmt_split_ms(split_ms)
                medal = medals.get(idx, "")
                next_times.append(f"{medal} **{idx}.** **{fmt_ms(best_ms)}** ({split_str}) — {who} ({car_name})")
            
            if next_times:
                embed.add_field(
                    name="Race Times",
                    value="\n".join(next_times),
                    inline=False
                )
    else:
        embed.add_field(
            name="🏎️ Race",
            value="No times recorded",
            inline=False
        )
    
    # Set footer
    embed.set_footer(text="Use /leaders to see all track leaders")
    
    # Send embed with image file if found
    if img_file:
        await interaction.followup.send(embed=embed, file=img_file)
    else:
        await interaction.followup.send(embed=embed)

@tree.command(name="sync", description="Manually sync slash commands (admin)")
async def sync_commands(interaction: discord.Interaction):
    """Manually sync slash commands - useful if commands aren't appearing."""
    await interaction.response.defer(ephemeral=True)
    try:
        # Clear existing commands and re-sync
        synced = await tree.sync()
        
        cmd_list = "\n".join([f"  • /{cmd.name}" for cmd in synced])
        await interaction.followup.send(
            f"✅ Synced {len(synced)} command(s) to Discord:\n{cmd_list}\n\n"
            f"⏰ **Note:** It may take 5-10 minutes for new commands to appear.\n"
            f"Try restarting Discord if `/pb` still doesn't show up.",
            ephemeral=True
        )
        print(f"[OK] Manually synced {len(synced)} commands")
        for cmd in synced:
            print(f"  - /{cmd.name}")
    except Exception as e:
        await interaction.followup.send(f"❌ Error syncing commands: {e}", ephemeral=True)
        print(f"[ERR] Sync error: {e}")
        import traceback
        traceback.print_exc()

@tree.command(name="leaders", description="Show top 1 Q and R time for all tracks")
async def leaders(interaction: discord.Interaction):
    # Only allow in your target channel (optional safety)
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message(
            f"Use this in <#{CHANNEL_ID}>.",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    con = sqlite3.connect(DB_PATH)
    tracks_data = fetch_all_tracks_top_times(con)
    con.close()

    if not tracks_data:
        await interaction.followup.send("No track records found in the database yet.")
        return

    lines = []
    lines.append(f"**Top Times for All Tracks**\n")

    for track in sorted(tracks_data.keys()):
        q_data = tracks_data[track]['q']
        r_data = tracks_data[track]['r']
        
        lines.append(f"**{track}**")
        
        # Qualifying
        if q_data:
            best_ms, first, last, short, car_model, set_at_utc = q_data
            who = "Unknown"
            if first or last:
                who = f"{(first or '').strip()} {(last or '').strip()}".strip()
            elif short:
                who = short
            
            when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
            car_name = fmt_car_model(car_model)
            lines.append(f"  🏁 Q: **{fmt_ms(best_ms)}** — {who} ({car_name}) — {when}")
        else:
            lines.append(f"  🏁 Q: No times")
        
        # Race
        if r_data:
            best_ms, first, last, short, car_model, set_at_utc = r_data
            who = "Unknown"
            if first or last:
                who = f"{(first or '').strip()} {(last or '').strip()}".strip()
            elif short:
                who = short
            
            when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
            car_name = fmt_car_model(car_model)
            lines.append(f"  🏎️ R: **{fmt_ms(best_ms)}** — {who} ({car_name}) — {when}")
        else:
            lines.append(f"  🏎️ R: No times")
        
        lines.append("")  # Blank line between tracks

    # Discord message limit safety: chunk if needed
    msg = "\n".join(lines)
    if len(msg) <= 1900:
        await interaction.followup.send(msg)
        return

    # Chunk fallback - split by tracks
    chunk = "**Top Times for All Tracks**\n\n"
    for track in sorted(tracks_data.keys()):
        q_data = tracks_data[track]['q']
        r_data = tracks_data[track]['r']
        
        track_section = f"**{track}**\n"
        
        if q_data:
            best_ms, first, last, short, car_model, set_at_utc = q_data
            who = "Unknown"
            if first or last:
                who = f"{(first or '').strip()} {(last or '').strip()}".strip()
            elif short:
                who = short
            when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
            car_name = fmt_car_model(car_model)
            track_section += f"  🏁 Q: **{fmt_ms(best_ms)}** — {who} ({car_name}) — {when}\n"
        else:
            track_section += f"  🏁 Q: No times\n"
        
        if r_data:
            best_ms, first, last, short, car_model, set_at_utc = r_data
            who = "Unknown"
            if first or last:
                who = f"{(first or '').strip()} {(last or '').strip()}".strip()
            elif short:
                who = short
            when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
            car_name = fmt_car_model(car_model)
            track_section += f"  🏎️ R: **{fmt_ms(best_ms)}** — {who} ({car_name}) — {when}\n"
        else:
            track_section += f"  🏎️ R: No times\n"
        
        track_section += "\n"
        
        if len(chunk) + len(track_section) > 1900:
            await interaction.followup.send(chunk)
            chunk = ""
        chunk += track_section
    
    if chunk.strip():
        await interaction.followup.send(chunk)

@tree.command(name="pb", description="Show personal bests for a player across all tracks")
@app_commands.autocomplete(first_name=player_first_name_autocomplete, last_name=player_last_name_autocomplete)
async def pb(interaction: discord.Interaction, first_name: str, last_name: str):
    # Only allow in your target channel (optional safety)
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message(
            f"Use this in <#{CHANNEL_ID}>.",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    con = sqlite3.connect(DB_PATH)
    pbs = fetch_player_pbs(con, first_name, last_name)

    if not pbs:
        await interaction.followup.send(
            f"No personal bests found for **{first_name} {last_name}**.\n\n"
            f"*Make sure you've spelled the name correctly.*"
        )
        return

    # Create embed
    player_name = f"{first_name} {last_name}".strip()
    embed = discord.Embed(
        title=f"🎯 Personal Bests: {player_name}",
        color=discord.Color.green()
    )

    # Group by track and get additional stats
    tracks_dict = {}
    for track, stype, best_ms, car_model, set_at_utc in pbs:
        if track not in tracks_dict:
            tracks_dict[track] = {'q': None, 'r': None}
        
        car_name = fmt_car_model(car_model)
        when = fmt_dt(set_at_utc) if set_at_utc else "Unknown time"
        
        # Get additional stats
        rank, total = get_player_rank(con, track, stype, best_ms, first_name, last_name)
        track_record = get_track_record(con, track, stype)
        session_count = get_session_count(con, track, stype, first_name, last_name)
        previous_pb = get_previous_pb(con, track, stype, best_ms, first_name, last_name)
        
        # Calculate gap to track record
        gap_to_record = None
        if track_record:
            gap_ms = best_ms - track_record
            gap_to_record = gap_ms
        
        # Calculate trend (faster/slower than previous PB)
        trend = None
        if previous_pb:
            if best_ms < previous_pb:
                trend = "faster"  # Improved (lower time is better)
            elif best_ms > previous_pb:
                trend = "slower"  # Got worse
            else:
                trend = "equal"
        
        # Calculate performance percentage
        perf_pct = calculate_performance_percentage(best_ms, track_record)
        
        tracks_dict[track][stype.lower()] = {
            'time': best_ms,
            'car': car_name,
            'date': when,
            'rank': rank,
            'total': total,
            'gap_to_record': gap_to_record,
            'track_record': track_record,
            'session_count': session_count,
            'trend': trend,
            'perf_pct': perf_pct
        }

    # Build embed fields with all stats
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    favorite_track = None
    best_perf_pct = None
    
    for track in sorted(tracks_dict.keys()):
        track_data = tracks_dict[track]
        track_text = []
        
        if track_data['q']:
            q_data = track_data['q']
            rank = q_data['rank']
            total = q_data['total']
            medal = medals.get(rank, "")
            rank_text = f"#{rank} of {total}" if rank and total else "?"
            
            # Build the line with all info
            if rank and rank <= 3:
                line_parts = [f"🏁 **Q**: {medal} **{fmt_ms(q_data['time'])}**"]
            else:
                line_parts = [f"🏁 **Q**: {fmt_ms(q_data['time'])}"]
            
            line_parts.append(f"({q_data['car']})")
            
            # Rank
            if rank and total:
                line_parts.append(f"**#{rank} of {total}**")
            elif rank_text != "?":
                line_parts.append(rank_text)
            
            # Gap to track record
            if q_data['gap_to_record'] is not None:
                gap_str = fmt_split_ms(q_data['gap_to_record'])
                line_parts.append(f"*{gap_str} off record*")
            
            # Session count
            if q_data['session_count'] > 0:
                sessions_text = f"{q_data['session_count']} session" + ("s" if q_data['session_count'] > 1 else "")
                line_parts.append(f"({sessions_text})")
            
            # Trend indicator
            if q_data['trend']:
                if q_data['trend'] == "faster":
                    trend_emoji = "⬇️"
                elif q_data['trend'] == "slower":
                    trend_emoji = "⬆️"
                else:
                    trend_emoji = "➡️"
                line_parts.append(trend_emoji)
            
            track_text.append(" ".join(line_parts))
            
            # Track favorite track (best performance percentage)
            if q_data['perf_pct'] is not None:
                if best_perf_pct is None or q_data['perf_pct'] < best_perf_pct:
                    best_perf_pct = q_data['perf_pct']
                    favorite_track = (track, "Q", q_data['perf_pct'])
        
        if track_data['r']:
            r_data = track_data['r']
            rank = r_data['rank']
            total = r_data['total']
            medal = medals.get(rank, "")
            rank_text = f"#{rank} of {total}" if rank and total else "?"
            
            # Build the line with all info
            if rank and rank <= 3:
                line_parts = [f"🏎️ **R**: {medal} **{fmt_ms(r_data['time'])}**"]
            else:
                line_parts = [f"🏎️ **R**: {fmt_ms(r_data['time'])}"]
            
            line_parts.append(f"({r_data['car']})")
            
            # Rank
            if rank and total:
                line_parts.append(f"**#{rank} of {total}**")
            elif rank_text != "?":
                line_parts.append(rank_text)
            
            # Gap to track record
            if r_data['gap_to_record'] is not None:
                gap_str = fmt_split_ms(r_data['gap_to_record'])
                line_parts.append(f"*{gap_str} off record*")
            
            # Session count
            if r_data['session_count'] > 0:
                sessions_text = f"{r_data['session_count']} session" + ("s" if r_data['session_count'] > 1 else "")
                line_parts.append(f"({sessions_text})")
            
            # Trend indicator
            if r_data['trend']:
                if r_data['trend'] == "faster":
                    trend_emoji = "⬇️"
                elif r_data['trend'] == "slower":
                    trend_emoji = "⬆️"
                else:
                    trend_emoji = "➡️"
                line_parts.append(trend_emoji)
            
            track_text.append(" ".join(line_parts))
            
            # Track favorite track (best performance percentage)
            if r_data['perf_pct'] is not None:
                if best_perf_pct is None or r_data['perf_pct'] < best_perf_pct:
                    best_perf_pct = r_data['perf_pct']
                    favorite_track = (track, "R", r_data['perf_pct'])
        
        if track_text:
            embed.add_field(
                name=f"**{track}**",
                value="\n".join(track_text),
                inline=False
            )
    
    con.close()

    # Add favorite track to footer (best performance relative to track record)
    footer_text = f"Total tracks: {len(tracks_dict)}"
    if favorite_track:
        track_name, stype, perf_pct = favorite_track
        gap_pct = perf_pct - 100.0
        if gap_pct > 0:
            footer_text += f" | ⭐ Favorite: {track_name} ({stype}, +{gap_pct:.2f}% off record)"
        else:
            footer_text += f" | ⭐ Favorite: {track_name} ({stype}, {abs(gap_pct):.2f}% faster than record!)"
    
    embed.set_footer(text=footer_text)
    
    await interaction.followup.send(embed=embed)

@tree.command(name="tracks", description="List all available tracks")
async def tracks(interaction: discord.Interaction):
    # Only allow in your target channel (optional safety)
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message(
            f"Use this in <#{CHANNEL_ID}>.",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    con = sqlite3.connect(DB_PATH)
    available = fetch_available_tracks(con)
    con.close()

    if not available:
        await interaction.followup.send("No tracks found in the database yet.")
        return

    # Format track list
    track_names = [t[0] for t in available]
    track_list = "\n".join([f"• {name}" for name in track_names])
    
    msg = f"**Available Tracks ({len(track_names)}):**\n\n{track_list}\n\n*Use `/records <trackname>` to see top times for a track.*"
    
    # Discord message limit safety
    if len(msg) <= 1900:
        await interaction.followup.send(msg)
    else:
        # Split into chunks if too long
        chunks = []
        current_chunk = f"**Available Tracks ({len(track_names)}):**\n\n"
        for name in track_names:
            line = f"• {name}\n"
            if len(current_chunk) + len(line) > 1900:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line
        if current_chunk:
            chunks.append(current_chunk + "\n*Use `/records <trackname>` to see top times for a track.*")
        
        for chunk in chunks:
            await interaction.followup.send(chunk)

@client.event
async def on_ready():
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[ERR] Could not find channel {CHANNEL_ID}. Is the bot in the server and has access?")
        return

    print(f"[OK] Logged in as {client.user}. Watching for queued record announcements...")

    try:
        synced = await tree.sync()
        print(f"[OK] Slash commands synced ({len(synced)} commands)")
        for cmd in synced:
            print(f"  - /{cmd.name}")
    except Exception as e:
        print(f"[ERR] Failed to sync commands: {e}")

    while True:
        try:
            con = sqlite3.connect(DB_PATH)
            
            # Process record announcements (TR and PB)
            rows = fetch_queue(con)
            for (
                announcement_id, track, stype, best_ms, when_utc,
                announcement_type, player_id, first, last, short, car_model
            ) in rows:
                # Build embed based on announcement type
                if announcement_type == "PB":
                    embed, img_file = build_personal_best_embed(track, stype, best_ms, when_utc, first, last, short, car_model)
                else:  # TR (Track Record)
                    embed, img_file = build_track_record_embed(track, stype, best_ms, when_utc, first, last, short, car_model)
                
                # Send embed with image if available
                if img_file:
                    sent = await channel.send(embed=embed, file=img_file)
                else:
                    sent = await channel.send(embed=embed)
                
                mark_sent(con, announcement_id, sent.id)
            
            # Process race results announcements
            try:
                race_rows = fetch_race_results_queue(con)
                for (announcement_id, session_id, track, when_utc) in race_rows:
                    session_data, entries = fetch_race_session_data(con, session_id)
                    
                    if session_data and entries:
                        embed, img_file = build_race_results_embed(track, session_data, entries, when_utc)
                        
                        if img_file:
                            sent = await channel.send(embed=embed, file=img_file)
                        else:
                            sent = await channel.send(embed=embed)
                        
                        mark_race_results_sent(con, announcement_id, sent.id)
                    else:
                        print(f"[WARN] No data found for race session {session_id}")
            except Exception as e:
                # Table might not exist yet, ignore
                if "no such table" not in str(e).lower():
                    print(f"[WARN] Race results error: {e}")

            con.close()

        except Exception as e:
            print(f"[WARN] loop error: {e}")

        await asyncio.sleep(POLL_SECONDS)

client.run(DISCORD_TOKEN)
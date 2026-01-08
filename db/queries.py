"""Database query functions."""
import sqlite3
from typing import Any
from config import BATCH_SIZE
from constants import DEFAULT_TOP_TIMES_LIMIT


def fetch_queue(con: sqlite3.Connection) -> list[tuple[Any, ...]]:
    """Pull queued announcements and join to records for the extra fields."""
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


def mark_sent(con: sqlite3.Connection, announcement_id: int, message_id: int) -> None:
    """Mark an announcement as sent."""
    con.execute(
        """
        UPDATE record_announcements
        SET discord_message_id = ?
        WHERE announcement_id = ?
        """,
        (str(message_id), announcement_id),
    )
    con.commit()


def find_track_match(con: sqlite3.Connection, track_input: str) -> str | None:
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


def fetch_track_top_times(con: sqlite3.Connection, track_name: str, limit: int = DEFAULT_TOP_TIMES_LIMIT) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
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


def fetch_available_tracks(con: sqlite3.Connection) -> list[tuple[str]]:
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


def fetch_all_players(con: sqlite3.Connection) -> list[tuple[str, str]]:
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


def fetch_player_pbs(con: sqlite3.Connection, first_name: str, last_name: str) -> list[tuple[Any, ...]]:
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


def calculate_performance_percentage(player_time: int, track_record: int | None) -> float | None:
    """Calculate how close player is to track record as a percentage. 100% = equal to record, >100% = slower."""
    if track_record is None or track_record == 0:
        return None
    return (player_time / track_record) * 100


def fetch_all_tracks_top_times(con: sqlite3.Connection) -> dict[str, dict[str, tuple[Any, ...] | None]]:
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


def fetch_race_results_queue(con: sqlite3.Connection) -> list[tuple[Any, ...]]:
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


def fetch_race_session_data(con: sqlite3.Connection, session_id: int) -> tuple[tuple[Any, ...] | None, list[tuple[Any, ...]]]:
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


def fetch_player_pb_with_sectors(con: sqlite3.Connection, first_name: str, last_name: str, track: str, session_type: str) -> tuple[int, str | None, int | None, str] | None:
    """
    Get player's personal best for a specific track/session with sector data.
    Returns: (best_lap_ms, best_splits_json, car_model, set_at_utc) or None
    """
    result = con.execute(
        """
        SELECT 
            e.best_lap_ms,
            e.best_splits_json,
            e.car_model,
            MIN(s.file_mtime_utc) as set_at_utc
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = ?
          AND e.best_lap_ms IS NOT NULL
          AND e.first_name = ?
          AND e.last_name = ?
        GROUP BY e.first_name, e.last_name
        ORDER BY e.best_lap_ms ASC
        LIMIT 1
        """,
        (track, session_type, first_name, last_name)
    ).fetchone()
    
    return result


def fetch_track_record_with_sectors(con: sqlite3.Connection, track: str, session_type: str) -> tuple[int, str | None] | None:
    """
    Get track record with sector data.
    Returns: (best_lap_ms, best_splits_json) or None
    """
    result = con.execute(
        """
        SELECT r.best_lap_ms,
               (SELECT e.best_splits_json 
                FROM entries e 
                JOIN sessions s ON e.session_id = s.session_id
                WHERE s.track = r.track 
                  AND UPPER(s.session_type) = r.session_type
                  AND e.best_lap_ms = r.best_lap_ms
                  AND e.best_splits_json IS NOT NULL
                LIMIT 1) as best_splits_json
        FROM records r
        WHERE r.track = ? AND r.session_type = ?
        """,
        (track, session_type)
    ).fetchone()
    
    return result


def mark_race_results_sent(con: sqlite3.Connection, announcement_id: int, message_id: int) -> None:
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


def get_previous_track_record(con: sqlite3.Connection, track: str, session_type: str, current_best_ms: int) -> int | None:
    """
    Get the previous track record (second-best time) for a track and session type.
    Returns None if no previous record exists.
    """
    result = con.execute(
        """
        SELECT MIN(e.best_lap_ms)
        FROM entries e
        JOIN sessions s ON e.session_id = s.session_id
        WHERE s.track = ?
          AND UPPER(s.session_type) = ?
          AND e.best_lap_ms IS NOT NULL
          AND e.best_lap_ms > ?
        ORDER BY e.best_lap_ms ASC
        LIMIT 1
        """,
        (track, session_type, current_best_ms)
    ).fetchone()
    
    return result[0] if result else None


def get_player_previous_rank(con: sqlite3.Connection, track: str, session_type: str, current_best_ms: int, first_name: str, last_name: str) -> int | None:
    """
    Get player's previous rank on a track (based on their previous PB).
    Returns None if no previous PB exists.
    """
    # Get player's previous best time (excluding current one)
    previous_pb = get_previous_pb(con, track, session_type, current_best_ms, first_name, last_name)
    
    if previous_pb is None:
        return None
    
    # Calculate rank with previous PB
    rank, _ = get_player_rank(con, track, session_type, previous_pb, first_name, last_name)
    return rank


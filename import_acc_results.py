import json
import os
import re
import sqlite3
from datetime import datetime, timezone

RESULTS_DIR = r"C:\accserver\server\results"
DB_PATH = r"C:\accserver\stats\acc_stats.sqlite"

FILENAME_RE = re.compile(r"^(?P<yymmdd>\d{6})_(?P<hhmmss>\d{6})_(?P<stype>FP|Q|R)\.JSON$", re.IGNORECASE)

SENTINEL_TIMES = {0, 2147483647}

def parse_filename_ts(filename: str):
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    yymmdd = m.group("yymmdd")
    hhmmss = m.group("hhmmss")
    stype = m.group("stype").upper()
    # Interpret YY as 20YY
    dt = datetime.strptime("20" + yymmdd + hhmmss, "%Y%m%d%H%M%S")
    return dt, stype

def norm_time_ms(val):
    if val is None:
        return None
    try:
        v = int(val)
    except Exception:
        return None
    return None if v in SENTINEL_TIMES else v

def maybe_update_records(cur, session_id: int):
    sess = cur.execute(
        "SELECT track, session_type, file_mtime_utc FROM sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    if not sess:
        return

    track, stype, file_mtime_utc = sess
    stype = (stype or "").upper()
    if stype not in ("Q", "R"):
        return

    # Get best time from this session (for track record check)
    row = cur.execute(
        """
        SELECT player_id, first_name, last_name, short_name, car_model, race_number, cup_category, best_lap_ms
        FROM entries
        WHERE session_id = ? AND best_lap_ms IS NOT NULL
        ORDER BY best_lap_ms ASC
        LIMIT 1
        """,
        (session_id,)
    ).fetchone()
    if not row:
        return

    player_id, first_name, last_name, short_name, car_model, race_number, cup_category, best_lap_ms = row

    # Check for new track record
    existing = cur.execute(
        "SELECT best_lap_ms FROM records WHERE track = ? AND session_type = ?",
        (track, stype)
    ).fetchone()

    is_new_record = (existing is None) or (best_lap_ms < existing[0])
    
    # Track record handling
    if is_new_record:
        cur.execute(
            """
            INSERT INTO records
            (track, session_type, best_lap_ms, player_id, first_name, last_name, short_name, car_model, race_number, cup_category, set_session_id, set_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track, session_type) DO UPDATE SET
              best_lap_ms     = excluded.best_lap_ms,
              player_id       = excluded.player_id,
              first_name      = excluded.first_name,
              last_name       = excluded.last_name,
              short_name      = excluded.short_name,
              car_model       = excluded.car_model,
              race_number     = excluded.race_number,
              cup_category    = excluded.cup_category,
              set_session_id  = excluded.set_session_id,
              set_at_utc      = excluded.set_at_utc
            """,
            (track, stype, best_lap_ms, player_id, first_name, last_name, short_name, car_model, race_number, cup_category, session_id, file_mtime_utc)
        )

        # Track record announcement
        cur.execute(
            """
            INSERT OR IGNORE INTO record_announcements
            (track, session_type, best_lap_ms, announced_at_utc, discord_message_id, announcement_type)
            VALUES (?, ?, ?, ?, NULL, 'TR')
            """,
            (track, stype, best_lap_ms, file_mtime_utc)
        )
    
    # Check for personal bests for ALL drivers in this session
    all_entries = cur.execute(
        """
        SELECT player_id, first_name, last_name, short_name, car_model, race_number, cup_category, best_lap_ms
        FROM entries
        WHERE session_id = ? AND best_lap_ms IS NOT NULL AND player_id IS NOT NULL
        """,
        (session_id,)
    ).fetchall()
    
    for (pid, fn, ln, sn, cm, rn, cc, blm) in all_entries:
        # Check if this is a NEW personal best for this driver
        # Get their previous best (excluding current session)
        previous_best = cur.execute(
            """
            SELECT MIN(e.best_lap_ms)
            FROM entries e
            JOIN sessions s ON e.session_id = s.session_id
            WHERE e.player_id = ? AND s.track = ? AND UPPER(s.session_type) = ? 
              AND e.best_lap_ms IS NOT NULL AND e.session_id != ?
            """,
            (pid, track, stype, session_id)
        ).fetchone()
        
        # This is a new PB if: no previous best exists, OR this time is better (lower)
        is_new_pb = (previous_best is None or previous_best[0] is None) or (blm < previous_best[0])
        
        if is_new_pb:
            # Check if we've already announced this PB for this driver
            existing_pb = cur.execute(
                """
                SELECT announcement_id FROM record_announcements a
                WHERE a.track = ? 
                  AND a.session_type = ? 
                  AND a.best_lap_ms = ? 
                  AND COALESCE(a.announcement_type, 'TR') = 'PB'
                  AND a.discord_message_id IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM entries e
                      JOIN sessions s ON e.session_id = s.session_id
                      WHERE s.track = a.track
                        AND s.session_type = a.session_type
                        AND e.best_lap_ms = a.best_lap_ms
                        AND e.player_id = ?
                  )
                LIMIT 1
                """,
                (track, stype, blm, pid)
            ).fetchone()
            
            # Only announce PB if:
            # 1. It's not also the track record (TR already announced) - check if this lap time equals the new record
            # 2. We haven't already announced this PB for this driver
            is_also_track_record = is_new_record and best_lap_ms == blm
            if not is_also_track_record and not existing_pb:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO record_announcements
                    (track, session_type, best_lap_ms, announced_at_utc, discord_message_id, announcement_type)
                    VALUES (?, ?, ?, ?, NULL, 'PB')
                    """,
                    (track, stype, blm, file_mtime_utc)
                )

def queue_race_results(cur, session_id: int):
    """Queue a race session for Discord announcement (only for R sessions)."""
    sess = cur.execute(
        "SELECT track, session_type, file_mtime_utc FROM sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    if not sess:
        return
    
    track, stype, file_mtime_utc = sess
    stype = (stype or "").upper()
    
    # Only queue race sessions (not Q or FP)
    if stype != "R":
        return
    
    # Insert race results announcement (skip if already queued)
    cur.execute(
        """
        INSERT OR IGNORE INTO race_results_announcements
        (session_id, track, announced_at_utc, discord_message_id)
        VALUES (?, ?, ?, NULL)
        """,
        (session_id, track, file_mtime_utc)
    )

def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()
    
    # Add announcement_type column if it doesn't exist (migration)
    try:
        cur.execute("ALTER TABLE record_announcements ADD COLUMN announcement_type TEXT DEFAULT 'TR'")
        con.commit()
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    # Create race_results_announcements table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS race_results_announcements (
            announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL UNIQUE,
            track TEXT NOT NULL,
            announced_at_utc TEXT NOT NULL,
            discord_message_id TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
    """)
    con.commit()

    files = [f for f in os.listdir(RESULTS_DIR) if f.upper().endswith(".JSON")]
    files.sort()

    imported = 0
    skipped_empty = 0
    skipped_badname = 0
    skipped_dupe = 0

    for fname in files:
        parsed = parse_filename_ts(fname)
        if not parsed:
            skipped_badname += 1
            continue

        _, stype = parsed
        full_path = os.path.join(RESULTS_DIR, fname)

        # Idempotency: skip if already imported
        exists = cur.execute("SELECT 1 FROM sessions WHERE source_file = ? LIMIT 1", (full_path,)).fetchone()
        if exists:
            skipped_dupe += 1
            continue

        # Load JSON
        try:
            with open(full_path, "r", encoding="utf-16le") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to parse {fname}: {e}")
            continue

        leader = (((data.get("sessionResult") or {}).get("leaderBoardLines")) or [])
        laps = data.get("laps") or []

        # Skip empty/template logs
        if len(leader) == 0 and len(laps) == 0:
            skipped_empty += 1
            continue

        track = data.get("trackName") or ""
        server_name = data.get("serverName")
        is_wet = ((data.get("sessionResult") or {}).get("isWetSession"))
        session_index = data.get("sessionIndex")
        race_weekend_index = data.get("raceWeekendIndex")

        file_mtime_utc = datetime.fromtimestamp(os.path.getmtime(full_path), timezone.utc).isoformat()

        # Insert session
        cur.execute(
            """
            INSERT INTO sessions
            (source_file, session_type, track, server_name, is_wet, session_index, race_weekend_index, file_mtime_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (full_path, stype, track, server_name, is_wet, session_index, race_weekend_index, file_mtime_utc),
        )
        session_id = cur.lastrowid

        # Insert entries from leaderboard lines
        for idx, line in enumerate(leader):
            car = (line.get("car") or {})
            timing = (line.get("timing") or {})
            driver = (line.get("currentDriver") or {})

            best_lap_ms = norm_time_ms(timing.get("bestLap"))
            total_time_ms = norm_time_ms(timing.get("totalTime"))

            cur.execute(
                """
                INSERT INTO entries
                (session_id, position, car_id, race_number, car_model, cup_category, car_group,
                player_id, first_name, last_name, short_name,
                best_lap_ms, total_time_ms, lap_count, missing_mandatory_pitstop)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    idx + 1,
                    car.get("carId"),
                    car.get("raceNumber"),
                    car.get("carModel"),
                    car.get("cupCategory"),
                    car.get("carGroup"),
                    driver.get("playerId"),
                    driver.get("firstName"),
                    driver.get("lastName"),
                    driver.get("shortName"),
                    best_lap_ms,
                    total_time_ms,
                    timing.get("lapCount"),
                    line.get("missingMandatoryPitstop"),
                ),
            )
            
        maybe_update_records(cur, session_id)
        queue_race_results(cur, session_id)
        imported += 1
        con.commit()

    print("Done.")
    print(f"Imported sessions: {imported}")
    print(f"Skipped empty/template: {skipped_empty}")
    print(f"Skipped already imported: {skipped_dupe}")
    print(f"Skipped bad filename: {skipped_badname}")

    con.close()

if __name__ == "__main__":
    main()
"""Discord embed builders."""
import discord
from datetime import datetime, timezone

from utils.formatting import fmt_ms, fmt_dt, fmt_split_ms, fmt_car_model
from utils.images import find_track_image


def build_track_record_embed(track, stype, best_ms, when_utc, first, last, short, car_model):
    """Build a Discord embed for track record announcements."""
    session_label = "Qualifying" if stype == "Q" else "Race"
    who = "Unknown driver"
    if first or last:
        who = f"{(first or '').strip()} {(last or '').strip()}".strip()
    elif short:
        who = short

    car_name = fmt_car_model(car_model)
    
    # Add session type emoji
    session_emoji = "🏁" if stype == "Q" else "🏎️"
    
    embed = discord.Embed(
        title=f"🏆 NEW TRACK RECORD! 🏆",
        description=f"{session_emoji} **{track}** - {session_label}",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="👤 Driver",
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


def build_personal_best_embed(track, stype, best_ms, when_utc, first, last, short, car_model):
    """Build a Discord embed for personal best announcements."""
    session_label = "Qualifying" if stype == "Q" else "Race"
    who = "Unknown driver"
    if first or last:
        who = f"{(first or '').strip()} {(last or '').strip()}".strip()
    elif short:
        who = short

    car_name = fmt_car_model(car_model)
    
    # Add session type emoji
    session_emoji = "🏁" if stype == "Q" else "🏎️"
    
    embed = discord.Embed(
        title=f"🎯 PERSONAL BEST ACHIEVED! 🎯",
        description=f"{session_emoji} **{track}** - {session_label}",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="👤 Driver",
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


def build_race_results_embed(track, session_data, entries, when_utc):
    """Build a Discord embed for race results."""
    track_name, session_type, server_name, is_wet, session_index, race_weekend_index, file_mtime_utc = session_data
    
    # Determine conditions
    conditions = "🌧️ Wet" if is_wet else "☀️ Dry"
    
    # Get lap count from first entry (should be same for all finishers)
    lap_count = entries[0][8] if entries and len(entries[0]) > 8 else 0
    
    # Determine embed color based on race completion
    # Use a vibrant blue for race results (can be enhanced with position-based accents in text)
    race_color = discord.Color.blue()
    
    # Create embed
    embed = discord.Embed(
        title=f"🏁 Race Results - {track.title().replace('_', ' ')}",
        color=race_color,
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
    leader_total_ms = entries[0][7] if entries and entries[0][7] else None
    leader_best_ms = entries[0][6] if entries and entries[0][6] else None
    
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
        
        # Best lap comparison - add 🔥 for leader's best lap
        if best_lap_ms and leader_best_ms:
            if position == 1:
                best_lap_str = f"**{fmt_ms(best_lap_ms)}** 🔥"
            elif best_lap_ms == leader_best_ms:
                # If tied for fastest lap but not leader, also show 🔥
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
        fastest_entry = min((e for e in entries if e[6]), key=lambda x: x[6], default=None)
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


"""Discord embed builders."""
import discord
from datetime import datetime, timezone
from typing import Any

from constants import MEDAL_EMOJIS, MAX_RACE_RESULTS_DISPLAY, TOP_3_POSITIONS
from utils.formatting import fmt_ms, fmt_dt, fmt_split_ms, fmt_car_model, format_driver_name, format_track_name
from utils.images import find_track_image


def build_track_record_embed(
    track: str,
    stype: str,
    best_ms: int,
    when_utc: str,
    first: str | None,
    last: str | None,
    short: str | None,
    car_model: int | None,
    previous_record_ms: int | None = None
) -> tuple[discord.Embed, discord.File | None]:
    """Build a Discord embed for track record announcements."""
    session_label = "Qualifying" if stype == "Q" else "Race"
    who = format_driver_name(first, last, short)

    car_name = fmt_car_model(car_model)
    
    # Add session type emoji
    session_emoji = "🏁" if stype == "Q" else "🏎️"
    
    # Format track name for display
    formatted_track = format_track_name(track)
    
    # Build description with optional improvement subtitle
    description = f"{session_emoji} **{formatted_track}** - {session_label}"
    if previous_record_ms is not None:
        improvement_ms = previous_record_ms - best_ms
        improvement_str = fmt_split_ms(improvement_ms)
        description += f"\n**🔥 Smashed the previous record by {improvement_str}!**"
    
    embed = discord.Embed(
        title=f"🏆 NEW TRACK RECORD! 🏆",
        description=description,
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


def build_personal_best_embed(
    track: str,
    stype: str,
    best_ms: int,
    when_utc: str,
    first: str | None,
    last: str | None,
    short: str | None,
    car_model: int | None,
    previous_rank: int | None = None,
    current_rank: int | None = None
) -> tuple[discord.Embed, discord.File | None]:
    """Build a Discord embed for personal best announcements."""
    session_label = "Qualifying" if stype == "Q" else "Race"
    who = format_driver_name(first, last, short)

    car_name = fmt_car_model(car_model)
    
    # Add session type emoji
    session_emoji = "🏁" if stype == "Q" else "🏎️"
    
    # Format track name for display
    formatted_track = format_track_name(track)
    
    # Build description with optional rank change subtitle
    description = f"{session_emoji} **{formatted_track}** - {session_label}"
    if previous_rank is not None and current_rank is not None and previous_rank > current_rank:
        positions_gained = previous_rank - current_rank
        description += f"\n**🚀 Moved up {positions_gained} position{'s' if positions_gained > 1 else ''} on the leaderboard!**"
    elif previous_rank is None and current_rank is not None:
        # First time on this track
        description += f"\n**✨ First time on this track - Rank #{current_rank}!**"
    
    embed = discord.Embed(
        title=f"🎯 PERSONAL BEST ACHIEVED! 🎯",
        description=description,
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


def build_race_results_embed(
    track: str,
    session_data: tuple[Any, ...],
    entries: list[tuple[Any, ...]],
    when_utc: str
) -> tuple[discord.Embed, discord.File | None]:
    """Build a Discord embed for race results."""
    track_name, session_type, server_name, is_wet, session_index, race_weekend_index, file_mtime_utc = session_data
    
    # Format track name for display
    formatted_track = format_track_name(track)
    
    # Determine conditions
    conditions = "🌧️ Wet" if is_wet else "☀️ Dry"
    
    # Get lap count from first entry (should be same for all finishers)
    lap_count = entries[0][8] if entries and len(entries[0]) > 8 else 0
    
    # Determine embed color based on race completion
    # Use a vibrant blue for race results (can be enhanced with position-based accents in text)
    race_color = discord.Color.blue()
    
    # Create embed
    embed = discord.Embed(
        title=f"🏁 Race Results - {formatted_track}",
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
    
    # Build standings
    standings_lines = []
    for entry in entries[:MAX_RACE_RESULTS_DISPLAY]:  # Limit to top N for embed space
        position, first_name, last_name, short_name, car_model, race_number, best_lap_ms, total_time_ms, entry_lap_count, car_group = entry
        
        # Format driver name
        driver_name = format_driver_name(first_name, last_name, short_name)
        
        car_name = fmt_car_model(car_model)
        medal = MEDAL_EMOJIS.get(position, "")
        
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
        if position in TOP_3_POSITIONS:
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
            fl_driver = format_driver_name(fl_first, fl_last, fl_short)
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


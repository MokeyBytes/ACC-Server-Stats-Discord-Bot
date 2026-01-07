"""Records command - show top times for a specific track."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from db.queries import find_track_match, fetch_track_top_times, fetch_available_tracks
from utils.formatting import fmt_ms, fmt_dt, fmt_split_ms, fmt_car_model
from utils.images import find_track_image
from bot.autocomplete import track_autocomplete


def setup_records_command(tree: app_commands.CommandTree):
    """Register the /records command."""
    
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
        
        # Get top 3 times for both Q and R
        q_times, r_times = fetch_track_top_times(con, actual_track, limit=3)
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
            leader_ms = q_times[0][1]  # Best time from first entry
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            times_list = []
            
            for idx, (stype, best_ms, first, last, short, car_model, set_at_utc) in enumerate(q_times[:3], 1):
                who = format_driver(first, last, short)
                car_name = fmt_car_model(car_model)
                medal = medals.get(idx, "")
                
                if idx == 1:
                    # First place - no split needed
                    times_list.append(f"{medal} **{fmt_ms(best_ms)}** — {who} ({car_name})")
                else:
                    # Calculate gap to leader
                    split_ms = best_ms - leader_ms  # Positive = slower
                    split_str = fmt_split_ms(split_ms)
                    times_list.append(f"{medal} **{fmt_ms(best_ms)}** ({split_str}) — {who} ({car_name})")
            
            embed.add_field(
                name="🏁 Qualifying",
                value="\n".join(times_list),
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
            leader_ms = r_times[0][1]  # Best time from first entry
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            times_list = []
            
            for idx, (stype, best_ms, first, last, short, car_model, set_at_utc) in enumerate(r_times[:3], 1):
                who = format_driver(first, last, short)
                car_name = fmt_car_model(car_model)
                medal = medals.get(idx, "")
                
                if idx == 1:
                    # First place - no split needed
                    times_list.append(f"{medal} **{fmt_ms(best_ms)}** — {who} ({car_name})")
                else:
                    # Calculate gap to leader
                    split_ms = best_ms - leader_ms  # Positive = slower
                    split_str = fmt_split_ms(split_ms)
                    times_list.append(f"{medal} **{fmt_ms(best_ms)}** ({split_str}) — {who} ({car_name})")
            
            embed.add_field(
                name="🏎️ Race",
                value="\n".join(times_list),
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


"""Records command - show top times for a specific track."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from constants import DEFAULT_TOP_TIMES_LIMIT, MEDAL_EMOJIS
from db.queries import find_track_match, fetch_track_top_times, fetch_available_tracks
from utils.formatting import fmt_ms, fmt_dt, fmt_split_ms, fmt_car_model, format_driver_name, format_track_name
from utils.images import find_track_image
from utils.errors import handle_command_error, create_error_embed, create_warning_embed, create_channel_restriction_embed
from utils.logging_config import logger
from bot.autocomplete import track_autocomplete


def setup_records_command(tree: app_commands.CommandTree) -> None:
    """Register the /records command."""
    
    @tree.command(name="records", description=f"Show top {DEFAULT_TOP_TIMES_LIMIT} times for a specific track (Q and R)")
    @app_commands.autocomplete(track=track_autocomplete)
    async def records(interaction: discord.Interaction, track: str):
        # Only allow in your target channel (optional safety)
        if interaction.channel_id != CHANNEL_ID:
            embed = create_channel_restriction_embed(CHANNEL_ID)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            con = sqlite3.connect(DB_PATH)
            
            # Try to find matching track name (case-insensitive)
            actual_track = find_track_match(con, track)
            if not actual_track:
                available = fetch_available_tracks(con)
                con.close()
                
                track_list = ", ".join([t[0] for t in available[:20]])  # Show first 20
                if len(available) > 20:
                    track_list += f", ... ({len(available)} total)"
                
                embed = create_warning_embed(
                    title="Track Not Found",
                    description=(
                        f"No track found matching **{track}**.\n\n"
                        f"Use `/tracks` to see all available tracks.\n"
                        f"*Track names are case-insensitive and can use spaces or underscores.*"
                    )
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get top times for both Q and R
            q_times, r_times = fetch_track_top_times(con, actual_track, limit=DEFAULT_TOP_TIMES_LIMIT)
            con.close()

            if not q_times and not r_times:
                formatted_track = format_track_name(actual_track)
                embed = create_warning_embed(
                    title="No Times Found",
                    description=(
                        f"No times found for track **{formatted_track}** yet.\n\n"
                        f"*Times will appear here once drivers complete sessions on this track.*"
                    )
                )
                await interaction.followup.send(embed=embed)
                return
        except sqlite3.Error as e:
            con.close()
            await handle_command_error(interaction, e, "retrieving track records")
            return
        except Exception as e:
            con.close()
            await handle_command_error(interaction, e, "processing your request")
            return

        # Format track name for display
        formatted_track = format_track_name(actual_track)
        
        # Create embed
        embed = discord.Embed(
            title=f"🏁 {formatted_track}",
            color=discord.Color.blue()
        )
        
        # Try to find and attach track image as thumbnail (appears near top, under title)
        img_filename, img_file = find_track_image(actual_track)
        if img_file:
            embed.set_thumbnail(url=f"attachment://{img_filename}")
        
        # Qualifying section
        if q_times:
            leader_ms = q_times[0][1]  # Best time from first entry
            times_list = []
            
            for idx, (stype, best_ms, first, last, short, car_model, set_at_utc) in enumerate(q_times[:DEFAULT_TOP_TIMES_LIMIT], 1):
                who = format_driver_name(first, last, short)
                car_name = fmt_car_model(car_model)
                medal = MEDAL_EMOJIS.get(idx, "")
                
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
            times_list = []
            
            for idx, (stype, best_ms, first, last, short, car_model, set_at_utc) in enumerate(r_times[:DEFAULT_TOP_TIMES_LIMIT], 1):
                who = format_driver_name(first, last, short)
                car_name = fmt_car_model(car_model)
                medal = MEDAL_EMOJIS.get(idx, "")
                
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
        try:
            if img_file:
                await interaction.followup.send(embed=embed, file=img_file)
            else:
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send records embed: {e}", exc_info=True)
            await handle_command_error(interaction, e, "sending the results")


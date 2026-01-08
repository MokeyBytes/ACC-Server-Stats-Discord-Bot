"""Leaders command - show top times for all tracks."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from constants import DISCORD_FIELD_VALUE_LIMIT, DISCORD_EMBED_FIELD_LIMIT, TRACKS_PER_FIELD, DEFAULT_TOP_TIMES_LIMIT
from db.queries import fetch_all_tracks_top_times
from utils.formatting import fmt_ms, fmt_dt, fmt_car_model, format_driver_name, format_track_name
from utils.errors import handle_command_error, create_channel_restriction_embed
from utils.logging_config import logger


def setup_leaders_command(tree: app_commands.CommandTree) -> None:
    """Register the /leaders command."""
    
    @tree.command(name="leaders", description="Show top 1 Q and R time for all tracks")
    async def leaders(interaction: discord.Interaction):
        # Only allow in your target channel (optional safety)
        if interaction.channel_id != CHANNEL_ID:
            embed = create_channel_restriction_embed(CHANNEL_ID)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            con = sqlite3.connect(DB_PATH)
            tracks_data = fetch_all_tracks_top_times(con)
            con.close()

            if not tracks_data:
            embed = discord.Embed(
                title="🏆 Server Leaders",
                description="No track records found in the database yet.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            return

        # Helper function to format a track entry
        def format_track_entry(track, q_data, r_data):
            formatted_track = format_track_name(track)
            lines = [f"**{formatted_track}**"]
            
            # Qualifying
            if q_data:
                best_ms, first, last, short, car_model, set_at_utc = q_data
                who = format_driver_name(first, last, short)
                car_name = fmt_car_model(car_model)
                when = fmt_dt(set_at_utc) if set_at_utc else "Unknown"
                lines.append(f"🏁 **Q:** {fmt_ms(best_ms)} — {who}\n   `{car_name}` • {when}")
            else:
                lines.append("🏁 **Q:** No times recorded")
            
            # Race
            if r_data:
                best_ms, first, last, short, car_model, set_at_utc = r_data
                who = format_driver_name(first, last, short)
                car_name = fmt_car_model(car_model)
                when = fmt_dt(set_at_utc) if set_at_utc else "Unknown"
                lines.append(f"🏎️ **R:** {fmt_ms(best_ms)} — {who}\n   `{car_name}` • {when}")
            else:
                lines.append("🏎️ **R:** No times recorded")
            
            return "\n".join(lines)

        # Create embeds with organized fields
        # Discord embed field value limit is 1024 characters
        # We'll group tracks per field for readability
        embeds = []
        current_embed = discord.Embed(
            title="🏆 Server Leaders - All Tracks",
            description=f"Top Qualifying and Race times across **{len(tracks_data)}** track(s)",
            color=discord.Color.gold()
        )
        
        current_field_value = ""
        tracks_in_current_field = 0
        field_count = 0
        track_number = 0
        
        for track in sorted(tracks_data.keys()):
            track_number += 1
            q_data = tracks_data[track].get('q')
            r_data = tracks_data[track].get('r')
            
            track_entry = format_track_entry(track, q_data, r_data)
            
            # Check if we need a new embed (Discord field limit per embed)
            if field_count >= DISCORD_EMBED_FIELD_LIMIT:
                # Save current field if it has content
                if current_field_value:
                    start_track = track_number - tracks_in_current_field
                    end_track = track_number - 1
                    current_embed.add_field(
                        name=f"Tracks {start_track}-{end_track}",
                        value=current_field_value.strip(),
                        inline=False
                    )
                
                # Create new embed
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="🏆 Server Leaders (continued)",
                    color=discord.Color.gold()
                )
                field_count = 0
                current_field_value = ""
                tracks_in_current_field = 0
            
            # Add track to current field
            if current_field_value:
                current_field_value += "\n\n" + track_entry
            else:
                current_field_value = track_entry
            
            tracks_in_current_field += 1
            
            # Check if we should finalize this field (after TRACKS_PER_FIELD tracks or if next would exceed limit)
            test_next_entry = ""
            if track_number < len(tracks_data):
                next_track = sorted(tracks_data.keys())[track_number]
                next_q = tracks_data[next_track].get('q')
                next_r = tracks_data[next_track].get('r')
                test_next_entry = "\n\n" + format_track_entry(next_track, next_q, next_r)
            
            should_finalize = (
                tracks_in_current_field >= TRACKS_PER_FIELD or
                len(current_field_value + test_next_entry) > DISCORD_FIELD_VALUE_LIMIT
            )
            
            if should_finalize or track_number == len(tracks_data):
                start_track = track_number - tracks_in_current_field + 1
                end_track = track_number
                field_name = f"Tracks {start_track}-{end_track}" if start_track != end_track else f"Track {start_track}"
                
                current_embed.add_field(
                    name=field_name,
                    value=current_field_value.strip(),
                    inline=False
                )
                field_count += 1
                current_field_value = ""
                tracks_in_current_field = 0
        
        # Add footer to last embed
        final_embed = embeds[-1] if embeds else current_embed
        final_embed.set_footer(text=f"💡 Use /records <track> to see top {DEFAULT_TOP_TIMES_LIMIT} times for a specific track")
        
            # Send all embeds
            try:
                if embeds:
                    for embed in embeds:
                        await interaction.followup.send(embed=embed)
                
                if current_embed.fields:
                    await interaction.followup.send(embed=current_embed)
            except Exception as e:
                logger.error(f"Failed to send leaders embeds: {e}", exc_info=True)
                await handle_command_error(interaction, e, "sending the results")
                
        except sqlite3.Error as e:
            try:
                con.close()
            except:
                pass
            await handle_command_error(interaction, e, "retrieving leaderboard data")
        except Exception as e:
            try:
                con.close()
            except:
                pass
            await handle_command_error(interaction, e, "processing your request")


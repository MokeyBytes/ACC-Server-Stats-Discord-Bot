"""Personal bests command - show player's PB with detailed sector breakdown for a specific track."""
import sqlite3
import json
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from constants import MEDAL_EMOJIS, TOP_3_POSITIONS
from db.queries import (
    find_track_match, fetch_player_pb_with_sectors, fetch_track_record_with_sectors,
    get_player_rank, get_session_count, get_previous_pb
)
from utils.formatting import fmt_ms, fmt_dt, fmt_split_ms, fmt_car_model
from utils.images import find_track_image
from utils.errors import handle_command_error, create_warning_embed
from utils.logging_config import logger
from bot.autocomplete import player_name_autocomplete, track_autocomplete


def setup_pb_command(tree: app_commands.CommandTree):
    """Register the /pb command."""
    
    @tree.command(name="pb", description="Show detailed personal best with sector breakdown for a player at a track")
    @app_commands.autocomplete(player=player_name_autocomplete, track=track_autocomplete)
    async def pb(interaction: discord.Interaction, player: str, track: str):
        # Only allow in your target channel (optional safety)
        if interaction.channel_id != CHANNEL_ID:
            await interaction.response.send_message(
                f"Use this in <#{CHANNEL_ID}>.",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            # Parse full name into first and last name
            name_parts = player.strip().split(None, 1)
            if len(name_parts) == 1:
                first_name = name_parts[0]
                last_name = ""
            else:
                first_name = name_parts[0]
                last_name = name_parts[1]

            con = sqlite3.connect(DB_PATH)
            
            # Find matching track name
            actual_track = find_track_match(con, track)
            if not actual_track:
                con.close()
                embed = create_warning_embed(
                    title="Track Not Found",
                    description=(
                        f"Track **{track}** not found.\n\n"
                        f"Use `/tracks` to see all available tracks."
                    )
                )
                await interaction.followup.send(embed=embed)
                return

            # Get PB data for both Q and R
            q_pb = fetch_player_pb_with_sectors(con, first_name or "", last_name or "", actual_track, "Q")
            r_pb = fetch_player_pb_with_sectors(con, first_name or "", last_name or "", actual_track, "R")

            if not q_pb and not r_pb:
                con.close()
                embed = create_warning_embed(
                    title="No Personal Bests Found",
                    description=(
                        f"No personal bests found for **{player}** at **{actual_track}**.\n\n"
                        f"*Make sure you've spelled the name correctly. Use autocomplete to help find the correct name.*"
                    )
                )
                await interaction.followup.send(embed=embed)
                return

            # Get track records for comparison
            q_record = fetch_track_record_with_sectors(con, actual_track, "Q")
            r_record = fetch_track_record_with_sectors(con, actual_track, "R")

            # Create embed
        embed = discord.Embed(
            title=f"🎯 Personal Best: {player}",
            description=f"🏁 **{actual_track}**",
            color=discord.Color.green()
        )

        # Add track image thumbnail
        img_filename, img_file = find_track_image(actual_track)
        if img_file:
            embed.set_thumbnail(url=f"attachment://{img_filename}")

        # Helper function to parse sectors from JSON
        def parse_sectors(splits_json):
            if not splits_json:
                return None
            try:
                return json.loads(splits_json)
            except:
                return None

        # Helper function to format sector breakdown
        def format_sector_breakdown(pb_splits, record_splits, pb_time, record_time):
            if not pb_splits:
                return "No sector data available"
            
            sector_lines = []
            num_sectors = len(pb_splits)
            
            # Calculate cumulative times for comparison
            pb_cumulative = []
            record_cumulative = []
            pb_sum = 0
            record_sum = 0
            
            for i, pb_s in enumerate(pb_splits):
                pb_sum += pb_s
                pb_cumulative.append(pb_sum)
                
                if record_splits and i < len(record_splits):
                    record_sum += record_splits[i]
                    record_cumulative.append(record_sum)
                else:
                    record_cumulative.append(None)

            # Build sector comparison lines
            sector_gaps = []
            for i in range(num_sectors):
                sector_num = i + 1
                pb_sector = pb_splits[i]
                pb_cum = pb_cumulative[i]
                
                sector_str = f"**S{sector_num}**: {fmt_ms(pb_sector)}"
                
                if record_splits and i < len(record_splits):
                    record_sector = record_splits[i]
                    record_cum = record_cumulative[i]
                    
                    # Sector time difference
                    sector_diff = pb_sector - record_sector
                    if sector_diff < 0:
                        sector_str += f" *(-{fmt_split_ms(abs(sector_diff))})* ✅"
                    elif sector_diff > 0:
                        sector_str += f" *(+{fmt_split_ms(sector_diff)})*"
                    
                    sector_gaps.append(sector_diff)
                else:
                    sector_gaps.append(None)
                
                sector_lines.append(sector_str)

            # Add summary: strongest/weakest sectors
            if record_splits and len(sector_gaps) == len(record_splits):
                valid_gaps = [(i, g) for i, g in enumerate(sector_gaps) if g is not None]
                if valid_gaps:
                    # Find strongest (best relative to record) and weakest
                    best_item = min(valid_gaps, key=lambda x: x[1])
                    worst_item = max(valid_gaps, key=lambda x: x[1])
                    
                    best_idx = best_item[0]
                    worst_idx = worst_item[0]
                    best_gap = best_item[1]
                    worst_gap = worst_item[1]
                    
                    summary_lines = []
                    if best_gap < 0:
                        summary_lines.append(f"🏆 **Strongest**: S{best_idx + 1} ({fmt_split_ms(abs(best_gap))} faster than record)")
                    if worst_gap > 0:
                        summary_lines.append(f"💪 **Weakest**: S{worst_idx + 1} ({fmt_split_ms(worst_gap)} slower than record)")

                    if summary_lines:
                        sector_lines.append("")  # Empty line
                        sector_lines.extend(summary_lines)

            return "\n".join(sector_lines)

        # Qualifying section
        if q_pb:
            q_best_ms, q_splits_json, q_car_model, q_set_at_utc = q_pb
            q_splits = parse_sectors(q_splits_json)
            
            # Get track record sectors
            q_record_splits = None
            q_record_time = None
            if q_record:
                q_record_time = q_record[0]
                q_record_splits_json = q_record[1] if len(q_record) > 1 else None
                q_record_splits = parse_sectors(q_record_splits_json)
            
            # Build qualifying field
            q_value = f"⏱️ **Time**: {fmt_ms(q_best_ms)}\n"
            q_value += f"🚗 **Car**: {fmt_car_model(q_car_model)}\n"
            
            if q_set_at_utc:
                q_value += f"📅 **Set**: {fmt_dt(q_set_at_utc)}\n"
            
            # Add rank
            rank, total = get_player_rank(con, actual_track, "Q", q_best_ms, first_name or "", last_name or "")
            if rank and total:
                medal = MEDAL_EMOJIS.get(rank, "")
                q_value += f"📊 **Rank**: {medal} #{rank} of {total}\n"
            
            # Add gap to record
            if q_record_time:
                gap_ms = q_best_ms - q_record_time
                gap_str = fmt_split_ms(gap_ms)
                if gap_ms < 0:
                    q_value += f"🏆 **vs Record**: {gap_str} faster! 🔥\n"
                else:
                    q_value += f"🏆 **vs Record**: +{gap_str}\n"
            
            # Add session count
            session_count = get_session_count(con, actual_track, "Q", first_name or "", last_name or "")
            if session_count > 0:
                q_value += f"🔄 **Sessions**: {session_count}\n"
            
            embed.add_field(
                name="🏁 Qualifying",
                value=q_value,
                inline=False
            )
            
            # Add sector breakdown if available
            if q_splits:
                sector_text = format_sector_breakdown(q_splits, q_record_splits, q_best_ms, q_record_time)
                embed.add_field(
                    name="⚡ Sector Breakdown (Q)",
                    value=sector_text,
                    inline=False
                )

        # Race section
        if r_pb:
            r_best_ms, r_splits_json, r_car_model, r_set_at_utc = r_pb
            r_splits = parse_sectors(r_splits_json)
            
            # Get track record sectors
            r_record_splits = None
            r_record_time = None
            if r_record:
                r_record_time = r_record[0]
                r_record_splits_json = r_record[1] if len(r_record) > 1 else None
                r_record_splits = parse_sectors(r_record_splits_json)
            
            # Build race field
            r_value = f"⏱️ **Time**: {fmt_ms(r_best_ms)}\n"
            r_value += f"🚗 **Car**: {fmt_car_model(r_car_model)}\n"
            
            if r_set_at_utc:
                r_value += f"📅 **Set**: {fmt_dt(r_set_at_utc)}\n"
            
            # Add rank
            rank, total = get_player_rank(con, actual_track, "R", r_best_ms, first_name or "", last_name or "")
            if rank and total:
                medal = MEDAL_EMOJIS.get(rank, "")
                r_value += f"📊 **Rank**: {medal} #{rank} of {total}\n"
            
            # Add gap to record
            if r_record_time:
                gap_ms = r_best_ms - r_record_time
                gap_str = fmt_split_ms(gap_ms)
                if gap_ms < 0:
                    r_value += f"🏆 **vs Record**: {gap_str} faster! 🔥\n"
                else:
                    r_value += f"🏆 **vs Record**: +{gap_str}\n"
            
            # Add session count
            session_count = get_session_count(con, actual_track, "R", first_name or "", last_name or "")
            if session_count > 0:
                r_value += f"🔄 **Sessions**: {session_count}\n"
            
            embed.add_field(
                name="🏎️ Race",
                value=r_value,
                inline=False
            )
            
            # Add sector breakdown if available
            if r_splits:
                sector_text = format_sector_breakdown(r_splits, r_record_splits, r_best_ms, r_record_time)
                embed.add_field(
                    name="⚡ Sector Breakdown (R)",
                    value=sector_text,
                    inline=False
                )

            con.close()

            # Send embed
            try:
                if img_file:
                    await interaction.followup.send(embed=embed, file=img_file)
                else:
                    await interaction.followup.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send PB embed: {e}", exc_info=True)
                await handle_command_error(interaction, e, "sending the results")
                
        except sqlite3.Error as e:
            try:
                con.close()
            except:
                pass
            await handle_command_error(interaction, e, "retrieving personal best data")
        except Exception as e:
            try:
                con.close()
            except:
                pass
            await handle_command_error(interaction, e, "processing your request")

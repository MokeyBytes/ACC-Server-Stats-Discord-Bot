"""Personal bests command - show player's PBs across all tracks."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from db.queries import (
    fetch_player_pbs, get_player_rank, get_track_record, 
    get_session_count, get_previous_pb, calculate_performance_percentage
)
from utils.formatting import fmt_ms, fmt_dt, fmt_split_ms, fmt_car_model
from bot.autocomplete import player_first_name_autocomplete, player_last_name_autocomplete


def setup_pb_command(tree: app_commands.CommandTree):
    """Register the /pb command."""
    
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
            con.close()
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


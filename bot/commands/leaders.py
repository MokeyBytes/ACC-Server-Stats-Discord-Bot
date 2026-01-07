"""Leaders command - show top times for all tracks."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from db.queries import fetch_all_tracks_top_times
from utils.formatting import fmt_ms, fmt_dt, fmt_car_model


def setup_leaders_command(tree: app_commands.CommandTree):
    """Register the /leaders command."""
    
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


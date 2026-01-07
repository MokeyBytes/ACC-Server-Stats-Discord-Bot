"""Tracks command - list all available tracks."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from db.queries import fetch_available_tracks


def setup_tracks_command(tree: app_commands.CommandTree):
    """Register the /tracks command."""
    
    @tree.command(name="tracks", description="List all available tracks")
    async def tracks(interaction: discord.Interaction):
        # Only allow in your target channel (optional safety)
        if interaction.channel_id != CHANNEL_ID:
            await interaction.response.send_message(
                f"Use this in <#{CHANNEL_ID}>.",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        con = sqlite3.connect(DB_PATH)
        available = fetch_available_tracks(con)
        con.close()

        if not available:
            await interaction.followup.send("No tracks found in the database yet.")
            return

        # Format track list
        track_names = [t[0] for t in available]
        track_list = "\n".join([f"• {name}" for name in track_names])
        
        msg = f"**Available Tracks ({len(track_names)}):**\n\n{track_list}\n\n*Use `/records <trackname>` to see top times for a track.*"
        
        # Discord message limit safety
        if len(msg) <= 1900:
            await interaction.followup.send(msg)
        else:
            # Split into chunks if too long
            chunks = []
            current_chunk = f"**Available Tracks ({len(track_names)}):**\n\n"
            for name in track_names:
                line = f"• {name}\n"
                if len(current_chunk) + len(line) > 1900:
                    chunks.append(current_chunk)
                    current_chunk = ""
                current_chunk += line
            if current_chunk:
                chunks.append(current_chunk + "\n*Use `/records <trackname>` to see top times for a track.*")
            
            for chunk in chunks:
                await interaction.followup.send(chunk)


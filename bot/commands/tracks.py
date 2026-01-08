"""Tracks command - list all available tracks."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID
from constants import DISCORD_FIELD_VALUE_LIMIT
from db.queries import fetch_available_tracks
from utils.errors import handle_command_error
from utils.logging_config import logger


def setup_tracks_command(tree: app_commands.CommandTree) -> None:
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

        try:
            con = sqlite3.connect(DB_PATH)
            available = fetch_available_tracks(con)
            con.close()

            if not available:
            embed = discord.Embed(
                title="📍 Available Tracks",
                description="No tracks found in the database yet.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            return

        # Format track list
        track_names = [t[0] for t in available]
        sorted_tracks = sorted(track_names)
        
        # Create embed
        embed = discord.Embed(
            title="📍 Available Tracks",
            description=f"**{len(sorted_tracks)}** track(s) available in the database",
            color=discord.Color.blue()
        )
        
        # Format track list (Discord field value limit)
        track_list = "\n".join([f"• {name}" for name in sorted_tracks])
        
        # If track list is too long, split into multiple fields
        if len(track_list) <= DISCORD_FIELD_VALUE_LIMIT:
            embed.add_field(
                name="Track List",
                value=track_list,
                inline=False
            )
        else:
            # Split into chunks
            chunks = []
            current_chunk = ""
            for name in sorted_tracks:
                line = f"• {name}\n"
                if len(current_chunk) + len(line) > DISCORD_FIELD_VALUE_LIMIT:
                    chunks.append(current_chunk.strip())
                    current_chunk = line
                else:
                    current_chunk += line
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Add chunks as separate fields
            for i, chunk in enumerate(chunks, 1):
                field_name = "Track List" if i == 1 else f"Track List (continued {i})"
                embed.add_field(
                    name=field_name,
                    value=chunk,
                    inline=False
                )
        
            embed.set_footer(text="💡 Use /records <trackname> to see top times for a track")
            
            try:
                await interaction.followup.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send tracks embed: {e}", exc_info=True)
                await handle_command_error(interaction, e, "sending the results")
                
        except sqlite3.Error as e:
            try:
                con.close()
            except:
                pass
            await handle_command_error(interaction, e, "retrieving track list")
        except Exception as e:
            try:
                con.close()
            except:
                pass
            await handle_command_error(interaction, e, "processing your request")


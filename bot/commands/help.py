"""Help command - show all available commands and usage."""
import sqlite3
import discord
from discord import app_commands

from config import CHANNEL_ID, DB_PATH
from utils.errors import create_channel_restriction_embed, handle_command_error
from utils.formatting import format_track_name, format_driver_name
from utils.logging_config import logger
from constants import DEFAULT_TOP_TIMES_LIMIT
from db.queries import fetch_available_tracks, fetch_all_players


def setup_help_command(tree: app_commands.CommandTree) -> None:
    """Register the /help command."""
    
    @tree.command(name="help", description="Show all available commands and how to use them")
    async def help(interaction: discord.Interaction):
        # Only allow in your target channel (optional safety)
        if interaction.channel_id != CHANNEL_ID:
            embed = create_channel_restriction_embed(CHANNEL_ID)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        # Get real examples from database
        example_track = None
        example_player = None
        
        try:
            con = sqlite3.connect(DB_PATH)
            
            # Get first available track as example
            tracks = fetch_available_tracks(con)
            if tracks:
                example_track = format_track_name(tracks[0][0])
            
            # Get first available player as example
            players = fetch_all_players(con)
            if players:
                first_name, last_name = players[0]
                example_player = format_driver_name(first_name, last_name, None)
            
            con.close()
        except Exception as e:
            logger.warning(f"Failed to fetch examples for help command: {e}")
            # Continue with default examples if database query fails

        # Use real examples if available, otherwise use defaults
        track_example = example_track or "Barcelona"
        player_example = example_player or "Mokey Bytes"
        
        # If we have both track and player, use them together for PB example
        pb_example = f"{player_example} {track_example}" if example_player and example_track else f"{player_example} Barcelona"

        embed = discord.Embed(
            title="📚 ACC Server Stats Bot - Commands",
            description=(
                "All available commands and how to use them\n\n"
                "💡 **Quick Commands:**\n"
                f"• `/records {track_example}` - View track leaderboard\n"
                f"• `/pb {pb_example}` - View player's personal best\n"
                "• `/leaders` - See all track records\n"
                "• `/tracks` - List all available tracks"
            ),
            color=discord.Color.blue()
        )

        # Records command
        records_desc = (
            f"Show the top {DEFAULT_TOP_TIMES_LIMIT} Qualifying and Race times for a specific track.\n"
            f"**Usage:** `/records {track_example}`\n"
            "**Example:** Displays leaderboard with medals (🥇🥈🥉) and splits to leader."
        )
        if example_track:
            records_desc += f"\n*Try it with: `/records {track_example}`*"
        
        embed.add_field(
            name="🏁 `/records <track>`",
            value=records_desc,
            inline=False
        )

        # PB command
        pb_desc = (
            "Show a player's personal best for a specific track with detailed sector breakdown.\n"
            f"**Usage:** `/pb {pb_example}`\n"
            "**Example:** Shows PB time, rank, gap to record, session count, and sector-by-sector analysis."
        )
        if example_player and example_track:
            pb_desc += f"\n*Try it with: `/pb {pb_example}`*"
        
        embed.add_field(
            name="🎯 `/pb <player> <track>`",
            value=pb_desc,
            inline=False
        )

        # Leaders command
        embed.add_field(
            name="🏆 `/leaders`",
            value=(
                "Show the #1 Qualifying and Race time for every track.\n"
                "**Usage:** `/leaders`\n"
                "**Example:** Displays a comprehensive list of all track records across the server.\n"
                "*Perfect for seeing who holds records on each track!*"
            ),
            inline=False
        )

        # Tracks command
        tracks_desc = (
            "List all available tracks in the database.\n"
            "**Usage:** `/tracks`\n"
            "**Example:** Shows all tracks you can query with `/records` or `/pb`."
        )
        if tracks:
            tracks_desc += f"\n*Currently **{len(tracks)}** track(s) available in the database*"
        
        embed.add_field(
            name="📍 `/tracks`",
            value=tracks_desc,
            inline=False
        )

        # Sync command
        embed.add_field(
            name="🔄 `/sync`",
            value=(
                "Manually sync slash commands with Discord (admin use).\n"
                "**Usage:** `/sync`\n"
                "**Note:** Use this if commands aren't appearing. May take 5-10 minutes to update."
            ),
            inline=False
        )

        # Help command
        embed.add_field(
            name="❓ `/help`",
            value=(
                "Show this help message with all available commands.\n"
                "**Usage:** `/help`"
            ),
            inline=False
        )

        # Footer with additional info
        footer_text = "💡 Tip: Use autocomplete when typing commands to see available options!"
        if example_track or example_player:
            footer_text += " | Examples shown from your database"
        
        embed.set_footer(text=footer_text)

        try:
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send help embed: {e}", exc_info=True)
            await handle_command_error(interaction, e, "sending the help message")


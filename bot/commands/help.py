"""Help command - show all available commands and usage."""
import discord
from discord import app_commands

from config import CHANNEL_ID
from constants import DEFAULT_TOP_TIMES_LIMIT


def setup_help_command(tree: app_commands.CommandTree) -> None:
    """Register the /help command."""
    
    @tree.command(name="help", description="Show all available commands and how to use them")
    async def help(interaction: discord.Interaction):
        # Only allow in your target channel (optional safety)
        if interaction.channel_id != CHANNEL_ID:
            await interaction.response.send_message(
                f"Use this in <#{CHANNEL_ID}>.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📚 ACC Server Stats Bot - Commands",
            description="All available commands and how to use them",
            color=discord.Color.blue()
        )

        # Records command
        embed.add_field(
            name="🏁 `/records <track>`",
            value=(
                f"Show the top {DEFAULT_TOP_TIMES_LIMIT} Qualifying and Race times for a specific track.\n"
                "**Usage:** `/records Barcelona`\n"
                "**Example:** Displays leaderboard with medals (🥇🥈🥉) and splits to leader."
            ),
            inline=False
        )

        # PB command
        embed.add_field(
            name="🎯 `/pb <player> <track>`",
            value=(
                "Show a player's personal best for a specific track with detailed sector breakdown.\n"
                "**Usage:** `/pb Mokey Bytes Barcelona`\n"
                "**Example:** Shows PB time, rank, gap to record, session count, and sector-by-sector analysis."
            ),
            inline=False
        )

        # Leaders command
        embed.add_field(
            name="🏆 `/leaders`",
            value=(
                "Show the #1 Qualifying and Race time for every track.\n"
                "**Usage:** `/leaders`\n"
                "**Example:** Displays a comprehensive list of all track records across the server."
            ),
            inline=False
        )

        # Tracks command
        embed.add_field(
            name="📍 `/tracks`",
            value=(
                "List all available tracks in the database.\n"
                "**Usage:** `/tracks`\n"
                "**Example:** Shows all tracks you can query with `/records` or `/pb`."
            ),
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
        embed.set_footer(
            text="💡 Tip: Use autocomplete when typing commands to see available options!"
        )

        await interaction.response.send_message(embed=embed)


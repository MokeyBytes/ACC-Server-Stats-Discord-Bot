"""Sync command - manually sync slash commands."""
import discord
from discord import app_commands


def setup_sync_command(tree: app_commands.CommandTree):
    """Register the /sync command."""
    
    @tree.command(name="sync", description="Manually sync slash commands (admin)")
    async def sync_commands(interaction: discord.Interaction):
        """Manually sync slash commands - useful if commands aren't appearing."""
        await interaction.response.defer(ephemeral=True)
        try:
            # Clear existing commands and re-sync
            synced = await tree.sync()
            
            cmd_list = "\n".join([f"  • /{cmd.name}" for cmd in synced])
            await interaction.followup.send(
                f"✅ Synced {len(synced)} command(s) to Discord:\n{cmd_list}\n\n"
                f"⏰ **Note:** It may take 5-10 minutes for new commands to appear.\n"
                f"Try restarting Discord if `/pb` still doesn't show up.",
                ephemeral=True
            )
            print(f"[OK] Manually synced {len(synced)} commands")
            for cmd in synced:
                print(f"  - /{cmd.name}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error syncing commands: {e}", ephemeral=True)
            print(f"[ERR] Sync error: {e}")
            import traceback
            traceback.print_exc()


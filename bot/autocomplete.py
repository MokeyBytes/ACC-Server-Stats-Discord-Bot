"""Autocomplete handlers for Discord slash commands."""
import sqlite3
import discord
from discord import app_commands

from config import DB_PATH
from db.queries import fetch_available_tracks, fetch_all_players


async def track_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for track names."""
    con = sqlite3.connect(DB_PATH)
    available = fetch_available_tracks(con)
    con.close()
    
    # Filter tracks based on current input
    current_lower = current.lower()
    matches = [
        app_commands.Choice(name=track[0], value=track[0])
        for track in available
        if current_lower in track[0].lower()
    ][:25]  # Discord limit is 25 choices
    
    return matches


async def player_first_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for player first names."""
    try:
        con = sqlite3.connect(DB_PATH)
        players = fetch_all_players(con)
        con.close()
        
        # Get unique first names (filter out empty strings)
        first_names = sorted(set([p[0] for p in players if p[0] and p[0].strip()]))
        
        if not first_names:
            return []
        
        current_lower = current.lower() if current else ""
        if current_lower:
            matches = [
                app_commands.Choice(name=name, value=name)
                for name in first_names
                if current_lower in name.lower()
            ][:25]
        else:
            # If no input, return first 25 names
            matches = [
                app_commands.Choice(name=name, value=name)
                for name in first_names[:25]
            ]
        
        return matches
    except Exception as e:
        print(f"[WARN] Error in first_name autocomplete: {e}")
        import traceback
        traceback.print_exc()
        return []


async def player_last_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for player last names."""
    try:
        # Get first_name from interaction if available
        first_name = None
        try:
            if hasattr(interaction.namespace, 'first_name'):
                first_name = interaction.namespace.first_name
        except:
            pass
        
        con = sqlite3.connect(DB_PATH)
        players = fetch_all_players(con)
        con.close()
        
        # Filter by first name if provided
        if first_name:
            matching_players = [p for p in players if p[0] == first_name]
            last_names = sorted(set([p[1] for p in matching_players if p[1]]))
        else:
            last_names = sorted(set([p[1] for p in players if p[1]]))
        
        current_lower = current.lower()
        matches = [
            app_commands.Choice(name=name, value=name)
            for name in last_names
            if current_lower in name.lower()
        ][:25]
        
        return matches
    except Exception as e:
        print(f"[WARN] Error in last_name autocomplete: {e}")
        return []


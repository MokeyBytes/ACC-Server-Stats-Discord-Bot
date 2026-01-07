"""Discord bot client and main event loop."""
import sqlite3
import asyncio
import discord
from discord import app_commands

from config import DB_PATH, CHANNEL_ID, POLL_SECONDS
from db.queries import (
    fetch_queue, mark_sent, fetch_race_results_queue, 
    fetch_race_session_data, mark_race_results_sent,
    get_previous_track_record, get_player_rank, get_player_previous_rank
)
from bot.embeds import build_track_record_embed, build_personal_best_embed, build_race_results_embed
from bot.commands.records import setup_records_command
from bot.commands.pb import setup_pb_command
from bot.commands.leaders import setup_leaders_command
from bot.commands.tracks import setup_tracks_command
from bot.commands.sync import setup_sync_command
from bot.commands.help import setup_help_command


def create_bot() -> tuple[discord.Client, app_commands.CommandTree]:
    """Create and configure the Discord bot client."""
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    
    # Register all commands
    setup_records_command(tree)
    setup_pb_command(tree)
    setup_leaders_command(tree)
    setup_tracks_command(tree)
    setup_sync_command(tree)
    setup_help_command(tree)
    
    @client.event
    async def on_ready():
        channel = client.get_channel(CHANNEL_ID)
        if channel is None:
            print(f"[ERR] Could not find channel {CHANNEL_ID}. Is the bot in the server and has access?")
            return

        print(f"[OK] Logged in as {client.user}. Watching for queued record announcements...")

        try:
            synced = await tree.sync()
            print(f"[OK] Slash commands synced ({len(synced)} commands)")
            for cmd in synced:
                print(f"  - /{cmd.name}")
        except Exception as e:
            print(f"[ERR] Failed to sync commands: {e}")

        while True:
            try:
                con = sqlite3.connect(DB_PATH)
                
                # Process record announcements (TR and PB)
                rows = fetch_queue(con)
                for (
                    announcement_id, track, stype, best_ms, when_utc,
                    announcement_type, player_id, first, last, short, car_model
                ) in rows:
                    # Build embed based on announcement type
                    if announcement_type == "PB":
                        # Get rank information for PB subtitle
                        current_rank, _ = get_player_rank(con, track, stype, best_ms, first or "", last or "")
                        previous_rank = get_player_previous_rank(con, track, stype, best_ms, first or "", last or "")
                        
                        embed, img_file = build_personal_best_embed(
                            track, stype, best_ms, when_utc, first, last, short, car_model,
                            previous_rank=previous_rank, current_rank=current_rank
                        )
                    else:  # TR (Track Record)
                        # Get previous record for improvement subtitle
                        previous_record_ms = get_previous_track_record(con, track, stype, best_ms)
                        
                        embed, img_file = build_track_record_embed(
                            track, stype, best_ms, when_utc, first, last, short, car_model,
                            previous_record_ms=previous_record_ms
                        )
                    
                    # Send embed with image if available
                    if img_file:
                        sent = await channel.send(embed=embed, file=img_file)
                    else:
                        sent = await channel.send(embed=embed)
                    
                    mark_sent(con, announcement_id, sent.id)
                
                # Process race results announcements
                try:
                    race_rows = fetch_race_results_queue(con)
                    for (announcement_id, session_id, track, when_utc) in race_rows:
                        session_data, entries = fetch_race_session_data(con, session_id)
                        
                        if session_data and entries:
                            embed, img_file = build_race_results_embed(track, session_data, entries, when_utc)
                            
                            if img_file:
                                sent = await channel.send(embed=embed, file=img_file)
                            else:
                                sent = await channel.send(embed=embed)
                            
                            mark_race_results_sent(con, announcement_id, sent.id)
                        else:
                            print(f"[WARN] No data found for race session {session_id}")
                except Exception as e:
                    # Table might not exist yet, ignore
                    if "no such table" not in str(e).lower():
                        print(f"[WARN] Race results error: {e}")

                con.close()

            except Exception as e:
                print(f"[WARN] loop error: {e}")

            await asyncio.sleep(POLL_SECONDS)
    
    return client, tree


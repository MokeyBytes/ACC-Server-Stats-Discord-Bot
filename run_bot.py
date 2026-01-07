"""Entry point for the Discord bot."""
from config import DISCORD_TOKEN
from bot.client import create_bot

if __name__ == "__main__":
    client, tree = create_bot()
    client.run(DISCORD_TOKEN)


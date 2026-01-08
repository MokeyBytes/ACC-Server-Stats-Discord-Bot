"""Error handling utilities for Discord bot commands."""
import sqlite3
import logging
import traceback
from typing import Callable, Any
import discord

logger = logging.getLogger("acc_bot")


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class UserFriendlyError(Exception):
    """Exception that should show a user-friendly message."""
    def __init__(self, message: str, technical_details: str | None = None) -> None:
        self.message = message
        self.technical_details = technical_details
        super().__init__(self.message)


def create_error_embed(title: str, description: str, color: discord.Color | None = None) -> discord.Embed:
    """
    Create a user-friendly error embed.
    
    Args:
        title: Error title
        description: Error description
        color: Embed color (default: red)
    
    Returns:
        Discord embed with error information
    """
    if color is None:
        color = discord.Color.red()
    
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=color
    )
    embed.set_footer(text="If this problem persists, please contact an administrator.")
    return embed


def create_warning_embed(title: str, description: str) -> discord.Embed:
    """
    Create a warning embed.
    
    Args:
        title: Warning title
        description: Warning description
    
    Returns:
        Discord embed with warning information
    """
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=discord.Color.orange()
    )
    return embed


def handle_database_error(error: Exception, operation: str) -> None:
    """
    Log database errors with context.
    
    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
    """
    if isinstance(error, sqlite3.Error):
        logger.error(f"Database error during {operation}: {error}", exc_info=True)
    else:
        logger.error(f"Unexpected error during {operation}: {error}", exc_info=True)


def get_user_friendly_error_message(error: Exception, operation: str) -> str:
    """
    Convert technical errors to user-friendly messages.
    
    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
    
    Returns:
        User-friendly error message
    """
    if isinstance(error, UserFriendlyError):
        return error.message
    
    if isinstance(error, sqlite3.OperationalError):
        if "no such table" in str(error).lower():
            return "The database structure appears to be incomplete. Please contact an administrator."
        elif "database is locked" in str(error).lower():
            return "The database is currently in use. Please try again in a moment."
        else:
            return "A database error occurred. Please try again later."
    
    if isinstance(error, sqlite3.DatabaseError):
        return "The database encountered an error. Please try again later."
    
    if isinstance(error, FileNotFoundError):
        return "A required file could not be found. Please contact an administrator."
    
    if isinstance(error, PermissionError):
        return "Permission denied. Please contact an administrator."
    
    # Generic fallback
    return f"An error occurred while {operation}. Please try again later."


async def handle_command_error(
    interaction: discord.Interaction,
    error: Exception,
    operation: str = "processing your request",
    log_error: bool = True
) -> None:
    """
    Handle errors in Discord command handlers.
    
    Args:
        interaction: Discord interaction object
        operation: Description of the operation that failed
        error: The exception that occurred
        log_error: Whether to log the error (default: True)
    """
    if log_error:
        logger.error(f"Error in command '{interaction.command.name if interaction.command else 'unknown'}': {error}", exc_info=True)
    
    # Get user-friendly message
    user_message = get_user_friendly_error_message(error, operation)
    
    # Create error embed
    embed = create_error_embed(
        title="Error",
        description=user_message
    )
    
    # Try to send error message
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as send_error:
        logger.error(f"Failed to send error message to user: {send_error}")


def database_operation(operation_name: str):
    """
    Decorator for database operations with error handling.
    
    Args:
        operation_name: Name of the operation for logging
    
    Usage:
        @database_operation("fetching track records")
        def fetch_records(con):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(con: sqlite3.Connection, *args, **kwargs) -> Any:
            try:
                return func(con, *args, **kwargs)
            except sqlite3.Error as e:
                handle_database_error(e, operation_name)
                raise DatabaseError(f"Database error during {operation_name}") from e
            except Exception as e:
                logger.error(f"Unexpected error during {operation_name}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

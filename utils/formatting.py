"""Formatting utility functions."""
from datetime import datetime, timezone, timedelta
from typing import Union

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from config import CAR_MODELS


def fmt_car_model(car_model: Union[int, None]) -> str:
    """Convert car model ID to name, or return 'Unknown' if not found."""
    if car_model is None:
        return "Unknown"
    try:
        return CAR_MODELS.get(int(car_model), f"Unknown ({car_model})")
    except (ValueError, TypeError):
        return f"Unknown ({car_model})"


def fmt_ms(ms: int) -> str:
    """Format milliseconds as m:ss.mmm"""
    m, rem = divmod(ms, 60_000)
    s, ms2 = divmod(rem, 1000)
    return f"{m}:{s:02d}.{ms2:03d}"


def fmt_split_ms(ms: int) -> str:
    """Format split time (difference from leader). Positive = slower, shows as negative."""
    abs_ms = abs(ms)
    sign = "-" if ms > 0 else "+"
    m, rem = divmod(abs_ms, 60_000)
    s, ms2 = divmod(rem, 1000)
    return f"{sign}{m:02d}:{s:02d}.{ms2:03d}"


def fmt_dt(iso_utc: str) -> str:
    """Format UTC ISO datetime string as YYYY-MM-DD HH:MM EST/EDT"""
    if iso_utc.endswith("Z"):
        iso_utc = iso_utc.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_utc).astimezone(timezone.utc)
    
    # Convert to Eastern Time (automatically handles EST/EDT)
    if HAS_PYTZ:
        eastern = pytz.timezone("America/New_York")
        et_dt = dt.astimezone(eastern)
        # Get timezone abbreviation (EST or EDT)
        tz_abbr = et_dt.strftime("%Z")
        return et_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")
    else:
        # Fallback: manual calculation (EST = UTC-5, EDT = UTC-4)
        # Simple approximation: assume EDT from March to November
        month = dt.month
        is_dst = 3 <= month <= 11  # Rough approximation
        offset_hours = -4 if is_dst else -5
        tz_abbr = "EDT" if is_dst else "EST"
        et_dt = dt + timedelta(hours=offset_hours)
        return et_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")


def format_driver_name(first: str | None, last: str | None, short: str | None) -> str:
    """
    Format a driver's name from first name, last name, and short name.
    
    Priority: first + last name > short name > "Unknown"
    
    Args:
        first: Driver's first name (can be None or empty)
        last: Driver's last name (can be None or empty)
        short: Driver's short name (can be None or empty)
    
    Returns:
        Formatted driver name string
    """
    if first or last:
        return f"{(first or '').strip()} {(last or '').strip()}".strip()
    elif short:
        return short
    return "Unknown"


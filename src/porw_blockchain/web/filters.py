# src/porw_blockchain/web/filters.py
"""
Template filters for the web interface.

This module provides template filters for the web interface, including
formatting functions for timestamps, durations, and byte sizes.
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Union


def timestamp_to_datetime(timestamp: Optional[int]) -> str:
    """
    Convert a Unix timestamp to a formatted datetime string.

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted datetime string
    """
    if timestamp is None:
        return "N/A"
    
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def timestamp_to_age(timestamp: Optional[int]) -> str:
    """
    Convert a Unix timestamp to a human-readable age string.

    Args:
        timestamp: Unix timestamp

    Returns:
        Human-readable age string
    """
    if timestamp is None:
        return "N/A"
    
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    delta = now - dt
    
    if delta.days >= 365:
        years = delta.days // 365
        return f"{years} year{'s' if years != 1 else ''}"
    elif delta.days >= 30:
        months = delta.days // 30
        return f"{months} month{'s' if months != 1 else ''}"
    elif delta.days >= 1:
        return f"{delta.days} day{'s' if delta.days != 1 else ''}"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{delta.seconds} second{'s' if delta.seconds != 1 else ''}"


def format_bytes(size: Optional[Union[int, float]]) -> str:
    """
    Format a byte size to a human-readable string.

    Args:
        size: Size in bytes

    Returns:
        Human-readable size string
    """
    if size is None:
        return "N/A"
    
    size = float(size)
    if size == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = int(math.floor(math.log(size, 1024)))
    i = min(i, len(units) - 1)
    
    size = size / (1024 ** i)
    return f"{size:.2f} {units[i]}"


def format_duration(seconds: Optional[int]) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string
    """
    if seconds is None:
        return "N/A"
    
    delta = timedelta(seconds=seconds)
    
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts)


def setup_filters(env):
    """
    Set up template filters.

    Args:
        env: Jinja2 environment
    """
    env.filters['timestamp_to_datetime'] = timestamp_to_datetime
    env.filters['timestamp_to_age'] = timestamp_to_age
    env.filters['format_bytes'] = format_bytes
    env.filters['format_duration'] = format_duration

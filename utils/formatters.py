import math

def format_msec_to_time(msec: float) -> str:
    """Format milliseconds to a human-readable duration string."""
    if math.isnan(msec) or msec == 0:
        return "N/A"
    
    total_seconds = msec / 1000
    days = int(total_seconds // (24 * 3600))
    remaining_sec = total_seconds % (24 * 3600)
    hours = int(remaining_sec // 3600)
    minutes = int((remaining_sec % 3600) // 60)
    
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} Day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    return ", ".join(parts)

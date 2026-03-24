import math

def format_msec_to_time(msec: float) -> str:
    if math.isnan(msec) or msec == 0:
        return "N/A"
    
    total_seconds = msec / 1000
    days = int(total_seconds // (24 * 3600))
    remaining_sec = total_seconds % (24 * 3600)
    hours = int(remaining_sec // 3600)
    minutes = int((remaining_sec % 3600) // 60)
    seconds = int(remaining_sec % 60)
    
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} sec{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts) if parts else "N/A"

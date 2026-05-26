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


def format_msec_to_compact_time(msec: float) -> str:
    if math.isnan(msec) or msec == 0:
        return "N/A"
    
    if msec < 60000:
        sec = msec / 1000
        if sec < 1.0:
            return f"{sec:.2f}s"
        return f"{sec:.1f}s"
    
    total_seconds = msec / 1000
    days = int(total_seconds // (24 * 3600))
    remaining_sec = total_seconds % (24 * 3600)
    hours = int(remaining_sec // 3600)
    minutes = int((remaining_sec % 3600) // 60)
    seconds = int(remaining_sec % 60)
    
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")
    
    return " ".join(parts) if parts else "0s"


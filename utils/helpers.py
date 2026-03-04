import re

def progress_bar(current: int, total: int, width: int = 10) -> str:
    pct   = int(current * 100 / total) if total else 0
    filled= int(width * pct / 100)
    bar   = "▓" * filled + "░" * (width - filled)
    size  = f"{current/1024/1024:.1f}/{total/1024/1024:.1f} MB"
    return f"[{bar}] {pct}%\n<code>{size}</code>"

def make_file_name(prefix: str, title: str, season: int,
                   episode: int, audio: str, quality: str, ext: str = ".mp4") -> str:
    # Sanitize title
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    return (f"{prefix} - {safe} "
            f"S{season:02d}E{episode:02d} "
            f"[{audio}] [{quality}]{ext}")

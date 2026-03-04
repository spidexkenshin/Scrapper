from config import Config

def build_caption(template: str, anime_name: str, season: int,
                  episode: int, audio: str, quality: str) -> str:
    return (template
        .replace("{anime_name}", anime_name)
        .replace("{season}",     f"Season {season:02d}")
        .replace("{episode}",    f"Episode {episode:02d}")
        .replace("{audio}",      audio)
        .replace("{quality}",    quality))

def validate(template: str) -> bool:
    import re
    allowed = {"{anime_name}","{season}","{episode}","{audio}","{quality}"}
    found   = set(re.findall(r"\{[^}]+\}", template))
    return found.issubset(allowed)

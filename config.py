import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # ─── Telegram ────────────────────────────────────────────
    API_ID        = int(os.getenv("API_ID", 0))
    API_HASH      = os.getenv("API_HASH", "")
    BOT_TOKEN     = os.getenv("BOT_TOKEN", "")

    # ─── Admins (comma-separated user IDs) ───────────────────
    ADMIN_IDS     = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()]

    # ─── Database ─────────────────────────────────────────────
    MONGO_URI     = os.getenv("MONGO_URI", "")
    DB_NAME       = os.getenv("DB_NAME", "kenshin_bot")

    # ─── Groups ───────────────────────────────────────────────
    STORAGE_GROUP = int(os.getenv("STORAGE_GROUP_ID", 0))

    # ─── Scraping sources ─────────────────────────────────────
    ANIMESALT_URL    = "https://animesalt.top"
    ANIMEWORLD_URL   = "https://watchanimeworld.net"

    # ─── Defaults ─────────────────────────────────────────────
    DELETE_AFTER       = int(os.getenv("DELETE_AFTER", 10))
    AUTO_CHECK_MINS    = int(os.getenv("AUTO_CHECK_INTERVAL", 60))
    FILE_PREFIX        = os.getenv("FILE_PREFIX", "@KENSHIN_ANIME")
    PREFERRED_LANG     = "Hindi Dub"
    MAX_PARALLEL_DL    = int(os.getenv("MAX_PARALLEL_DL", 3))

    DEFAULT_CAPTION = (
        "<b>📺 ᴀɴɪᴍᴇ : {anime_name}\n"
        "━━━━━━━━━━━━━━━━━━━⭒\n"
        "❖ Sᴇᴀsᴏɴ: {season}\n"
        "❖ ᴇᴘɪꜱᴏᴅᴇ: {episode}\n"
        "❖ ᴀᴜᴅɪᴏ: {audio}| #Official\n"
        "❖ Qᴜᴀʟɪᴛʏ: {quality}\n"
        "━━━━━━━━━━━━━━━━━━━⭒\n"
        "<blockquote>POWERED BY: [@KENSHIN_ANIME & @MANWHA_VERSE]</blockquote></b>"
    )

    # ─── Request headers (mimic browser) ──────────────────────
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

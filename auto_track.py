"""Auto-check for new anime episodes and notify admins."""
import asyncio, logging
from pyrogram import Client
from utils.scrapers.anilist import get_detail
from config import Config

logger = logging.getLogger(__name__)

class AutoTracker:
    def __init__(self, app: Client, db):
        self.app = app
        self.db  = db

    async def start(self):
        logger.info("AutoTracker started.")
        while True:
            mins = await self.db.get("auto_check_interval") or Config.AUTO_CHECK_MINS
            await asyncio.sleep(mins * 60)
            await self._check_all()

    async def _check_all(self):
        tracks = await self.db.get_tracks()
        if not tracks: return
        logger.info(f"Checking {len(tracks)} tracked anime…")
        for t in tracks:
            try: await self._check_one(t)
            except Exception as e: logger.error(f"track check failed: {e}")

    async def _check_one(self, t: dict):
        if t.get("source") != "anilist": return
        detail = await get_detail(t["id"])
        if not detail: return
        seasons = detail.get("seasons",[])
        s_data  = next((s for s in seasons if s["num"]==t.get("season",1)), None)
        if not s_data: return
        cur_eps   = s_data.get("episodes",0) or 0
        last_ep   = t.get("last_ep",0)
        if cur_eps > last_ep:
            new_ep = last_ep + 1
            msg = (
                f"🆕 <b>New Episode!</b>\n\n"
                f"📺 <b>{detail['title']}</b>\n"
                f"📌 S{t.get('season',1):02d} E{new_ep:02d} is available!\n\n"
                f"Use /anime {detail['title']} to upload."
            )
            for aid in await self.db.get_admins():
                try: await self.app.send_message(aid, msg, parse_mode="html")
                except: pass

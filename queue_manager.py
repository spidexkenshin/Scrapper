"""
Upload queue — processes one item at a time.
Each item can have multiple qualities (uploaded sequentially).
"""
import asyncio, os, logging
from typing import Dict, List
from pyrogram import Client
from pyrogram.types import Message
from config import Config
from utils.helpers import progress_bar, make_file_name
from utils.downloader import download_thumb, cleanup

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self, app: Client, db):
        self.app   = app
        self.db    = db
        self.queue: asyncio.Queue = asyncio.Queue()

    def enqueue(self, item: Dict):
        self.queue.put_nowait(item)
        logger.info(f"Queue +1 | size={self.queue.qsize()}")

    @property
    def size(self): return self.queue.qsize()

    async def run(self):
        logger.info("Queue worker started.")
        while True:
            item = await self.queue.get()
            try:
                await self._process(item)
            except Exception as e:
                logger.exception(f"Queue item failed: {e}")
                await self._notify_admins(f"❌ Upload failed:\n<code>{e}</code>")
            finally:
                self.queue.task_done()

    # ── Core processor ────────────────────────────────────────
    async def _process(self, item: Dict):
        """
        item keys:
          video_file   – local path OR direct URL string
          episodes     – list of {num, url} dicts (for multi-ep) OR None
          qualities    – list of quality dicts [{quality, url}]
          anime_name, season, episode, audio, quality
          caption_tpl  – caption template
          thumb_url    – thumbnail URL
          notif_chat   – chat to edit progress in
          notif_mid    – message id to edit
          target        – "chat" | "channel"
          chat_id       – if target==chat, send here
        """
        notif_chat = item.get("notif_chat")
        notif_mid  = item.get("notif_mid")

        async def edit(text: str):
            if notif_chat and notif_mid:
                try:
                    await self.app.edit_message_text(
                        notif_chat, notif_mid, text, parse_mode="html")
                except Exception: pass

        # ── Get storage group ────────────────────────────────
        storage_gid = await self.db.get("storage_group") or Config.STORAGE_GROUP
        if not storage_gid:
            raise ValueError("Storage group not set. Use /set_storage")

        channels = await self.db.get_channels()
        target   = item.get("target", "channel")

        # ── Process each quality ──────────────────────────────
        qualities = item.get("qualities", [])
        if not qualities and item.get("quality"):
            qualities = [{"quality": item["quality"],
                          "url":     item.get("video_file","")}]

        for q_item in qualities:
            quality  = q_item["quality"]
            src      = q_item["url"]  # local path or URL

            await edit(f"⏳ <b>Processing {quality}…</b>")

            # Get thumb
            thumb_path = ""
            thumb_fid  = await self.db.get("thumbnail_file_id")
            if thumb_fid:
                thumb_path = f"/tmp/kenshin/thumb_{item.get('episode',0)}.jpg"
                await self.app.download_media(thumb_fid, file_name=thumb_path)
            elif item.get("thumb_url"):
                thumb_path = await download_thumb(
                    item["thumb_url"],
                    f"thumb_{item.get('episode',0)}.jpg")

            # Build caption
            from utils.caption import build_caption
            caption = build_caption(
                item["caption_tpl"],
                anime_name=item["anime_name"],
                season=item["season"],
                episode=item["episode"],
                audio=item["audio"],
                quality=quality,
            )

            # File name
            prefix    = await self.db.get("file_prefix") or Config.FILE_PREFIX
            ext       = os.path.splitext(src)[1] if os.path.exists(src) else ".mp4"
            file_name = make_file_name(
                prefix, item["anime_name"],
                item["season"], item["episode"],
                item["audio"], quality, ext
            )

            last_pct  = [0]
            prog_lock = asyncio.Lock()

            async def progress(cur, tot):
                pct = int(cur*100/tot)
                async with prog_lock:
                    if pct - last_pct[0] >= 5:
                        last_pct[0] = pct
                        await edit(
                            f"📤 <b>Uploading {quality}…</b>\n"
                            f"{progress_bar(cur,tot)}"
                        )

            # ── Upload to storage group ───────────────────────
            storage_msg: Message = await self.app.send_video(
                chat_id   = storage_gid,
                video     = src,
                file_name = file_name,
                thumb     = thumb_path or None,
                caption   = caption,
                parse_mode= "html",
                progress  = progress,
            )

            # ── Forward to destinations ───────────────────────
            if target == "channel":
                sent = 0
                for ch in channels:
                    try:
                        await self.app.copy_message(
                            ch["cid"], storage_gid, storage_msg.id,
                            caption=caption, parse_mode="html")
                        sent += 1
                        await asyncio.sleep(0.8)
                    except Exception as e:
                        logger.warning(f"Forward to {ch['cid']} failed: {e}")
            else:
                # Send to requesting chat
                await self.app.copy_message(
                    item["chat_id"], storage_gid, storage_msg.id,
                    caption=caption, parse_mode="html")

            # ── Sticker ───────────────────────────────────────
            sticker = await self.db.get("sticker_file_id")
            if sticker and target == "channel":
                for ch in channels:
                    try:
                        await self.app.send_sticker(ch["cid"], sticker)
                        await asyncio.sleep(0.4)
                    except Exception: pass

            # ── Log ───────────────────────────────────────────
            await self.db.log_upload({
                "anime":   item["anime_name"],
                "season":  item["season"],
                "ep":      item["episode"],
                "quality": quality,
                "target":  target,
            })

            # ── Cleanup after delay ───────────────────────────
            delay = await self.db.get("delete_after") or Config.DELETE_AFTER
            await asyncio.sleep(delay)
            if os.path.exists(src):
                cleanup(src)
            cleanup(thumb_path)

        await edit(
            f"✅ <b>Done!</b>\n"
            f"📺 <b>{item['anime_name']}</b> "
            f"S{item['season']:02d}E{item['episode']:02d}\n"
            f"🎯 {len(qualities)} quality/qualities uploaded"
        )

    async def _notify_admins(self, msg: str):
        for aid in await self.db.get_admins():
            try:
                await self.app.send_message(aid, msg, parse_mode="html")
            except Exception: pass

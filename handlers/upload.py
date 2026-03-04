"""
/upload <name> — Manual upload flow (admin sends the video file directly).
Separate from /anime search flow.
"""
import os, logging
from typing import Dict
from pyrogram import Client, filters
from pyrogram.types import (Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton)
from utils.scrapers.anilist import search as anilist_search, get_detail
from utils.caption import build_caption
from utils.helpers import make_file_name, progress_bar
from config import Config

logger = logging.getLogger(__name__)
STATE: Dict[int, dict] = {}
DL_DIR = "/tmp/kenshin"
os.makedirs(DL_DIR, exist_ok=True)

AUDIO_OPTS    = ["Hindi Dub","English Dub","Japanese Sub",
                 "Multi-Audio","Tamil Dub","Telugu Dub"]
QUALITY_OPTS  = ["480p","720p","1080p","4K"]

def _af(db):
    async def f(_,__,m): return await db.is_admin(m.from_user.id)
    return filters.create(f)
def _caf(db):
    async def f(_,__,c): return await db.is_admin(c.from_user.id)
    return filters.create(f)

def register(app: Client, db, qmgr):
    af  = _af(db)
    caf = _caf(db)

    @app.on_message(filters.command("upload") & af)
    async def cmd_upload(_, msg: Message):
        if len(msg.command) < 2:
            await msg.reply("Usage: /upload <anime name>"); return
        query = " ".join(msg.command[1:])
        uid   = msg.from_user.id
        w = await msg.reply(f"🔍 Searching <b>{query}</b>…", parse_mode="html")
        results = await anilist_search(query)
        if not results:
            await w.edit("❌ Not found."); return

        STATE[uid] = {"step":"select","results":results,"query":query}
        btns = []
        for i,r in enumerate(results[:6]):
            label = f"{r['title']} ({r.get('year','?')})"
            if len(label)>50: label=label[:47]+"…"
            btns.append([InlineKeyboardButton(label, callback_data=f"up_sel:{i}")])
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="up_cancel")])
        await w.edit(
            f"🔍 Select anime for <b>{query}</b>:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    @app.on_callback_query(filters.regex(r"^up_sel:\d+$") & caf)
    async def cb_sel(_, cq: CallbackQuery):
        uid = cq.from_user.id
        idx = int(cq.data.split(":")[1])
        if uid not in STATE:
            await cq.answer("Expired.", show_alert=True); return
        r = STATE[uid]["results"][idx]
        detail = await get_detail(r["id"])
        STATE[uid].update({"step":"audio","detail":detail})
        btns = [[InlineKeyboardButton(
            f"{'⭐ ' if a=='Hindi Dub' else ''}{a}",
            callback_data=f"up_audio:{a}")] for a in AUDIO_OPTS]
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="up_cancel")])
        await cq.message.edit(
            f"🎌 <b>{detail['title']}</b>\n\nSelect audio:",
            reply_markup=InlineKeyboardMarkup(btns), parse_mode="html")

    @app.on_callback_query(filters.regex(r"^up_audio:") & caf)
    async def cb_audio(_, cq: CallbackQuery):
        uid   = cq.from_user.id
        audio = cq.data.split(":",1)[1]
        if uid not in STATE:
            await cq.answer("Expired.", show_alert=True); return
        STATE[uid].update({"step":"season","audio":audio})
        detail  = STATE[uid]["detail"]
        seasons = detail.get("seasons",[{"num":1,"episodes":detail.get("episodes",0)}])
        btns = []
        if len(seasons)>1:
            btns.append([InlineKeyboardButton("📦 ALL Seasons",callback_data="up_s:0")])
        for s in seasons:
            btns.append([InlineKeyboardButton(
                f"Season {s['num']} ({s['episodes']} eps)",
                callback_data=f"up_s:{s['num']}")])
        btns.append([InlineKeyboardButton("❌ Cancel",callback_data="up_cancel")])
        await cq.message.edit(
            f"🎌 <b>{detail['title']}</b> | {audio}\n\nSelect Season:",
            reply_markup=InlineKeyboardMarkup(btns), parse_mode="html")

    @app.on_callback_query(filters.regex(r"^up_s:\d+$") & caf)
    async def cb_season(_, cq: CallbackQuery):
        uid  = cq.from_user.id
        snum = int(cq.data.split(":")[1])
        if uid not in STATE:
            await cq.answer("Expired.", show_alert=True); return
        STATE[uid].update({"step":"episode","season":snum})
        detail  = STATE[uid]["detail"]
        seasons = detail.get("seasons",[])
        if snum == 0:
            ep_count = max((s["episodes"] for s in seasons), default=24)
        else:
            s_data = next((s for s in seasons if s["num"]==snum),{})
            ep_count = s_data.get("episodes",24) or 24

        btns = [[InlineKeyboardButton(
            f"📦 ALL Episodes ({ep_count})",callback_data="up_e:all")]]
        row=[]
        for e in range(1, min(ep_count+1,49)):
            row.append(InlineKeyboardButton(str(e),callback_data=f"up_e:{e}"))
            if len(row)==6: btns.append(row); row=[]
        if row: btns.append(row)
        btns.append([InlineKeyboardButton("✏️ Type number",callback_data="up_e:type")])
        btns.append([InlineKeyboardButton("❌ Cancel",callback_data="up_cancel")])
        await cq.message.edit("Select Episode:",
            reply_markup=InlineKeyboardMarkup(btns))

    @app.on_callback_query(filters.regex(r"^up_e:") & caf)
    async def cb_episode(_, cq: CallbackQuery):
        uid = cq.from_user.id
        val = cq.data.split(":")[1]
        if uid not in STATE:
            await cq.answer("Expired.", show_alert=True); return
        if val=="type":
            STATE[uid]["step"]="ep_type"
            await cq.message.edit("✏️ Type the episode number:")
            return
        STATE[uid].update({"step":"quality",
                           "episode": "all" if val=="all" else int(val)})
        btns = [[InlineKeyboardButton(
            "📦 ALL Qualities (480p→1080p)",callback_data="up_q:all")]]
        for q in QUALITY_OPTS:
            btns.append([InlineKeyboardButton(q,callback_data=f"up_q:{q}")])
        btns.append([InlineKeyboardButton("❌ Cancel",callback_data="up_cancel")])
        await cq.message.edit("Select Quality:",
            reply_markup=InlineKeyboardMarkup(btns))

    @app.on_callback_query(filters.regex(r"^up_q:") & caf)
    async def cb_quality(_, cq: CallbackQuery):
        uid = cq.from_user.id
        val = cq.data.split(":",1)[1]
        if uid not in STATE:
            await cq.answer("Expired.", show_alert=True); return
        STATE[uid].update({"step":"video_wait","quality":val})
        st = STATE[uid]
        ep_s = "All" if st["episode"]=="all" else f"Ep {st['episode']:02d}"
        q_s  = "All" if val=="all" else val
        await cq.message.edit(
            f"<b>📤 Ready!</b>\n\n"
            f"📺 {st['detail']['title']}\n"
            f"📌 S{st['season']:02d} | {ep_s} | {st['audio']} | {q_s}\n\n"
            f"Now <b>send the video file</b>:",
            parse_mode="html")

    @app.on_callback_query(filters.regex(r"^up_cancel$") & caf)
    async def cb_cancel(_, cq: CallbackQuery):
        STATE.pop(cq.from_user.id, None)
        await cq.message.edit("❌ Cancelled.")

    @app.on_message(filters.private & af & ~filters.command(""))
    async def msg_handler(_, msg: Message):
        uid = msg.from_user.id
        if uid not in STATE: return
        st = STATE[uid]

        if st["step"] == "ep_type":
            if msg.text and msg.text.strip().isdigit():
                ep = int(msg.text.strip())
                STATE[uid].update({"step":"quality","episode":ep})
                btns = [[InlineKeyboardButton(
                    "📦 ALL Qualities",callback_data="up_q:all")]]
                for q in QUALITY_OPTS:
                    btns.append([InlineKeyboardButton(q,callback_data=f"up_q:{q}")])
                await msg.reply("Select Quality:",
                    reply_markup=InlineKeyboardMarkup(btns))
            else:
                await msg.reply("Enter a valid number.")
            return

        if st["step"] == "video_wait":
            if not (msg.video or msg.document):
                await msg.reply("❌ Please send a video file.")
                return

            detail  = st["detail"]
            audio   = st["audio"]
            season  = st["season"]
            episode = st["episode"]
            quality = st["quality"]

            tpl = await db.get("caption_template") or Config.DEFAULT_CAPTION
            prefix = await db.get("file_prefix") or Config.FILE_PREFIX

            notif = await msg.reply(
                "⏳ <b>Downloading…</b>", parse_mode="html")

            # ── Download the video ────────────────────────────
            last=[0]
            async def progress(cur,tot):
                pct=int(cur*100/tot)
                if pct-last[0]>=10:
                    last[0]=pct
                    try:
                        await notif.edit(
                            f"📥 <b>Downloading…</b>\n{progress_bar(cur,tot)}")
                    except: pass

            file = msg.video or msg.document
            ext = ".mp4"
            if msg.document and msg.document.file_name:
                _, ext = os.path.splitext(msg.document.file_name)
                ext = ext or ".mp4"

            file_path = await app.download_media(
                file,
                file_name=os.path.join(
                    DL_DIR, f"manual_{uid}_{episode}{ext}"),
                progress=progress)

            # Episodes to process
            seasons_to_proc = []
            all_seasons = detail.get("seasons",[])
            if season==0:
                seasons_to_proc = all_seasons
            else:
                s = next((s for s in all_seasons if s["num"]==season),
                         {"num":season,"episodes":[]})
                seasons_to_proc = [s]

            # For manual upload — single file, figure out episode list
            qualities_list = (
                [{"quality":q,"url":file_path} for q in QUALITY_OPTS]
                if quality=="all" else
                [{"quality":quality,"url":file_path}]
            )

            for s_data in seasons_to_proc:
                ep_num = episode if episode != "all" else 1
                qmgr.enqueue({
                    "anime_name":  detail["title"],
                    "season":      s_data["num"],
                    "episode":     ep_num,
                    "audio":       audio,
                    "qualities":   qualities_list,
                    "caption_tpl": tpl,
                    "thumb_url":   detail.get("thumb",""),
                    "target":      "channel",
                    "chat_id":     msg.chat.id,
                    "notif_chat":  msg.chat.id,
                    "notif_mid":   notif.id,
                })

            await notif.edit(
                f"✅ <b>Queued!</b>\n"
                f"📋 Queue size: <b>{qmgr.size}</b>",
                parse_mode="html")

            STATE.pop(uid, None)

    @app.on_message(filters.command("queue") & af)
    async def cmd_queue(_, msg: Message):
        await msg.reply(
            f"<b>📋 Upload Queue</b>\n"
            f"Pending: <b>{qmgr.size}</b>",
            parse_mode="html")

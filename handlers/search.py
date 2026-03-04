"""
/anime, /movie, /series commands.
Full interactive flow:
  Search → Select Result → Select Language → Select Source →
  Select Season → Select Episodes (with ALL) →
  Select Quality (with ALL) → Select Target → Upload
"""
import asyncio, logging, os
from typing import Dict, List
from pyrogram import Client, filters
from pyrogram.types import (Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton)
from utils.scrapers.aggregator import multi_search, source_label
from utils.scrapers import animesalt, animeworld
from utils.caption import build_caption
from utils.helpers import make_file_name
from config import Config

logger = logging.getLogger(__name__)
# user_id → state dict
STATE: Dict[int, dict] = {}

QUALITY_ORDER = ["480p","720p","1080p","4K"]
AUDIO_OPTS = ["Hindi Dub","English Dub","Japanese Sub",
              "Multi-Audio","Tamil Dub","Telugu Dub"]

def _afilter(db):
    async def f(_,__,m): return await db.is_admin(m.from_user.id)
    return filters.create(f)

def _caf(db):
    async def f(_,__,c): return await db.is_admin(c.from_user.id)
    return filters.create(f)

def register(app: Client, db, qmgr):
    af  = _afilter(db)
    caf = _caf(db)

    # ── /anime /movie /series ─────────────────────────────────
    for cmd, cat in [("anime","anime"),("movie","movie"),("series","series")]:
        @app.on_message(filters.command(cmd) & af)
        async def cmd_search(_, msg: Message, _cat=cat):
            if len(msg.command) < 2:
                await msg.reply(f"Usage: /{_cat} <name>\nExample: /{_cat} Solo Leveling")
                return
            await db.add_user(msg.from_user.id,
                               msg.from_user.username,
                               msg.from_user.first_name)
            query = " ".join(msg.command[1:])
            uid   = msg.from_user.id
            w = await msg.reply(
                f"🔍 Searching <b>{query}</b> "
                f"[{_cat}] across all sources…",
                parse_mode="html")

            results = await multi_search(query, _cat)
            if not results:
                await w.edit("❌ No results found. Try different keywords.")
                return

            STATE[uid] = {"step": "result_select", "category": _cat,
                          "query": query, "results": results}

            btns = []
            for i, r in enumerate(results[:8]):
                src_badge = source_label(r.get("sources",[r["source"]]))
                label = f"{r['title']} [{src_badge}]"
                if len(label) > 55: label = label[:52]+"…"
                btns.append([InlineKeyboardButton(label,
                    callback_data=f"rs:{i}")])
            btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

            await w.edit(
                f"🔍 <b>Results for '{query}'</b>\n"
                f"<i>Sources shown in brackets</i>",
                reply_markup=InlineKeyboardMarkup(btns),
                parse_mode="html")

    # ── Result selected ───────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^rs:\d+$") & caf)
    async def cb_result(_, cq: CallbackQuery):
        uid = cq.from_user.id
        idx = int(cq.data.split(":")[1])
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        r = STATE[uid]["results"][idx]
        STATE[uid].update({"step":"lang_select","selected":r})

        # Show language options (highlight Hindi Dub)
        btns = []
        for lang in AUDIO_OPTS:
            label = f"{'⭐ ' if lang=='Hindi Dub' else ''}{lang}"
            btns.append([InlineKeyboardButton(label,
                callback_data=f"lang:{lang}")])
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

        await cq.message.edit(
            f"<b>📺 {r['title']}</b>\n\n🎵 Select audio language:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    # ── Language selected ─────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^lang:") & caf)
    async def cb_lang(_, cq: CallbackQuery):
        uid  = cq.from_user.id
        lang = cq.data.split(":",1)[1]
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        STATE[uid].update({"step":"source_select","audio":lang})
        r = STATE[uid]["selected"]
        sources = r.get("sources",[r["source"]])

        if len(sources) == 1:
            # Auto-select single source
            STATE[uid]["src_source"] = sources[0]
            await _fetch_detail_and_show_seasons(cq, uid, r, sources[0], db)
            return

        # Multiple sources — let user choose
        src_labels = {
            "animesalt":  "🌊 AnimeSalt",
            "animeworld": "🌍 AnimeWorld",
            "anilist":    "📋 AniList (metadata only)",
        }
        btns = [
            [InlineKeyboardButton(src_labels.get(s,s),
             callback_data=f"src:{s}")]
            for s in sources
        ]
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        await cq.message.edit(
            f"<b>📺 {r['title']}</b>\nAudio: <b>{lang}</b>\n\n"
            f"📡 Available on multiple sources. Choose:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    # ── Source selected ───────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^src:") & caf)
    async def cb_source(_, cq: CallbackQuery):
        uid    = cq.from_user.id
        source = cq.data.split(":",1)[1]
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        STATE[uid]["src_source"] = source
        r = STATE[uid]["selected"]
        await _fetch_detail_and_show_seasons(cq, uid, r, source, db)

    # ── Season selected ───────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^s:\d+$") & caf)
    async def cb_season(_, cq: CallbackQuery):
        uid  = cq.from_user.id
        snum = int(cq.data.split(":")[1])
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        detail = STATE[uid]["detail"]
        if snum == 0:  # ALL seasons
            STATE[uid].update({"step":"ep_select","season":"all"})
            await _show_episodes(cq, uid, detail, season_num=None)
            return

        STATE[uid].update({"step":"ep_select","season":snum})
        await _show_episodes(cq, uid, detail, season_num=snum)

    # ── Episodes selected ─────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^e:") & caf)
    async def cb_episode(_, cq: CallbackQuery):
        uid = cq.from_user.id
        val = cq.data.split(":")[1]   # "all" or episode number
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        STATE[uid].update({"step":"quality_select",
                           "episode": "all" if val=="all" else int(val)})
        await _show_quality(cq, uid)

    # ── Quality selected ──────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^q:") & caf)
    async def cb_quality(_, cq: CallbackQuery):
        uid = cq.from_user.id
        val = cq.data.split(":",1)[1]   # "all" or "480p" etc
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        STATE[uid].update({"step":"target_select",
                           "quality": "all" if val=="all" else val})

        btns = [
            [InlineKeyboardButton("📢 Target Channels", callback_data="tgt:channel")],
            [InlineKeyboardButton("💬 This Chat",       callback_data="tgt:chat")],
            [InlineKeyboardButton("❌ Cancel",           callback_data="cancel")],
        ]
        st = STATE[uid]
        ep_str = "All Episodes" if st["episode"]=="all" else f"Ep {st['episode']:02d}"
        q_str  = "All Qualities" if st["quality"]=="all" else st["quality"]
        await cq.message.edit(
            f"<b>📤 Upload Summary</b>\n\n"
            f"📺 <b>{st['selected']['title']}</b>\n"
            f"📌 Season {st['season']} | {ep_str}\n"
            f"🎵 {st['audio']} | 📹 {q_str}\n\n"
            f"<b>Send to?</b>",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    # ── Target selected → enqueue ─────────────────────────────
    @app.on_callback_query(filters.regex(r"^tgt:") & caf)
    async def cb_target(_, cq: CallbackQuery):
        uid    = cq.from_user.id
        target = cq.data.split(":")[1]
        if uid not in STATE:
            await cq.answer("Session expired.", show_alert=True); return

        st = STATE.pop(uid)
        detail   = st["detail"]
        audio    = st["audio"]
        quality  = st["quality"]
        season   = st["season"]
        episode  = st["episode"]
        source   = st["src_source"]

        tpl = await db.get("caption_template") or Config.DEFAULT_CAPTION

        notif = await cq.message.edit(
            "⏳ <b>Preparing upload queue…</b>", parse_mode="html")

        # ── Determine which episodes to upload ────────────────
        seasons_to_proc = []
        if season == "all":
            seasons_to_proc = detail["seasons"]
        else:
            s = next((s for s in detail["seasons"] if s["num"]==season), None)
            if s: seasons_to_proc = [s]

        total_jobs = 0
        for s_data in seasons_to_proc:
            eps = s_data["episodes"]
            if episode != "all":
                eps = [e for e in eps if e["num"] == episode]

            qualities = QUALITY_ORDER if quality == "all" else [quality]

            for ep in eps:
                ep_streams = await _get_streams(source, ep["url"])
                if not ep_streams:
                    # No stream found — skip with note
                    logger.warning(f"No streams for {ep['url']}")
                    continue

                # Filter to requested qualities
                if quality == "all":
                    q_list = ep_streams
                else:
                    q_list = [s for s in ep_streams if s["quality"]==quality]
                    if not q_list and ep_streams:
                        q_list = [ep_streams[-1]]  # fallback: highest available

                qmgr.enqueue({
                    "anime_name":  detail["title"],
                    "season":      s_data["num"],
                    "episode":     ep["num"],
                    "audio":       audio,
                    "qualities":   q_list,
                    "caption_tpl": tpl,
                    "thumb_url":   detail.get("thumb",""),
                    "target":      target,
                    "chat_id":     cq.message.chat.id,
                    "notif_chat":  cq.message.chat.id,
                    "notif_mid":   notif.id,
                })
                total_jobs += 1
                await asyncio.sleep(0.1)

        await cq.message.edit(
            f"✅ <b>{total_jobs} job(s) added to queue!</b>\n"
            f"📋 Queue size: <b>{qmgr.size}</b>\n\n"
            f"Processing will start automatically.",
            parse_mode="html")

    # ── Cancel ────────────────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^cancel$") & caf)
    async def cb_cancel(_, cq: CallbackQuery):
        STATE.pop(cq.from_user.id, None)
        await cq.message.edit("❌ Cancelled.")

    # ── Helpers ───────────────────────────────────────────────
    async def _fetch_detail_and_show_seasons(cq, uid, r, source, db):
        await cq.message.edit("⏳ Fetching details…")
        scraper = animesalt if source=="animesalt" else animeworld
        url = r.get(f"{source}_url") or r.get("url","")

        detail = await scraper.get_detail(url) if url else None
        if not detail:
            await cq.message.edit("❌ Failed to fetch content details. Try another source.")
            return

        STATE[uid].update({"step":"season_select","detail":detail})

        seasons = detail["seasons"]
        btns = []
        if len(seasons) > 1:
            btns.append([InlineKeyboardButton(
                "📦 ALL Seasons", callback_data="s:0")])
        for s in seasons:
            btns.append([InlineKeyboardButton(
                f"Season {s['num']} ({s['ep_count']} eps)",
                callback_data=f"s:{s['num']}")])
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

        await cq.message.edit(
            f"<b>📺 {detail['title']}</b>\n\nSelect Season:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    async def _show_episodes(cq, uid, detail, season_num):
        if season_num is None:
            # ALL seasons — show confirmation
            total_eps = sum(s["ep_count"] for s in detail["seasons"])
            btns = [
                [InlineKeyboardButton(f"📦 ALL Episodes ({total_eps} total)",
                    callback_data="e:all")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]
            await cq.message.edit(
                f"<b>📺 {detail['title']}</b>\nAll {len(detail['seasons'])} seasons\n\n"
                f"Select episodes:",
                reply_markup=InlineKeyboardMarkup(btns),
                parse_mode="html")
            return

        s = next((s for s in detail["seasons"] if s["num"]==season_num), None)
        if not s:
            await cq.message.edit("❌ Season not found.")
            return

        eps = s["episodes"]
        btns = [[InlineKeyboardButton(
            f"📦 ALL Episodes ({len(eps)})", callback_data="e:all")]]

        row = []
        for ep in eps[:48]:
            row.append(InlineKeyboardButton(
                str(ep["num"]), callback_data=f"e:{ep['num']}"))
            if len(row) == 6:
                btns.append(row); row = []
        if row: btns.append(row)
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

        await cq.message.edit(
            f"<b>📺 {detail['title']}</b> — Season {season_num}\n\n"
            f"Select Episode:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    async def _show_quality(cq, uid):
        st = STATE[uid]
        btns = [
            [InlineKeyboardButton("📦 ALL Qualities (480p→1080p)",
                callback_data="q:all")]
        ]
        for q in QUALITY_ORDER:
            btns.append([InlineKeyboardButton(q, callback_data=f"q:{q}")])
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        await cq.message.edit(
            f"<b>📺 {st['selected']['title']}</b>\n\nSelect Quality:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="html")

    async def _get_streams(source: str, ep_url: str):
        scraper = animesalt if source=="animesalt" else animeworld
        return await scraper.get_streams(ep_url)

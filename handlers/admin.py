import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

logger = logging.getLogger(__name__)

def _af(db):
    async def f(_,__,m): return await db.is_admin(m.from_user.id)
    return filters.create(f)

def register(app: Client, db):
    af = _af(db)

    @app.on_message(filters.command("add_admin") & af)
    async def add_admin(_, msg: Message):
        if len(msg.command)<2 or not msg.command[1].isdigit():
            await msg.reply("Usage: /add_admin <user_id>"); return
        uid=int(msg.command[1])
        await db.add_admin(uid, msg.from_user.id)
        await msg.reply(f"✅ Admin <code>{uid}</code> added.", parse_mode="html")

    @app.on_message(filters.command("remove_admin") & af)
    async def rm_admin(_, msg: Message):
        if len(msg.command)<2 or not msg.command[1].isdigit():
            await msg.reply("Usage: /remove_admin <user_id>"); return
        uid=int(msg.command[1])
        if uid in Config.ADMIN_IDS:
            await msg.reply("❌ Can't remove root admin."); return
        await db.remove_admin(uid)
        await msg.reply(f"✅ Removed <code>{uid}</code>.", parse_mode="html")

    @app.on_message(filters.command("admins") & af)
    async def list_admins(_, msg: Message):
        admins = await db.get_admins()
        text = "<b>👮 Admins</b>\n\n" + "\n".join(f"• <code>{a}</code>" for a in admins)
        await msg.reply(text, parse_mode="html")

    @app.on_message(filters.command("set_caption") & af)
    async def set_caption(_, msg: Message):
        txt = msg.text.split(None,1)
        if len(txt)<2:
            await msg.reply(
                "Send template after command.\n"
                "Vars: <code>{anime_name} {season} {episode} {audio} {quality}</code>",
                parse_mode="html"); return
        await db.set("caption_template", txt[1])
        await msg.reply("✅ Caption saved!")

    @app.on_message(filters.command("show_caption") & af)
    async def show_caption(_, msg: Message):
        tpl = await db.get("caption_template") or Config.DEFAULT_CAPTION
        await msg.reply(f"<b>Current caption:</b>\n\n{tpl}", parse_mode="html")

    @app.on_message(filters.command("reset_caption") & af)
    async def reset_caption(_, msg: Message):
        await db.set("caption_template", Config.DEFAULT_CAPTION)
        await msg.reply("✅ Caption reset to default.")

    @app.on_message(filters.command("set_thumbnail") & af)
    async def set_thumb(_, msg: Message):
        if msg.reply_to_message and msg.reply_to_message.photo:
            fid = msg.reply_to_message.photo.file_id
            await db.set("thumbnail_file_id", fid)
            await msg.reply("✅ Thumbnail saved!")
        else:
            await msg.reply("Reply to a photo with /set_thumbnail")

    @app.on_message(filters.command("clear_thumbnail") & af)
    async def clr_thumb(_, msg: Message):
        await db.set("thumbnail_file_id", None)
        await msg.reply("✅ Thumbnail cleared.")

    @app.on_message(filters.command("set_sticker") & af)
    async def set_sticker(_, msg: Message):
        if msg.reply_to_message and msg.reply_to_message.sticker:
            fid = msg.reply_to_message.sticker.file_id
            await db.set("sticker_file_id", fid)
            await msg.reply("✅ Sticker saved!")
        else:
            await msg.reply("Reply to a sticker with /set_sticker")

    @app.on_message(filters.command("clear_sticker") & af)
    async def clr_sticker(_, msg: Message):
        await db.set("sticker_file_id", None)
        await msg.reply("✅ Sticker cleared.")

    @app.on_message(filters.command("set_storage") & af)
    async def set_storage(_, msg: Message):
        if len(msg.command)<2:
            await msg.reply("Usage: /set_storage <group_id>"); return
        try:
            gid=int(msg.command[1])
            await db.set("storage_group", gid)
            await msg.reply(f"✅ Storage group: <code>{gid}</code>", parse_mode="html")
        except ValueError:
            await msg.reply("❌ Invalid ID")

    @app.on_message(filters.command("set_prefix") & af)
    async def set_prefix(_, msg: Message):
        txt = msg.text.split(None,1)
        if len(txt)<2:
            await msg.reply("Usage: /set_prefix @Channel"); return
        await db.set("file_prefix", txt[1].strip())
        await msg.reply(f"✅ Prefix: <code>{txt[1].strip()}</code>", parse_mode="html")

    @app.on_message(filters.command("delete_after") & af)
    async def del_after(_, msg: Message):
        if len(msg.command)<2 or not msg.command[1].isdigit():
            cur = await db.get("delete_after") or Config.DELETE_AFTER
            await msg.reply(f"Current: <b>{cur}s</b>\nUsage: /delete_after <secs>",
                            parse_mode="html"); return
        secs=int(msg.command[1])
        await db.set("delete_after", secs)
        await msg.reply(f"✅ Delete after <b>{secs}s</b>", parse_mode="html")

    @app.on_message(filters.command("users") & af)
    async def cmd_users(_, msg: Message):
        count = await db.user_count()
        users = await db.get_all_users()
        lines = []
        for u in users[-10:]:
            un = f"@{u['uname']}" if u.get("uname") else "—"
            lines.append(f"• <code>{u['uid']}</code> {un}")
        await msg.reply(
            f"<b>👥 Users: {count}</b>\n\n"+"\n".join(lines),
            parse_mode="html")

    @app.on_message(filters.command("stats") & af)
    async def cmd_stats(_, msg: Message):
        st    = await db.upload_stats()
        users = await db.user_count()
        chs   = await db.get_channels()
        trs   = await db.get_tracks()
        await msg.reply(
            f"<b>📊 Statistics</b>\n\n"
            f"👥 Users: <b>{users}</b>\n"
            f"📢 Channels: <b>{len(chs)}</b>\n"
            f"📤 Total uploads: <b>{st['total']}</b>\n"
            f"📅 Today: <b>{st['today']}</b>\n"
            f"🔄 Tracked: <b>{len(trs)}</b>",
            parse_mode="html")

    @app.on_message(filters.command("tracklist") & af)
    async def cmd_tracklist(_, msg: Message):
        trs = await db.get_tracks()
        if not trs:
            await msg.reply("Nothing tracked."); return
        lines = [f"• <b>{t['name']}</b> S{t.get('season',1):02d} (last:{t.get('last_ep',0)})"
                 for t in trs]
        await msg.reply(
            f"<b>🔄 Tracked ({len(trs)})</b>\n\n"+"\n".join(lines),
            parse_mode="html")

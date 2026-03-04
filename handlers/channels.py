import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
_adding: set = set()

def _af(db):
    async def f(_,__,m): return await db.is_admin(m.from_user.id)
    return filters.create(f)

def register(app: Client, db):
    af = _af(db)

    @app.on_message(filters.command("add_channel") & af)
    async def add_channel(_, msg: Message):
        _adding.add(msg.from_user.id)
        await msg.reply(
            "📢 <b>Add Channel Steps:</b>\n\n"
            "1. Add me as admin with 'Post Messages' permission\n"
            "2. Forward any message FROM that channel here\n\n"
            "/cancel to abort.", parse_mode="html")

    @app.on_message(filters.command("cancel") & af)
    async def cancel(_, msg: Message):
        _adding.discard(msg.from_user.id)
        await msg.reply("✅ Cancelled.")

    @app.on_message(filters.forwarded & af)
    async def handle_fwd(_, msg: Message):
        uid = msg.from_user.id
        if uid not in _adding: return
        _adding.discard(uid)
        origin = msg.forward_origin
        if not origin or not hasattr(origin,"chat"):
            await msg.reply("❌ Forward a message FROM a channel (not a user)."); return
        chat  = origin.chat
        cid   = chat.id
        name  = chat.title or "?"
        uname = chat.username
        try:
            t = await app.send_message(cid, "✅ Channel linked to KenshinAnime Bot!")
            await t.delete()
        except Exception as e:
            await msg.reply(
                f"❌ Can't post! Make sure I'm admin.\nError: <code>{e}</code>",
                parse_mode="html"); return
        await db.add_channel(cid, name, uname)
        await msg.reply(
            f"✅ <b>Added!</b>\n📢 {name}\n<code>{cid}</code>"
            +(f"\n@{uname}" if uname else ""), parse_mode="html")

    @app.on_message(filters.command("list_channels") & af)
    async def list_channels(_, msg: Message):
        chs = await db.get_channels()
        if not chs:
            await msg.reply("No channels. Use /add_channel"); return
        lines=[]
        for i,c in enumerate(chs,1):
            un = f"@{c['username']}" if c.get("username") else "private"
            lines.append(f"{i}. <b>{c['name']}</b> {un}\n   <code>{c['cid']}</code>")
        await msg.reply(
            f"<b>📢 Channels ({len(chs)})</b>\n\n"+"\n\n".join(lines),
            parse_mode="html")

    @app.on_message(filters.command("remove_channel") & af)
    async def rm_channel(_, msg: Message):
        chs = await db.get_channels()
        if not chs:
            await msg.reply("No channels."); return
        btns = [[InlineKeyboardButton(
            f"🗑 {c.get('username') or c['name']}",
            callback_data=f"rmch:{c['cid']}")] for c in chs]
        await msg.reply("Select channel to remove:",
            reply_markup=InlineKeyboardMarkup(btns))

    @app.on_callback_query(filters.regex(r"^rmch:\-?\d+$"))
    async def cb_rm(_, cq):
        if not await db.is_admin(cq.from_user.id):
            await cq.answer("Access denied.", show_alert=True); return
        cid = int(cq.data.split(":")[1])
        await db.remove_channel(cid)
        await cq.message.edit(f"✅ Channel <code>{cid}</code> removed.", parse_mode="html")

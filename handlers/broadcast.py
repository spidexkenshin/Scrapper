import asyncio, logging
from pyrogram import Client, filters
from pyrogram.types import Message

logger = logging.getLogger(__name__)
_waiting: set = set()

def _af(db):
    async def f(_,__,m): return await db.is_admin(m.from_user.id)
    return filters.create(f)

def register(app: Client, db):
    af = _af(db)

    @app.on_message(filters.command("broadcast") & af)
    async def cmd_bc(_, msg: Message):
        _waiting.add(msg.from_user.id)
        await msg.reply(
            "📣 <b>Broadcast</b>\nSend your message/media now.\n/cancel_bc to abort.",
            parse_mode="html")

    @app.on_message(filters.command("cancel_bc") & af)
    async def cancel_bc(_, msg: Message):
        _waiting.discard(msg.from_user.id)
        await msg.reply("✅ Cancelled.")

    @app.on_message(filters.private & af & ~filters.command(""))
    async def bc_handler(_, msg: Message):
        uid = msg.from_user.id
        if uid not in _waiting: return
        _waiting.discard(uid)
        users = await db.get_all_users()
        ok=0; fail=0
        status = await msg.reply(f"📣 Broadcasting to {len(users)} users…")
        for u in users:
            try:
                await msg.copy(u["uid"]); ok+=1
            except: fail+=1
            if (ok+fail)%20==0:
                try: await status.edit(f"📣 {ok}✅ {fail}❌ / {len(users)}")
                except: pass
            await asyncio.sleep(0.05)
        await status.edit(
            f"<b>📣 Done!</b>\n✅ {ok} | ❌ {fail} | 📊 {len(users)}",
            parse_mode="html")

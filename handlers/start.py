from pyrogram import Client, filters
from pyrogram.types import Message

HELP = """<b>🎌 KenshinAnime Bot — Commands</b>

<b>━━ Search & Upload ━━</b>
/anime <code>&lt;name&gt;</code>   — Search anime (Hindi Dub priority)
/movie <code>&lt;name&gt;</code>   — Search movies
/series <code>&lt;name&gt;</code>  — Search web series
/upload <code>&lt;name&gt;</code>  — Manual upload flow

<b>━━ Queue ━━</b>
/queue — View upload queue status

<b>━━ Channels ━━</b>
/add_channel    — Add target channel
/list_channels  — List channels
/remove_channel — Remove channel
/set_storage <code>&lt;id&gt;</code> — Set storage group

<b>━━ Caption & Style ━━</b>
/set_caption    — Set custom caption
/show_caption   — View current caption
/reset_caption  — Reset to default
/set_thumbnail  — Set default thumbnail
/clear_thumbnail
/set_sticker    — Set episode sticker
/clear_sticker
/set_prefix <code>&lt;text&gt;</code> — Set file rename prefix

<b>━━ Admins ━━</b>
/add_admin <code>&lt;id&gt;</code>
/remove_admin <code>&lt;id&gt;</code>
/admins

<b>━━ Stats ━━</b>
/users  — User count & list
/stats  — Upload statistics
/broadcast — Broadcast to all users

<b>━━ Auto-Track ━━</b>
/track <code>&lt;name&gt;</code> — Track anime for new episodes
/tracklist      — List tracked anime
/untrack        — Remove tracking

<b>━━ Caption Variables ━━</b>
<code>{anime_name} {season} {episode} {audio} {quality}</code>
"""

def register(app: Client, db):
    @app.on_message(filters.command("start") & filters.private)
    async def cmd_start(_, msg: Message):
        await db.add_user(msg.from_user.id,
                          msg.from_user.username,
                          msg.from_user.first_name)
        if not await db.is_admin(msg.from_user.id):
            await msg.reply("🚫 <b>Admin only bot.</b>", parse_mode="html")
            return
        await msg.reply(
            "<b>🎌 KenshinAnime Bot v3.0</b>\n\n"
            "Multi-source anime upload bot.\n"
            "Sources: AnimeSalt | AnimeWorld | AniList\n\n"
            "Use /help for commands.", parse_mode="html")

    @app.on_message(filters.command("help"))
    async def cmd_help(_, msg: Message):
        if not await db.is_admin(msg.from_user.id): return
        await msg.reply(HELP, parse_mode="html")

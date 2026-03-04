import asyncio, logging, sys
from pyrogram import Client, idle
from config import Config
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

db  = Database(Config.MONGO_URI)
app = Client(
    "KenshinAnimeBot",
    api_id    = Config.API_ID,
    api_hash  = Config.API_HASH,
    bot_token = Config.BOT_TOKEN,
    workers   = 10,
)

async def main():
    await db.connect()
    logger.info("✅ DB connected")

    from queue_manager import QueueManager
    from auto_track    import AutoTracker
    from handlers      import register_all

    qmgr    = QueueManager(app, db)
    tracker = AutoTracker(app, db)

    register_all(app, db, qmgr)
    logger.info("✅ Handlers registered")

    await app.start()
    me = await app.get_me()
    logger.info(f"✅ Bot started: @{me.username}")

    asyncio.create_task(qmgr.run())
    asyncio.create_task(tracker.start())

    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())

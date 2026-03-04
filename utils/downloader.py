import aiohttp, aiofiles, os, logging
from config import Config

logger = logging.getLogger(__name__)
DL_DIR = "/tmp/kenshin"
os.makedirs(DL_DIR, exist_ok=True)

async def download_url(url: str, dest: str,
                       progress_cb=None) -> str:
    """Download file from URL to dest path with optional progress callback."""
    async with aiohttp.ClientSession(headers=Config.HEADERS) as sess:
        async with sess.get(url, timeout=aiohttp.ClientTimeout(total=3600)) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            done  = 0
            async with aiofiles.open(dest, "wb") as f:
                async for chunk in r.content.iter_chunked(1024*256):
                    await f.write(chunk)
                    done += len(chunk)
                    if progress_cb and total:
                        await progress_cb(done, total)
    return dest

async def download_thumb(url: str, name: str) -> str:
    path = os.path.join(DL_DIR, name)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    async with aiofiles.open(path,"wb") as f:
                        await f.write(await r.read())
                    return path
    except Exception as e:
        logger.warning(f"thumb dl fail: {e}")
    return ""

def cleanup(*paths):
    for p in paths:
        if p and os.path.exists(p):
            try: os.remove(p)
            except: pass

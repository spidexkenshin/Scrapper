import asyncio, logging
import aiohttp
from bs4 import BeautifulSoup
from config import Config

logger = logging.getLogger(__name__)
_session = None

async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300, ssl=False)
        _session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=20, connect=8),
            headers=Config.HEADERS
        )
    return _session

async def fetch(url: str, params: dict = None, retries: int = 3) -> str:
    session = await get_session()
    for i in range(retries):
        try:
            async with session.get(url, params=params) as r:
                r.raise_for_status()
                return await r.text()
        except Exception as e:
            if i == retries - 1:
                logger.warning(f"fetch failed [{url}]: {e}")
                return ""
            await asyncio.sleep(1.5 ** i)
    return ""

def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")

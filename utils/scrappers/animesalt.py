"""
animesalt.top scraper
Typical WordPress anime site using ?s= search and /anime/ slugs.
Multi-selector fallbacks for robustness.
"""
import re, logging
from typing import List, Dict, Optional
from .base import fetch, soup
from config import Config

logger = logging.getLogger(__name__)
BASE = Config.ANIMESALT_URL
SOURCE = "animesalt"

# ── Search ────────────────────────────────────────────────────
async def search(query: str, category: str = "anime") -> List[Dict]:
    """Search animesalt. category: anime | movie | series"""
    html = await fetch(BASE, params={"s": query})
    if not html:
        return []
    bs = soup(html)
    results = []

    # Try common anime-site article card selectors
    cards = (
        bs.select("article.animpost") or
        bs.select("article.bs") or
        bs.select(".film_list-wrap .flw-item") or
        bs.select("div.animpost") or
        bs.select(".listupd article") or
        bs.select("article")[:12]
    )

    for card in cards[:12]:
        try:
            # Title
            title_el = (
                card.select_one("div.tt, h2.title, h3.title, .ntitle, a[title]")
            )
            title = (title_el.get_text(strip=True) if title_el
                     else card.select_one("a")["title"] if card.select_one("a") else "")

            # URL
            link_el = card.select_one("a[href]")
            url = link_el["href"] if link_el else ""

            # Thumb
            img_el = card.select_one("img")
            thumb = (img_el.get("data-src") or img_el.get("src", "")) if img_el else ""

            # Type detection
            ctype = _detect_type(card, url, title)

            # Filter by category
            if category != "all" and ctype != category:
                continue

            if title and url:
                results.append({
                    "source":   SOURCE,
                    "title":    title.strip(),
                    "url":      url,
                    "thumb":    thumb,
                    "type":     ctype,
                    "slug":     _slug(url),
                })
        except Exception as e:
            logger.debug(f"card parse error: {e}")
            continue

    return results

def _detect_type(card, url: str, title: str) -> str:
    text = (card.get_text() + url + title).lower()
    if any(w in text for w in ["movie", "film"]):
        return "movie"
    if any(w in text for w in ["series", "web series", "webseries", "live action"]):
        return "series"
    return "anime"

def _slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1]

# ── Detail page ───────────────────────────────────────────────
async def get_detail(url: str) -> Optional[Dict]:
    html = await fetch(url)
    if not html:
        return None
    bs = soup(html)

    title = _text(bs, "h1.entry-title, h1.titlani, .infox h1, h1")
    thumb_el = bs.select_one(".thumb img, .poster img, .entry-thumb img")
    thumb = (thumb_el.get("data-src") or thumb_el.get("src","")) if thumb_el else ""
    desc  = _text(bs, ".entry-content p, .synops p, .desc")

    # Languages available
    langs = _extract_langs(bs)

    # Seasons & episodes
    seasons = _extract_seasons(bs, url)

    return {
        "source": SOURCE,
        "title":  title,
        "thumb":  thumb,
        "desc":   desc[:200] if desc else "",
        "langs":  langs,
        "seasons": seasons,
        "url":    url,
        "slug":   _slug(url),
    }

def _text(bs, selectors: str) -> str:
    for sel in selectors.split(","):
        el = bs.select_one(sel.strip())
        if el:
            return el.get_text(strip=True)
    return ""

def _extract_langs(bs) -> List[str]:
    langs = []
    text = bs.get_text().lower()
    mapping = [
        ("hindi", "Hindi Dub"),
        ("english", "English Dub"),
        ("japanese", "Japanese Sub"),
        ("multi", "Multi-Audio"),
        ("tamil", "Tamil Dub"),
        ("telugu", "Telugu Dub"),
    ]
    for key, label in mapping:
        if key in text:
            langs.append(label)
    # Hindi first (preferred)
    if "Hindi Dub" in langs:
        langs.remove("Hindi Dub")
        langs.insert(0, "Hindi Dub")
    return langs or ["Hindi Dub", "English Dub"]

def _extract_seasons(bs, base_url: str) -> List[Dict]:
    """Extract season list with episode links."""
    seasons = []

    # Try season tabs / lists
    season_blocks = (
        bs.select(".season-list li, .bixbox.bxcl, .bixbox ul li") or
        bs.select("div[id*='season']") or
        bs.select(".tab-content .tab-pane")
    )

    if season_blocks:
        for i, block in enumerate(season_blocks, 1):
            eps = _extract_eps_from_block(block)
            s_title = _text_el(block, ".ts-main-side, span, a") or f"Season {i}"
            seasons.append({"num": i, "title": s_title,
                            "episodes": eps, "ep_count": len(eps)})
    else:
        # Single season — extract all episode links from page
        eps = _extract_all_eps(bs, base_url)
        seasons.append({"num": 1, "title": "Season 1",
                        "episodes": eps, "ep_count": len(eps)})

    return seasons

def _extract_eps_from_block(block) -> List[Dict]:
    eps = []
    for a in block.select("a[href]"):
        href = a.get("href","")
        text = a.get_text(strip=True)
        num  = _ep_num(text, href)
        if href:
            eps.append({"num": num, "title": text, "url": href})
    return eps

def _extract_all_eps(bs, base_url: str) -> List[Dict]:
    eps = []
    seen = set()
    # Look for episode links
    for a in bs.select("a[href]"):
        href = a.get("href","")
        text = a.get_text(strip=True)
        if (base_url.split("/")[-2] in href or "episode" in href.lower()
                or re.search(r"ep[-\s]?\d+", href.lower())):
            if href not in seen:
                seen.add(href)
                num = _ep_num(text, href)
                eps.append({"num": num, "title": text or f"Episode {num}", "url": href})
    eps.sort(key=lambda x: x["num"])
    return eps

def _ep_num(text: str, url: str) -> int:
    for s in [text, url]:
        m = re.search(r"(?:episode|ep|e)[-\s]?(\d+)", s.lower())
        if m:
            return int(m.group(1))
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0

def _text_el(el, selectors: str) -> str:
    for s in selectors.split(","):
        found = el.select_one(s.strip())
        if found:
            return found.get_text(strip=True)
    return el.get_text(strip=True)[:30]

# ── Episode stream page ───────────────────────────────────────
async def get_streams(ep_url: str) -> List[Dict]:
    """Get stream URLs from an episode page."""
    html = await fetch(ep_url)
    if not html:
        return []
    bs = soup(html)
    streams = []

    # Look for quality buttons / server tabs
    quality_map = {"1080": "1080p", "720": "720p", "480": "480p",
                   "360": "360p", "hd": "720p", "sd": "480p"}

    for btn in bs.select("a[data-src], a.mirror_link, .server-item a, .btn-quality a"):
        label  = btn.get_text(strip=True).lower()
        src    = btn.get("data-src","") or btn.get("href","")
        q_key  = next((k for k in quality_map if k in label), None)
        quality= quality_map.get(q_key, label or "720p")
        if src:
            streams.append({"quality": quality, "url": src})

    # iframes
    for iframe in bs.select("iframe[src]"):
        streams.append({"quality": "720p", "url": iframe["src"]})

    # Deduplicate by quality
    seen = set()
    deduped = []
    for s in streams:
        if s["quality"] not in seen:
            seen.add(s["quality"])
            deduped.append(s)

    # Sort 480p → 1080p
    order = ["480p","720p","1080p","1080p HDR","4K"]
    deduped.sort(key=lambda x: order.index(x["quality"]) if x["quality"] in order else 99)
    return deduped

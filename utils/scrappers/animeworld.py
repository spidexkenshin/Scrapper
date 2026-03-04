"""
watchanimeworld.net scraper
Similar WP-anime structure, robust multi-selector approach.
"""
import re, logging
from typing import List, Dict, Optional
from .base import fetch, soup
from config import Config

logger = logging.getLogger(__name__)
BASE   = Config.ANIMEWORLD_URL
SOURCE = "animeworld"

async def search(query: str, category: str = "anime") -> List[Dict]:
    # Try search page first
    html = await fetch(f"{BASE}/?s={query.replace(' ','+')}")
    if not html:
        html = await fetch(BASE, params={"s": query})
    if not html:
        return []

    bs  = soup(html)
    results = []
    cards = (
        bs.select("article.animpost, article.bs, .listupd article") or
        bs.select("div.bs, div.bsx") or
        bs.select("article")[:12]
    )

    for card in cards[:12]:
        try:
            title_el = card.select_one("div.tt h2, h2, h3, .ntitle, a[title]")
            title = (title_el.get_text(strip=True) if title_el
                     else (card.select_one("a") or {}).get("title",""))

            link_el = card.select_one("a[href]")
            url = link_el["href"] if link_el else ""

            img_el = card.select_one("img")
            thumb = (img_el.get("data-src") or img_el.get("src","")) if img_el else ""

            ctype = _detect_type(card, url, title)
            if category != "all" and ctype != category:
                continue

            if title and url:
                results.append({
                    "source": SOURCE,
                    "title":  title.strip(),
                    "url":    url,
                    "thumb":  thumb,
                    "type":   ctype,
                    "slug":   _slug(url),
                })
        except Exception as e:
            logger.debug(f"card error: {e}")

    return results

def _detect_type(card, url, title) -> str:
    text = (card.get_text() + url + title).lower()
    if any(w in text for w in ["movie","film"]):
        return "movie"
    if any(w in text for w in ["series","webseries","web-series","live action"]):
        return "series"
    return "anime"

def _slug(url):
    return url.rstrip("/").split("/")[-1]

async def get_detail(url: str) -> Optional[Dict]:
    html = await fetch(url)
    if not html:
        return None
    bs = soup(html)

    title = _text(bs, "h1.entry-title, h1.titlani, .infox h1, h1")
    img = bs.select_one(".thumb img, .poster img, img.lazy")
    thumb = (img.get("data-src") or img.get("src","")) if img else ""
    langs   = _extract_langs(bs)
    seasons = _extract_seasons(bs, url)

    return {
        "source":  SOURCE,
        "title":   title,
        "thumb":   thumb,
        "langs":   langs,
        "seasons": seasons,
        "url":     url,
        "slug":    _slug(url),
    }

def _text(bs, selectors):
    for sel in selectors.split(","):
        el = bs.select_one(sel.strip())
        if el: return el.get_text(strip=True)
    return ""

def _extract_langs(bs) -> List[str]:
    text = bs.get_text().lower()
    candidates = [
        ("hindi","Hindi Dub"),
        ("english","English Dub"),
        ("japanese","Japanese Sub"),
        ("multi","Multi-Audio"),
        ("tamil","Tamil Dub"),
        ("telugu","Telugu Dub"),
    ]
    found = [label for key,label in candidates if key in text]
    # Hindi first
    if "Hindi Dub" in found:
        found.remove("Hindi Dub"); found.insert(0,"Hindi Dub")
    return found or ["Hindi Dub","English Dub"]

def _extract_seasons(bs, base_url) -> List[Dict]:
    seasons = []
    season_blocks = (
        bs.select(".season-list li, .bixbox.bxcl li, #seasons-list li") or
        bs.select("div[id*='season'], div[class*='season']")
    )
    if season_blocks:
        for i, blk in enumerate(season_blocks,1):
            eps = [{"num": _ep_num(a.get_text()+" "+a["href"],a["href"]),
                    "title": a.get_text(strip=True),
                    "url":   a["href"]}
                   for a in blk.select("a[href]") if a.get("href")]
            seasons.append({"num":i,"title":f"Season {i}",
                            "episodes":eps,"ep_count":len(eps)})
    else:
        eps = []
        seen = set()
        for a in bs.select("a[href]"):
            href = a.get("href","")
            if (re.search(r"ep(?:isode)?[-\s]?\d+", href.lower()) or
                    re.search(r"ep(?:isode)?[-\s]?\d+", a.get_text().lower())):
                if href not in seen:
                    seen.add(href)
                    num = _ep_num(a.get_text()+" "+href, href)
                    eps.append({"num":num,"title":a.get_text(strip=True) or f"Ep {num}","url":href})
        eps.sort(key=lambda x: x["num"])
        seasons.append({"num":1,"title":"Season 1","episodes":eps,"ep_count":len(eps)})
    return seasons

def _ep_num(text, url="") -> int:
    for s in [text, url]:
        m = re.search(r"(?:episode|ep|e)[-\s]?(\d+)", s.lower())
        if m: return int(m.group(1))
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0

async def get_streams(ep_url: str) -> List[Dict]:
    html = await fetch(ep_url)
    if not html: return []
    bs = soup(html)
    streams = []
    quality_map = {"1080":"1080p","720":"720p","480":"480p","360":"360p","hd":"720p","sd":"480p"}

    for btn in bs.select("a[data-src], .mirror_link a, .btn-quality a, .server-item a, .moblink a"):
        label = btn.get_text(strip=True).lower()
        src   = btn.get("data-src","") or btn.get("href","")
        qkey  = next((k for k in quality_map if k in label), None)
        q     = quality_map.get(qkey, "720p")
        if src and src.startswith("http"):
            streams.append({"quality":q,"url":src})

    for iframe in bs.select("iframe[src]"):
        src = iframe["src"]
        if src.startswith("http"):
            streams.append({"quality":"720p","url":src})

    # deduplicate
    seen = set(); out = []
    for s in streams:
        if s["quality"] not in seen:
            seen.add(s["quality"]); out.append(s)

    order = ["480p","720p","1080p","4K"]
    out.sort(key=lambda x: order.index(x["quality"]) if x["quality"] in order else 5)
    return out

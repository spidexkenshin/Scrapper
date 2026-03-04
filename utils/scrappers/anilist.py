"""AniList GraphQL API — metadata + auto-track"""
import aiohttp, logging
from typing import List, Dict, Optional
from .base import get_session

logger = logging.getLogger(__name__)
URL = "https://graphql.anilist.co"
SOURCE = "anilist"

_SEARCH_Q = """
query($q:String,$type:MediaType){
  Page(perPage:8){
    media(search:$q,type:$type,sort:SEARCH_MATCH){
      id title{romaji english} episodes status seasonYear
      genres averageScore coverImage{large}
      nextAiringEpisode{episode airingAt}
    }
  }
}"""

_DETAIL_Q = """
query($id:Int){
  Media(id:$id,type:ANIME){
    id title{romaji english} episodes status seasonYear
    coverImage{large} nextAiringEpisode{episode airingAt}
    relations{edges{relationType node{id title{romaji english} type episodes seasonYear}}}
  }
}"""

async def _gql(query,variables):
    try:
        session = await get_session()
        async with session.post(URL,
            json={"query":query,"variables":variables},
            headers={"Content-Type":"application/json"},
            timeout=aiohttp.ClientTimeout(total=15)) as r:
            return await r.json()
    except Exception as e:
        logger.error(f"AniList error: {e}")
        return None

def _t(m): return m["title"]["english"] or m["title"]["romaji"]

async def search(query:str, media_type:str="ANIME") -> List[Dict]:
    data = await _gql(_SEARCH_Q,{"q":query,"type":media_type})
    if not data: return []
    results = []
    for m in data.get("data",{}).get("Page",{}).get("media",[]):
        results.append({
            "source": SOURCE,
            "id":     m["id"],
            "title":  _t(m),
            "year":   m.get("seasonYear"),
            "eps":    m.get("episodes") or "?",
            "status": m.get("status",""),
            "thumb":  m.get("coverImage",{}).get("large",""),
            "score":  m.get("averageScore"),
            "next":   m.get("nextAiringEpisode"),
            "type":   "anime",
        })
    return results

async def get_detail(anime_id:int) -> Optional[Dict]:
    data = await _gql(_DETAIL_Q,{"id":anime_id})
    if not data: return None
    m = data.get("data",{}).get("Media")
    if not m: return None

    seasons=[{"id":m["id"],"num":1,"title":_t(m),"episodes":m.get("episodes") or 0}]
    n=2
    for edge in m.get("relations",{}).get("edges",[]):
        if edge["relationType"]=="SEQUEL" and edge["node"]["type"]=="ANIME":
            nd=edge["node"]
            seasons.append({"id":nd["id"],"num":n,"title":_t(nd),"episodes":nd.get("episodes") or 0})
            n+=1

    return {
        "source":  SOURCE,
        "id":      m["id"],
        "title":   _t(m),
        "thumb":   m.get("coverImage",{}).get("large",""),
        "episodes":m.get("episodes") or 0,
        "status":  m.get("status",""),
        "next":    m.get("nextAiringEpisode"),
        "seasons": seasons,
    }

"""
Multi-source aggregator.
Searches all sources in parallel, deduplicates, ranks results.
Hindi Dub results get priority boost.
"""
import asyncio, logging
from typing import List, Dict
from . import animesalt, animeworld, anilist

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "anime":  "anime",
    "movie":  "movie",
    "series": "series",
    "all":    "all",
}

async def multi_search(query: str, category: str = "anime") -> List[Dict]:
    """
    Search all sources simultaneously.
    Returns merged + deduplicated list.
    Each result has a `sources` list showing where it was found.
    """
    tasks = [
        animesalt.search(query, category),
        animeworld.search(query, category),
    ]
    # For anime category, also hit AniList for metadata
    if category in ("anime", "all"):
        tasks.append(anilist.search(query))

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results, group by normalized title
    merged: Dict[str, Dict] = {}
    for result_list in all_results:
        if isinstance(result_list, Exception):
            logger.warning(f"Source failed: {result_list}")
            continue
        for item in result_list:
            key = _normalize(item["title"])
            if key not in merged:
                merged[key] = {**item, "sources": [item["source"]]}
            else:
                # Add this source to existing entry
                if item["source"] not in merged[key]["sources"]:
                    merged[key]["sources"].append(item["source"])
                # Prefer AniList thumb
                if item["source"] == "anilist" and item.get("thumb"):
                    merged[key]["thumb"] = item["thumb"]
                # Store per-source URL
                merged[key][f"{item['source']}_url"] = item.get("url","")

    results = list(merged.values())

    # Sort: hindi dub mentions first, then by source count
    results.sort(key=lambda x: (
        -_hindi_score(x["title"]),
        -len(x.get("sources",[])),
    ))

    return results[:10]

def _normalize(title: str) -> str:
    return title.lower().strip().replace("-"," ").replace("_"," ")

def _hindi_score(title: str) -> int:
    t = title.lower()
    return 2 if "hindi" in t else (1 if "dub" in t else 0)

def source_label(sources: List[str]) -> str:
    """Human readable source badges."""
    labels = {
        "animesalt":  "🌊 AnimeSalt",
        "animeworld": "🌍 AnimeWorld",
        "anilist":    "📋 AniList",
    }
    return " | ".join(labels.get(s, s) for s in sources)

"""
News/web mention connector.

Broadens "mentions" beyond social platforms to news, blogs, and forums --
the same category of source Mention.com/Google Alerts draw on. Written
against NewsAPI's schema (https://newsapi.org, free dev tier available);
swap the base_url/params if you use a different provider (GDELT, Bing
News Search, etc.) -- the normalized output shape stays the same.
"""
import logging
from typing import List, Dict, Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://newsapi.org/v2/everything"


def _is_configured() -> bool:
    if not settings.news_api_key:
        logger.warning("NEWS_API_KEY not set -- skipping news/web mention connector.")
        return False
    return True


def search_mentions(query: str, page_size: int = 50) -> List[Dict[str, Any]]:
    if not _is_configured():
        return []

    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": min(page_size, 100),
        "language": "en",
        "apiKey": settings.news_api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=20)
    if resp.status_code != 200:
        logger.error("News search failed [%s]: %s", resp.status_code, resp.text[:300])
        return []

    results = []
    for a in resp.json().get("articles", []):
        results.append({
            "platform": "news",
            "author": a.get("source", {}).get("name"),
            "url": a.get("url"),
            "text": f"{a.get('title', '')} -- {a.get('description', '')}".strip(" -"),
            "published_at": a.get("publishedAt"),
            "raw": a,
        })
    return results

"""
X (Twitter) API v2 connector.

Uses App-Only Bearer auth (read-only, public data). As of 2026 X runs
pay-per-use pricing with no free tier -- budget roughly $5 per 1,000 posts
read, and note recent search only covers the last 7 days on self-serve
access (full-archive requires an Enterprise contract). That's still
enough for day-to-day mention + competitor-posting-cadence tracking.

Docs: https://developer.x.com/en/docs/x-api
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.x.com/2"


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {settings.x_bearer_token}"}


def _is_configured() -> bool:
    if not settings.x_bearer_token:
        logger.warning("X_BEARER_TOKEN not set -- skipping X/Twitter connector.")
        return False
    return True


def search_recent_mentions(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """
    Search public posts from the last 7 days matching `query`
    (e.g. '"Acme Shoes" OR @acmeshoes -is:retweet').
    Returns a list of normalized mention dicts.
    """
    if not _is_configured():
        return []

    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,public_metrics,author_id,lang",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    resp = requests.get(f"{BASE_URL}/tweets/search/recent", headers=_headers(), params=params, timeout=20)
    if resp.status_code != 200:
        logger.error("X search failed [%s]: %s", resp.status_code, resp.text[:300])
        return []

    payload = resp.json()
    tweets = payload.get("data", [])
    users_by_id = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}

    results = []
    for t in tweets:
        author = users_by_id.get(t.get("author_id"), {})
        results.append({
            "platform": "twitter",
            "external_id": t["id"],
            "url": f"https://x.com/{author.get('username', 'i')}/status/{t['id']}",
            "author": author.get("username"),
            "text": t.get("text"),
            "published_at": t.get("created_at"),
            "metrics": t.get("public_metrics", {}),
            "raw": t,
        })
    return results


def get_competitor_recent_posts(handle: str, max_results: int = 25) -> List[Dict[str, Any]]:
    """
    Pull a competitor's own recent posts (their timeline) to analyze
    content type, posting cadence, and engagement.
    """
    if not _is_configured():
        return []

    # First resolve handle -> user id
    user_resp = requests.get(
        f"{BASE_URL}/users/by/username/{handle}",
        headers=_headers(),
        timeout=20,
    )
    if user_resp.status_code != 200:
        logger.error("X user lookup failed for @%s [%s]: %s", handle, user_resp.status_code, user_resp.text[:300])
        return []
    user_id = user_resp.json().get("data", {}).get("id")
    if not user_id:
        return []

    params = {
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,public_metrics,attachments",
        "exclude": "retweets,replies",
    }
    resp = requests.get(f"{BASE_URL}/users/{user_id}/tweets", headers=_headers(), params=params, timeout=20)
    if resp.status_code != 200:
        logger.error("X timeline fetch failed for @%s [%s]: %s", handle, resp.status_code, resp.text[:300])
        return []

    posts = []
    for t in resp.json().get("data", []):
        metrics = t.get("public_metrics", {})
        has_media = "attachments" in t
        posts.append({
            "platform": "twitter",
            "external_id": t["id"],
            "url": f"https://x.com/{handle}/status/{t['id']}",
            "caption": t.get("text"),
            "content_type": "image_or_video" if has_media else "text",
            "posted_at": t.get("created_at"),
            "likes": metrics.get("like_count", 0),
            "comments": metrics.get("reply_count", 0),
            "shares": metrics.get("retweet_count", 0),
            "views": metrics.get("impression_count"),
            "raw": t,
        })
    return posts

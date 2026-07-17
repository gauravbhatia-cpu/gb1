"""
Facebook/Instagram oEmbed connector.

There is no compliant, automated way to discover a competitor's full
organic feed (see README "Platform Access Reality"). What IS compliant
and requires no login/scraping: given a specific PUBLIC post URL (which
a human on your team copies from the competitor's profile -- a 5-second
manual step), Meta's oEmbed endpoints return real metadata about that
post with no App Review needed.

This turns "fully automated feed crawling" (not available) into
"paste a link, get structured data" (available today). Wire this into
a Slack command, a Chrome extension, or a simple form -- whatever fits
your team's workflow -- to make the manual step painless.

Docs:
  https://developers.facebook.com/docs/plugins/oembed
  https://developers.facebook.com/docs/instagram/oembed
"""
import logging
from typing import Dict, Any, Optional

import requests

from app.config import settings

logger = logging.getLogger(__name__)

FB_OEMBED_URL = "https://graph.facebook.com/v21.0/oembed_post"
IG_OEMBED_URL = "https://graph.facebook.com/v21.0/instagram_oembed"


def _is_configured() -> bool:
    if not settings.meta_access_token:
        logger.warning("META_ACCESS_TOKEN not set -- oEmbed lookups require a Meta app token too.")
        return False
    return True


def fetch_facebook_post(post_url: str) -> Optional[Dict[str, Any]]:
    if not _is_configured():
        return None
    params = {"url": post_url, "access_token": settings.meta_access_token}
    resp = requests.get(FB_OEMBED_URL, params=params, timeout=15)
    if resp.status_code != 200:
        logger.error("FB oEmbed failed for %s [%s]: %s", post_url, resp.status_code, resp.text[:300])
        return None
    data = resp.json()
    return {
        "platform": "facebook",
        "url": post_url,
        "author": data.get("author_name"),
        "html_embed": data.get("html"),
        "width": data.get("width"),
        "raw": data,
        # oEmbed doesn't return like/comment counts -- pair this with a
        # human glance at the post, or a licensed data vendor, for metrics.
    }


def fetch_instagram_post(post_url: str) -> Optional[Dict[str, Any]]:
    if not _is_configured():
        return None
    params = {"url": post_url, "access_token": settings.meta_access_token}
    resp = requests.get(IG_OEMBED_URL, params=params, timeout=15)
    if resp.status_code != 200:
        logger.error("IG oEmbed failed for %s [%s]: %s", post_url, resp.status_code, resp.text[:300])
        return None
    data = resp.json()
    return {
        "platform": "instagram",
        "url": post_url,
        "author": data.get("author_name"),
        "html_embed": data.get("html"),
        "width": data.get("width"),
        "raw": data,
    }

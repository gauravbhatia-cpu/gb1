"""
Meta Ad Library API connector.

This is the ONE fully official, public, non-App-Review-gated way to see
what competitors are running on Facebook/Instagram: the ads_archive
endpoint that Meta operates for ad-transparency compliance (Honest Ads
Act / EU DSA). It does NOT cover organic (unpaid) posts -- Meta's Graph
API restricts organic content to accounts you manage, full stop. If you
need organic competitor content, see oembed_connector.py for the
compliant (manual-import) path, or the README for licensed-data-vendor
options.

Docs: https://developers.facebook.com/docs/marketing-api/reference/ad-library/
"""
import logging
from typing import List, Dict, Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.facebook.com/v21.0/ads_archive"


def _is_configured() -> bool:
    if not settings.meta_access_token:
        logger.warning("META_ACCESS_TOKEN not set -- skipping Meta Ad Library connector.")
        return False
    return True


def get_active_ads(page_name_or_keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search the public Ad Library for a competitor's page name or a keyword
    (e.g. their brand name). Returns normalized ad-creative dicts.

    Note on data depth: standard commercial ads return creative text/media
    and active-status/date-range, but NOT spend or audience-demographic
    breakdowns -- that level of detail is only disclosed for political/
    issue ads, per Meta's transparency rules.
    """
    if not _is_configured():
        return []

    params = {
        "search_terms": page_name_or_keyword,
        "ad_reached_countries": f"['{settings.meta_ad_library_country}']",
        "ad_active_status": "ALL",
        "fields": "id,ad_creation_time,ad_creative_bodies,ad_delivery_start_time,"
                  "ad_delivery_stop_time,page_name,publisher_platforms,ad_snapshot_url",
        "limit": min(limit, 100),
        "access_token": settings.meta_access_token,
    }
    resp = requests.get(BASE_URL, params=params, timeout=20)
    if resp.status_code != 200:
        logger.error("Meta Ad Library search failed [%s]: %s", resp.status_code, resp.text[:300])
        return []

    ads = []
    for a in resp.json().get("data", []):
        bodies = a.get("ad_creative_bodies") or []
        ads.append({
            "platform": "meta",
            "ad_archive_id": a.get("id"),
            "page_name": a.get("page_name"),
            "creative_text": bodies[0] if bodies else None,
            "snapshot_url": a.get("ad_snapshot_url"),
            "start_date": a.get("ad_delivery_start_time"),
            "end_date": a.get("ad_delivery_stop_time"),
            "is_active": a.get("ad_delivery_stop_time") is None,
            "publisher_platforms": a.get("publisher_platforms", []),  # e.g. ["facebook","instagram"]
            "raw": a,
        })
    return ads

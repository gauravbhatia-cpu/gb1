"""
Brand search interest ("how much are people searching for this brand").

Uses pytrends, an unofficial wrapper around Google Trends' public,
no-login embeddable data (the same data behind trends.google.com's public
charts -- aggregate, non-personal search-interest scores, not individual
query logs). Because it's unofficial, Google can change the underlying
page and break it without notice; treat this module as "best effort" and
wrap calls in try/except in production, which is already done below.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_search_interest(keywords: List[str], timeframe: str = "today 3-m") -> Dict[str, List[Dict[str, Any]]]:
    """
    keywords: up to 5 brand names/terms to compare (Google Trends limit).
    timeframe: pytrends format, e.g. 'today 3-m', 'today 12-m', 'now 7-d'.

    Returns {keyword: [{"date": datetime, "interest_score": 0-100}, ...]}
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.error("pytrends not installed -- run `pip install pytrends`.")
        return {}

    try:
        pytrends = TrendReq(hl="en-US", tz=0)
        pytrends.build_payload(keywords[:5], timeframe=timeframe)
        df = pytrends.interest_over_time()
    except Exception as e:  # noqa: BLE001 -- Google Trends' unofficial endpoint changes shape often
        logger.error("Google Trends fetch failed: %s", e)
        return {}

    if df is None or df.empty:
        return {}

    result: Dict[str, List[Dict[str, Any]]] = {kw: [] for kw in keywords}
    for idx, row in df.iterrows():
        date = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
        for kw in keywords:
            if kw in row:
                result[kw].append({"date": date, "interest_score": int(row[kw])})
    return result

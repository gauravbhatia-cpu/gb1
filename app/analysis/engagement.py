"""Engagement rate calculations -- how well content performs, not just how much gets posted."""
from typing import List, Dict, Any, Optional


def engagement_rate(post: Dict[str, Any], follower_count: Optional[int] = None) -> Optional[float]:
    """
    Engagement rate as a percentage. Uses follower_count as the
    denominator when available (the standard definition); falls back to
    views when follower count is unknown (common for public competitor
    tracking where you don't have their internal follower-growth data).
    """
    total_engagement = (post.get("likes", 0) or 0) + (post.get("comments", 0) or 0) + (post.get("shares", 0) or 0)
    denominator = follower_count or post.get("views")
    if not denominator:
        return None
    return round(total_engagement / denominator * 100, 3)


def average_engagement(posts: List[Dict[str, Any]], follower_count: Optional[int] = None) -> Optional[float]:
    rates = [r for r in (engagement_rate(p, follower_count) for p in posts) if r is not None]
    if not rates:
        return None
    return round(sum(rates) / len(rates), 3)


def top_performing_posts(posts: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    def total_engagement(p):
        return (p.get("likes", 0) or 0) + (p.get("comments", 0) or 0) + (p.get("shares", 0) or 0)
    return sorted(posts, key=total_engagement, reverse=True)[:n]

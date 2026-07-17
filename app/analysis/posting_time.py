"""
Posting-time pattern analysis: turns a competitor's post history into a
day-of-week x hour-of-day heatmap, plus a plain-English "best times"
summary -- the classic "when does this brand post / when does it get
the most engagement" view.
"""
from collections import defaultdict
from typing import List, Dict, Any

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_posting_heatmap(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    posts: list of dicts with at least `posted_at` (datetime) and
    optionally `likes`/`comments`/`shares` for an engagement-weighted view.

    Returns a 7x24 matrix (day_of_week x hour) of post counts, plus the
    same shape weighted by total engagement, and a ranked "best times".
    """
    count_matrix = [[0] * 24 for _ in range(7)]
    engagement_matrix = [[0] * 24 for _ in range(7)]

    for p in posts:
        dt = p.get("posted_at")
        if dt is None:
            continue
        dow = dt.weekday()
        hour = dt.hour
        count_matrix[dow][hour] += 1
        engagement_matrix[dow][hour] += (p.get("likes", 0) or 0) + (p.get("comments", 0) or 0) + (p.get("shares", 0) or 0)

    # Rank (day, hour) slots by average engagement per post in that slot
    ranked = []
    for dow in range(7):
        for hour in range(24):
            c = count_matrix[dow][hour]
            if c > 0:
                avg_engagement = engagement_matrix[dow][hour] / c
                ranked.append({
                    "day": DAY_NAMES[dow],
                    "hour": hour,
                    "post_count": c,
                    "avg_engagement": round(avg_engagement, 1),
                })
    ranked.sort(key=lambda r: r["avg_engagement"], reverse=True)

    return {
        "count_matrix": count_matrix,
        "engagement_matrix": engagement_matrix,
        "day_labels": DAY_NAMES,
        "hour_labels": list(range(24)),
        "best_slots": ranked[:5],
    }


def posting_frequency_summary(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Simple cadence stats: posts per week, most common content type, etc."""
    if not posts:
        return {"posts_per_week": 0, "top_content_type": None, "total_posts": 0}

    dated = [p for p in posts if p.get("posted_at")]
    if not dated:
        return {"posts_per_week": 0, "top_content_type": None, "total_posts": len(posts)}

    span_days = max((max(p["posted_at"] for p in dated) - min(p["posted_at"] for p in dated)).days, 1)
    posts_per_week = round(len(dated) / span_days * 7, 1)

    type_counts: Dict[str, int] = defaultdict(int)
    for p in posts:
        type_counts[p.get("content_type", "unknown")] += 1
    top_type = max(type_counts.items(), key=lambda kv: kv[1])[0] if type_counts else None

    return {
        "posts_per_week": posts_per_week,
        "top_content_type": top_type,
        "content_type_breakdown": dict(type_counts),
        "total_posts": len(posts),
    }

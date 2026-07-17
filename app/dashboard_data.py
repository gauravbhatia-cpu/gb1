"""Read model data into one compact payload for the browser dashboard."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.analysis import engagement, posting_time


BRAND_COLORS = ["#7cdbb5", "#f5ad72", "#a8a5ff", "#68b8ff", "#ff8fa3"]


def _change(current: float, previous: float) -> float:
    if not previous:
        return 0.0
    return round((current - previous) / previous * 100, 1)


def build_dashboard_payload(db: Session, days: int = 30, competitor_id: int | None = None) -> dict:
    days = max(7, min(days, 90))
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    previous_cutoff = cutoff - timedelta(days=days)

    competitors = db.query(models.Competitor).order_by(models.Competitor.id).all()
    selected = [c for c in competitors if competitor_id is None or c.id == competitor_id]
    selected_ids = [c.id for c in selected]

    database_posts = db.query(models.Post).all()
    database_mentions = db.query(models.Mention).all()
    database_ads = db.query(models.AdCreative).all()
    database_snapshots = db.query(models.BrandSearchSnapshot).all()
    all_posts = [p for p in database_posts if p.competitor_id in selected_ids]
    all_mentions = [m for m in database_mentions if m.competitor_id in selected_ids]
    all_ads = [a for a in database_ads if a.competitor_id in selected_ids]
    all_snapshots = [s for s in database_snapshots if s.competitor_id in selected_ids]

    posts = [p for p in all_posts if p.posted_at and p.posted_at >= cutoff]
    previous_posts = [p for p in all_posts if p.posted_at and previous_cutoff <= p.posted_at < cutoff]
    mentions = [m for m in all_mentions if m.published_at and m.published_at >= cutoff]
    previous_mentions = [m for m in all_mentions if m.published_at and previous_cutoff <= m.published_at < cutoff]
    active_ads = [a for a in all_ads if a.is_active]

    def post_dict(post):
        return {
            "posted_at": post.posted_at,
            "likes": post.likes,
            "comments": post.comments,
            "shares": post.shares,
            "views": post.views,
            "content_type": post.content_type,
        }

    post_dicts = [post_dict(p) for p in posts]
    previous_post_dicts = [post_dict(p) for p in previous_posts]
    avg_engagement = engagement.average_engagement(post_dicts) or 0
    previous_engagement = engagement.average_engagement(previous_post_dicts) or 0

    competitor_rows = []
    by_id = {c.id: c for c in competitors}
    for index, competitor in enumerate(competitors):
        comp_posts = [p for p in database_posts if p.competitor_id == competitor.id and p.posted_at and p.posted_at >= cutoff]
        comp_mentions = [m for m in database_mentions if m.competitor_id == competitor.id and m.published_at and m.published_at >= cutoff]
        comp_ads = [a for a in database_ads if a.competitor_id == competitor.id and a.is_active]
        comp_dicts = [post_dict(p) for p in comp_posts]
        cadence = posting_time.posting_frequency_summary(comp_dicts)
        comp_snapshots = sorted(
            [s for s in database_snapshots if s.competitor_id == competitor.id and s.date >= cutoff],
            key=lambda s: s.date,
        )
        search_change = 0
        if len(comp_snapshots) > 1 and comp_snapshots[0].interest_score:
            search_change = _change(comp_snapshots[-1].interest_score, comp_snapshots[0].interest_score)
        competitor_rows.append({
            "id": competitor.id,
            "name": competitor.name,
            "website": competitor.website,
            "handle": competitor.handle_instagram or competitor.handle_twitter,
            "color": BRAND_COLORS[index % len(BRAND_COLORS)],
            "posts": len(comp_posts),
            "mentions": len(comp_mentions),
            "active_ads": len(comp_ads),
            "engagement_rate": engagement.average_engagement(comp_dicts) or 0,
            "posts_per_week": cadence["posts_per_week"],
            "top_format": cadence.get("top_content_type") or "—",
            "search_change": search_change,
        })

    content_counts = Counter((p.content_type or "unknown") for p in posts)
    sentiment_counts = Counter((m.sentiment_label or "neutral") for m in mentions)
    platform_counts = Counter((p.platform or "other") for p in posts)

    daily_engagement = defaultdict(int)
    daily_posts = defaultdict(int)
    for post in posts:
        key = post.posted_at.date().isoformat()
        daily_engagement[key] += (post.likes or 0) + (post.comments or 0) + (post.shares or 0)
        daily_posts[key] += 1
    series = []
    for offset in range(days - 1, -1, -1):
        date = (now - timedelta(days=offset)).date().isoformat()
        series.append({
            "date": date,
            "engagement": daily_engagement[date],
            "posts": daily_posts[date],
        })

    snapshots_by_date = defaultdict(list)
    for snapshot in all_snapshots:
        if snapshot.date >= cutoff:
            snapshots_by_date[snapshot.date.date().isoformat()].append(snapshot.interest_score)
    search_series = [
        {"date": date, "score": round(sum(values) / len(values), 1)}
        for date, values in sorted(snapshots_by_date.items())
    ]

    heatmap = posting_time.build_posting_heatmap(post_dicts)
    boosted = [p for p in posts if p.is_boosted]

    recent_posts = sorted(posts, key=lambda p: p.posted_at, reverse=True)[:18]
    recent_mentions = sorted(mentions, key=lambda m: m.published_at, reverse=True)[:18]
    ad_rows = sorted(all_ads, key=lambda a: a.start_date or datetime.min, reverse=True)[:16]

    return {
        "generated_at": now.isoformat(),
        "is_demo": all((c.notes or "").startswith("Demo brand") for c in competitors) if competitors else False,
        "days": days,
        "selected_competitor": competitor_id,
        "summary": {
            "competitors": len(competitors),
            "posts": len(posts),
            "posts_change": _change(len(posts), len(previous_posts)),
            "mentions": len(mentions),
            "mentions_change": _change(len(mentions), len(previous_mentions)),
            "active_ads": len(active_ads),
            "engagement_rate": avg_engagement,
            "engagement_change": round(avg_engagement - previous_engagement, 2),
            "boosted_pct": round(len(boosted) / len(posts) * 100, 1) if posts else 0,
        },
        "competitors": competitor_rows,
        "content_mix": [{"label": key, "value": value} for key, value in content_counts.most_common()],
        "platform_mix": [{"label": key, "value": value} for key, value in platform_counts.most_common()],
        "sentiment": {
            "positive": sentiment_counts["positive"],
            "neutral": sentiment_counts["neutral"],
            "negative": sentiment_counts["negative"],
        },
        "engagement_series": series,
        "search_series": search_series,
        "best_times": heatmap["best_slots"],
        "posts": [{
            "id": p.id,
            "competitor": by_id[p.competitor_id].name,
            "competitor_color": BRAND_COLORS[(p.competitor_id - 1) % len(BRAND_COLORS)],
            "platform": p.platform,
            "content_type": p.content_type,
            "caption": p.caption,
            "posted_at": p.posted_at.isoformat(),
            "engagement": (p.likes or 0) + (p.comments or 0) + (p.shares or 0),
            "likes": p.likes or 0,
            "comments": p.comments or 0,
            "shares": p.shares or 0,
            "is_boosted": bool(p.is_boosted),
            "url": p.url,
        } for p in recent_posts],
        "mentions": [{
            "id": m.id,
            "competitor": by_id[m.competitor_id].name,
            "platform": m.platform,
            "author": m.author,
            "text": m.text,
            "published_at": m.published_at.isoformat(),
            "sentiment": m.sentiment_label or "neutral",
            "url": m.url,
        } for m in recent_mentions],
        "ads": [{
            "id": a.id,
            "competitor": by_id[a.competitor_id].name,
            "creative_text": a.creative_text,
            "start_date": a.start_date.isoformat() if a.start_date else None,
            "is_active": bool(a.is_active),
            "platform": a.platform,
        } for a in ad_rows],
    }

"""
FastAPI app -- the backend the Streamlit dashboard (and anything else)
talks to. Run with:  uvicorn app.main:app --reload
"""
import logging
from datetime import datetime
from typing import List

from dateutil import parser as dateparser
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app import models, schemas
from app.connectors import twitter_connector, meta_ads_connector, oembed_connector, news_connector
from app.analysis import content_classifier, posting_time, engagement, ad_organic_matcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Competitor Social Intel API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    init_db()


def _parse_dt(value):
    if not value:
        return None
    try:
        return dateparser.parse(value)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Competitors
# --------------------------------------------------------------------------- #

@app.post("/competitors", response_model=schemas.CompetitorOut)
def create_competitor(payload: schemas.CompetitorCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Competitor).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(400, f"Competitor '{payload.name}' already exists (id={existing.id}).")
    comp = models.Competitor(**payload.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


@app.get("/competitors", response_model=List[schemas.CompetitorOut])
def list_competitors(db: Session = Depends(get_db)):
    return db.query(models.Competitor).all()


def _get_competitor_or_404(competitor_id: int, db: Session) -> models.Competitor:
    comp = db.query(models.Competitor).get(competitor_id)
    if not comp:
        raise HTTPException(404, "Competitor not found")
    return comp


# --------------------------------------------------------------------------- #
# Sync jobs -- pull fresh data from each connector and persist it
# --------------------------------------------------------------------------- #

@app.post("/competitors/{competitor_id}/sync/twitter")
def sync_twitter(competitor_id: int, db: Session = Depends(get_db)):
    comp = _get_competitor_or_404(competitor_id, db)
    if not comp.handle_twitter:
        raise HTTPException(400, "Competitor has no handle_twitter set.")

    raw_posts = twitter_connector.get_competitor_recent_posts(comp.handle_twitter)
    saved = 0
    for rp in raw_posts:
        if db.query(models.Post).filter_by(external_id=rp["external_id"], platform="twitter").first():
            continue
        content_type = content_classifier.classify_content_type(rp)
        post = models.Post(
            competitor_id=comp.id,
            platform="twitter",
            external_id=rp["external_id"],
            url=rp["url"],
            content_type=content_type,
            caption=rp.get("caption"),
            hashtags=content_classifier.extract_hashtags(rp.get("caption", "")),
            posted_at=_parse_dt(rp.get("posted_at")),
            likes=rp.get("likes", 0),
            comments=rp.get("comments", 0),
            shares=rp.get("shares", 0),
            views=rp.get("views"),
            raw_json=rp.get("raw"),
        )
        db.add(post)
        saved += 1
    db.commit()
    return {"platform": "twitter", "fetched": len(raw_posts), "saved_new": saved}


@app.post("/competitors/{competitor_id}/sync/mentions")
def sync_mentions(competitor_id: int, query: str, db: Session = Depends(get_db)):
    """
    query: search string, e.g. '"Acme Shoes" OR @acmeshoes'.
    Pulls from both X (last 7 days) and news/web sources.
    """
    comp = _get_competitor_or_404(competitor_id, db)

    twitter_mentions = twitter_connector.search_recent_mentions(query)
    news_mentions = news_connector.search_mentions(query)

    saved = 0
    for m in twitter_mentions + news_mentions:
        if m.get("url") and db.query(models.Mention).filter_by(url=m["url"]).first():
            continue
        tag = content_classifier.classify_with_claude(m.get("text", ""))
        mention = models.Mention(
            competitor_id=comp.id,
            platform=m["platform"],
            author=m.get("author"),
            url=m.get("url"),
            text=m.get("text"),
            published_at=_parse_dt(m.get("published_at")),
            sentiment_label=(tag or {}).get("sentiment"),
            sentiment_score=(tag or {}).get("sentiment_score"),
            raw_json=m.get("raw"),
        )
        db.add(mention)
        saved += 1
    db.commit()
    return {
        "twitter_fetched": len(twitter_mentions),
        "news_fetched": len(news_mentions),
        "saved_new": saved,
    }


@app.post("/competitors/{competitor_id}/sync/meta-ads")
def sync_meta_ads(competitor_id: int, search_term: str, db: Session = Depends(get_db)):
    comp = _get_competitor_or_404(competitor_id, db)
    raw_ads = meta_ads_connector.get_active_ads(search_term)

    saved = 0
    for a in raw_ads:
        if a.get("ad_archive_id") and db.query(models.AdCreative).filter_by(ad_archive_id=a["ad_archive_id"]).first():
            continue
        ad = models.AdCreative(
            competitor_id=comp.id,
            platform="meta",
            ad_archive_id=a.get("ad_archive_id"),
            creative_text=a.get("creative_text"),
            snapshot_url=a.get("snapshot_url"),
            page_name=a.get("page_name"),
            start_date=_parse_dt(a.get("start_date")),
            end_date=_parse_dt(a.get("end_date")),
            is_active=a.get("is_active", True),
            countries=a.get("publisher_platforms"),
            raw_json=a.get("raw"),
        )
        db.add(ad)
        saved += 1
    db.commit()
    return {"fetched": len(raw_ads), "saved_new": saved}


@app.post("/competitors/{competitor_id}/import/oembed")
def import_oembed_post(competitor_id: int, payload: schemas.OEmbedImportRequest, db: Session = Depends(get_db)):
    """Compliant manual-import path for a single public IG/FB post URL."""
    comp = _get_competitor_or_404(competitor_id, db)

    if payload.platform == "facebook":
        data = oembed_connector.fetch_facebook_post(payload.post_url)
    elif payload.platform == "instagram":
        data = oembed_connector.fetch_instagram_post(payload.post_url)
    else:
        raise HTTPException(400, "platform must be 'facebook' or 'instagram'")

    if not data:
        raise HTTPException(502, "oEmbed lookup failed -- check META_ACCESS_TOKEN and that the post is public.")

    post = models.Post(
        competitor_id=comp.id,
        platform=payload.platform,
        url=payload.post_url,
        content_type="unknown_via_oembed",
        caption=None,
        ingested_via="oembed_manual",
        raw_json=data.get("raw"),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"saved_post_id": post.id, "embed_html": data.get("html_embed")}


@app.post("/competitors/{competitor_id}/analyze/match-ads")
def match_posts_to_ads(competitor_id: int, db: Session = Depends(get_db)):
    """
    Run best-effort content matching between this competitor's organic posts
    and their tracked ad creatives, flagging each post as boosted or
    organic-only. Re-run this after every sync to keep flags current --
    it's cheap (no external API calls, pure text comparison).
    """
    comp = _get_competitor_or_404(competitor_id, db)
    posts = db.query(models.Post).filter_by(competitor_id=comp.id).all()
    ads = db.query(models.AdCreative).filter_by(competitor_id=comp.id).all()

    if not ads:
        return {"warning": "No ad data for this competitor yet -- sync /sync/meta-ads first.", "total_posts": len(posts)}

    summary = ad_organic_matcher.match_posts_to_ads(posts, ads)
    db.commit()
    return summary


@app.get("/competitors/{competitor_id}/posts/organic-only", response_model=List[schemas.PostOut])
def get_organic_only_posts(competitor_id: int, db: Session = Depends(get_db)):
    """Posts with no ad spend detected behind them (or not yet matched)."""
    _get_competitor_or_404(competitor_id, db)
    return (
        db.query(models.Post)
        .filter_by(competitor_id=competitor_id)
        .filter(models.Post.is_boosted.isnot(True))
        .order_by(models.Post.posted_at.desc())
        .all()
    )


@app.get("/competitors/{competitor_id}/posts/boosted", response_model=List[schemas.PostOut])
def get_boosted_posts(competitor_id: int, db: Session = Depends(get_db)):
    """Organic posts that are also running as paid ads right now."""
    _get_competitor_or_404(competitor_id, db)
    return (
        db.query(models.Post)
        .filter_by(competitor_id=competitor_id, is_boosted=True)
        .order_by(models.Post.posted_at.desc())
        .all()
    )


# --------------------------------------------------------------------------- #
# Read endpoints
# --------------------------------------------------------------------------- #

@app.get("/competitors/{competitor_id}/posts", response_model=List[schemas.PostOut])
def get_posts(competitor_id: int, db: Session = Depends(get_db)):
    _get_competitor_or_404(competitor_id, db)
    return db.query(models.Post).filter_by(competitor_id=competitor_id).order_by(models.Post.posted_at.desc()).all()


@app.get("/competitors/{competitor_id}/mentions", response_model=List[schemas.MentionOut])
def get_mentions(competitor_id: int, db: Session = Depends(get_db)):
    _get_competitor_or_404(competitor_id, db)
    return db.query(models.Mention).filter_by(competitor_id=competitor_id).order_by(models.Mention.published_at.desc()).all()


@app.get("/competitors/{competitor_id}/ads", response_model=List[schemas.AdCreativeOut])
def get_ads(competitor_id: int, db: Session = Depends(get_db)):
    _get_competitor_or_404(competitor_id, db)
    return db.query(models.AdCreative).filter_by(competitor_id=competitor_id).all()


@app.get("/competitors/{competitor_id}/analysis/posting-time")
def analysis_posting_time(competitor_id: int, db: Session = Depends(get_db)):
    _get_competitor_or_404(competitor_id, db)
    posts = db.query(models.Post).filter_by(competitor_id=competitor_id).all()
    post_dicts = [{"posted_at": p.posted_at, "likes": p.likes, "comments": p.comments, "shares": p.shares} for p in posts]
    return posting_time.build_posting_heatmap(post_dicts)


@app.get("/competitors/{competitor_id}/analysis/summary")
def analysis_summary(competitor_id: int, db: Session = Depends(get_db)):
    _get_competitor_or_404(competitor_id, db)
    posts = db.query(models.Post).filter_by(competitor_id=competitor_id).all()
    post_dicts = [{
        "posted_at": p.posted_at, "likes": p.likes, "comments": p.comments,
        "shares": p.shares, "views": p.views, "content_type": p.content_type,
    } for p in posts]
    return {
        "cadence": posting_time.posting_frequency_summary(post_dicts),
        "avg_engagement_rate_pct": engagement.average_engagement(post_dicts),
        "top_posts": engagement.top_performing_posts(post_dicts, n=5),
        "organic_vs_boosted": ad_organic_matcher.organic_vs_boosted_summary(posts),
    }

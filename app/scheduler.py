"""
Periodic polling. Run standalone with:  python -m app.scheduler
(keep it running in a separate process/container from the API server).

For each competitor in the DB, on the configured interval:
  - pull their own recent posts (Twitter, if handle_twitter is set)
  - pull mentions of their name (Twitter + news)
  - pull active Meta ads under their page name

Everything here reuses the same connector + analysis functions the API
uses, just triggered on a timer instead of an HTTP request.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import settings
from app.database import SessionLocal, init_db
from app import models
from app.connectors import twitter_connector, meta_ads_connector, news_connector
from app.analysis import content_classifier, ad_organic_matcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def poll_all_competitors():
    db = SessionLocal()
    try:
        competitors = db.query(models.Competitor).all()
        logger.info("Polling %d competitor(s)...", len(competitors))

        for comp in competitors:
            _poll_one(db, comp)
            db.flush()  # make sure new posts/ads have IDs before matching
            posts = db.query(models.Post).filter_by(competitor_id=comp.id).all()
            ads = db.query(models.AdCreative).filter_by(competitor_id=comp.id).all()
            if ads:
                ad_organic_matcher.match_posts_to_ads(posts, ads)

        db.commit()
    finally:
        db.close()


def _poll_one(db, comp: models.Competitor):
    if comp.handle_twitter:
        for rp in twitter_connector.get_competitor_recent_posts(comp.handle_twitter):
            if db.query(models.Post).filter_by(external_id=rp["external_id"], platform="twitter").first():
                continue
            db.add(models.Post(
                competitor_id=comp.id, platform="twitter", external_id=rp["external_id"],
                url=rp["url"], content_type=content_classifier.classify_content_type(rp),
                caption=rp.get("caption"), posted_at=rp.get("posted_at"),
                likes=rp.get("likes", 0), comments=rp.get("comments", 0),
                shares=rp.get("shares", 0), views=rp.get("views"), raw_json=rp.get("raw"),
            ))

        query = f'"{comp.name}" OR @{comp.handle_twitter}'
        for m in twitter_connector.search_recent_mentions(query):
            if m.get("url") and db.query(models.Mention).filter_by(url=m["url"]).first():
                continue
            db.add(models.Mention(
                competitor_id=comp.id, platform=m["platform"], author=m.get("author"),
                url=m.get("url"), text=m.get("text"), published_at=m.get("published_at"),
                raw_json=m.get("raw"),
            ))

    for m in news_connector.search_mentions(comp.name):
        if m.get("url") and db.query(models.Mention).filter_by(url=m["url"]).first():
            continue
        db.add(models.Mention(
            competitor_id=comp.id, platform="news", author=m.get("author"),
            url=m.get("url"), text=m.get("text"), published_at=m.get("published_at"),
            raw_json=m.get("raw"),
        ))

    for a in meta_ads_connector.get_active_ads(comp.name):
        if a.get("ad_archive_id") and db.query(models.AdCreative).filter_by(ad_archive_id=a["ad_archive_id"]).first():
            continue
        db.add(models.AdCreative(
            competitor_id=comp.id, platform="meta", ad_archive_id=a.get("ad_archive_id"),
            creative_text=a.get("creative_text"), snapshot_url=a.get("snapshot_url"),
            page_name=a.get("page_name"), is_active=a.get("is_active", True), raw_json=a.get("raw"),
        ))


if __name__ == "__main__":
    init_db()
    scheduler = BlockingScheduler()
    scheduler.add_job(poll_all_competitors, "interval", minutes=settings.poll_interval_minutes)
    logger.info("Scheduler started -- polling every %d minutes.", settings.poll_interval_minutes)
    poll_all_competitors()  # run once immediately on startup
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

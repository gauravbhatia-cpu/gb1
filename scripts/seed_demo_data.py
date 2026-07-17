"""
Seeds the database with synthetic-but-realistic demo data so you can
open the dashboard and see it working *before* wiring up any real API
keys. Run with:  python -m scripts.seed_demo_data
"""
import random
from datetime import datetime, timedelta

from app.database import SessionLocal, init_db
from app import models
from app.analysis import ad_organic_matcher

random.seed(42)

CONTENT_TYPES = ["image", "video", "carousel", "text", "reel"]
PLATFORMS = ["instagram", "twitter", "facebook"]

DEMO_COMPETITORS = [
    {"name": "Acme Running Co", "handle_twitter": "acmerunning", "handle_instagram": "acmerunning", "website": "https://acmerunning.example"},
    {"name": "Velocity Sportswear", "handle_twitter": "velocitysport", "handle_instagram": "velocitysport", "website": "https://velocitysport.example"},
]

CAPTION_TEMPLATES = [
    "New drop alert! Our {product} just landed. #newrelease #{tag}",
    "Behind the scenes at our latest photoshoot. {product} coming soon.",
    "Customer spotlight: see how {product} performed at the marathon this weekend. #{tag}",
    "Flash sale: 20% off {product} today only!",
    "Q&A with our design team about the {product} line. #{tag} #design",
    "Just a regular Tuesday thought about {product}.",
]
PRODUCTS = ["Velocity Pro", "AirFlex Trainer", "Trail Runner X", "CoreFit Legging", "StrideMax"]
TAGS = ["running", "fitness", "newdrop", "training", "athlete"]


def random_caption():
    template = random.choice(CAPTION_TEMPLATES)
    return template.format(product=random.choice(PRODUCTS), tag=random.choice(TAGS))


def random_datetime_within(days_back: int) -> datetime:
    base = datetime.utcnow() - timedelta(days=random.uniform(0, days_back))
    # bias toward common posting hours (9-11am, 12-1pm, 5-8pm) to make the
    # posting-time heatmap demo look like a real pattern instead of noise
    hour_bucket = random.choice([9, 10, 11, 12, 17, 18, 19, 20])
    return base.replace(hour=hour_bucket, minute=random.randint(0, 59))


def seed():
    init_db()
    db = SessionLocal()
    try:
        for comp_data in DEMO_COMPETITORS:
            existing = db.query(models.Competitor).filter_by(name=comp_data["name"]).first()
            if existing:
                print(f"Skipping existing competitor: {comp_data['name']}")
                continue

            comp = models.Competitor(**comp_data, notes="Seeded demo data")
            db.add(comp)
            db.flush()  # get comp.id

            # --- Posts (own content) ---
            post_objs = []
            for i in range(60):
                caption = random_caption()
                posted_at = random_datetime_within(90)
                content_type = random.choices(CONTENT_TYPES, weights=[35, 25, 15, 10, 15])[0]
                base_engagement = random.randint(50, 2000)
                post = models.Post(
                    competitor_id=comp.id,
                    platform=random.choice(PLATFORMS),
                    external_id=f"demo-{comp.id}-{i}",
                    url=f"https://example.com/post/{comp.id}/{i}",
                    content_type=content_type,
                    caption=caption,
                    hashtags=[w for w in caption.split() if w.startswith("#")],
                    posted_at=posted_at,
                    likes=base_engagement,
                    comments=int(base_engagement * random.uniform(0.02, 0.08)),
                    shares=int(base_engagement * random.uniform(0.01, 0.05)),
                    views=base_engagement * random.randint(5, 20),
                    ingested_via="demo_seed",
                )
                db.add(post)
                post_objs.append(post)
            db.flush()  # get post IDs

            # --- Mentions (what others say about them) ---
            sentiments = ["positive", "neutral", "negative"]
            sample_texts = [
                "Just tried {name}'s new running shoes, honestly impressed with the cushioning.",
                "{name}'s customer service was slow to respond about my order.",
                "Anyone else think {name} is overpriced for the quality?",
                "Loving my new gear from {name}, perfect for marathon training season.",
                "{name} just announced a new sustainability initiative, pretty cool.",
            ]
            for i in range(30):
                text = random.choice(sample_texts).format(name=comp.name)
                db.add(models.Mention(
                    competitor_id=comp.id,
                    platform=random.choice(["twitter", "news"]),
                    author=f"user_{random.randint(1000,9999)}",
                    url=f"https://example.com/mention/{comp.id}/{i}",
                    text=text,
                    published_at=random_datetime_within(30),
                    sentiment_label=random.choices(sentiments, weights=[45, 35, 20])[0],
                    sentiment_score=round(random.uniform(-1, 1), 2),
                ))

            # --- Ad creatives ---
            # Roughly a third are "boosted" versions of an actual organic post
            # (same copy, close in time) -- the rest are independent ad-only
            # creative, simulating the common real-world mix of boosted posts
            # and standalone/"dark" ads that never ran organically.
            recent_posts = [p for p in post_objs if p.posted_at and (datetime.utcnow() - p.posted_at).days < 45]
            for i in range(10):
                if recent_posts and random.random() < 0.35:
                    source_post = random.choice(recent_posts)
                    creative_text = source_post.caption
                    start = source_post.posted_at + timedelta(days=random.randint(0, 2))
                else:
                    creative_text = f"Shop the new {random.choice(PRODUCTS)} collection today."
                    start = random_datetime_within(60)

                db.add(models.AdCreative(
                    competitor_id=comp.id,
                    platform="meta",
                    ad_archive_id=f"demo-ad-{comp.id}-{i}",
                    creative_text=creative_text,
                    page_name=comp.name,
                    start_date=start,
                    end_date=start + timedelta(days=random.randint(5, 30)) if random.random() > 0.4 else None,
                    is_active=random.random() > 0.4,
                    countries=["facebook", "instagram"],
                ))
            db.flush()  # get ad IDs

            # --- Run the real organic-vs-boosted matcher on what we just seeded ---
            ads_for_comp = db.query(models.AdCreative).filter_by(competitor_id=comp.id).all()
            match_summary = ad_organic_matcher.match_posts_to_ads(post_objs, ads_for_comp)
            print(f"  Matched: {match_summary['boosted']} boosted / {match_summary['organic_only']} organic-only")

            # --- Brand search interest snapshots ---
            score = 40
            for d in range(90, 0, -1):
                score = max(10, min(100, score + random.randint(-5, 6)))
                db.add(models.BrandSearchSnapshot(
                    competitor_id=comp.id,
                    keyword=comp.name,
                    date=datetime.utcnow() - timedelta(days=d),
                    interest_score=score,
                ))

            print(f"Seeded demo data for: {comp.name}")

        db.commit()
        print("\nDone. Launch the dashboard with: streamlit run dashboard/app.py")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

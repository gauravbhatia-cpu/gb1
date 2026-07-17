"""Deterministic sample data used by the hosted product demo."""

import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.analysis import ad_organic_matcher


BRANDS = [
    {
        "name": "Nova Athletics",
        "website": "https://nova-athletics.example",
        "handle_twitter": "novarunclub",
        "handle_instagram": "novarunclub",
        "base": 1860,
        "accent": "#7cdbb5",
        "products": ["CloudStride 2", "Tempo Shell", "AeroFlex Set"],
    },
    {
        "name": "Drift Coffee",
        "website": "https://drift-coffee.example",
        "handle_twitter": "driftcoffee",
        "handle_instagram": "driftcoffee",
        "base": 1320,
        "accent": "#f5ad72",
        "products": ["Daybreak Blend", "Cold Brew Kit", "Origin Series"],
    },
    {
        "name": "Luma Skin",
        "website": "https://luma-skin.example",
        "handle_twitter": "lumaskinlab",
        "handle_instagram": "lumaskinlab",
        "base": 2240,
        "accent": "#a8a5ff",
        "products": ["Barrier Reset", "Dew Serum", "Night Cloud"],
    },
]

CAPTIONS = [
    "The wait is over. {product} is here — designed for the days that do not slow down. #{tag}",
    "Three details that make {product} different. Save this for your next upgrade. #{tag}",
    "Community check-in: how are you using {product} this week? Tell us below.",
    "Behind the launch: six months of testing went into {product}. Here is what changed.",
    "A quiet morning, a clear plan, and {product}. That is the whole mood. #{tag}",
    "48 hours only: early access to {product} is live for our community.",
    "Creator spotlight: @maya.makes puts {product} through a full day in the city.",
    "The most requested color of {product} just landed. Which one are you choosing?",
]

MENTIONS = [
    ("The new {product} campaign from {brand} is genuinely excellent.", "positive", 0.82),
    ("Has anyone compared {brand} with the other options in this category?", "neutral", 0.05),
    ("My {brand} order arrived today and the packaging feels so thoughtful.", "positive", 0.74),
    ("I like {brand}, but the last launch sold out before I could check out.", "negative", -0.42),
    ("Interesting creator partnership from {brand} this week.", "neutral", 0.12),
    ("{brand} keeps getting the small product details right.", "positive", 0.68),
]


def ensure_demo_data(db: Session) -> bool:
    """Seed a compact, realistic dataset when the database is empty.

    Returns True when new demo data was created. User-created databases are
    never overwritten or supplemented automatically.
    """
    if db.query(models.Competitor).first():
        return False

    rng = random.Random(20260717)
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    for brand_index, brand in enumerate(BRANDS):
        competitor = models.Competitor(
            name=brand["name"],
            website=brand["website"],
            handle_twitter=brand["handle_twitter"],
            handle_instagram=brand["handle_instagram"],
            notes=f"Demo brand · accent {brand['accent']}",
        )
        db.add(competitor)
        db.flush()

        posts = []
        for index in range(42):
            age_days = index * 2 + rng.randint(0, 1)
            hour = rng.choice([8, 9, 11, 12, 17, 18, 20])
            published = (now - timedelta(days=age_days)).replace(hour=hour)
            if published > now:
                published -= timedelta(days=1)
            product = brand["products"][index % len(brand["products"])]
            caption = CAPTIONS[(index + brand_index) % len(CAPTIONS)].format(
                product=product,
                tag=rng.choice(["newdrop", "community", "behindthescenes", "launchday"]),
            )
            baseline = brand["base"] + int((42 - index) * 18)
            likes = max(120, int(baseline * rng.uniform(0.68, 1.32)))
            comments = max(8, int(likes * rng.uniform(0.025, 0.075)))
            shares = max(5, int(likes * rng.uniform(0.018, 0.065)))
            views = int((likes + comments + shares) * rng.uniform(11, 19))
            post = models.Post(
                competitor_id=competitor.id,
                platform=rng.choices(["instagram", "twitter", "facebook"], [60, 28, 12])[0],
                external_id=f"demo-{competitor.id}-{index}",
                url=f"https://example.com/{brand['handle_instagram']}/post/{index}",
                content_type=rng.choices(["video", "carousel", "image", "text"], [36, 28, 27, 9])[0],
                caption=caption,
                hashtags=[word for word in caption.split() if word.startswith("#")],
                posted_at=published,
                likes=likes,
                comments=comments,
                shares=shares,
                views=views,
                ingested_via="demo_seed",
            )
            db.add(post)
            posts.append(post)

        db.flush()

        for index in range(24):
            template, sentiment, score = MENTIONS[(index + brand_index) % len(MENTIONS)]
            text = template.format(brand=brand["name"], product=brand["products"][index % 3])
            db.add(models.Mention(
                competitor_id=competitor.id,
                platform=rng.choice(["twitter", "news", "web"]),
                author=rng.choice(["maya.makes", "trendbrief", "alexreviews", "studio.notes", "market.daily"]),
                url=f"https://example.com/mention/{competitor.id}/{index}",
                text=text,
                published_at=now - timedelta(days=index * 2 + rng.randint(0, 2), hours=rng.randint(0, 20)),
                sentiment_label=sentiment,
                sentiment_score=score,
            ))

        ads = []
        for index in range(7):
            source_post = posts[index * 4]
            is_boosted_copy = index < 3
            ad = models.AdCreative(
                competitor_id=competitor.id,
                platform="meta",
                ad_archive_id=f"demo-ad-{competitor.id}-{index}",
                creative_text=(source_post.caption if is_boosted_copy else
                               f"Meet {brand['products'][index % 3]}. Built for your everyday ritual."),
                snapshot_url=f"https://example.com/ad/{competitor.id}/{index}",
                page_name=brand["name"],
                start_date=source_post.posted_at + timedelta(days=1),
                end_date=None if index < 5 else now - timedelta(days=4),
                is_active=index < 5,
                countries=["instagram", "facebook"],
            )
            db.add(ad)
            ads.append(ad)

        db.flush()
        ad_organic_matcher.match_posts_to_ads(posts, ads)

        interest = 42 + brand_index * 9
        for day in range(90, -1, -1):
            interest = max(18, min(96, interest + rng.randint(-3, 4)))
            if day in (14, 13, 12):
                interest = min(100, interest + 8)
            db.add(models.BrandSearchSnapshot(
                competitor_id=competitor.id,
                keyword=brand["name"],
                date=now - timedelta(days=day),
                interest_score=interest,
            ))

    db.commit()
    return True

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


class Workspace(Base):
    """One private Scout workspace owned by one Supabase user."""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(100), nullable=False, unique=True, index=True)
    brand_name = Column(String(200), nullable=False)
    website = Column(String(300), nullable=True)
    handle_instagram = Column(String(100), nullable=True)
    handle_twitter = Column(String(100), nullable=True)
    is_sample_data = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    competitors = relationship("Competitor", back_populates="workspace", cascade="all, delete-orphan")


class Competitor(Base):
    """A brand/competitor being tracked."""
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    website = Column(String(300), nullable=True)

    handle_twitter = Column(String(100), nullable=True)     # e.g. "nike"
    handle_instagram = Column(String(100), nullable=True)
    handle_facebook_page_id = Column(String(100), nullable=True)
    handle_linkedin = Column(String(100), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="competitors")
    posts = relationship("Post", back_populates="competitor", cascade="all, delete-orphan")
    mentions = relationship("Mention", back_populates="competitor", cascade="all, delete-orphan")
    ads = relationship("AdCreative", back_populates="competitor", cascade="all, delete-orphan")
    search_snapshots = relationship("BrandSearchSnapshot", back_populates="competitor", cascade="all, delete-orphan")


class Post(Base):
    """An organic post published BY the competitor (own content, not mentions)."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)

    platform = Column(String(30), nullable=False)          # twitter | instagram | facebook | linkedin
    external_id = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)

    content_type = Column(String(30), nullable=True)        # image | video | carousel | text | link | reel
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)                  # list[str]
    topics = Column(JSON, nullable=True)                    # list[str] from classifier

    posted_at = Column(DateTime, nullable=True)

    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    views = Column(Integer, nullable=True)

    ingested_via = Column(String(30), default="api")        # api | oembed_manual
    raw_json = Column(JSON, nullable=True)

    # Organic-vs-boosted tracking: is this specific organic post ALSO running
    # as a paid ad right now, or is it organic-only (no ad spend behind it)?
    # See app/analysis/ad_organic_matcher.py -- this is a best-effort content
    # match against Ad Library creative text, not an official platform link
    # (Meta doesn't expose that link for pages you don't manage).
    is_boosted = Column(Boolean, nullable=True)              # None = not yet checked
    matched_ad_id = Column(Integer, ForeignKey("ad_creatives.id"), nullable=True)
    match_confidence = Column(Float, nullable=True)          # 0-1 text-similarity score

    competitor = relationship("Competitor", back_populates="posts")


class Mention(Base):
    """Someone else talking ABOUT the brand (mention tracking, not owned content)."""
    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)

    platform = Column(String(30), nullable=False)           # twitter | news | web
    author = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)
    text = Column(Text, nullable=True)

    published_at = Column(DateTime, nullable=True)
    sentiment_label = Column(String(20), nullable=True)      # positive | neutral | negative
    sentiment_score = Column(Float, nullable=True)            # -1..1

    raw_json = Column(JSON, nullable=True)

    competitor = relationship("Competitor", back_populates="mentions")


class AdCreative(Base):
    """A paid ad the competitor is running, from the Meta Ad Library (public data)."""
    __tablename__ = "ad_creatives"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)

    platform = Column(String(30), default="meta")
    ad_archive_id = Column(String(100), nullable=True)
    creative_text = Column(Text, nullable=True)
    snapshot_url = Column(String(500), nullable=True)
    page_name = Column(String(200), nullable=True)

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    countries = Column(JSON, nullable=True)                 # list[str]
    raw_json = Column(JSON, nullable=True)

    competitor = relationship("Competitor", back_populates="ads")


class BrandSearchSnapshot(Base):
    """Time series of relative search interest for a brand/keyword."""
    __tablename__ = "brand_search_snapshots"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)

    keyword = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False)
    interest_score = Column(Integer, nullable=False)         # 0-100, Google Trends style

    competitor = relationship("Competitor", back_populates="search_snapshots")

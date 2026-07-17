from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, Field


class CompetitorCreate(BaseModel):
    name: str
    website: Optional[str] = None
    handle_twitter: Optional[str] = None
    handle_instagram: Optional[str] = None
    handle_facebook_page_id: Optional[str] = None
    handle_linkedin: Optional[str] = None
    notes: Optional[str] = None


class CompetitorOut(CompetitorCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceCreate(BaseModel):
    brand_name: str
    website: Optional[str] = None
    handle_instagram: Optional[str] = None
    handle_twitter: Optional[str] = None
    competitor_names: List[str] = Field(default_factory=list)


class WorkspaceOut(BaseModel):
    id: str
    brand_name: str
    website: Optional[str]
    handle_instagram: Optional[str]
    handle_twitter: Optional[str]
    is_sample_data: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PostOut(BaseModel):
    id: int
    platform: str
    url: Optional[str]
    content_type: Optional[str]
    caption: Optional[str]
    posted_at: Optional[datetime]
    likes: int
    comments: int
    shares: int
    views: Optional[int]
    is_boosted: Optional[bool] = None
    matched_ad_id: Optional[int] = None
    match_confidence: Optional[float] = None

    class Config:
        from_attributes = True


class MentionOut(BaseModel):
    id: int
    platform: str
    author: Optional[str]
    url: Optional[str]
    text: Optional[str]
    published_at: Optional[datetime]
    sentiment_label: Optional[str]

    class Config:
        from_attributes = True


class AdCreativeOut(BaseModel):
    id: int
    ad_archive_id: Optional[str]
    creative_text: Optional[str]
    snapshot_url: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class OEmbedImportRequest(BaseModel):
    competitor_id: int
    post_url: str
    platform: str  # "facebook" | "instagram"

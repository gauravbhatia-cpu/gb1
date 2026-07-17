"""Public preview setup without synthetic market data."""

from sqlalchemy.orm import Session

from app import models


def ensure_demo_data(db: Session) -> bool:
    """Ensure the public preview exists and remove legacy fabricated records."""
    workspace = db.query(models.Workspace).filter_by(id="demo").first()
    changed = False
    if not workspace:
        workspace = models.Workspace(
            id="demo", owner_id="demo", brand_name="Scout Preview", is_sample_data=False
        )
        db.add(workspace)
        db.flush()
        changed = True

    # Earlier releases populated this workspace with synthetic metrics. The
    # production product now shows only persisted, sourced records.
    legacy_competitors = db.query(models.Competitor).filter(
        (models.Competitor.workspace_id == "demo") |
        (models.Competitor.workspace_id.is_(None))
    ).all()
    legacy_ids = [competitor.id for competitor in legacy_competitors]
    if legacy_ids:
        db.query(models.Post).filter(models.Post.competitor_id.in_(legacy_ids)).update(
            {models.Post.matched_ad_id: None}, synchronize_session=False
        )
        db.flush()
    for competitor in legacy_competitors:
        db.delete(competitor)
        changed = True

    db.commit()
    return changed

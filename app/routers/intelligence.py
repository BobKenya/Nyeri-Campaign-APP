"""Intelligence routes: opponents, dossiers, county issues, media, endorsements, tags."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.intel_election import (
    Opponent, OpponentActivity, Dossier, CountyIssue,
    MediaCoverage, Endorsement, Tag, EntityTag, CampaignMaterial,
)
from app.schemas.common import (
    OpponentCreate, OpponentResponse, DossierCreate, CountyIssueCreate,
    MediaCoverageCreate, EndorsementCreate,
)
from app.dependencies import get_current_user, require_coordinator

router = APIRouter()


# ── Opponents ──────────────────────────────────────────────────────

@router.get("/opponents", response_model=list[OpponentResponse])
async def list_opponents(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Opponent).order_by(Opponent.full_name))
    return result.scalars().all()


@router.post("/opponents", response_model=OpponentResponse, status_code=status.HTTP_201_CREATED)
async def create_opponent(body: OpponentCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    opponent = Opponent(**body.model_dump())
    db.add(opponent)
    await db.flush()
    await db.refresh(opponent)
    return opponent


@router.get("/opponents/{opponent_id}/activities")
async def opponent_activities(opponent_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(OpponentActivity).where(OpponentActivity.opponent_id == opponent_id)
        .order_by(OpponentActivity.activity_date.desc())
    )
    return [
        {
            "activity_id": str(a.activity_id), "activity_type": a.activity_type,
            "activity_date": a.activity_date.isoformat() if a.activity_date else None,
            "location": a.location, "description": a.description,
        }
        for a in result.scalars().all()
    ]


# ── Dossiers ───────────────────────────────────────────────────────

@router.get("/dossiers")
async def list_dossiers(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Dossier)
    if category:
        query = query.where(Dossier.category == category)
    result = await db.execute(query.order_by(Dossier.full_name))
    return [
        {
            "dossier_id": str(d.dossier_id), "full_name": d.full_name,
            "category": str(d.category) if d.category else None,
            "influence_level": str(d.influence_level) if d.influence_level else None,
        }
        for d in result.scalars().all()
    ]


@router.post("/dossiers", status_code=status.HTTP_201_CREATED)
async def create_dossier(body: DossierCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    dossier = Dossier(**body.model_dump())
    db.add(dossier)
    await db.flush()
    return {"dossier_id": str(dossier.dossier_id), "message": "Dossier created"}


# ── County Issues ──────────────────────────────────────────────────

@router.get("/issues")
async def list_issues(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(CountyIssue).order_by(CountyIssue.priority_level.desc()))
    return [
        {
            "issue_id": str(i.issue_id), "issue_title": i.issue_title,
            "issue_category": i.issue_category, "priority_level": i.priority_level,
            "campaign_stance": i.campaign_stance,
        }
        for i in result.scalars().all()
    ]


@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(body: CountyIssueCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    issue = CountyIssue(**body.model_dump())
    db.add(issue)
    await db.flush()
    return {"issue_id": str(issue.issue_id), "message": "Issue created"}


# ── Media Coverage ─────────────────────────────────────────────────

@router.get("/media")
async def list_media(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(MediaCoverage).order_by(MediaCoverage.published_at.desc()).limit(50))
    return [
        {
            "coverage_id": str(m.coverage_id), "source_name": m.source_name,
            "headline": m.headline, "sentiment": str(m.sentiment) if m.sentiment else None,
            "published_at": m.published_at.isoformat() if m.published_at else None,
        }
        for m in result.scalars().all()
    ]


@router.post("/media", status_code=status.HTTP_201_CREATED)
async def log_media(body: MediaCoverageCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    coverage = MediaCoverage(**body.model_dump())
    db.add(coverage)
    await db.flush()
    return {"coverage_id": str(coverage.coverage_id), "message": "Media coverage logged"}


# ── Endorsements ───────────────────────────────────────────────────

@router.get("/endorsements")
async def list_endorsements(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Endorsement).order_by(Endorsement.announced_at.desc()))
    return [
        {
            "endorsement_id": str(e.endorsement_id), "endorser_name": e.endorser_name,
            "endorser_type": e.endorser_type, "endorser_title": e.endorser_title,
            "announced_at": e.announced_at.isoformat() if e.announced_at else None,
        }
        for e in result.scalars().all()
    ]


@router.post("/endorsements", status_code=status.HTTP_201_CREATED)
async def log_endorsement(body: EndorsementCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    endorsement = Endorsement(**body.model_dump())
    db.add(endorsement)
    await db.flush()
    return {"endorsement_id": str(endorsement.endorsement_id), "message": "Endorsement recorded"}


# ── Tags ───────────────────────────────────────────────────────────

@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Tag).order_by(Tag.tag_category, Tag.tag_name))
    return [
        {"tag_id": str(t.tag_id), "tag_name": t.tag_name, "tag_category": t.tag_category, "tag_color": t.tag_color}
        for t in result.scalars().all()
    ]


@router.post("/tags/{entity_type}/{entity_id}/tag/{tag_id}", status_code=status.HTTP_201_CREATED)
async def apply_tag(entity_type: str, entity_id: UUID, tag_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    entity_tag = EntityTag(entity_id=entity_id, entity_type=entity_type, tag_id=tag_id)
    db.add(entity_tag)
    await db.flush()
    return {"message": "Tag applied"}

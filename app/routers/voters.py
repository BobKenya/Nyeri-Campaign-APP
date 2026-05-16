"""Voter routes: CRUD, search, constituency/ward/station lookups."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models.voters import Voter, Constituency, Ward, PollingStation, VotingHistory, DataConsentLog
from app.schemas.voters import (
    VoterCreate, VoterUpdate, VoterResponse, VoterSearchParams,
    ConstituencyResponse, WardResponse, PollingStationResponse,
)
from app.dependencies import get_current_user, require_field_agent
from app.utils.pagination import PaginationParams, PaginatedResponse, paginate

router = APIRouter()


# ── Constituencies / Wards / Stations ─────────────────────────────

@router.get("/constituencies", response_model=list[ConstituencyResponse])
async def list_constituencies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Constituency).order_by(Constituency.constituency_name))
    return result.scalars().all()


@router.get("/constituencies/{constituency_id}/wards", response_model=list[WardResponse])
async def list_wards(constituency_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ward).where(Ward.constituency_id == str(constituency_id)).order_by(Ward.ward_name)
    )
    return result.scalars().all()


@router.get("/wards/{ward_id}/polling-stations", response_model=list[PollingStationResponse])
async def list_polling_stations(ward_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PollingStation).where(PollingStation.ward_id == ward_id).order_by(PollingStation.station_name)
    )
    return result.scalars().all()


# ── Voters CRUD ───────────────────────────────────────────────────

@router.get("/", response_model=list[VoterResponse])
async def list_voters(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    constituency_id: Optional[UUID] = None,
    ward_id: Optional[UUID] = None,
    support_level: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Voter).where(Voter.is_deceased.is_(False))

    if constituency_id:
        query = query.where(Voter.constituency_id == constituency_id)
    if ward_id:
        query = query.where(Voter.ward_id == ward_id)
    if support_level:
        query = query.where(Voter.support_level == support_level)
    if q:
        query = query.where(
            or_(Voter.full_name.ilike(f"%{q}%"), Voter.id_number.ilike(f"%{q}%"))
        )

    query = query.order_by(Voter.full_name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats")
async def voter_stats(
    constituency_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    base = select(Voter).where(Voter.is_deceased.is_(False))
    if constituency_id:
        base = base.where(Voter.constituency_id == constituency_id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar()

    support_q = (
        select(Voter.support_level, func.count())
        .where(Voter.is_deceased.is_(False))
        .group_by(Voter.support_level)
    )
    if constituency_id:
        support_q = support_q.where(Voter.constituency_id == constituency_id)
    support_result = await db.execute(support_q)

    return {
        "total_voters": total,
        "by_support_level": {str(row[0]): row[1] for row in support_result.all()},
    }


@router.post("/", response_model=VoterResponse, status_code=status.HTTP_201_CREATED)
async def create_voter(body: VoterCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_field_agent)):
    existing = await db.execute(select(Voter).where(Voter.id_number == body.id_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Voter with this ID number exists")
    voter_data = body.model_dump()
    # Convert UUIDs to strings for SQLite
    if voter_data.get('constituency_id'):
        voter_data['constituency_id'] = str(voter_data['constituency_id'])
    if voter_data.get('ward_id'):
        voter_data['ward_id'] = str(voter_data['ward_id'])
    voter = Voter(**voter_data)
    db.add(voter)
    await db.flush()
    await db.refresh(voter)
    return voter


@router.get("/{voter_id}", response_model=VoterResponse)
async def get_voter(voter_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Voter).where(Voter.voter_id == voter_id))
    voter = result.scalar_one_or_none()
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    return voter


@router.patch("/{voter_id}", response_model=VoterResponse)
async def update_voter(
    voter_id: UUID, body: VoterUpdate, db: AsyncSession = Depends(get_db), _user=Depends(require_field_agent)
):
    result = await db.execute(select(Voter).where(Voter.voter_id == voter_id))
    voter = result.scalar_one_or_none()
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(voter, field, value)
    await db.flush()
    await db.refresh(voter)
    return voter


@router.get("/{voter_id}/interactions")
async def voter_interactions(voter_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    from app.models.operations import VoterInteraction
    result = await db.execute(
        select(VoterInteraction)
        .where(VoterInteraction.voter_id == voter_id)
        .order_by(VoterInteraction.interaction_at.desc())
        .limit(50)
    )
    interactions = result.scalars().all()
    return [
        {
            "interaction_id": str(i.interaction_id),
            "type": str(i.interaction_type),
            "source_table": i.source_table,
            "summary": i.summary,
            "interaction_at": i.interaction_at.isoformat() if i.interaction_at else None,
        }
        for i in interactions
    ]

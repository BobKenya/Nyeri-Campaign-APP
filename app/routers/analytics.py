"""Analytics routes: snapshots, trend queries."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.intel_election import AnalyticsSnapshot
from app.models.voters import Voter, Constituency
from app.models.messaging_finance import Donation, CampaignExpense
from app.models.operations import Event
from app.models.operations import Volunteer
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/snapshots")
async def list_snapshots(
    constituency_id: Optional[UUID] = None,
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(AnalyticsSnapshot)
    if constituency_id:
        query = query.where(AnalyticsSnapshot.constituency_id == constituency_id)
    query = query.order_by(AnalyticsSnapshot.snapshot_date.desc()).limit(limit)
    result = await db.execute(query)
    return [
        {
            "snapshot_date": s.snapshot_date.isoformat(),
            "constituency_id": str(s.constituency_id) if s.constituency_id else None,
            "support_percentage": float(s.support_percentage) if s.support_percentage else None,
            "canvass_coverage_pct": float(s.canvass_coverage_pct) if s.canvass_coverage_pct else None,
            "volunteer_hours": float(s.volunteer_hours_total) if s.volunteer_hours_total else None,
            "funds_raised_ksh": float(s.funds_raised_ksh) if s.funds_raised_ksh else None,
            "funds_spent_ksh": float(s.funds_spent_ksh) if s.funds_spent_ksh else None,
        }
        for s in result.scalars().all()
    ]


@router.get("/live-dashboard")
async def live_dashboard(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """Real-time campaign dashboard aggregating key metrics."""
    total_voters = (await db.execute(
        select(func.count()).select_from(Voter).where(Voter.is_deceased.is_(False))
    )).scalar() or 0

    total_donations = (await db.execute(select(func.sum(Donation.donation_amount)))).scalar() or 0
    total_expenses = (await db.execute(select(func.sum(CampaignExpense.amount)))).scalar() or 0

    total_events = (await db.execute(select(func.count()).select_from(Event))).scalar() or 0
    active_volunteers = (await db.execute(
        select(func.count()).select_from(Volunteer).where(Volunteer.status == "active")
    )).scalar() or 0

    support_breakdown = await db.execute(
        select(Voter.support_level, func.count())
        .where(Voter.is_deceased.is_(False))
        .group_by(Voter.support_level)
    )

    constituency_stats = await db.execute(
        select(
            Constituency.constituency_name,
            func.count(Voter.voter_id),
        )
        .outerjoin(Voter, Voter.constituency_id == Constituency.constituency_id)
        .group_by(Constituency.constituency_id)
        .order_by(Constituency.constituency_name)
    )

    return {
        "voters": {
            "total": total_voters,
            "by_support_level": {str(r[0]): r[1] for r in support_breakdown.all()},
        },
        "finance": {
            "total_raised_ksh": float(total_donations),
            "total_spent_ksh": float(total_expenses),
            "balance_ksh": float(total_donations - total_expenses),
        },
        "operations": {
            "total_events": total_events,
            "active_volunteers": active_volunteers,
        },
        "by_constituency": [
            {"name": r[0], "voters": r[1]} for r in constituency_stats.all()
        ],
    }

"""Election Day routes: candidates, dashboard, agents, incidents, results."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.intel_election import (
    Candidate, ElectionDayDashboard, PollingAgent, ElectionIncident,
    ProvisionalResult, ConstituencyResult,
)
from app.schemas.common import (
    CandidateCreate, CandidateResponse, ProvisionalResultCreate,
    IncidentCreate, PollingAgentCreate,
)
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()


# ── Candidates ────────────────────────────────────────────────────

@router.get("/candidates", response_model=list[CandidateResponse])
async def list_candidates(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Candidate).order_by(Candidate.ballot_order))
    return result.scalars().all()


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(body: CandidateCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_admin)):
    candidate = Candidate(**body.model_dump())
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


# ── Dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(
    constituency_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(ElectionDayDashboard)
    # Join with polling station -> ward -> constituency if filtering
    result = await db.execute(query)
    dashboards = result.scalars().all()

    total = len(dashboards)
    opened = sum(1 for d in dashboards if d.station_status in ("open", "voting", "counting"))
    closed = sum(1 for d in dashboards if d.station_status == "closed")
    total_turnout = sum(d.voting_turnout_count or 0 for d in dashboards)
    total_issues = sum(d.issues_reported_count or 0 for d in dashboards)

    return {
        "total_stations": total,
        "stations_opened": opened,
        "stations_closed": closed,
        "total_turnout": total_turnout,
        "total_issues": total_issues,
    }


# ── Polling Agents ────────────────────────────────────────────────

@router.get("/agents")
async def list_agents(
    polling_station_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(PollingAgent)
    if polling_station_id:
        query = query.where(PollingAgent.polling_station_id == polling_station_id)
    result = await db.execute(query.order_by(PollingAgent.full_name))
    return [
        {
            "agent_id": str(a.agent_id), "full_name": a.full_name,
            "polling_station_id": str(a.polling_station_id),
            "is_chief_agent": a.is_chief_agent,
            "accreditation_status": str(a.accreditation_status) if a.accreditation_status else None,
        }
        for a in result.scalars().all()
    ]


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(body: PollingAgentCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    agent = PollingAgent(**body.model_dump())
    db.add(agent)
    await db.flush()
    return {"agent_id": str(agent.agent_id), "message": "Polling agent registered"}


# ── Incidents ─────────────────────────────────────────────────────

@router.get("/incidents")
async def list_incidents(
    resolution_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(ElectionIncident)
    if resolution_status:
        query = query.where(ElectionIncident.resolution_status == resolution_status)
    result = await db.execute(query.order_by(ElectionIncident.created_at.desc()))
    return [
        {
            "incident_id": str(i.incident_id),
            "polling_station_id": str(i.polling_station_id),
            "incident_type": str(i.incident_type),
            "description": i.description,
            "resolution_status": str(i.resolution_status),
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in result.scalars().all()
    ]


@router.post("/incidents", status_code=status.HTTP_201_CREATED)
async def report_incident(body: IncidentCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    incident = ElectionIncident(reported_by_user_id=user.user_id, **body.model_dump())
    db.add(incident)
    await db.flush()
    return {"incident_id": str(incident.incident_id), "message": "Incident reported"}


# ── Results ───────────────────────────────────────────────────────

@router.post("/results", status_code=status.HTTP_201_CREATED)
async def submit_result(body: ProvisionalResultCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = ProvisionalResult(**body.model_dump())
    db.add(result)
    await db.flush()
    return {"result_id": str(result.result_id), "message": "Result submitted"}


@router.get("/results/tally")
async def results_tally(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """Aggregate Form 34A results by candidate."""
    result = await db.execute(
        select(
            Candidate.full_name,
            Candidate.political_party,
            func.sum(ProvisionalResult.candidate_votes).label("total_votes"),
            func.count(ProvisionalResult.result_id).label("stations_counted"),
        )
        .join(ProvisionalResult, ProvisionalResult.candidate_id == Candidate.candidate_id)
        .group_by(Candidate.candidate_id)
        .order_by(func.sum(ProvisionalResult.candidate_votes).desc())
    )
    return [
        {
            "candidate": row[0], "party": row[1],
            "total_votes": int(row[2]) if row[2] else 0,
            "stations_counted": row[3],
        }
        for row in result.all()
    ]


@router.get("/results/constituency/{constituency_id}")
async def constituency_results(constituency_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(ConstituencyResult)
        .where(ConstituencyResult.constituency_id == constituency_id)
        .order_by(ConstituencyResult.total_votes.desc())
    )
    return [
        {
            "candidate_id": str(r.candidate_id),
            "total_votes": r.total_votes,
            "total_valid": r.total_valid,
            "stations_reporting": r.stations_reporting,
            "total_stations": r.total_stations,
        }
        for r in result.scalars().all()
    ]

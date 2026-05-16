"""Volunteer routes: CRUD, shifts, event assignments."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.operations import Volunteer, VolunteerShift, EventVolunteer
from app.schemas.common import VolunteerCreate, VolunteerResponse, ShiftCreate
from app.dependencies import get_current_user, require_coordinator

router = APIRouter()


@router.get("/", response_model=list[VolunteerResponse])
async def list_volunteers(
    status_filter: Optional[str] = None,
    constituency_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Volunteer)
    if status_filter:
        query = query.where(Volunteer.status == status_filter)
    if constituency_id:
        query = query.where(Volunteer.constituency_id == constituency_id)
    query = query.order_by(Volunteer.full_name).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=VolunteerResponse, status_code=status.HTTP_201_CREATED)
async def create_volunteer(body: VolunteerCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    volunteer = Volunteer(**body.model_dump())
    db.add(volunteer)
    await db.flush()
    await db.refresh(volunteer)
    return volunteer


@router.get("/{volunteer_id}", response_model=VolunteerResponse)
async def get_volunteer(volunteer_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Volunteer).where(Volunteer.volunteer_id == volunteer_id))
    vol = result.scalar_one_or_none()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    return vol


@router.post("/shifts", status_code=status.HTTP_201_CREATED)
async def create_shift(body: ShiftCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    shift = VolunteerShift(**body.model_dump())
    db.add(shift)
    await db.flush()
    return {"shift_id": str(shift.shift_id), "message": "Shift created"}


@router.get("/{volunteer_id}/shifts")
async def get_volunteer_shifts(volunteer_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(VolunteerShift).where(VolunteerShift.volunteer_id == volunteer_id).order_by(VolunteerShift.shift_date.desc())
    )
    shifts = result.scalars().all()
    return [
        {
            "shift_id": str(s.shift_id),
            "shift_date": s.shift_date.isoformat(),
            "location": s.location,
            "status": str(s.status) if s.status else None,
            "hours_worked": float(s.hours_worked) if s.hours_worked else None,
        }
        for s in shifts
    ]

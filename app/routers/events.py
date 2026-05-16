"""Event routes: CRUD, attendees, tasks."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.operations import Event, EventAttendee, EventTask
from app.schemas.common import EventCreate, EventUpdate, EventResponse, EventAttendeeCreate
from app.dependencies import get_current_user, require_coordinator

router = APIRouter()


@router.get("/", response_model=list[EventResponse])
async def list_events(
    event_type: Optional[str] = None,
    event_status: Optional[str] = None,
    constituency_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Event)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if event_status:
        query = query.where(Event.event_status == event_status)
    if constituency_id:
        query = query.where(Event.constituency_id == constituency_id)
    query = query.order_by(Event.event_date.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(body: EventCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    event = Event(**body.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(event_id: UUID, body: EventUpdate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await db.flush()
    await db.refresh(event)
    return event


@router.post("/{event_id}/attendees", status_code=status.HTTP_201_CREATED)
async def add_attendee(event_id: UUID, body: EventAttendeeCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    attendee = EventAttendee(event_id=event_id, **body.model_dump())
    db.add(attendee)
    await db.flush()
    return {"attendee_id": str(attendee.attendee_id), "message": "Attendee registered"}


@router.get("/{event_id}/attendees")
async def list_attendees(event_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(EventAttendee).where(EventAttendee.event_id == event_id))
    return [
        {
            "attendee_id": str(a.attendee_id),
            "voter_id": str(a.voter_id) if a.voter_id else None,
            "check_in_time": a.check_in_time.isoformat() if a.check_in_time else None,
        }
        for a in result.scalars().all()
    ]


@router.get("/{event_id}/stats")
async def event_stats(event_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    attendee_count = (await db.execute(
        select(func.count()).select_from(EventAttendee).where(EventAttendee.event_id == event_id)
    )).scalar()
    checked_in = (await db.execute(
        select(func.count()).select_from(EventAttendee)
        .where(EventAttendee.event_id == event_id, EventAttendee.check_in_time.isnot(None))
    )).scalar()
    return {"registered": attendee_count, "checked_in": checked_in}

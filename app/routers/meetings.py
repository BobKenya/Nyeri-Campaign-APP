"""Meetings: schedule, recurring series, attendance, minutes, governor briefing."""

from typing import Optional
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from app.database import get_db
from app.models.meetings import Meeting, MeetingSeries, MeetingAttendee, MeetingMinutes
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MeetingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    meeting_type: str = "weekly_review"
    meeting_date: date
    start_time: str = "09:00"
    end_time: Optional[str] = "10:00"
    duration_minutes: int = 60
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_latitude: Optional[float] = None
    venue_longitude: Optional[float] = None
    is_virtual: bool = False
    virtual_link: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    target_group: Optional[str] = "all"
    agenda_json: Optional[list] = []

class SeriesCreate(BaseModel):
    title: str
    description: Optional[str] = None
    meeting_type: str = "weekly_review"
    recurrence: str  # daily, weekly, biweekly, monthly
    day_of_week: Optional[str] = None  # monday-sunday
    day_of_month: Optional[int] = None  # 1-28
    start_time: str = "09:00"
    end_time: Optional[str] = "10:00"
    duration_minutes: int = 60
    starts_on: date
    ends_on: Optional[date] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    target_group: Optional[str] = "all"
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    is_virtual: bool = False
    virtual_link: Optional[str] = None
    default_agenda_json: Optional[list] = []

class AttendeeAdd(BaseModel):
    user_id: Optional[str] = None
    agent_profile_id: Optional[str] = None
    external_name: Optional[str] = None
    external_phone: Optional[str] = None
    role: str = "attendee"

class MinutesCreate(BaseModel):
    content: str
    decisions_json: Optional[list] = []
    action_items_json: Optional[list] = []
    issues_raised_json: Optional[list] = []
    next_meeting_date: Optional[date] = None
    next_meeting_notes: Optional[str] = None
    governor_summary: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SINGLE MEETINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/")
async def list_meetings(
    meeting_type: Optional[str] = None,
    ward_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    target_group: Optional[str] = None,
    status_filter: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Meeting)
    if meeting_type:
        query = query.where(Meeting.meeting_type == meeting_type)
    if ward_id:
        query = query.where(Meeting.ward_id == ward_id)
    if constituency_id:
        query = query.where(Meeting.constituency_id == constituency_id)
    if target_group:
        query = query.where(Meeting.target_group == target_group)
    if status_filter:
        query = query.where(Meeting.status == status_filter)
    if from_date:
        query = query.where(Meeting.meeting_date >= from_date)
    if to_date:
        query = query.where(Meeting.meeting_date <= to_date)
    query = query.order_by(Meeting.meeting_date.desc(), Meeting.start_time.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "meeting_id": m.meeting_id, "title": m.title, "meeting_type": m.meeting_type,
            "meeting_date": m.meeting_date.isoformat(), "start_time": m.start_time,
            "end_time": m.end_time, "venue_name": m.venue_name,
            "is_virtual": m.is_virtual, "target_group": m.target_group,
            "ward_id": m.ward_id, "constituency_id": m.constituency_id,
            "status": m.status, "series_id": m.series_id,
        }
        for m in result.scalars().all()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_meeting(body: MeetingCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    meeting = Meeting(organized_by_user_id=user.user_id, **body.model_dump())
    db.add(meeting)
    await db.flush()
    return {"meeting_id": meeting.meeting_id, "message": f"Meeting '{meeting.title}' scheduled for {meeting.meeting_date}"}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Get attendees
    att_result = await db.execute(select(MeetingAttendee).where(MeetingAttendee.meeting_id == meeting_id))
    attendees = [
        {
            "attendee_id": a.attendee_id, "user_id": a.user_id,
            "agent_profile_id": a.agent_profile_id,
            "external_name": a.external_name, "role": a.role,
            "rsvp_status": a.rsvp_status, "attended": a.attended,
            "check_in_time": a.check_in_time.isoformat() if a.check_in_time else None,
            "absence_reason": a.absence_reason,
        }
        for a in att_result.scalars().all()
    ]

    return {
        "meeting_id": m.meeting_id, "title": m.title, "description": m.description,
        "meeting_type": m.meeting_type, "meeting_date": m.meeting_date.isoformat(),
        "start_time": m.start_time, "end_time": m.end_time,
        "duration_minutes": m.duration_minutes,
        "venue_name": m.venue_name, "venue_address": m.venue_address,
        "venue_latitude": m.venue_latitude, "venue_longitude": m.venue_longitude,
        "is_virtual": m.is_virtual, "virtual_link": m.virtual_link,
        "constituency_id": m.constituency_id, "ward_id": m.ward_id,
        "target_group": m.target_group, "status": m.status,
        "agenda": m.agenda_json, "summary": m.summary,
        "action_items": m.action_items_json,
        "series_id": m.series_id,
        "attendees": attendees,
    }


@router.patch("/{meeting_id}")
async def update_meeting(meeting_id: str, updates: dict, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    allowed = {
        "title", "description", "meeting_date", "start_time", "end_time",
        "venue_name", "venue_address", "venue_latitude", "venue_longitude",
        "is_virtual", "virtual_link", "target_group", "status",
        "cancellation_reason", "agenda_json", "summary", "action_items_json",
        "actual_start_time", "actual_end_time", "duration_minutes",
    }
    for k, v in updates.items():
        if k in allowed:
            setattr(m, k, v)
    m.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Meeting updated"}


@router.patch("/{meeting_id}/cancel")
async def cancel_meeting(meeting_id: str, reason: Optional[str] = None, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    m.status = "cancelled"
    m.cancellation_reason = reason
    await db.flush()
    return {"message": f"Meeting '{m.title}' cancelled"}


@router.patch("/{meeting_id}/complete")
async def complete_meeting(meeting_id: str, summary: Optional[str] = None, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    m.status = "completed"
    if summary:
        m.summary = summary
    await db.flush()
    return {"message": f"Meeting '{m.title}' marked complete"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RECURRING SERIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/series", status_code=status.HTTP_201_CREATED)
async def create_series(body: SeriesCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    """Create a recurring meeting series and auto-generate upcoming meetings."""
    series = MeetingSeries(organized_by_user_id=user.user_id, **body.model_dump())
    db.add(series)
    await db.flush()

    # Generate meetings for next 90 days (or until ends_on)
    generated = await _generate_series_meetings(db, series, user.user_id, days_ahead=90)

    return {
        "series_id": series.series_id,
        "message": f"Recurring '{series.recurrence}' series created",
        "meetings_generated": generated,
    }


@router.get("/series")
async def list_series(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(MeetingSeries).where(MeetingSeries.is_active == True).order_by(MeetingSeries.title))
    return [
        {
            "series_id": s.series_id, "title": s.title, "recurrence": s.recurrence,
            "meeting_type": s.meeting_type, "day_of_week": s.day_of_week,
            "day_of_month": s.day_of_month, "start_time": s.start_time,
            "target_group": s.target_group, "ward_id": s.ward_id,
            "constituency_id": s.constituency_id, "is_active": s.is_active,
            "total_meetings_generated": s.total_meetings_generated,
        }
        for s in result.scalars().all()
    ]


@router.post("/series/{series_id}/generate")
async def generate_more_meetings(series_id: str, days_ahead: int = Query(30, ge=7, le=180), db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    """Extend a series by generating more future meetings."""
    result = await db.execute(select(MeetingSeries).where(MeetingSeries.series_id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    generated = await _generate_series_meetings(db, series, user.user_id, days_ahead)
    return {"message": f"Generated {generated} additional meetings"}


async def _generate_series_meetings(db: AsyncSession, series: MeetingSeries, user_id: str, days_ahead: int = 90) -> int:
    """Internal: generate individual Meeting records from a series pattern."""
    today = date.today()
    end_date = min(today + timedelta(days=days_ahead), series.ends_on) if series.ends_on else today + timedelta(days=days_ahead)
    start_date = max(today, series.starts_on)

    DAY_MAP = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}

    dates_to_create = []
    current = start_date

    while current <= end_date:
        should_add = False
        if series.recurrence == "daily":
            should_add = True
        elif series.recurrence == "weekly" and series.day_of_week:
            if current.weekday() == DAY_MAP.get(series.day_of_week.lower(), -1):
                should_add = True
        elif series.recurrence == "biweekly" and series.day_of_week:
            if current.weekday() == DAY_MAP.get(series.day_of_week.lower(), -1):
                week_num = (current - series.starts_on).days // 7
                if week_num % 2 == 0:
                    should_add = True
        elif series.recurrence == "monthly" and series.day_of_month:
            if current.day == series.day_of_month:
                should_add = True

        if should_add:
            dates_to_create.append(current)
        current += timedelta(days=1)

    count = 0
    for d in dates_to_create:
        # Check not already created
        existing = await db.execute(
            select(Meeting).where(Meeting.series_id == series.series_id, Meeting.meeting_date == d)
        )
        if existing.scalar_one_or_none():
            continue

        meeting = Meeting(
            series_id=series.series_id,
            title=series.title,
            description=series.description,
            meeting_type=series.meeting_type,
            meeting_date=d,
            start_time=series.start_time,
            end_time=series.end_time,
            duration_minutes=series.duration_minutes,
            constituency_id=series.constituency_id,
            ward_id=series.ward_id,
            target_group=series.target_group,
            venue_name=series.venue_name,
            venue_address=series.venue_address,
            venue_latitude=series.venue_latitude,
            venue_longitude=series.venue_longitude,
            is_virtual=series.is_virtual,
            virtual_link=series.virtual_link,
            agenda_json=series.default_agenda_json or [],
            organized_by_user_id=user_id,
        )
        db.add(meeting)
        count += 1

    series.total_meetings_generated = (series.total_meetings_generated or 0) + count
    await db.flush()
    return count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ATTENDEES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{meeting_id}/attendees", status_code=status.HTTP_201_CREATED)
async def add_attendee(meeting_id: str, body: AttendeeAdd, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    attendee = MeetingAttendee(meeting_id=meeting_id, **body.model_dump())
    db.add(attendee)
    await db.flush()
    return {"attendee_id": attendee.attendee_id, "message": "Attendee added"}


@router.post("/{meeting_id}/attendees/bulk", status_code=status.HTTP_201_CREATED)
async def add_attendees_bulk(meeting_id: str, attendees: list[AttendeeAdd], db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    """Add multiple attendees at once."""
    count = 0
    for a in attendees:
        att = MeetingAttendee(meeting_id=meeting_id, **a.model_dump())
        db.add(att)
        count += 1
    await db.flush()
    return {"message": f"Added {count} attendees"}


@router.patch("/{meeting_id}/attendees/{attendee_id}/rsvp")
async def update_rsvp(meeting_id: str, attendee_id: str, rsvp_status: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(MeetingAttendee).where(MeetingAttendee.attendee_id == attendee_id))
    att = result.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attendee not found")
    att.rsvp_status = rsvp_status
    await db.flush()
    return {"message": f"RSVP updated to {rsvp_status}"}


@router.post("/{meeting_id}/attendees/{attendee_id}/check-in")
async def check_in_attendee(
    meeting_id: str, attendee_id: str,
    latitude: Optional[float] = None, longitude: Optional[float] = None,
    db: AsyncSession = Depends(get_db), _user=Depends(get_current_user),
):
    result = await db.execute(select(MeetingAttendee).where(MeetingAttendee.attendee_id == attendee_id))
    att = result.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attendee not found")
    att.attended = True
    att.check_in_time = datetime.now(timezone.utc)
    att.check_in_latitude = latitude
    att.check_in_longitude = longitude
    await db.flush()
    return {"message": "Checked in", "time": att.check_in_time.isoformat()}


@router.get("/{meeting_id}/attendance")
async def get_attendance(meeting_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    atts = (await db.execute(
        select(MeetingAttendee).where(MeetingAttendee.meeting_id == meeting_id)
    )).scalars().all()
    total = len(atts)
    attended = sum(1 for a in atts if a.attended)
    absent = total - attended
    return {
        "total_invited": total,
        "attended": attended,
        "absent": absent,
        "attendance_rate": round(attended / total * 100, 1) if total else 0,
        "by_rsvp": {
            "accepted": sum(1 for a in atts if a.rsvp_status == "accepted"),
            "declined": sum(1 for a in atts if a.rsvp_status == "declined"),
            "pending": sum(1 for a in atts if a.rsvp_status == "pending"),
            "tentative": sum(1 for a in atts if a.rsvp_status == "tentative"),
        },
        "absentees": [
            {"attendee_id": a.attendee_id, "external_name": a.external_name, "user_id": a.user_id, "absence_reason": a.absence_reason}
            for a in atts if not a.attended
        ],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MINUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{meeting_id}/minutes", status_code=status.HTTP_201_CREATED)
async def create_minutes(meeting_id: str, body: MinutesCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    existing = await db.execute(select(MeetingMinutes).where(MeetingMinutes.meeting_id == meeting_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Minutes already recorded")
    minutes = MeetingMinutes(meeting_id=meeting_id, recorded_by_user_id=user.user_id, **body.model_dump())
    db.add(minutes)

    # Also update meeting action items
    meeting = (await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))).scalar_one_or_none()
    if meeting and body.action_items_json:
        meeting.action_items_json = body.action_items_json

    await db.flush()
    return {"minutes_id": minutes.minutes_id, "message": "Minutes recorded"}


@router.get("/{meeting_id}/minutes")
async def get_minutes(meeting_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(MeetingMinutes).where(MeetingMinutes.meeting_id == meeting_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="No minutes recorded")
    return {
        "minutes_id": m.minutes_id, "content": m.content,
        "decisions": m.decisions_json, "action_items": m.action_items_json,
        "issues_raised": m.issues_raised_json,
        "next_meeting_date": m.next_meeting_date.isoformat() if m.next_meeting_date else None,
        "governor_summary": m.governor_summary,
        "governor_viewed": m.governor_viewed,
        "approved": m.approved,
    }


@router.patch("/{meeting_id}/minutes/approve")
async def approve_minutes(meeting_id: str, db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    result = await db.execute(select(MeetingMinutes).where(MeetingMinutes.meeting_id == meeting_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="No minutes found")
    m.approved = True
    m.approved_by_user_id = user.user_id
    m.approved_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Minutes approved"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GOVERNOR'S MEETING DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/dashboard")
async def meetings_dashboard(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Governor's overview of all meetings across the campaign."""
    today = date.today()
    from_date = today - timedelta(days=days)
    to_date = today + timedelta(days=days)

    # Upcoming
    upcoming = (await db.execute(
        select(func.count()).select_from(Meeting)
        .where(Meeting.meeting_date >= today, Meeting.status.in_(["scheduled", "confirmed"]))
    )).scalar() or 0

    # Completed recently
    completed = (await db.execute(
        select(func.count()).select_from(Meeting)
        .where(Meeting.meeting_date >= from_date, Meeting.status == "completed")
    )).scalar() or 0

    # Cancelled
    cancelled = (await db.execute(
        select(func.count()).select_from(Meeting)
        .where(Meeting.meeting_date >= from_date, Meeting.status == "cancelled")
    )).scalar() or 0

    # Today's meetings
    today_meetings = (await db.execute(
        select(Meeting).where(Meeting.meeting_date == today).order_by(Meeting.start_time)
    )).scalars().all()

    # Upcoming week
    week_meetings = (await db.execute(
        select(Meeting).where(
            Meeting.meeting_date >= today,
            Meeting.meeting_date <= today + timedelta(days=7),
            Meeting.status.in_(["scheduled", "confirmed"]),
        ).order_by(Meeting.meeting_date, Meeting.start_time)
    )).scalars().all()

    # Unviewed minutes
    unviewed_minutes = (await db.execute(
        select(func.count()).select_from(MeetingMinutes)
        .where(MeetingMinutes.governor_viewed == False, MeetingMinutes.governor_summary.isnot(None))
    )).scalar() or 0

    # Active series
    active_series = (await db.execute(
        select(func.count()).select_from(MeetingSeries).where(MeetingSeries.is_active == True)
    )).scalar() or 0

    # Attendance rate (last N days)
    total_att = (await db.execute(
        select(func.count()).select_from(MeetingAttendee)
        .join(Meeting, MeetingAttendee.meeting_id == Meeting.meeting_id)
        .where(Meeting.meeting_date >= from_date, Meeting.status == "completed")
    )).scalar() or 0
    attended_att = (await db.execute(
        select(func.count()).select_from(MeetingAttendee)
        .join(Meeting, MeetingAttendee.meeting_id == Meeting.meeting_id)
        .where(Meeting.meeting_date >= from_date, Meeting.status == "completed", MeetingAttendee.attended == True)
    )).scalar() or 0

    return {
        "summary": {
            "upcoming_meetings": upcoming,
            "completed_last_{}_days".format(days): completed,
            "cancelled": cancelled,
            "active_recurring_series": active_series,
            "unviewed_minutes": unviewed_minutes,
            "avg_attendance_rate": round(attended_att / total_att * 100, 1) if total_att else 0,
        },
        "today": [
            {"meeting_id": m.meeting_id, "title": m.title, "start_time": m.start_time, "venue_name": m.venue_name, "target_group": m.target_group, "status": m.status}
            for m in today_meetings
        ],
        "this_week": [
            {"meeting_id": m.meeting_id, "title": m.title, "meeting_date": m.meeting_date.isoformat(), "start_time": m.start_time, "target_group": m.target_group, "ward_id": m.ward_id}
            for m in week_meetings
        ],
    }

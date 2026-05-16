"""Meetings: scheduling, recurrence, attendance, minutes for coordinators/mobilizers/agents."""
import uuid
from datetime import datetime, date, time, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index, Time
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())


class Meeting(Base):
    """A scheduled meeting — one-time or part of a recurring series."""
    __tablename__ = "meetings"

    meeting_id = Column(String(36), primary_key=True, default=genuuid)
    series_id = Column(String(36), ForeignKey("meeting_series.series_id"))  # null if one-time

    # Basic info
    title = Column(String(300), nullable=False)
    description = Column(Text)
    meeting_type = Column(String(30), nullable=False)
    # daily_standup, weekly_review, monthly_strategy, ad_hoc, training, emergency, debrief

    # Schedule
    meeting_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(10), nullable=False)  # "09:00"
    end_time = Column(String(10))  # "10:30"
    duration_minutes = Column(Integer, default=60)
    timezone_str = Column(String(50), default="Africa/Nairobi")

    # Location
    venue_name = Column(String(300))
    venue_address = Column(Text)
    venue_latitude = Column(Float)
    venue_longitude = Column(Float)
    is_virtual = Column(Boolean, default=False)
    virtual_link = Column(Text)  # Zoom/Meet/Teams link
    virtual_passcode = Column(String(50))

    # Scope
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    target_group = Column(String(50))
    # all, ward_coordinators, mobilizers, agents, polling_agents, finance, comms

    # Organizer
    organized_by_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)

    # Status
    status = Column(String(20), default="scheduled")
    # scheduled, confirmed, in_progress, completed, cancelled, postponed
    cancellation_reason = Column(Text)
    postponed_to_meeting_id = Column(String(36), ForeignKey("meetings.meeting_id"))

    # Agenda
    agenda_json = Column(JSON, default=list)
    # [{"order":1,"topic":"Budget review","duration_min":15,"presenter":"John"},...]
    agenda_document_url = Column(Text)

    # Post-meeting
    actual_start_time = Column(String(10))
    actual_end_time = Column(String(10))
    summary = Column(Text)
    action_items_json = Column(JSON, default=list)
    # [{"task":"Print 500 flyers","assigned_to":"Mary","deadline":"2026-05-01","status":"pending"},...]

    # Notifications
    reminder_sent = Column(Boolean, default=False)
    reminder_hours_before = Column(Integer, default=24)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    attendees = relationship("MeetingAttendee", back_populates="meeting", cascade="all, delete-orphan")
    minutes = relationship("MeetingMinutes", back_populates="meeting", uselist=False)
    series = relationship("MeetingSeries", back_populates="meetings")

    __table_args__ = (
        Index("ix_meeting_date_type", "meeting_date", "meeting_type"),
        Index("ix_meeting_ward", "ward_id", "meeting_date"),
        Index("ix_meeting_constituency", "constituency_id", "meeting_date"),
        Index("ix_meeting_series", "series_id", "meeting_date"),
    )


class MeetingSeries(Base):
    """Defines a recurring meeting pattern — generates individual Meeting instances."""
    __tablename__ = "meeting_series"

    series_id = Column(String(36), primary_key=True, default=genuuid)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    meeting_type = Column(String(30), nullable=False)

    # Recurrence pattern
    recurrence = Column(String(20), nullable=False)  # daily, weekly, biweekly, monthly
    day_of_week = Column(String(10))  # monday, tuesday, ... (for weekly/biweekly)
    day_of_month = Column(Integer)  # 1-28 (for monthly)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10))
    duration_minutes = Column(Integer, default=60)

    # Scope
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    target_group = Column(String(50))

    # Location defaults
    venue_name = Column(String(300))
    venue_address = Column(Text)
    venue_latitude = Column(Float)
    venue_longitude = Column(Float)
    is_virtual = Column(Boolean, default=False)
    virtual_link = Column(Text)

    # Default agenda
    default_agenda_json = Column(JSON, default=list)

    # Series lifecycle
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date)  # null = indefinite
    is_active = Column(Boolean, default=True)
    total_meetings_generated = Column(Integer, default=0)

    organized_by_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    meetings = relationship("Meeting", back_populates="series", order_by="Meeting.meeting_date")


class MeetingAttendee(Base):
    """Who is invited/attended a meeting — links to users, agents, or external names."""
    __tablename__ = "meeting_attendees"

    attendee_id = Column(String(36), primary_key=True, default=genuuid)
    meeting_id = Column(String(36), ForeignKey("meetings.meeting_id"), nullable=False, index=True)

    # Who (at least one should be set)
    user_id = Column(String(36), ForeignKey("users.user_id"))
    agent_profile_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"))
    external_name = Column(String(200))  # for people not in the system
    external_phone = Column(String(20))

    # Role in meeting
    role = Column(String(30), default="attendee")
    # organizer, chair, presenter, attendee, observer, minute_taker

    # Attendance tracking
    rsvp_status = Column(String(20), default="pending")  # pending, accepted, declined, tentative
    attended = Column(Boolean, default=False)
    check_in_time = Column(DateTime)
    check_in_latitude = Column(Float)
    check_in_longitude = Column(Float)
    check_out_time = Column(DateTime)

    # Excuses
    absence_reason = Column(Text)
    apology_sent = Column(Boolean, default=False)

    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime)

    meeting = relationship("Meeting", back_populates="attendees")

    __table_args__ = (
        Index("ix_attendee_user", "user_id", "meeting_id"),
        Index("ix_attendee_agent", "agent_profile_id", "meeting_id"),
    )


class MeetingMinutes(Base):
    """Official minutes for a completed meeting."""
    __tablename__ = "meeting_minutes"

    minutes_id = Column(String(36), primary_key=True, default=genuuid)
    meeting_id = Column(String(36), ForeignKey("meetings.meeting_id"), nullable=False, unique=True)

    content = Column(Text, nullable=False)  # full text of minutes
    decisions_json = Column(JSON, default=list)
    # [{"decision":"Increase Tetu budget by 20%","decided_by":"vote","votes_for":8,"votes_against":2}]

    action_items_json = Column(JSON, default=list)
    # [{"task":"Print posters","assigned_to":"James","deadline":"2026-05-10","status":"pending"}]

    issues_raised_json = Column(JSON, default=list)
    # [{"issue":"Lack of t-shirts in Mathira","raised_by":"Mary","resolution":"Order 1000 more"}]

    next_meeting_date = Column(Date)
    next_meeting_notes = Column(Text)

    recorded_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    approved = Column(Boolean, default=False)
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    approved_at = Column(DateTime)

    # Governor briefing
    governor_summary = Column(Text)  # concise summary for the governor
    governor_viewed = Column(Boolean, default=False)
    governor_viewed_at = Column(DateTime)

    document_url = Column(Text)  # uploaded PDF/doc of signed minutes

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    meeting = relationship("Meeting", back_populates="minutes")

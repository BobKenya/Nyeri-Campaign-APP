"""Field Operations, Volunteers, Events models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Time, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())

# ── Field Ops ──────────────────────────────────────────────────────

class CanvassingRoute(Base):
    __tablename__ = "canvassing_routes"
    route_id = Column(String(36), primary_key=True, default=genuuid)
    route_name = Column(String(200), nullable=False)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False)
    assigned_to_user_id = Column(String(36), ForeignKey("users.user_id"))
    route_geometry_json = Column(Text)
    estimated_houses = Column(Integer)
    created_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=utcnow)
    contacts = relationship("CanvassingContact", back_populates="route")

class CanvassingContact(Base):
    __tablename__ = "canvassing_contacts"
    contact_id = Column(String(36), primary_key=True, default=genuuid)
    route_id = Column(String(36), ForeignKey("canvassing_routes.route_id"), nullable=False)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"), nullable=False)
    contact_timestamp = Column(DateTime, default=utcnow)
    contact_type = Column(String(20), default="door_to_door")
    contact_result = Column(String(20))
    issues_discussed = Column(Text)
    sentiment_score = Column(Float)
    gps_latitude = Column(Float)
    gps_longitude = Column(Float)
    created_at = Column(DateTime, default=utcnow)
    route = relationship("CanvassingRoute", back_populates="contacts")

class VoterInteraction(Base):
    __tablename__ = "voter_interactions"
    interaction_id = Column(String(36), primary_key=True, default=genuuid)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"), nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False)
    source_table = Column(String(50), nullable=False)
    source_id = Column(String(36), nullable=False)
    summary = Column(Text)
    interaction_at = Column(DateTime, default=utcnow)

# ── Volunteers ─────────────────────────────────────────────────────

class Volunteer(Base):
    __tablename__ = "volunteers"
    volunteer_id = Column(String(36), primary_key=True, default=genuuid)
    user_id = Column(String(36), ForeignKey("users.user_id"), unique=True)
    full_name = Column(String(200), nullable=False)
    id_number = Column(String(20), index=True)
    phone_number = Column(String(20))
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    skills_json = Column(JSON, default=list)
    emergency_contact = Column(String(200))
    status = Column(String(20), default="pending")
    training_completed_at = Column(DateTime)
    background_check_status = Column(String(20), default="not_started")
    vetting_notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    shifts = relationship("VolunteerShift", back_populates="volunteer")
    event_assignments = relationship("EventVolunteer", back_populates="volunteer")

class VolunteerShift(Base):
    __tablename__ = "volunteer_shifts"
    shift_id = Column(String(36), primary_key=True, default=genuuid)
    volunteer_id = Column(String(36), ForeignKey("volunteers.volunteer_id"), nullable=False)
    event_id = Column(String(36), ForeignKey("events.event_id"))
    shift_date = Column(Date, nullable=False)
    start_time = Column(String(10))
    end_time = Column(String(10))
    location = Column(String(300))
    hours_worked = Column(Float)
    check_in_time = Column(DateTime)
    status = Column(String(20), default="scheduled")
    volunteer = relationship("Volunteer", back_populates="shifts")

class EventVolunteer(Base):
    __tablename__ = "event_volunteers"
    event_id = Column(String(36), ForeignKey("events.event_id"), primary_key=True)
    volunteer_id = Column(String(36), ForeignKey("volunteers.volunteer_id"), primary_key=True)
    role = Column(String(100))
    assigned_at = Column(DateTime, default=utcnow)
    confirmed = Column(Boolean, default=False)
    volunteer = relationship("Volunteer", back_populates="event_assignments")

# ── Events ─────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"
    event_id = Column(String(36), primary_key=True, default=genuuid)
    event_name = Column(String(300), nullable=False)
    event_type = Column(String(30), nullable=False)
    event_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(10))
    end_time = Column(String(10))
    venue_address = Column(Text)
    venue_latitude = Column(Float)
    venue_longitude = Column(Float)
    expected_attendance = Column(Integer)
    actual_attendance = Column(Integer)
    event_status = Column(String(20), default="draft")
    budget_allocated = Column(Float)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    cancellation_reason = Column(Text)
    rescheduled_from_id = Column(String(36), ForeignKey("events.event_id"))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    attendees = relationship("EventAttendee", back_populates="event")
    tasks = relationship("EventTask", back_populates="event")

class EventAttendee(Base):
    __tablename__ = "event_attendees"
    attendee_id = Column(String(36), primary_key=True, default=genuuid)
    event_id = Column(String(36), ForeignKey("events.event_id"), nullable=False)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"))
    user_id = Column(String(36), ForeignKey("users.user_id"))
    registration_date = Column(Date)
    check_in_time = Column(DateTime)
    feedback_content = Column(Text)
    event = relationship("Event", back_populates="attendees")

class EventTask(Base):
    __tablename__ = "event_tasks"
    task_id = Column(String(36), primary_key=True, default=genuuid)
    event_id = Column(String(36), ForeignKey("events.event_id"), nullable=False)
    activity = Column(String(300), nullable=False)
    assigned_to_user_id = Column(String(36), ForeignKey("users.user_id"))
    priority = Column(String(10), default="medium")
    status = Column(String(20), default="todo")
    completed_at = Column(DateTime)
    event = relationship("Event", back_populates="tasks")

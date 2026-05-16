"""Pydantic schemas for events, volunteers, messaging, finance, intelligence, election day, analytics."""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


# ── Events ──────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    event_name: str
    event_type: str
    event_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_address: Optional[str] = None
    expected_attendance: Optional[int] = None
    budget_allocated: Optional[float] = None
    constituency_id: Optional[UUID] = None
    ward_id: Optional[UUID] = None

class EventUpdate(BaseModel):
    event_name: Optional[str] = None
    event_status: Optional[str] = None
    actual_attendance: Optional[int] = None
    cancellation_reason: Optional[str] = None

class EventResponse(BaseModel):
    event_id: UUID
    event_name: str
    event_type: str
    event_date: date
    event_status: Optional[str]
    venue_address: Optional[str]
    expected_attendance: Optional[int]
    actual_attendance: Optional[int]
    constituency_id: Optional[UUID]
    created_at: datetime
    class Config:
        from_attributes = True

class EventAttendeeCreate(BaseModel):
    voter_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


# ── Volunteers ──────────────────────────────────────────────────────

class VolunteerCreate(BaseModel):
    full_name: str
    id_number: Optional[str] = None
    phone_number: Optional[str] = None
    constituency_id: Optional[UUID] = None
    ward_id: Optional[UUID] = None
    skills_json: Optional[list] = []

class VolunteerResponse(BaseModel):
    volunteer_id: UUID
    full_name: str
    phone_number: Optional[str]
    status: Optional[str]
    training_completed_at: Optional[datetime]
    background_check_status: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class ShiftCreate(BaseModel):
    volunteer_id: UUID
    event_id: Optional[UUID] = None
    shift_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None


# ── Messaging ───────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    message_type: str
    subject: Optional[str] = None
    message_content: str
    template_id: Optional[UUID] = None
    recipient_group_id: Optional[UUID] = None
    scheduled_send_at: Optional[datetime] = None

class MessageResponse(BaseModel):
    message_id: UUID
    message_type: str
    subject: Optional[str]
    recipient_group_id: Optional[UUID]
    open_rate: Optional[float]
    click_rate: Optional[float]
    sent_date: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True

class RecipientGroupCreate(BaseModel):
    group_name: str
    group_description: Optional[str] = None
    filter_criteria_json: Optional[dict] = {}

class MessageTemplateCreate(BaseModel):
    template_name: str
    content_subject: Optional[str] = None
    content_body: str
    category: Optional[str] = None


# ── Finance ─────────────────────────────────────────────────────────

class DonationCreate(BaseModel):
    donor_name: str
    donation_amount: float
    payment_method: str
    donor_voter_id: Optional[UUID] = None
    mpesa_transaction_code: Optional[str] = None
    bank_reference: Optional[str] = None
    donor_id_number: Optional[str] = None
    donor_phone: Optional[str] = None
    is_recurring: bool = False
    is_anonymous: bool = False

class DonationResponse(BaseModel):
    donation_id: UUID
    donor_name: str
    donation_amount: float
    payment_method: str
    is_anonymous: bool
    receipt_number: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class ExpenseCreate(BaseModel):
    expense_category: str
    amount: float
    description: Optional[str] = None
    payment_method: Optional[str] = None
    vendor_name: Optional[str] = None
    receipt_number: Optional[str] = None
    expense_date: date

class BudgetAllocationCreate(BaseModel):
    constituency_id: Optional[UUID] = None
    category: str
    total_amount: float
    fiscal_period: Optional[str] = None


# ── Intelligence ────────────────────────────────────────────────────

class OpponentCreate(BaseModel):
    full_name: str
    political_party: Optional[str] = None
    threat_level: Optional[str] = "moderate"

class OpponentResponse(BaseModel):
    opponent_id: UUID
    full_name: str
    political_party: Optional[str]
    threat_level: Optional[str]
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True

class DossierCreate(BaseModel):
    full_name: str
    category: str
    constituency_id: Optional[UUID] = None
    ward_id: Optional[UUID] = None
    influence_level: Optional[str] = None

class CountyIssueCreate(BaseModel):
    issue_category: str
    issue_title: str
    description: Optional[str] = None
    priority_level: int = 3
    campaign_stance: Optional[str] = None

class MediaCoverageCreate(BaseModel):
    source_name: str
    source_type: Optional[str] = None
    headline: Optional[str] = None
    sentiment: Optional[str] = None
    url: Optional[str] = None
    constituency_id: Optional[UUID] = None

class EndorsementCreate(BaseModel):
    endorser_name: str
    endorser_type: Optional[str] = None
    endorser_title: Optional[str] = None
    constituency_id: Optional[UUID] = None
    announced_at: Optional[date] = None


# ── Election Day ────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    full_name: str
    political_party: Optional[str] = None
    position: str = "governor"
    is_our_candidate: bool = False
    ballot_order: Optional[int] = None

class CandidateResponse(BaseModel):
    candidate_id: UUID
    full_name: str
    political_party: Optional[str]
    position: str
    is_our_candidate: bool
    ballot_order: Optional[int]
    class Config:
        from_attributes = True

class ProvisionalResultCreate(BaseModel):
    polling_station_id: UUID
    candidate_id: UUID
    registered_voters: Optional[int] = None
    votes_cast: Optional[int] = None
    valid_votes: Optional[int] = None
    rejected_votes: Optional[int] = None
    candidate_votes: int
    form_34a_image_url: Optional[str] = None
    verified_by_agent_id: Optional[UUID] = None

class IncidentCreate(BaseModel):
    polling_station_id: UUID
    incident_type: str
    description: str
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    photo_evidence_url: Optional[str] = None

class PollingAgentCreate(BaseModel):
    volunteer_id: Optional[UUID] = None
    polling_station_id: UUID
    full_name: str
    phone_number: Optional[str] = None
    id_number: Optional[str] = None
    is_chief_agent: bool = False

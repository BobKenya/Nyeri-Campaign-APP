"""Intelligence, Election Day, Analytics models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())

# ── Intelligence ───────────────────────────────────────────────────

class Opponent(Base):
    __tablename__ = "opponents"
    opponent_id = Column(String(36), primary_key=True, default=genuuid)
    full_name = Column(String(200), nullable=False)
    political_party = Column(String(100))
    contact_number = Column(String(20))
    social_media_json = Column(JSON, default=dict)
    manifesto_url = Column(Text)
    threat_level = Column(String(20), default="moderate")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    activities = relationship("OpponentActivity", back_populates="opponent")

class OpponentActivity(Base):
    __tablename__ = "opponent_activities"
    activity_id = Column(String(36), primary_key=True, default=genuuid)
    opponent_id = Column(String(36), ForeignKey("opponents.opponent_id"), nullable=False)
    activity_type = Column(String(50), nullable=False)
    activity_date = Column(Date)
    location = Column(String(300))
    description = Column(Text)
    media_url = Column(Text)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    created_at = Column(DateTime, default=utcnow)
    opponent = relationship("Opponent", back_populates="activities")

class Dossier(Base):
    __tablename__ = "dossiers"
    dossier_id = Column(String(36), primary_key=True, default=genuuid)
    full_name = Column(String(200), nullable=False)
    political_party = Column(String(100))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    address = Column(Text)
    phone = Column(String(20))
    category = Column(String(20), nullable=False)
    influence_level = Column(String(20))
    engagement_priority = Column(String(20), default="medium")
    public_profile_summary = Column(Text)
    created_at = Column(DateTime, default=utcnow)

class CountyIssue(Base):
    __tablename__ = "county_issues"
    issue_id = Column(String(36), primary_key=True, default=genuuid)
    issue_category = Column(String(100), nullable=False)
    issue_title = Column(String(300), nullable=False)
    description = Column(Text)
    priority_level = Column(Integer, default=3)
    campaign_stance = Column(Text)
    public_sentiment_score = Column(Float)
    created_at = Column(DateTime, default=utcnow)

class MediaCoverage(Base):
    __tablename__ = "media_coverage"
    coverage_id = Column(String(36), primary_key=True, default=genuuid)
    source_name = Column(String(200), nullable=False)
    source_type = Column(String(50))
    headline = Column(String(500))
    sentiment = Column(String(20))
    url = Column(Text)
    reach_estimate = Column(Integer)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)

class Endorsement(Base):
    __tablename__ = "endorsements"
    endorsement_id = Column(String(36), primary_key=True, default=genuuid)
    endorser_name = Column(String(200), nullable=False)
    endorser_type = Column(String(50))
    endorser_title = Column(String(200))
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    influence_reach = Column(String(20))
    announced_at = Column(Date)
    evidence_url = Column(Text)
    created_at = Column(DateTime, default=utcnow)

class Tag(Base):
    __tablename__ = "tags"
    tag_id = Column(String(36), primary_key=True, default=genuuid)
    tag_name = Column(String(100), unique=True, nullable=False)
    tag_category = Column(String(50))
    tag_color = Column(String(7))
    created_at = Column(DateTime, default=utcnow)

class EntityTag(Base):
    __tablename__ = "entity_tags"
    entity_tag_id = Column(String(36), primary_key=True, default=genuuid)
    entity_id = Column(String(36), nullable=False)
    entity_type = Column(String(50), nullable=False)
    tag_id = Column(String(36), ForeignKey("tags.tag_id"), nullable=False)
    assigned_at = Column(DateTime, default=utcnow)

class CampaignMaterial(Base):
    __tablename__ = "campaign_materials"
    material_id = Column(String(36), primary_key=True, default=genuuid)
    material_type = Column(String(50), nullable=False)
    description = Column(Text)
    quantity = Column(Integer)
    material_status = Column(String(20), default="draft")
    distribution_area = Column(String(200))
    cost_per_unit = Column(Float)
    total_cost = Column(Float)
    created_at = Column(DateTime, default=utcnow)

# ── Election Day ───────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidates"
    candidate_id = Column(String(36), primary_key=True, default=genuuid)
    full_name = Column(String(200), nullable=False)
    political_party = Column(String(100))
    position = Column(String(20), default="governor")
    is_our_candidate = Column(Boolean, default=False)
    ballot_order = Column(Integer)
    photo_url = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    provisional_results = relationship("ProvisionalResult", back_populates="candidate")
    constituency_results = relationship("ConstituencyResult", back_populates="candidate")

class ElectionDayDashboard(Base):
    __tablename__ = "election_day_dashboard"
    dashboard_id = Column(String(36), primary_key=True, default=genuuid)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"), nullable=False, unique=True)
    station_status = Column(String(20), default="not_opened")
    agents_reported_in = Column(Integer, default=0)
    opened_at = Column(DateTime)
    voting_turnout_count = Column(Integer, default=0)
    issues_reported_count = Column(Integer, default=0)
    closed_at = Column(DateTime)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class PollingAgent(Base):
    __tablename__ = "polling_agents"
    agent_id = Column(String(36), primary_key=True, default=genuuid)
    volunteer_id = Column(String(36), ForeignKey("volunteers.volunteer_id"))
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"), nullable=False)
    full_name = Column(String(200), nullable=False)
    phone_number = Column(String(20))
    id_number = Column(String(20))
    is_chief_agent = Column(Boolean, default=False)
    emergency_contact = Column(String(200))
    accreditation_status = Column(String(20), default="pending")

class ElectionIncident(Base):
    __tablename__ = "election_incidents"
    incident_id = Column(String(36), primary_key=True, default=genuuid)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"), nullable=False)
    incident_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    reported_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    gps_latitude = Column(Float)
    gps_longitude = Column(Float)
    photo_evidence_url = Column(Text)
    resolution_status = Column(String(20), default="reported")
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

class ProvisionalResult(Base):
    __tablename__ = "provisional_results"
    result_id = Column(String(36), primary_key=True, default=genuuid)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"), nullable=False)
    candidate_id = Column(String(36), ForeignKey("candidates.candidate_id"), nullable=False)
    registered_voters = Column(Integer)
    votes_cast = Column(Integer)
    valid_votes = Column(Integer)
    rejected_votes = Column(Integer)
    candidate_votes = Column(Integer, nullable=False)
    form_34a_image_url = Column(Text)
    verified_by_agent_id = Column(String(36), ForeignKey("polling_agents.agent_id"))
    created_at = Column(DateTime, default=utcnow)
    candidate = relationship("Candidate", back_populates="provisional_results")

class ConstituencyResult(Base):
    __tablename__ = "constituency_results"
    result_id = Column(String(36), primary_key=True, default=genuuid)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=False)
    candidate_id = Column(String(36), ForeignKey("candidates.candidate_id"), nullable=False)
    total_votes = Column(Integer)
    total_valid = Column(Integer)
    total_rejected = Column(Integer)
    stations_reporting = Column(Integer)
    total_stations = Column(Integer)
    form_34b_image_url = Column(Text)
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    candidate = relationship("Candidate", back_populates="constituency_results")

# ── Analytics ──────────────────────────────────────────────────────

class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    snapshot_id = Column(String(36), primary_key=True, default=genuuid)
    snapshot_date = Column(Date, nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    support_percentage = Column(Float)
    canvass_coverage_pct = Column(Float)
    volunteer_hours_total = Column(Float)
    funds_raised_ksh = Column(Float)
    funds_spent_ksh = Column(Float)
    data_json = Column(JSON, default=dict)

"""Tracking & Intelligence: Agent profiles, opponent tracking, cross-reference detection."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())


class AgentProfile(Base):
    """Full profile for every mobilizer/agent with contacts, social media, and live GPS."""
    __tablename__ = "agent_profiles"

    agent_profile_id = Column(String(36), primary_key=True, default=genuuid)
    volunteer_id = Column(String(36), ForeignKey("volunteers.volunteer_id"), unique=True)
    user_id = Column(String(36), ForeignKey("users.user_id"))

    # Identity
    full_name = Column(String(200), nullable=False)
    id_number = Column(String(20), index=True)
    photo_url = Column(Text)
    role_title = Column(String(100))  # mobilizer, coordinator, chief_agent, driver, etc.

    # Contact info
    phone_primary = Column(String(20), nullable=False)
    phone_secondary = Column(String(20))
    whatsapp_number = Column(String(20))
    email = Column(String(255))

    # Social media
    facebook_url = Column(Text)
    twitter_handle = Column(String(100))
    instagram_handle = Column(String(100))
    tiktok_handle = Column(String(100))
    linkedin_url = Column(Text)
    youtube_channel = Column(Text)
    social_media_json = Column(JSON, default=dict)  # any additional platforms

    # Location
    home_latitude = Column(Float)
    home_longitude = Column(Float)
    home_address = Column(Text)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"))

    # Live GPS tracking
    last_known_latitude = Column(Float)
    last_known_longitude = Column(Float)
    last_location_update = Column(DateTime)
    is_location_sharing = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    is_trusted = Column(Boolean, default=True)
    trust_score = Column(Integer, default=100)  # 0-100, decreases if flagged
    notes = Column(Text)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    location_history = relationship("AgentLocationLog", back_populates="agent", order_by="AgentLocationLog.timestamp.desc()")
    flagged_connections = relationship("ConnectionFlag", foreign_keys="ConnectionFlag.agent_profile_id", back_populates="agent")

    __table_args__ = (
        Index("ix_agent_constituency", "constituency_id", "is_active"),
        Index("ix_agent_ward", "ward_id", "is_active"),
    )


class AgentLocationLog(Base):
    """GPS location history for agents — tracks movement patterns."""
    __tablename__ = "agent_location_log"

    log_id = Column(String(36), primary_key=True, default=genuuid)
    agent_profile_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float)
    altitude = Column(Float)
    speed = Column(Float)  # km/h
    activity = Column(String(50))  # canvassing, event, transit, stationary
    battery_level = Column(Integer)  # 0-100
    timestamp = Column(DateTime, default=utcnow, nullable=False)

    agent = relationship("AgentProfile", back_populates="location_history")

    __table_args__ = (
        Index("ix_location_agent_time", "agent_profile_id", "timestamp"),
    )


class OpponentProfile(Base):
    """Detailed opponent tracking with contacts, social media, GIS, and network."""
    __tablename__ = "opponent_profiles"

    opponent_profile_id = Column(String(36), primary_key=True, default=genuuid)
    opponent_id = Column(String(36), ForeignKey("opponents.opponent_id"), unique=True)

    # Identity
    full_name = Column(String(200), nullable=False)
    alias = Column(String(100))
    photo_url = Column(Text)
    political_party = Column(String(100))
    position_vying = Column(String(50))  # governor, senator, mp, mca

    # Contact info
    phone_primary = Column(String(20))
    phone_secondary = Column(String(20))
    whatsapp_number = Column(String(20))
    email = Column(String(255))

    # Social media
    facebook_url = Column(Text)
    twitter_handle = Column(String(100))
    instagram_handle = Column(String(100))
    tiktok_handle = Column(String(100))
    linkedin_url = Column(Text)
    youtube_channel = Column(Text)
    social_media_json = Column(JSON, default=dict)

    # Location
    home_latitude = Column(Float)
    home_longitude = Column(Float)
    home_address = Column(Text)
    office_latitude = Column(Float)
    office_longitude = Column(Float)
    office_address = Column(Text)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))

    # Last sighted / tracked location
    last_known_latitude = Column(Float)
    last_known_longitude = Column(Float)
    last_sighted_at = Column(DateTime)
    last_sighted_location_name = Column(String(300))

    # Intelligence
    threat_level = Column(String(20), default="moderate")  # low, moderate, high, critical
    estimated_funding_ksh = Column(Float)
    estimated_supporters = Column(Integer)
    key_allies_json = Column(JSON, default=list)  # names of known allies
    known_strategy_notes = Column(Text)
    weaknesses_notes = Column(Text)
    strengths_notes = Column(Text)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    sighting_log = relationship("OpponentSighting", back_populates="opponent_profile", order_by="OpponentSighting.sighted_at.desc()")
    flagged_connections = relationship("ConnectionFlag", foreign_keys="ConnectionFlag.opponent_profile_id", back_populates="opponent_profile")


class OpponentSighting(Base):
    """Log of opponent sightings with GPS, activity, and evidence."""
    __tablename__ = "opponent_sightings"

    sighting_id = Column(String(36), primary_key=True, default=genuuid)
    opponent_profile_id = Column(String(36), ForeignKey("opponent_profiles.opponent_profile_id"), nullable=False, index=True)
    reported_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(300))
    activity_type = Column(String(50))  # rally, meeting, canvassing, fundraiser, private_meeting
    description = Column(Text)
    people_present_estimate = Column(Integer)
    photo_evidence_url = Column(Text)
    video_evidence_url = Column(Text)

    # Was any of our people spotted with them?
    our_people_spotted = Column(Boolean, default=False)
    our_people_names = Column(Text)  # comma-separated names if spotted

    sighted_at = Column(DateTime, default=utcnow, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    opponent_profile = relationship("OpponentProfile", back_populates="sighting_log")


class ConnectionFlag(Base):
    """Flags suspicious connections between our agents and opponents.
    Created automatically or manually when an agent is seen with an opponent."""
    __tablename__ = "connection_flags"

    flag_id = Column(String(36), primary_key=True, default=genuuid)
    agent_profile_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"), nullable=False)
    opponent_profile_id = Column(String(36), ForeignKey("opponent_profiles.opponent_profile_id"), nullable=False)

    # Evidence
    flag_type = Column(String(30), nullable=False)  # phone_contact, social_media, physical_meeting, financial, sighting
    evidence_description = Column(Text, nullable=False)
    evidence_url = Column(Text)  # photo/video/screenshot
    location_latitude = Column(Float)
    location_longitude = Column(Float)
    location_name = Column(String(300))
    occurred_at = Column(DateTime)

    # Assessment
    severity = Column(String(20), default="low")  # low, medium, high, critical
    status = Column(String(20), default="pending")  # pending, investigating, confirmed, cleared, dismissed
    investigation_notes = Column(Text)
    investigated_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    resolved_at = Column(DateTime)

    # Action taken
    action_taken = Column(Text)  # warned, suspended, removed, monitored, cleared

    reported_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    agent = relationship("AgentProfile", back_populates="flagged_connections")
    opponent_profile = relationship("OpponentProfile", back_populates="flagged_connections")

    __table_args__ = (
        Index("ix_flag_agent", "agent_profile_id", "status"),
        Index("ix_flag_opponent", "opponent_profile_id", "status"),
        Index("ix_flag_severity", "severity", "status"),
    )


class OpponentNetworkMember(Base):
    """Track known members of opponent's network — their coordinators, funders, allies."""
    __tablename__ = "opponent_network_members"

    member_id = Column(String(36), primary_key=True, default=genuuid)
    opponent_profile_id = Column(String(36), ForeignKey("opponent_profiles.opponent_profile_id"), nullable=False, index=True)

    full_name = Column(String(200), nullable=False)
    phone_number = Column(String(20))
    role_in_network = Column(String(50))  # funder, coordinator, mobilizer, driver, advisor, relative
    photo_url = Column(Text)
    social_media_json = Column(JSON, default=dict)

    # Cross-reference: is this person also one of our agents?
    matched_agent_profile_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"))
    matched_voter_id = Column(String(36), ForeignKey("voters.voter_id"))
    is_double_agent = Column(Boolean, default=False)

    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(Text)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

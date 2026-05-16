"""Voters: Voter, Constituency, Ward, PollingStation, VotingHistory, DataConsentLog."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())

class Constituency(Base):
    __tablename__ = "constituencies"
    constituency_id = Column(String(36), primary_key=True, default=genuuid)
    constituency_name = Column(String(100), unique=True, nullable=False)
    county_name = Column(String(100), default="Nyeri")
    registered_voters_count = Column(Integer, default=0)
    geographic_polygon_json = Column(Text)  # GeoJSON stored as text
    mp_name = Column(String(200))
    created_at = Column(DateTime, default=utcnow)
    wards = relationship("Ward", back_populates="constituency")
    voters = relationship("Voter", back_populates="constituency")

class Ward(Base):
    __tablename__ = "wards"
    ward_id = Column(String(36), primary_key=True, default=genuuid)
    ward_name = Column(String(100), nullable=False)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=False)
    population = Column(Integer)
    area_sq_km = Column(Float)
    registered_voters = Column(Integer, default=0)
    geographic_polygon_json = Column(Text)
    mca_name = Column(String(200))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    constituency = relationship("Constituency", back_populates="wards")
    polling_stations = relationship("PollingStation", back_populates="ward")
    voters = relationship("Voter", back_populates="ward")

class PollingStation(Base):
    __tablename__ = "polling_stations"
    polling_station_id = Column(String(36), primary_key=True, default=genuuid)
    station_name = Column(String(200), nullable=False)
    station_code = Column(String(20), unique=True, nullable=False)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    registered_voters = Column(Integer, default=0)
    accessibility_status = Column(String(20), default="accessible")
    created_at = Column(DateTime, default=utcnow)
    ward = relationship("Ward", back_populates="polling_stations")
    voters = relationship("Voter", back_populates="polling_station")

class Voter(Base):
    __tablename__ = "voters"
    voter_id = Column(String(36), primary_key=True, default=genuuid)
    full_name = Column(String(200), nullable=False)
    id_number = Column(String(20), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), index=True)
    date_of_birth = Column(Date)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"))
    support_level = Column(String(20), default="unknown")  # strong_support, lean_support, undecided, lean_oppose, strong_oppose
    is_registered = Column(Boolean, default=True)
    occupation = Column(String(100))
    religious_affiliation = Column(String(50))
    gender = Column(String(10))
    is_deceased = Column(Boolean, default=False)
    data_consent_granted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    constituency = relationship("Constituency", back_populates="voters")
    ward = relationship("Ward", back_populates="voters")
    polling_station = relationship("PollingStation", back_populates="voters")
    voting_history = relationship("VotingHistory", back_populates="voter")
    consent_logs = relationship("DataConsentLog", back_populates="voter")
    __table_args__ = (
        Index("ix_voters_constituency_support", "constituency_id", "support_level"),
    )

class VotingHistory(Base):
    __tablename__ = "voting_history"
    history_id = Column(String(36), primary_key=True, default=genuuid)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"), nullable=False, index=True)
    election_year = Column(Integer, nullable=False)
    election_type = Column(String(50))
    voted = Column(Boolean, default=False)
    voter = relationship("Voter", back_populates="voting_history")

class DataConsentLog(Base):
    __tablename__ = "data_consent_log"
    consent_id = Column(String(36), primary_key=True, default=genuuid)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"), nullable=False)
    consent_type = Column(String(20), nullable=False)
    consent_method = Column(String(50))
    granted_at = Column(DateTime, default=utcnow)
    revoked_at = Column(DateTime)
    voter = relationship("Voter", back_populates="consent_logs")

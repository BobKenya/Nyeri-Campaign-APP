"""Pydantic schemas for voters, constituencies, wards, polling stations."""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


# ── Constituency ────────────────────────────────────────────────────

class ConstituencyResponse(BaseModel):
    constituency_id: UUID
    constituency_name: str
    county_name: str
    registered_voters_count: int
    mp_name: Optional[str]
    class Config:
        from_attributes = True


class WardResponse(BaseModel):
    ward_id: UUID
    ward_name: str
    constituency_id: UUID
    population: Optional[int]
    registered_voters: Optional[int]
    mca_name: Optional[str]
    class Config:
        from_attributes = True


class PollingStationResponse(BaseModel):
    polling_station_id: UUID
    station_name: str
    station_code: str
    ward_id: UUID
    latitude: Optional[float]
    longitude: Optional[float]
    registered_voters: int
    class Config:
        from_attributes = True


# ── Voter ───────────────────────────────────────────────────────────

class VoterCreate(BaseModel):
    full_name: str
    id_number: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    constituency_id: Optional[UUID] = None
    ward_id: Optional[UUID] = None
    polling_station_id: Optional[UUID] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None


class VoterUpdate(BaseModel):
    phone_number: Optional[str] = None
    support_level: Optional[str] = None
    ward_id: Optional[UUID] = None
    polling_station_id: Optional[UUID] = None
    occupation: Optional[str] = None
    is_deceased: Optional[bool] = None


class VoterResponse(BaseModel):
    voter_id: UUID
    full_name: str
    id_number: str
    phone_number: Optional[str]
    date_of_birth: Optional[date]
    constituency_id: Optional[UUID]
    ward_id: Optional[UUID]
    polling_station_id: Optional[UUID]
    support_level: Optional[str]
    gender: Optional[str]
    is_registered: bool
    is_deceased: bool
    data_consent_granted: bool
    created_at: datetime
    class Config:
        from_attributes = True


class VoterSearchParams(BaseModel):
    q: Optional[str] = None  # name or ID search
    constituency_id: Optional[UUID] = None
    ward_id: Optional[UUID] = None
    support_level: Optional[str] = None
    gender: Optional[str] = None
    has_phone: Optional[bool] = None

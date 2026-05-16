"""Tracking routes: agent profiles, GPS tracking, opponent profiles, sightings, connection detection."""

from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel

from app.database import get_db
from app.models.tracking import (
    AgentProfile, AgentLocationLog, OpponentProfile, OpponentSighting,
    ConnectionFlag, OpponentNetworkMember,
)
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentProfileCreate(BaseModel):
    full_name: str
    id_number: Optional[str] = None
    role_title: Optional[str] = "mobilizer"
    phone_primary: str
    phone_secondary: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    instagram_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    home_latitude: Optional[float] = None
    home_longitude: Optional[float] = None
    home_address: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    volunteer_id: Optional[str] = None

class AgentLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    altitude: Optional[float] = None
    speed: Optional[float] = None
    activity: Optional[str] = None
    battery_level: Optional[int] = None

class OpponentProfileCreate(BaseModel):
    full_name: str
    alias: Optional[str] = None
    political_party: Optional[str] = None
    position_vying: Optional[str] = "governor"
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    instagram_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    home_latitude: Optional[float] = None
    home_longitude: Optional[float] = None
    home_address: Optional[str] = None
    office_latitude: Optional[float] = None
    office_longitude: Optional[float] = None
    office_address: Optional[str] = None
    constituency_id: Optional[str] = None
    threat_level: Optional[str] = "moderate"
    opponent_id: Optional[str] = None

class SightingCreate(BaseModel):
    opponent_profile_id: str
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    activity_type: Optional[str] = None
    description: Optional[str] = None
    people_present_estimate: Optional[int] = None
    photo_evidence_url: Optional[str] = None
    our_people_spotted: bool = False
    our_people_names: Optional[str] = None

class ConnectionFlagCreate(BaseModel):
    agent_profile_id: str
    opponent_profile_id: str
    flag_type: str  # phone_contact, social_media, physical_meeting, financial, sighting
    evidence_description: str
    evidence_url: Optional[str] = None
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None
    location_name: Optional[str] = None
    severity: Optional[str] = "medium"
    occurred_at: Optional[datetime] = None

class NetworkMemberCreate(BaseModel):
    opponent_profile_id: str
    full_name: str
    phone_number: Optional[str] = None
    role_in_network: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT PROFILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/agents")
async def list_agent_profiles(
    constituency_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    role_title: Optional[str] = None,
    is_active: Optional[bool] = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(AgentProfile)
    if is_active is not None:
        query = query.where(AgentProfile.is_active == is_active)
    if constituency_id:
        query = query.where(AgentProfile.constituency_id == constituency_id)
    if ward_id:
        query = query.where(AgentProfile.ward_id == ward_id)
    if role_title:
        query = query.where(AgentProfile.role_title == role_title)
    query = query.order_by(AgentProfile.full_name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    agents = result.scalars().all()
    return [
        {
            "agent_profile_id": a.agent_profile_id,
            "full_name": a.full_name,
            "role_title": a.role_title,
            "phone_primary": a.phone_primary,
            "whatsapp_number": a.whatsapp_number,
            "facebook_url": a.facebook_url,
            "twitter_handle": a.twitter_handle,
            "instagram_handle": a.instagram_handle,
            "tiktok_handle": a.tiktok_handle,
            "constituency_id": a.constituency_id,
            "ward_id": a.ward_id,
            "home_latitude": a.home_latitude,
            "home_longitude": a.home_longitude,
            "last_known_latitude": a.last_known_latitude,
            "last_known_longitude": a.last_known_longitude,
            "last_location_update": a.last_location_update.isoformat() if a.last_location_update else None,
            "is_active": a.is_active,
            "is_trusted": a.is_trusted,
            "trust_score": a.trust_score,
        }
        for a in agents
    ]


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent_profile(body: AgentProfileCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    agent = AgentProfile(**body.model_dump())
    db.add(agent)
    await db.flush()
    return {"agent_profile_id": agent.agent_profile_id, "message": f"Agent profile created for {agent.full_name}"}


@router.get("/agents/{agent_id}")
async def get_agent_profile(agent_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(AgentProfile).where(AgentProfile.agent_profile_id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    return {
        "agent_profile_id": agent.agent_profile_id,
        "full_name": agent.full_name,
        "id_number": agent.id_number,
        "role_title": agent.role_title,
        "photo_url": agent.photo_url,
        "phone_primary": agent.phone_primary,
        "phone_secondary": agent.phone_secondary,
        "whatsapp_number": agent.whatsapp_number,
        "email": agent.email,
        "facebook_url": agent.facebook_url,
        "twitter_handle": agent.twitter_handle,
        "instagram_handle": agent.instagram_handle,
        "tiktok_handle": agent.tiktok_handle,
        "linkedin_url": agent.linkedin_url,
        "youtube_channel": agent.youtube_channel,
        "social_media_json": agent.social_media_json,
        "home_latitude": agent.home_latitude,
        "home_longitude": agent.home_longitude,
        "home_address": agent.home_address,
        "constituency_id": agent.constituency_id,
        "ward_id": agent.ward_id,
        "polling_station_id": agent.polling_station_id,
        "last_known_latitude": agent.last_known_latitude,
        "last_known_longitude": agent.last_known_longitude,
        "last_location_update": agent.last_location_update.isoformat() if agent.last_location_update else None,
        "is_location_sharing": agent.is_location_sharing,
        "is_active": agent.is_active,
        "is_trusted": agent.is_trusted,
        "trust_score": agent.trust_score,
        "notes": agent.notes,
    }


@router.patch("/agents/{agent_id}")
async def update_agent_profile(agent_id: str, updates: dict, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(AgentProfile).where(AgentProfile.agent_profile_id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    allowed = {
        "full_name", "phone_primary", "phone_secondary", "whatsapp_number", "email",
        "facebook_url", "twitter_handle", "instagram_handle", "tiktok_handle",
        "linkedin_url", "youtube_channel", "home_latitude", "home_longitude",
        "home_address", "role_title", "is_active", "is_trusted", "trust_score", "notes",
        "constituency_id", "ward_id", "polling_station_id", "photo_url",
    }
    for key, value in updates.items():
        if key in allowed:
            setattr(agent, key, value)
    agent.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Agent profile updated"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT GPS TRACKING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/agents/{agent_id}/location")
async def update_agent_location(agent_id: str, body: AgentLocationUpdate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """Push live GPS coordinates for an agent. Called from mobile app."""
    result = await db.execute(select(AgentProfile).where(AgentProfile.agent_profile_id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    now = datetime.now(timezone.utc)

    # Update agent's current position
    agent.last_known_latitude = body.latitude
    agent.last_known_longitude = body.longitude
    agent.last_location_update = now
    agent.is_location_sharing = True

    # Log to history
    log = AgentLocationLog(
        agent_profile_id=agent_id,
        latitude=body.latitude,
        longitude=body.longitude,
        accuracy_meters=body.accuracy_meters,
        altitude=body.altitude,
        speed=body.speed,
        activity=body.activity,
        battery_level=body.battery_level,
        timestamp=now,
    )
    db.add(log)
    await db.flush()
    return {"message": "Location updated", "timestamp": now.isoformat()}


@router.get("/agents/{agent_id}/location-history")
async def agent_location_history(
    agent_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_coordinator),
):
    result = await db.execute(
        select(AgentLocationLog)
        .where(AgentLocationLog.agent_profile_id == agent_id)
        .order_by(AgentLocationLog.timestamp.desc())
        .limit(limit)
    )
    return [
        {
            "latitude": l.latitude,
            "longitude": l.longitude,
            "accuracy_meters": l.accuracy_meters,
            "speed": l.speed,
            "activity": l.activity,
            "battery_level": l.battery_level,
            "timestamp": l.timestamp.isoformat(),
        }
        for l in result.scalars().all()
    ]


@router.get("/agents/live-map")
async def agents_live_map(
    constituency_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_coordinator),
):
    """Get all active agents with their latest GPS positions — for the governor's live map view."""
    query = select(AgentProfile).where(
        AgentProfile.is_active == True,
        AgentProfile.last_known_latitude.isnot(None),
    )
    if constituency_id:
        query = query.where(AgentProfile.constituency_id == constituency_id)
    result = await db.execute(query)
    return [
        {
            "agent_profile_id": a.agent_profile_id,
            "full_name": a.full_name,
            "role_title": a.role_title,
            "phone_primary": a.phone_primary,
            "latitude": a.last_known_latitude,
            "longitude": a.last_known_longitude,
            "last_update": a.last_location_update.isoformat() if a.last_location_update else None,
            "battery_level": None,
            "is_trusted": a.is_trusted,
            "trust_score": a.trust_score,
            "ward_id": a.ward_id,
        }
        for a in result.scalars().all()
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OPPONENT PROFILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/opponents")
async def list_opponent_profiles(
    threat_level: Optional[str] = None,
    constituency_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(OpponentProfile)
    if threat_level:
        query = query.where(OpponentProfile.threat_level == threat_level)
    if constituency_id:
        query = query.where(OpponentProfile.constituency_id == constituency_id)
    result = await db.execute(query.order_by(OpponentProfile.full_name))
    return [
        {
            "opponent_profile_id": o.opponent_profile_id,
            "full_name": o.full_name,
            "alias": o.alias,
            "political_party": o.political_party,
            "position_vying": o.position_vying,
            "phone_primary": o.phone_primary,
            "whatsapp_number": o.whatsapp_number,
            "facebook_url": o.facebook_url,
            "twitter_handle": o.twitter_handle,
            "instagram_handle": o.instagram_handle,
            "tiktok_handle": o.tiktok_handle,
            "threat_level": o.threat_level,
            "home_latitude": o.home_latitude,
            "home_longitude": o.home_longitude,
            "office_latitude": o.office_latitude,
            "office_longitude": o.office_longitude,
            "last_known_latitude": o.last_known_latitude,
            "last_known_longitude": o.last_known_longitude,
            "last_sighted_at": o.last_sighted_at.isoformat() if o.last_sighted_at else None,
            "estimated_supporters": o.estimated_supporters,
        }
        for o in result.scalars().all()
    ]


@router.post("/opponents", status_code=status.HTTP_201_CREATED)
async def create_opponent_profile(body: OpponentProfileCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    opp = OpponentProfile(**body.model_dump())
    db.add(opp)
    await db.flush()
    return {"opponent_profile_id": opp.opponent_profile_id, "message": f"Opponent profile created for {opp.full_name}"}


@router.get("/opponents/{opponent_id}")
async def get_opponent_profile(opponent_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(OpponentProfile).where(OpponentProfile.opponent_profile_id == opponent_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opponent profile not found")
    return {
        "opponent_profile_id": opp.opponent_profile_id,
        "full_name": opp.full_name,
        "alias": opp.alias,
        "political_party": opp.political_party,
        "position_vying": opp.position_vying,
        "phone_primary": opp.phone_primary,
        "phone_secondary": opp.phone_secondary,
        "whatsapp_number": opp.whatsapp_number,
        "email": opp.email,
        "facebook_url": opp.facebook_url,
        "twitter_handle": opp.twitter_handle,
        "instagram_handle": opp.instagram_handle,
        "tiktok_handle": opp.tiktok_handle,
        "linkedin_url": opp.linkedin_url,
        "youtube_channel": opp.youtube_channel,
        "home_address": opp.home_address,
        "home_latitude": opp.home_latitude,
        "home_longitude": opp.home_longitude,
        "office_address": opp.office_address,
        "office_latitude": opp.office_latitude,
        "office_longitude": opp.office_longitude,
        "last_known_latitude": opp.last_known_latitude,
        "last_known_longitude": opp.last_known_longitude,
        "last_sighted_at": opp.last_sighted_at.isoformat() if opp.last_sighted_at else None,
        "last_sighted_location_name": opp.last_sighted_location_name,
        "threat_level": opp.threat_level,
        "estimated_funding_ksh": opp.estimated_funding_ksh,
        "estimated_supporters": opp.estimated_supporters,
        "key_allies_json": opp.key_allies_json,
        "known_strategy_notes": opp.known_strategy_notes,
        "strengths_notes": opp.strengths_notes,
        "weaknesses_notes": opp.weaknesses_notes,
    }


@router.get("/opponents/map")
async def opponents_map(db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    """All opponents with GPS pins — home, office, and last sighting."""
    result = await db.execute(select(OpponentProfile))
    opponents = result.scalars().all()
    pins = []
    for o in opponents:
        if o.home_latitude:
            pins.append({"name": o.full_name, "type": "home", "lat": o.home_latitude, "lng": o.home_longitude, "threat_level": o.threat_level})
        if o.office_latitude:
            pins.append({"name": o.full_name, "type": "office", "lat": o.office_latitude, "lng": o.office_longitude, "threat_level": o.threat_level})
        if o.last_known_latitude:
            pins.append({"name": o.full_name, "type": "last_sighted", "lat": o.last_known_latitude, "lng": o.last_known_longitude, "threat_level": o.threat_level, "sighted_at": o.last_sighted_at.isoformat() if o.last_sighted_at else None})
    return pins


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SIGHTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/sightings", status_code=status.HTTP_201_CREATED)
async def report_sighting(body: SightingCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    sighting = OpponentSighting(reported_by_user_id=user.user_id, **body.model_dump())
    db.add(sighting)

    # Update opponent's last known location
    result = await db.execute(select(OpponentProfile).where(OpponentProfile.opponent_profile_id == body.opponent_profile_id))
    opp = result.scalar_one_or_none()
    if opp:
        opp.last_known_latitude = body.latitude
        opp.last_known_longitude = body.longitude
        opp.last_sighted_at = datetime.now(timezone.utc)
        opp.last_sighted_location_name = body.location_name

    # Auto-flag if our people were spotted
    if body.our_people_spotted and body.our_people_names:
        flag = ConnectionFlag(
            agent_profile_id="UNKNOWN",  # to be resolved
            opponent_profile_id=body.opponent_profile_id,
            flag_type="sighting",
            evidence_description=f"Spotted with opponent: {body.our_people_names}. {body.description or ''}",
            location_latitude=body.latitude,
            location_longitude=body.longitude,
            location_name=body.location_name,
            severity="high",
            occurred_at=datetime.now(timezone.utc),
            reported_by_user_id=user.user_id,
        )
        db.add(flag)

    await db.flush()
    return {"sighting_id": sighting.sighting_id, "message": "Sighting reported"}


@router.get("/sightings")
async def list_sightings(
    opponent_profile_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(OpponentSighting)
    if opponent_profile_id:
        query = query.where(OpponentSighting.opponent_profile_id == opponent_profile_id)
    result = await db.execute(query.order_by(OpponentSighting.sighted_at.desc()).limit(limit))
    return [
        {
            "sighting_id": s.sighting_id,
            "opponent_profile_id": s.opponent_profile_id,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "location_name": s.location_name,
            "activity_type": s.activity_type,
            "description": s.description,
            "people_present_estimate": s.people_present_estimate,
            "our_people_spotted": s.our_people_spotted,
            "our_people_names": s.our_people_names,
            "sighted_at": s.sighted_at.isoformat(),
        }
        for s in result.scalars().all()
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONNECTION FLAGS (opponent ↔ our people cross-references)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/flags", status_code=status.HTTP_201_CREATED)
async def flag_connection(body: ConnectionFlagCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    """Flag a suspicious connection between one of our agents and an opponent."""
    flag = ConnectionFlag(reported_by_user_id=user.user_id, **body.model_dump())
    db.add(flag)

    # Reduce trust score of flagged agent
    result = await db.execute(select(AgentProfile).where(AgentProfile.agent_profile_id == body.agent_profile_id))
    agent = result.scalar_one_or_none()
    if agent:
        severity_penalty = {"low": 5, "medium": 15, "high": 30, "critical": 50}
        agent.trust_score = max(0, agent.trust_score - severity_penalty.get(body.severity, 10))
        if agent.trust_score < 30:
            agent.is_trusted = False

    await db.flush()
    return {"flag_id": flag.flag_id, "message": "Connection flagged", "agent_trust_score": agent.trust_score if agent else None}


@router.get("/flags")
async def list_flags(
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    agent_id: Optional[str] = None,
    opponent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_coordinator),
):
    query = select(ConnectionFlag)
    if status_filter:
        query = query.where(ConnectionFlag.status == status_filter)
    if severity:
        query = query.where(ConnectionFlag.severity == severity)
    if agent_id:
        query = query.where(ConnectionFlag.agent_profile_id == agent_id)
    if opponent_id:
        query = query.where(ConnectionFlag.opponent_profile_id == opponent_id)
    result = await db.execute(query.order_by(ConnectionFlag.created_at.desc()))
    return [
        {
            "flag_id": f.flag_id,
            "agent_profile_id": f.agent_profile_id,
            "opponent_profile_id": f.opponent_profile_id,
            "flag_type": f.flag_type,
            "evidence_description": f.evidence_description,
            "severity": f.severity,
            "status": f.status,
            "location_name": f.location_name,
            "occurred_at": f.occurred_at.isoformat() if f.occurred_at else None,
            "action_taken": f.action_taken,
            "created_at": f.created_at.isoformat(),
        }
        for f in result.scalars().all()
    ]


@router.patch("/flags/{flag_id}")
async def update_flag(flag_id: str, updates: dict, db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    """Update investigation status, add notes, take action on a flagged connection."""
    result = await db.execute(select(ConnectionFlag).where(ConnectionFlag.flag_id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    allowed = {"status", "investigation_notes", "action_taken", "severity"}
    for key, value in updates.items():
        if key in allowed:
            setattr(flag, key, value)

    if updates.get("status") in ("confirmed", "cleared", "dismissed"):
        flag.resolved_at = datetime.now(timezone.utc)
        flag.investigated_by_user_id = user.user_id

    # If cleared, restore trust score
    if updates.get("status") == "cleared":
        agent_result = await db.execute(select(AgentProfile).where(AgentProfile.agent_profile_id == flag.agent_profile_id))
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.trust_score = min(100, agent.trust_score + 20)
            if agent.trust_score >= 50:
                agent.is_trusted = True

    await db.flush()
    return {"message": f"Flag updated to {updates.get('status', 'modified')}"}


@router.get("/flags/dashboard")
async def flags_dashboard(db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    """Governor's overview: how many agents are flagged, by severity."""
    total_flags = (await db.execute(select(func.count()).select_from(ConnectionFlag))).scalar()
    pending = (await db.execute(select(func.count()).select_from(ConnectionFlag).where(ConnectionFlag.status == "pending"))).scalar()
    investigating = (await db.execute(select(func.count()).select_from(ConnectionFlag).where(ConnectionFlag.status == "investigating"))).scalar()
    confirmed = (await db.execute(select(func.count()).select_from(ConnectionFlag).where(ConnectionFlag.status == "confirmed"))).scalar()

    by_severity = await db.execute(
        select(ConnectionFlag.severity, func.count())
        .where(ConnectionFlag.status.in_(["pending", "investigating"]))
        .group_by(ConnectionFlag.severity)
    )

    untrusted_agents = (await db.execute(
        select(func.count()).select_from(AgentProfile).where(AgentProfile.is_trusted == False)
    )).scalar()

    return {
        "total_flags": total_flags,
        "pending": pending,
        "investigating": investigating,
        "confirmed_traitors": confirmed,
        "untrusted_agents": untrusted_agents,
        "open_by_severity": {row[0]: row[1] for row in by_severity.all()},
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OPPONENT NETWORK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/opponents/network", status_code=status.HTTP_201_CREATED)
async def add_network_member(body: NetworkMemberCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    member = OpponentNetworkMember(**body.model_dump())

    # Auto cross-reference: check if this phone matches any of our agents
    if body.phone_number:
        agent_match = await db.execute(
            select(AgentProfile).where(
                or_(
                    AgentProfile.phone_primary == body.phone_number,
                    AgentProfile.phone_secondary == body.phone_number,
                    AgentProfile.whatsapp_number == body.phone_number,
                )
            )
        )
        matched_agent = agent_match.scalar_one_or_none()
        if matched_agent:
            member.matched_agent_profile_id = matched_agent.agent_profile_id
            member.is_double_agent = True

            # Auto-create a connection flag
            auto_flag = ConnectionFlag(
                agent_profile_id=matched_agent.agent_profile_id,
                opponent_profile_id=body.opponent_profile_id,
                flag_type="phone_contact",
                evidence_description=f"Phone number {body.phone_number} matches agent '{matched_agent.full_name}' and appears in opponent's network as '{body.role_in_network}'",
                severity="critical",
                status="pending",
            )
            db.add(auto_flag)

            # Drop trust score
            matched_agent.trust_score = max(0, matched_agent.trust_score - 40)
            matched_agent.is_trusted = False

    db.add(member)
    await db.flush()

    response = {"member_id": member.member_id, "message": "Network member added"}
    if member.is_double_agent:
        response["WARNING"] = f"MATCH FOUND — this person matches agent: {matched_agent.full_name}. Auto-flagged as critical."
    return response


@router.get("/opponents/{opponent_id}/network")
async def get_opponent_network(opponent_id: str, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(
        select(OpponentNetworkMember).where(OpponentNetworkMember.opponent_profile_id == opponent_id)
    )
    return [
        {
            "member_id": m.member_id,
            "full_name": m.full_name,
            "phone_number": m.phone_number,
            "role_in_network": m.role_in_network,
            "is_double_agent": m.is_double_agent,
            "matched_agent_profile_id": m.matched_agent_profile_id,
            "latitude": m.latitude,
            "longitude": m.longitude,
            "notes": m.notes,
        }
        for m in result.scalars().all()
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GOVERNOR'S COMMAND CENTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/command-center")
async def governor_command_center(db: AsyncSession = Depends(get_db), _user=Depends(require_admin)):
    """Single endpoint giving the governor a full operational picture."""
    total_agents = (await db.execute(select(func.count()).select_from(AgentProfile).where(AgentProfile.is_active == True))).scalar()
    agents_sharing_location = (await db.execute(
        select(func.count()).select_from(AgentProfile)
        .where(AgentProfile.is_active == True, AgentProfile.last_known_latitude.isnot(None))
    )).scalar()
    untrusted = (await db.execute(select(func.count()).select_from(AgentProfile).where(AgentProfile.is_trusted == False))).scalar()
    total_opponents = (await db.execute(select(func.count()).select_from(OpponentProfile))).scalar()
    critical_opponents = (await db.execute(
        select(func.count()).select_from(OpponentProfile).where(OpponentProfile.threat_level == "critical")
    )).scalar()
    pending_flags = (await db.execute(
        select(func.count()).select_from(ConnectionFlag).where(ConnectionFlag.status.in_(["pending", "investigating"]))
    )).scalar()
    double_agents = (await db.execute(
        select(func.count()).select_from(OpponentNetworkMember).where(OpponentNetworkMember.is_double_agent == True)
    )).scalar()
    recent_sightings = (await db.execute(select(func.count()).select_from(OpponentSighting))).scalar()

    return {
        "our_team": {
            "total_agents": total_agents,
            "sharing_location": agents_sharing_location,
            "untrusted_agents": untrusted,
        },
        "opponents": {
            "total_tracked": total_opponents,
            "critical_threat": critical_opponents,
            "total_sightings": recent_sightings,
        },
        "security": {
            "pending_flags": pending_flags,
            "confirmed_double_agents": double_agents,
        },
    }

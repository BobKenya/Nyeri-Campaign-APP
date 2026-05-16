"""Field operations routes: canvassing routes, contacts."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.operations import CanvassingRoute, CanvassingContact, VoterInteraction
from app.dependencies import get_current_user, require_field_agent

router = APIRouter()


@router.get("/routes")
async def list_routes(
    ward_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(CanvassingRoute)
    if ward_id:
        query = query.where(CanvassingRoute.ward_id == ward_id)
    result = await db.execute(query.order_by(CanvassingRoute.created_at.desc()))
    routes = result.scalars().all()
    return [
        {
            "route_id": str(r.route_id),
            "route_name": r.route_name,
            "ward_id": str(r.ward_id),
            "estimated_houses": r.estimated_houses,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in routes
    ]


@router.post("/routes", status_code=status.HTTP_201_CREATED)
async def create_route(
    route_name: str,
    ward_id: UUID,
    estimated_houses: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_field_agent),
):
    route = CanvassingRoute(
        route_name=route_name,
        ward_id=ward_id,
        assigned_to_user_id=user.user_id,
        created_by_user_id=user.user_id,
        estimated_houses=estimated_houses,
    )
    db.add(route)
    await db.flush()
    return {"route_id": str(route.route_id), "message": "Route created"}


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
async def log_contact(
    route_id: UUID,
    voter_id: UUID,
    contact_type: str = "door_to_door",
    contact_result: str = "contacted",
    issues_discussed: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    gps_latitude: Optional[float] = None,
    gps_longitude: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_field_agent),
):
    contact = CanvassingContact(
        route_id=route_id,
        voter_id=voter_id,
        contact_type=contact_type,
        contact_result=contact_result,
        issues_discussed=issues_discussed,
        sentiment_score=sentiment_score,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
    )
    db.add(contact)

    # Also log to unified interaction table
    interaction = VoterInteraction(
        voter_id=voter_id,
        interaction_type="canvass",
        source_table="canvassing_contacts",
        source_id=contact.contact_id,
        summary=f"Canvass: {contact_result}" + (f" — {issues_discussed[:100]}" if issues_discussed else ""),
    )
    db.add(interaction)
    await db.flush()
    return {"contact_id": str(contact.contact_id), "message": "Contact logged"}


@router.get("/contacts")
async def list_contacts(
    route_id: Optional[UUID] = None,
    voter_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(CanvassingContact)
    if route_id:
        query = query.where(CanvassingContact.route_id == route_id)
    if voter_id:
        query = query.where(CanvassingContact.voter_id == voter_id)
    query = query.order_by(CanvassingContact.contact_timestamp.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    contacts = result.scalars().all()
    return [
        {
            "contact_id": str(c.contact_id),
            "voter_id": str(c.voter_id),
            "contact_type": str(c.contact_type),
            "contact_result": str(c.contact_result),
            "sentiment_score": float(c.sentiment_score) if c.sentiment_score else None,
            "contact_timestamp": c.contact_timestamp.isoformat() if c.contact_timestamp else None,
        }
        for c in contacts
    ]

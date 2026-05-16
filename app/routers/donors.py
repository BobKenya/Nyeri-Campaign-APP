"""Donors: profiles, businesses, pledges, payments, ward reports, governor dashboard."""

from typing import Optional
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from pydantic import BaseModel

from app.database import get_db
from app.models.donors import DonorProfile, DonorBusiness, DonorPledge, DonorPayment, DonorInteraction
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  SCHEMAS
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

class DonorCreate(BaseModel):
    full_name: str
    phone_primary: str
    id_number: Optional[str] = None
    kra_pin: Optional[str] = None
    gender: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone_secondary: Optional[str] = None
    whatsapp_number: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    home_address: Optional[str] = None
    home_latitude: Optional[float] = None
    home_longitude: Optional[float] = None
    donor_category: str = "individual"
    referral_source: Optional[str] = None
    is_anonymous: bool = False
    is_vip: bool = False
    engagement_notes: Optional[str] = None
    voter_id: Optional[str] = None
    recruited_by_agent_id: Optional[str] = None

class BusinessCreate(BaseModel):
    business_name: str
    business_type: Optional[str] = None
    registration_number: Optional[str] = None
    kra_pin: Optional[str] = None
    industry: Optional[str] = None
    business_address: Optional[str] = None
    business_latitude: Optional[float] = None
    business_longitude: Optional[float] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    business_phone: Optional[str] = None
    business_email: Optional[str] = None
    website: Optional[str] = None
    estimated_annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    years_in_operation: Optional[int] = None
    can_provide_venue: bool = False
    can_provide_transport: bool = False
    can_provide_catering: bool = False
    can_provide_printing: bool = False
    other_in_kind_support: Optional[str] = None
    notes: Optional[str] = None

class PledgeCreate(BaseModel):
    pledge_type: str = "cash"
    pledge_amount: float
    in_kind_description: Optional[str] = None
    pledge_date: Optional[date] = None
    expected_fulfillment_date: Optional[date] = None
    payment_plan: str = "one_time"
    installment_amount: Optional[float] = None
    total_installments: Optional[int] = None
    pledge_occasion: Optional[str] = None
    event_id: Optional[str] = None
    witnessed_by: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    follow_up_date: Optional[date] = None
    assigned_to_user_id: Optional[str] = None

class PaymentCreate(BaseModel):
    amount: float
    payment_method: str = "mpesa"
    pledge_id: Optional[str] = None
    mpesa_code: Optional[str] = None
    bank_reference: Optional[str] = None
    cheque_number: Optional[str] = None
    in_kind_description: Optional[str] = None
    in_kind_estimated_value: Optional[float] = None
    payment_date: Optional[date] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    notes: Optional[str] = None

class InteractionCreate(BaseModel):
    interaction_type: str
    subject: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  DONOR PROFILES
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”


@router.get("/pledges/all")
async def list_all_pledges(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """Get all pledges across all donors."""
    result = await db.execute(
        select(DonorPledge, DonorProfile.full_name)
        .join(DonorProfile, DonorPledge.donor_id == DonorProfile.donor_id)
        .order_by(DonorPledge.pledge_date.desc())
    )
    return [
        {
            "pledge_id": r[0].pledge_id,
            "donor_id": r[0].donor_id,
            "donor_name": r[1],
            "pledge_amount": r[0].pledge_amount,
            "amount_paid": r[0].amount_paid,
            "amount_outstanding": r[0].amount_outstanding,
            "status": r[0].status,
            "pledge_date": r[0].pledge_date.isoformat(),
            "expected_fulfillment_date": r[0].expected_fulfillment_date.isoformat() if r[0].expected_fulfillment_date else None,
            "follow_up_date": r[0].follow_up_date.isoformat() if r[0].follow_up_date else None,
            "follow_up_notes": r[0].follow_up_notes,
        }
        for r in result.all()
    ]
@router.get("/")
async def list_donors(
    ward_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    donor_category: Optional[str] = None,
    donor_tier: Optional[str] = None,
    relationship_status: Optional[str] = None,
    is_vip: Optional[bool] = None,
    q: Optional[str] = None,
    sort_by: Optional[str] = "full_name",  # full_name, total_pledged, total_paid, last_donation_date
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(DonorProfile).where(DonorProfile.is_active == True)
    if ward_id:
        query = query.where(DonorProfile.ward_id == ward_id)
    if constituency_id:
        query = query.where(DonorProfile.constituency_id == constituency_id)
    if donor_category:
        query = query.where(DonorProfile.donor_category == donor_category)
    if donor_tier:
        query = query.where(DonorProfile.donor_tier == donor_tier)
    if relationship_status:
        query = query.where(DonorProfile.relationship_status == relationship_status)
    if is_vip is not None:
        query = query.where(DonorProfile.is_vip == is_vip)
    if q:
        query = query.where(or_(
            DonorProfile.full_name.ilike(f"%{q}%"),
            DonorProfile.phone_primary.ilike(f"%{q}%"),
            DonorProfile.id_number.ilike(f"%{q}%"),
        ))

    sort_map = {
        "full_name": DonorProfile.full_name,
        "total_pledged": DonorProfile.total_pledged.desc(),
        "total_paid": DonorProfile.total_paid.desc(),
        "last_donation_date": DonorProfile.last_donation_date.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, DonorProfile.full_name))
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "donor_id": d.donor_id, "full_name": d.full_name, "title": d.title,
            "phone_primary": d.phone_primary, "whatsapp_number": d.whatsapp_number,
            "email": d.email, "constituency_id": d.constituency_id, "ward_id": d.ward_id,
            "donor_category": d.donor_category, "donor_tier": d.donor_tier,
            "relationship_status": d.relationship_status,
            "total_pledged": d.total_pledged, "total_paid": d.total_paid,
            "total_outstanding": d.total_outstanding,
            "donation_count": d.donation_count, "is_vip": d.is_vip,
            "last_donation_date": d.last_donation_date.isoformat() if d.last_donation_date else None,
        }
        for d in result.scalars().all()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_donor(body: DonorCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    if body.id_number:
        existing = await db.execute(select(DonorProfile).where(DonorProfile.id_number == body.id_number))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Donor with this ID number already exists")
    donor = DonorProfile(**body.model_dump())
    db.add(donor)
    await db.flush()
    return {"donor_id": donor.donor_id, "message": f"Donor '{donor.full_name}' registered"}


@router.get("/{donor_id}")
async def get_donor_detail(donor_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donor_id))
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Donor not found")

    # Businesses
    biz = (await db.execute(select(DonorBusiness).where(DonorBusiness.donor_id == donor_id))).scalars().all()
    # Pledges
    pledges = (await db.execute(
        select(DonorPledge).where(DonorPledge.donor_id == donor_id).order_by(DonorPledge.pledge_date.desc())
    )).scalars().all()
    # Recent payments
    payments = (await db.execute(
        select(DonorPayment).where(DonorPayment.donor_id == donor_id).order_by(DonorPayment.payment_date.desc()).limit(20)
    )).scalars().all()
    # Recent interactions
    interactions = (await db.execute(
        select(DonorInteraction).where(DonorInteraction.donor_id == donor_id).order_by(DonorInteraction.interaction_date.desc()).limit(10)
    )).scalars().all()

    return {
        "donor_id": d.donor_id, "full_name": d.full_name, "title": d.title,
        "id_number": d.id_number, "kra_pin": d.kra_pin, "gender": d.gender,
        "phone_primary": d.phone_primary, "phone_secondary": d.phone_secondary,
        "whatsapp_number": d.whatsapp_number, "email": d.email,
        "facebook_url": d.facebook_url, "twitter_handle": d.twitter_handle,
        "constituency_id": d.constituency_id, "ward_id": d.ward_id,
        "home_address": d.home_address,
        "donor_category": d.donor_category, "donor_tier": d.donor_tier,
        "relationship_status": d.relationship_status, "is_vip": d.is_vip,
        "total_pledged": d.total_pledged, "total_paid": d.total_paid,
        "total_outstanding": d.total_outstanding, "donation_count": d.donation_count,
        "preferred_contact_method": d.preferred_contact_method,
        "engagement_notes": d.engagement_notes, "referral_source": d.referral_source,
        "businesses": [
            {"business_id": b.business_id, "business_name": b.business_name, "business_type": b.business_type,
             "industry": b.industry, "business_phone": b.business_phone, "ward_id": b.ward_id,
             "employee_count": b.employee_count, "estimated_annual_revenue": b.estimated_annual_revenue,
             "can_provide_venue": b.can_provide_venue, "can_provide_transport": b.can_provide_transport}
            for b in biz
        ],
        "pledges": [
            {"pledge_id": p.pledge_id, "pledge_type": p.pledge_type, "pledge_amount": p.pledge_amount,
             "status": p.status, "amount_fulfilled": p.amount_fulfilled,
             "amount_outstanding": p.amount_outstanding, "payment_plan": p.payment_plan,
             "pledge_date": p.pledge_date.isoformat() if p.pledge_date else None,
             "expected_fulfillment_date": p.expected_fulfillment_date.isoformat() if p.expected_fulfillment_date else None}
            for p in pledges
        ],
        "recent_payments": [
            {"payment_id": p.payment_id, "amount": p.amount, "payment_method": p.payment_method,
             "payment_date": p.payment_date.isoformat() if p.payment_date else None, "verified": p.verified}
            for p in payments
        ],
        "recent_interactions": [
            {"interaction_type": i.interaction_type, "subject": i.subject, "outcome": i.outcome,
             "interaction_date": i.interaction_date.isoformat() if i.interaction_date else None}
            for i in interactions
        ],
    }


@router.patch("/{donor_id}")
async def update_donor(donor_id: str, updates: dict, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donor_id))
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Donor not found")
    safe = {"full_name","title","phone_primary","phone_secondary","whatsapp_number","email",
            "facebook_url","twitter_handle","constituency_id","ward_id","home_address",
            "donor_category","donor_tier","relationship_status","is_vip","is_anonymous",
            "engagement_notes","preferred_contact_method","preferred_contact_time","risk_flag"}
    for k, v in updates.items():
        if k in safe:
            setattr(d, k, v)
    d.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Donor updated"}


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  BUSINESSES
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

@router.post("/{donor_id}/businesses", status_code=status.HTTP_201_CREATED)
async def add_business(donor_id: str, body: BusinessCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    biz = DonorBusiness(donor_id=donor_id, **body.model_dump())
    db.add(biz)
    await db.flush()
    return {"business_id": biz.business_id, "message": f"Business '{biz.business_name}' added"}


@router.get("/{donor_id}/businesses")
async def list_businesses(donor_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(DonorBusiness).where(DonorBusiness.donor_id == donor_id))
    return [
        {"business_id": b.business_id, "business_name": b.business_name, "business_type": b.business_type,
         "industry": b.industry, "registration_number": b.registration_number,
         "business_address": b.business_address, "business_phone": b.business_phone,
         "ward_id": b.ward_id, "employee_count": b.employee_count,
         "estimated_annual_revenue": b.estimated_annual_revenue,
         "can_provide_venue": b.can_provide_venue, "can_provide_transport": b.can_provide_transport,
         "can_provide_catering": b.can_provide_catering, "can_provide_printing": b.can_provide_printing}
        for b in result.scalars().all()
    ]


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  PLEDGES
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

@router.post("/{donor_id}/pledges", status_code=status.HTTP_201_CREATED)
async def create_pledge(donor_id: str, body: PledgeCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    pledge = DonorPledge(
        donor_id=donor_id,
        pledge_date=body.pledge_date or date.today(),
        amount_outstanding=body.pledge_amount,
        **body.model_dump(exclude={"pledge_date"}),
    )
    db.add(pledge)

    donor = (await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donor_id))).scalar_one_or_none()
    if donor:
        donor.total_pledged = (donor.total_pledged or 0) + body.pledge_amount
        donor.total_outstanding = (donor.total_outstanding or 0) + body.pledge_amount
        if donor.relationship_status in ("prospect", "contacted"):
            donor.relationship_status = "pledged"

    await db.flush()
    return {"pledge_id": pledge.pledge_id, "message": f"Pledge of KSH {body.pledge_amount:,.0f} recorded"}


@router.get("/pledges/overdue")
async def list_overdue_pledges(db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    today = date.today()
    result = await db.execute(
        select(DonorPledge, DonorProfile.full_name, DonorProfile.phone_primary)
        .join(DonorProfile, DonorPledge.donor_id == DonorProfile.donor_id)
        .where(
            DonorPledge.status.in_(["pledged", "partially_fulfilled"]),
            DonorPledge.expected_fulfillment_date < today,
        )
        .order_by(DonorPledge.expected_fulfillment_date)
    )
    return [
        {"pledge_id": r[0].pledge_id, "donor_name": r[1], "phone": r[2],
         "pledge_amount": r[0].pledge_amount, "amount_outstanding": r[0].amount_outstanding,
         "expected_date": r[0].expected_fulfillment_date.isoformat() if r[0].expected_fulfillment_date else None,
         "days_overdue": (today - r[0].expected_fulfillment_date).days if r[0].expected_fulfillment_date else 0,
         "ward_id": r[0].ward_id}
        for r in result.all()
    ]


@router.get("/pledges/follow-ups")
async def pledges_needing_follow_up(db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    today = date.today()
    result = await db.execute(
        select(DonorPledge, DonorProfile.full_name, DonorProfile.phone_primary)
        .join(DonorProfile, DonorPledge.donor_id == DonorProfile.donor_id)
        .where(DonorPledge.follow_up_date <= today, DonorPledge.status.in_(["pledged", "partially_fulfilled"]))
        .order_by(DonorPledge.follow_up_date)
    )
    return [
        {"pledge_id": r[0].pledge_id, "donor_name": r[1], "phone": r[2],
         "pledge_amount": r[0].pledge_amount, "follow_up_date": r[0].follow_up_date.isoformat(),
         "follow_up_notes": r[0].follow_up_notes}
        for r in result.all()
    ]


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  PAYMENTS
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

@router.post("/{donor_id}/payments", status_code=status.HTTP_201_CREATED)
async def record_payment(donor_id: str, body: PaymentCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    import secrets
    payment = DonorPayment(
        donor_id=donor_id,
        payment_date=body.payment_date or date.today(),
        received_by_user_id=user.user_id,
        receipt_number=f"DON-{secrets.token_hex(4).upper()}",
        **body.model_dump(exclude={"payment_date"}),
    )
    db.add(payment)

    # Update donor totals
    donor = (await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donor_id))).scalar_one_or_none()
    if donor:
        donor.total_paid = (donor.total_paid or 0) + body.amount
        donor.total_outstanding = max(0, (donor.total_outstanding or 0) - body.amount)
        donor.donation_count = (donor.donation_count or 0) + 1
        donor.last_donation_date = body.payment_date or date.today()
        if not donor.first_donation_date:
            donor.first_donation_date = donor.last_donation_date
        donor.relationship_status = "active_donor"
        # Auto-tier
        total = donor.total_paid
        if total >= 1000000: donor.donor_tier = "platinum"
        elif total >= 500000: donor.donor_tier = "gold"
        elif total >= 100000: donor.donor_tier = "silver"
        elif total >= 50000: donor.donor_tier = "bronze"

    # Update pledge if linked
    if body.pledge_id:
        pledge = (await db.execute(select(DonorPledge).where(DonorPledge.pledge_id == body.pledge_id))).scalar_one_or_none()
        if pledge:
            pledge.amount_fulfilled = (pledge.amount_fulfilled or 0) + body.amount
            pledge.amount_outstanding = max(0, pledge.pledge_amount - pledge.amount_fulfilled)
            pledge.last_payment_date = body.payment_date or date.today()
            if pledge.amount_outstanding <= 0:
                pledge.status = "fulfilled"
            else:
                pledge.status = "partially_fulfilled"

    await db.flush()
    return {"payment_id": payment.payment_id, "receipt_number": payment.receipt_number, "message": f"Payment of KSH {body.amount:,.0f} recorded"}


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  INTERACTIONS (CRM)
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

@router.post("/{donor_id}/interactions", status_code=status.HTTP_201_CREATED)
async def log_interaction(donor_id: str, body: InteractionCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    interaction = DonorInteraction(donor_id=donor_id, conducted_by_user_id=user.user_id, **body.model_dump())
    db.add(interaction)
    await db.flush()
    return {"interaction_id": interaction.interaction_id, "message": "Interaction logged"}


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  REPORTS BY WARD / CONSTITUENCY
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

@router.get("/reports/by-ward")
async def donors_by_ward(db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    """All 30 wards with donor counts, pledges, and payments."""
    from app.models.voters import Ward, Constituency
    result = await db.execute(
        select(
            Ward.ward_name, Constituency.constituency_name,
            func.count(DonorProfile.donor_id),
            func.coalesce(func.sum(DonorProfile.total_pledged), 0),
            func.coalesce(func.sum(DonorProfile.total_paid), 0),
            func.coalesce(func.sum(DonorProfile.total_outstanding), 0),
        )
        .outerjoin(DonorProfile, DonorProfile.ward_id == Ward.ward_id)
        .join(Constituency, Ward.constituency_id == Constituency.constituency_id)
        .group_by(Ward.ward_id, Constituency.constituency_id)
        .order_by(Constituency.constituency_name, Ward.ward_name)
    )
    return [
        {"ward": r[0], "constituency": r[1], "donors": r[2],
         "total_pledged": float(r[3]), "total_paid": float(r[4]), "outstanding": float(r[5])}
        for r in result.all()
    ]


@router.get("/reports/by-constituency")
async def donors_by_constituency(db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    from app.models.voters import Constituency
    result = await db.execute(
        select(
            Constituency.constituency_name,
            func.count(DonorProfile.donor_id),
            func.coalesce(func.sum(DonorProfile.total_pledged), 0),
            func.coalesce(func.sum(DonorProfile.total_paid), 0),
            func.coalesce(func.sum(DonorProfile.total_outstanding), 0),
            func.count(case((DonorProfile.is_vip == True, 1))),
        )
        .outerjoin(DonorProfile, DonorProfile.constituency_id == Constituency.constituency_id)
        .group_by(Constituency.constituency_id)
        .order_by(Constituency.constituency_name)
    )
    return [
        {"constituency": r[0], "donors": r[1], "total_pledged": float(r[2]),
         "total_paid": float(r[3]), "outstanding": float(r[4]), "vip_donors": r[5]}
        for r in result.all()
    ]


@router.get("/reports/by-category")
async def donors_by_category(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(
            DonorProfile.donor_category,
            func.count(DonorProfile.donor_id),
            func.coalesce(func.sum(DonorProfile.total_pledged), 0),
            func.coalesce(func.sum(DonorProfile.total_paid), 0),
        )
        .where(DonorProfile.is_active == True)
        .group_by(DonorProfile.donor_category)
        .order_by(func.sum(DonorProfile.total_paid).desc())
    )
    return [
        {"category": r[0], "donors": r[1], "total_pledged": float(r[2]), "total_paid": float(r[3])}
        for r in result.all()
    ]


@router.get("/reports/by-tier")
async def donors_by_tier(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(
            DonorProfile.donor_tier,
            func.count(DonorProfile.donor_id),
            func.coalesce(func.sum(DonorProfile.total_pledged), 0),
            func.coalesce(func.sum(DonorProfile.total_paid), 0),
        )
        .where(DonorProfile.is_active == True)
        .group_by(DonorProfile.donor_tier)
    )
    tier_order = {"platinum": 1, "gold": 2, "silver": 3, "bronze": 4, "standard": 5}
    rows = sorted(result.all(), key=lambda r: tier_order.get(r[0], 99))
    return [
        {"tier": r[0], "donors": r[1], "total_pledged": float(r[2]), "total_paid": float(r[3])}
        for r in rows
    ]


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
#  GOVERNOR'S DONOR DASHBOARD
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

@router.get("/governor-dashboard")
async def governor_donor_dashboard(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """Governor's single view of the entire donor pipeline."""
    total_donors = (await db.execute(select(func.count()).select_from(DonorProfile).where(DonorProfile.is_active == True))).scalar() or 0
    vip_donors = (await db.execute(select(func.count()).select_from(DonorProfile).where(DonorProfile.is_vip == True))).scalar() or 0
    total_pledged = (await db.execute(select(func.coalesce(func.sum(DonorProfile.total_pledged), 0)))).scalar()
    total_collected = (await db.execute(select(func.coalesce(func.sum(DonorProfile.total_paid), 0)))).scalar()
    total_outstanding = (await db.execute(select(func.coalesce(func.sum(DonorProfile.total_outstanding), 0)))).scalar()
    total_businesses = (await db.execute(select(func.count()).select_from(DonorBusiness))).scalar() or 0

    # Collection rate
    collection_rate = round(float(total_collected) / float(total_pledged) * 100, 1) if total_pledged else 0

    # Overdue pledges
    overdue = (await db.execute(
        select(func.count()).select_from(DonorPledge)
        .where(DonorPledge.status.in_(["pledged", "partially_fulfilled"]), DonorPledge.expected_fulfillment_date < date.today())
    )).scalar() or 0
    overdue_amount = (await db.execute(
        select(func.coalesce(func.sum(DonorPledge.amount_outstanding), 0))
        .where(DonorPledge.status.in_(["pledged", "partially_fulfilled"]), DonorPledge.expected_fulfillment_date < date.today())
    )).scalar()

    # This month collections
    month_start = date.today().replace(day=1)
    month_collections = (await db.execute(
        select(func.coalesce(func.sum(DonorPayment.amount), 0))
        .where(DonorPayment.payment_date >= month_start)
    )).scalar()

    # By status pipeline
    pipeline = await db.execute(
        select(DonorProfile.relationship_status, func.count(), func.coalesce(func.sum(DonorProfile.total_pledged), 0))
        .group_by(DonorProfile.relationship_status)
    )

    # Top 10 donors
    top_donors = await db.execute(
        select(DonorProfile.full_name, DonorProfile.donor_tier, DonorProfile.total_paid, DonorProfile.total_outstanding, DonorProfile.ward_id)
        .where(DonorProfile.is_active == True)
        .order_by(DonorProfile.total_paid.desc())
        .limit(10)
    )

    # In-kind support available
    in_kind = await db.execute(
        select(
            func.count(case((DonorBusiness.can_provide_venue == True, 1))),
            func.count(case((DonorBusiness.can_provide_transport == True, 1))),
            func.count(case((DonorBusiness.can_provide_catering == True, 1))),
            func.count(case((DonorBusiness.can_provide_printing == True, 1))),
        )
    )
    ik = in_kind.one()

    return {
        "overview": {
            "total_donors": total_donors, "vip_donors": vip_donors,
            "total_businesses": total_businesses,
            "total_pledged_ksh": float(total_pledged),
            "total_collected_ksh": float(total_collected),
            "total_outstanding_ksh": float(total_outstanding),
            "collection_rate_pct": collection_rate,
            "this_month_collections_ksh": float(month_collections),
        },
        "overdue": {
            "count": overdue, "total_overdue_ksh": float(overdue_amount),
        },
        "pipeline": [
            {"status": r[0], "count": r[1], "pledged_ksh": float(r[2])}
            for r in pipeline.all()
        ],
        "top_10_donors": [
            {"name": r[0], "tier": r[1], "paid_ksh": float(r[2] or 0), "outstanding_ksh": float(r[3] or 0), "ward_id": r[4]}
            for r in top_donors.all()
        ],
        "in_kind_support_available": {
            "venues": ik[0], "transport": ik[1], "catering": ik[2], "printing": ik[3],
        },
    }


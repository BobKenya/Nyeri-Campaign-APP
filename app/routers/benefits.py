"""Benefits Distribution: register recipients, track handouts, daily reports to governor."""

from typing import Optional
from datetime import datetime, date, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from pydantic import BaseModel

from app.database import get_db
from app.models.benefits import (
    BenefitItem, BenefitRecipient, BenefitDistribution,
    DailyDistributionReport, BenefitBudgetWard,
)
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ItemCreate(BaseModel):
    item_name: str
    item_category: str  # apparel, cash, food, transport, airtime, other
    unit: str = "piece"
    unit_cost: float = 0
    total_stock: int = 0
    description: Optional[str] = None

class RecipientCreate(BaseModel):
    full_name: str
    id_number: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    occupation: Optional[str] = None
    ward_id: str
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    village: Optional[str] = None
    home_address: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    support_level: Optional[str] = "unknown"
    recruited_by_agent_id: Optional[str] = None
    is_mobilizer: bool = False
    group_affiliation: Optional[str] = None
    voter_id: Optional[str] = None
    notes: Optional[str] = None

class DistributionCreate(BaseModel):
    recipient_id: str
    item_id: str
    quantity: int = 1
    cash_amount: float = 0
    item_size: Optional[str] = None
    item_color: Optional[str] = None
    distribution_date: Optional[date] = None
    distribution_location: Optional[str] = None
    event_name: Optional[str] = None
    event_id: Optional[str] = None
    ward_id: str
    constituency_id: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    distributed_by_agent_id: Optional[str] = None
    photo_evidence_url: Optional[str] = None
    verification_method: Optional[str] = None
    notes: Optional[str] = None

class BulkDistributionCreate(BaseModel):
    """Distribute same item to multiple recipients at once (e.g. 200 t-shirts at a rally)."""
    item_id: str
    recipient_ids: list[str]
    quantity: int = 1
    cash_amount: float = 0
    distribution_date: Optional[date] = None
    distribution_location: Optional[str] = None
    event_name: Optional[str] = None
    ward_id: str
    constituency_id: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BENEFIT ITEMS (catalog)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(BenefitItem).where(BenefitItem.is_active == True).order_by(BenefitItem.item_category))
    return [
        {
            "item_id": i.item_id, "item_name": i.item_name, "item_category": i.item_category,
            "unit": i.unit, "unit_cost": i.unit_cost, "total_stock": i.total_stock,
            "distributed_count": i.distributed_count, "remaining_stock": i.remaining_stock,
        }
        for i in result.scalars().all()
    ]


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(body: ItemCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    item = BenefitItem(remaining_stock=body.total_stock, **body.model_dump())
    db.add(item)
    await db.flush()
    return {"item_id": item.item_id, "message": f"Item '{item.item_name}' added to catalog"}


@router.patch("/items/{item_id}/restock")
async def restock_item(item_id: str, additional_stock: int, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(BenefitItem).where(BenefitItem.item_id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.total_stock += additional_stock
    item.remaining_stock += additional_stock
    await db.flush()
    return {"message": f"Restocked {additional_stock} units. New stock: {item.remaining_stock}"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RECIPIENTS (registration)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/recipients")
async def list_recipients(
    ward_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    is_mobilizer: Optional[bool] = None,
    group_affiliation: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(BenefitRecipient)
    if ward_id:
        query = query.where(BenefitRecipient.ward_id == ward_id)
    if constituency_id:
        query = query.where(BenefitRecipient.constituency_id == constituency_id)
    if is_mobilizer is not None:
        query = query.where(BenefitRecipient.is_mobilizer == is_mobilizer)
    if group_affiliation:
        query = query.where(BenefitRecipient.group_affiliation.ilike(f"%{group_affiliation}%"))
    if q:
        from sqlalchemy import or_
        query = query.where(or_(
            BenefitRecipient.full_name.ilike(f"%{q}%"),
            BenefitRecipient.id_number.ilike(f"%{q}%"),
            BenefitRecipient.phone_number.ilike(f"%{q}%"),
        ))
    query = query.order_by(BenefitRecipient.full_name).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "recipient_id": r.recipient_id, "full_name": r.full_name,
            "id_number": r.id_number, "phone_number": r.phone_number,
            "gender": r.gender, "age": r.age, "occupation": r.occupation,
            "ward_id": r.ward_id, "constituency_id": r.constituency_id,
            "village": r.village, "support_level": r.support_level,
            "is_mobilizer": r.is_mobilizer, "group_affiliation": r.group_affiliation,
            "total_items_received": r.total_items_received,
            "total_cash_received": r.total_cash_received,
            "last_benefit_date": r.last_benefit_date.isoformat() if r.last_benefit_date else None,
        }
        for r in result.scalars().all()
    ]


@router.post("/recipients", status_code=status.HTTP_201_CREATED)
async def register_recipient(body: RecipientCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    # Check for duplicate by ID number
    if body.id_number:
        existing = await db.execute(select(BenefitRecipient).where(BenefitRecipient.id_number == body.id_number))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Recipient with this ID number already registered")
    recipient = BenefitRecipient(**body.model_dump())
    db.add(recipient)
    await db.flush()
    return {"recipient_id": recipient.recipient_id, "message": f"Registered {recipient.full_name}"}


@router.get("/recipients/{recipient_id}")
async def get_recipient_detail(recipient_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(BenefitRecipient).where(BenefitRecipient.recipient_id == recipient_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Get distribution history
    dist_result = await db.execute(
        select(BenefitDistribution, BenefitItem.item_name)
        .join(BenefitItem, BenefitDistribution.item_id == BenefitItem.item_id)
        .where(BenefitDistribution.recipient_id == recipient_id)
        .order_by(BenefitDistribution.distribution_date.desc())
    )
    history = [
        {
            "item_name": row[1], "quantity": row[0].quantity,
            "cash_amount": row[0].cash_amount,
            "distribution_date": row[0].distribution_date.isoformat() if row[0].distribution_date else None,
            "distribution_location": row[0].distribution_location,
            "event_name": row[0].event_name,
        }
        for row in dist_result.all()
    ]

    return {
        "recipient_id": r.recipient_id, "full_name": r.full_name,
        "id_number": r.id_number, "phone_number": r.phone_number,
        "gender": r.gender, "age": r.age, "occupation": r.occupation,
        "ward_id": r.ward_id, "constituency_id": r.constituency_id,
        "village": r.village, "home_address": r.home_address,
        "gps_latitude": r.gps_latitude, "gps_longitude": r.gps_longitude,
        "support_level": r.support_level, "is_mobilizer": r.is_mobilizer,
        "group_affiliation": r.group_affiliation,
        "total_items_received": r.total_items_received,
        "total_cash_received": r.total_cash_received,
        "first_benefit_date": r.first_benefit_date.isoformat() if r.first_benefit_date else None,
        "last_benefit_date": r.last_benefit_date.isoformat() if r.last_benefit_date else None,
        "distribution_history": history,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISTRIBUTIONS (handouts)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/distribute", status_code=status.HTTP_201_CREATED)
async def record_distribution(body: DistributionCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Record giving an item to a recipient."""
    # Validate item exists and has stock
    item_result = await db.execute(select(BenefitItem).where(BenefitItem.item_id == body.item_id))
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.remaining_stock < body.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {item.remaining_stock}")

    dist_date = body.distribution_date or date.today()
    dist = BenefitDistribution(
        distributed_by_user_id=user.user_id,
        distribution_date=dist_date,
        verified=body.verification_method is not None,
        **body.model_dump(exclude={"distribution_date"}),
    )
    db.add(dist)

    # Update item stock
    item.distributed_count += body.quantity
    item.remaining_stock -= body.quantity

    # Update recipient totals
    recip_result = await db.execute(select(BenefitRecipient).where(BenefitRecipient.recipient_id == body.recipient_id))
    recipient = recip_result.scalar_one_or_none()
    if recipient:
        recipient.total_items_received = (recipient.total_items_received or 0) + body.quantity
        recipient.total_cash_received = (recipient.total_cash_received or 0) + body.cash_amount
        recipient.last_benefit_date = dist_date
        if not recipient.first_benefit_date:
            recipient.first_benefit_date = dist_date

    await db.flush()
    return {"distribution_id": dist.distribution_id, "message": f"Distributed {body.quantity}x {item.item_name} to recipient"}


@router.post("/distribute/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_distribute(body: BulkDistributionCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Distribute same item to many recipients at once (e.g. t-shirts at a rally)."""
    item_result = await db.execute(select(BenefitItem).where(BenefitItem.item_id == body.item_id))
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    total_needed = body.quantity * len(body.recipient_ids)
    if item.remaining_stock < total_needed:
        raise HTTPException(status_code=400, detail=f"Need {total_needed} but only {item.remaining_stock} in stock")

    dist_date = body.distribution_date or date.today()
    count = 0
    for rid in body.recipient_ids:
        dist = BenefitDistribution(
            recipient_id=rid, item_id=body.item_id, quantity=body.quantity,
            cash_amount=body.cash_amount, distribution_date=dist_date,
            distribution_location=body.distribution_location, event_name=body.event_name,
            ward_id=body.ward_id, constituency_id=body.constituency_id,
            distributed_by_user_id=user.user_id,
        )
        db.add(dist)

        recip = (await db.execute(select(BenefitRecipient).where(BenefitRecipient.recipient_id == rid))).scalar_one_or_none()
        if recip:
            recip.total_items_received = (recip.total_items_received or 0) + body.quantity
            recip.total_cash_received = (recip.total_cash_received or 0) + body.cash_amount
            recip.last_benefit_date = dist_date
            if not recip.first_benefit_date:
                recip.first_benefit_date = dist_date
        count += 1

    item.distributed_count += total_needed
    item.remaining_stock -= total_needed
    await db.flush()
    return {"message": f"Distributed {item.item_name} to {count} recipients", "total_units": total_needed}


@router.get("/distributions")
async def list_distributions(
    ward_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    item_id: Optional[str] = None,
    distribution_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(BenefitDistribution, BenefitRecipient.full_name, BenefitItem.item_name).join(
        BenefitRecipient, BenefitDistribution.recipient_id == BenefitRecipient.recipient_id
    ).join(BenefitItem, BenefitDistribution.item_id == BenefitItem.item_id)

    if ward_id:
        query = query.where(BenefitDistribution.ward_id == ward_id)
    if constituency_id:
        query = query.where(BenefitDistribution.constituency_id == constituency_id)
    if item_id:
        query = query.where(BenefitDistribution.item_id == item_id)
    if distribution_date:
        query = query.where(BenefitDistribution.distribution_date == distribution_date)

    query = query.order_by(BenefitDistribution.distribution_date.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "distribution_id": row[0].distribution_id,
            "recipient_name": row[1], "item_name": row[2],
            "quantity": row[0].quantity, "cash_amount": row[0].cash_amount,
            "distribution_date": row[0].distribution_date.isoformat() if row[0].distribution_date else None,
            "distribution_location": row[0].distribution_location,
            "ward_id": row[0].ward_id, "verified": row[0].verified,
        }
        for row in result.all()
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DAILY REPORTS (for the governor)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/reports/generate-daily")
async def generate_daily_report(
    report_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_coordinator),
):
    """Generate daily distribution reports for all wards. Run at end of each day."""
    target_date = report_date or date.today()

    from app.models.voters import Ward
    wards = (await db.execute(select(Ward))).scalars().all()
    reports_created = 0

    for ward in wards:
        # Check if report already exists
        existing = await db.execute(
            select(DailyDistributionReport).where(
                DailyDistributionReport.report_date == target_date,
                DailyDistributionReport.ward_id == ward.ward_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Aggregate distributions for this ward on this date
        dist_q = select(BenefitDistribution).where(
            BenefitDistribution.distribution_date == target_date,
            BenefitDistribution.ward_id == ward.ward_id,
        )
        dists = (await db.execute(dist_q)).scalars().all()
        if not dists:
            continue

        total_items = sum(d.quantity for d in dists)
        total_cash = sum(d.cash_amount or 0 for d in dists)
        unique_recipients = len(set(d.recipient_id for d in dists))

        # Count new recipients (first benefit today)
        new_recipients = 0
        for d in dists:
            r = (await db.execute(select(BenefitRecipient).where(BenefitRecipient.recipient_id == d.recipient_id))).scalar_one_or_none()
            if r and r.first_benefit_date == target_date:
                new_recipients += 1

        # Item breakdown
        breakdown = {}
        for d in dists:
            item = (await db.execute(select(BenefitItem).where(BenefitItem.item_id == d.item_id))).scalar_one_or_none()
            if item:
                key = item.item_name
                breakdown[key] = breakdown.get(key, 0) + d.quantity

        total_cost = sum(
            d.quantity * ((await db.execute(select(BenefitItem.unit_cost).where(BenefitItem.item_id == d.item_id))).scalar() or 0) + (d.cash_amount or 0)
            for d in dists
        )

        report = DailyDistributionReport(
            report_date=target_date,
            constituency_id=ward.constituency_id,
            ward_id=ward.ward_id,
            total_recipients=unique_recipients,
            new_recipients=new_recipients,
            total_items_distributed=total_items,
            total_cash_distributed=total_cash,
            items_breakdown_json=breakdown,
            total_cost=total_cost,
            submitted_by_user_id=user.user_id,
        )
        db.add(report)
        reports_created += 1

    await db.flush()
    return {"message": f"Generated {reports_created} ward reports for {target_date.isoformat()}"}


@router.get("/reports/daily")
async def get_daily_reports(
    report_date: Optional[date] = None,
    constituency_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get daily reports — the governor's daily briefing view."""
    target_date = report_date or date.today()
    query = select(DailyDistributionReport).where(DailyDistributionReport.report_date == target_date)
    if constituency_id:
        query = query.where(DailyDistributionReport.constituency_id == constituency_id)
    result = await db.execute(query.order_by(DailyDistributionReport.constituency_id))
    return [
        {
            "report_id": r.report_id, "report_date": r.report_date.isoformat(),
            "constituency_id": r.constituency_id, "ward_id": r.ward_id,
            "total_recipients": r.total_recipients, "new_recipients": r.new_recipients,
            "total_items_distributed": r.total_items_distributed,
            "total_cash_distributed": r.total_cash_distributed,
            "items_breakdown": r.items_breakdown_json,
            "total_cost": r.total_cost,
            "governor_viewed": r.governor_viewed,
        }
        for r in result.scalars().all()
    ]


@router.patch("/reports/{report_id}/governor-viewed")
async def mark_governor_viewed(report_id: str, governor_notes: Optional[str] = None, db: AsyncSession = Depends(get_db), _user=Depends(require_admin)):
    result = await db.execute(select(DailyDistributionReport).where(DailyDistributionReport.report_id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.governor_viewed = True
    report.governor_viewed_at = datetime.now(timezone.utc)
    if governor_notes:
        report.governor_notes = governor_notes
    await db.flush()
    return {"message": "Report marked as viewed by governor"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GOVERNOR'S BENEFITS DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/governor-dashboard")
async def governor_benefits_dashboard(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """The governor's single view of all benefits distribution across Nyeri County."""
    since_date = date.today() - timedelta(days=days)

    # Overall totals
    total_recipients = (await db.execute(select(func.count()).select_from(BenefitRecipient))).scalar() or 0
    total_items = (await db.execute(
        select(func.sum(BenefitDistribution.quantity))
        .where(BenefitDistribution.distribution_date >= since_date)
    )).scalar() or 0
    total_cash = (await db.execute(
        select(func.sum(BenefitDistribution.cash_amount))
        .where(BenefitDistribution.distribution_date >= since_date)
    )).scalar() or 0

    # By constituency
    from app.models.voters import Constituency, Ward
    constituency_stats = await db.execute(
        select(
            Constituency.constituency_name,
            func.count(func.distinct(BenefitDistribution.recipient_id)),
            func.sum(BenefitDistribution.quantity),
            func.sum(BenefitDistribution.cash_amount),
        )
        .join(BenefitDistribution, BenefitDistribution.constituency_id == Constituency.constituency_id)
        .where(BenefitDistribution.distribution_date >= since_date)
        .group_by(Constituency.constituency_id)
        .order_by(Constituency.constituency_name)
    )

    # By item
    item_stats = await db.execute(
        select(
            BenefitItem.item_name,
            BenefitItem.item_category,
            func.sum(BenefitDistribution.quantity),
            BenefitItem.remaining_stock,
        )
        .join(BenefitDistribution, BenefitDistribution.item_id == BenefitItem.item_id)
        .where(BenefitDistribution.distribution_date >= since_date)
        .group_by(BenefitItem.item_id)
        .order_by(func.sum(BenefitDistribution.quantity).desc())
    )

    # Today's activity
    today_items = (await db.execute(
        select(func.sum(BenefitDistribution.quantity))
        .where(BenefitDistribution.distribution_date == date.today())
    )).scalar() or 0
    today_cash = (await db.execute(
        select(func.sum(BenefitDistribution.cash_amount))
        .where(BenefitDistribution.distribution_date == date.today())
    )).scalar() or 0
    today_recipients = (await db.execute(
        select(func.count(func.distinct(BenefitDistribution.recipient_id)))
        .where(BenefitDistribution.distribution_date == date.today())
    )).scalar() or 0

    # Unviewed reports
    unviewed = (await db.execute(
        select(func.count()).select_from(DailyDistributionReport)
        .where(DailyDistributionReport.governor_viewed == False)
    )).scalar() or 0

    # Ward budget status
    ward_budgets = await db.execute(
        select(
            Ward.ward_name,
            BenefitBudgetWard.allocated_amount,
            BenefitBudgetWard.spent_amount,
            BenefitBudgetWard.remaining_amount,
            BenefitBudgetWard.target_recipients,
            BenefitBudgetWard.actual_recipients,
        )
        .join(BenefitBudgetWard, BenefitBudgetWard.ward_id == Ward.ward_id)
        .order_by(Ward.ward_name)
    )

    return {
        "period_days": days,
        "today": {
            "items_distributed": today_items,
            "cash_distributed": float(today_cash),
            "recipients_served": today_recipients,
        },
        "period_totals": {
            "total_registered_recipients": total_recipients,
            "total_items_distributed": total_items,
            "total_cash_distributed_ksh": float(total_cash),
        },
        "unviewed_daily_reports": unviewed,
        "by_constituency": [
            {"constituency": r[0], "recipients": r[1], "items": r[2] or 0, "cash_ksh": float(r[3] or 0)}
            for r in constituency_stats.all()
        ],
        "by_item": [
            {"item": r[0], "category": r[1], "distributed": r[2] or 0, "stock_remaining": r[3] or 0}
            for r in item_stats.all()
        ],
        "ward_budgets": [
            {
                "ward": r[0], "allocated": r[1], "spent": r[2],
                "remaining": r[3], "target_recipients": r[4], "actual_recipients": r[5],
            }
            for r in ward_budgets.all()
        ],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WARD BUDGET ALLOCATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/ward-budgets", status_code=status.HTTP_201_CREATED)
async def set_ward_budget(
    ward_id: str, constituency_id: str, allocated_amount: float, target_recipients: int = 0,
    db: AsyncSession = Depends(get_db), _user=Depends(require_admin),
):
    existing = await db.execute(select(BenefitBudgetWard).where(BenefitBudgetWard.ward_id == ward_id))
    budget = existing.scalar_one_or_none()
    if budget:
        budget.allocated_amount = allocated_amount
        budget.remaining_amount = allocated_amount - (budget.spent_amount or 0)
        budget.target_recipients = target_recipients
    else:
        budget = BenefitBudgetWard(
            ward_id=ward_id, constituency_id=constituency_id,
            allocated_amount=allocated_amount, remaining_amount=allocated_amount,
            target_recipients=target_recipients,
        )
        db.add(budget)
    await db.flush()
    return {"message": f"Ward budget set to KSH {allocated_amount:,.0f}"}


@router.get("/ward-budgets")
async def list_ward_budgets(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    from app.models.voters import Ward, Constituency
    result = await db.execute(
        select(Ward.ward_name, Constituency.constituency_name, BenefitBudgetWard)
        .join(Ward, BenefitBudgetWard.ward_id == Ward.ward_id)
        .join(Constituency, BenefitBudgetWard.constituency_id == Constituency.constituency_id)
        .order_by(Constituency.constituency_name, Ward.ward_name)
    )
    return [
        {
            "ward": r[0], "constituency": r[1],
            "allocated": r[2].allocated_amount, "spent": r[2].spent_amount,
            "remaining": r[2].remaining_amount,
            "target_recipients": r[2].target_recipients,
            "actual_recipients": r[2].actual_recipients,
        }
        for r in result.all()
    ]

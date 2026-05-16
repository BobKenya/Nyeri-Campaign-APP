"""Budget Management: county/constituency/ward budgets, real-time spending, alerts, governor view."""

from typing import Optional
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from app.database import get_db
from app.models.budgets import (
    CountyBudget, ConstituencyBudget, WardBudget,
    BudgetLineItem, SpendingTransaction, BudgetAlert,
)
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()

SPEND_CATEGORIES = [
    "personnel","transport","printing","events","catering","media","fuel",
    "airtime","apparel","donations_to_groups","venue","security","equipment","other"
]


# ── SCHEMAS ────────────────────────────────────────────────────────

class CountyBudgetCreate(BaseModel):
    budget_name: str
    budget_period: str
    start_date: date
    end_date: date
    total_allocated: float
    category_allocations_json: Optional[dict] = {}
    self_funding: float = 0
    notes: Optional[str] = None

class ConstituencyBudgetCreate(BaseModel):
    constituency_id: str
    total_allocated: float
    category_allocations_json: Optional[dict] = {}
    target_voters_reached: int = 0
    target_events: int = 0

class WardBudgetCreate(BaseModel):
    ward_id: str
    total_allocated: float
    category_allocations_json: Optional[dict] = {}
    coordinator_name: Optional[str] = None
    coordinator_user_id: Optional[str] = None

class LineItemCreate(BaseModel):
    category: str
    description: str
    quantity: int = 1
    unit_cost: float = 0
    allocated_amount: float
    supplier_id: Optional[str] = None
    notes: Optional[str] = None

class SpendCreate(BaseModel):
    category: str
    description: str
    amount: float
    transaction_date: Optional[date] = None
    ward_id: str
    constituency_id: Optional[str] = None
    line_item_id: Optional[str] = None
    payment_method: Optional[str] = None
    mpesa_code: Optional[str] = None
    bank_reference: Optional[str] = None
    receipt_number: Optional[str] = None
    paid_to: Optional[str] = None
    supplier_id: Optional[str] = None
    purchase_order_id: Optional[str] = None
    photo_evidence_url: Optional[str] = None
    notes: Optional[str] = None


# ── COUNTY BUDGET ──────────────────────────────────────────────────

@router.post("/county", status_code=status.HTTP_201_CREATED)
async def create_county_budget(body: CountyBudgetCreate, db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    budget = CountyBudget(
        total_remaining=body.total_allocated,
        funding_gap=body.total_allocated - body.self_funding,
        created_by_user_id=user.user_id,
        **body.model_dump(),
    )
    db.add(budget)
    await db.flush()
    return {"budget_id": budget.budget_id, "message": f"County budget '{budget.budget_name}' created — KSH {body.total_allocated:,.0f}"}


@router.get("/county")
async def get_county_budget(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(CountyBudget).where(CountyBudget.status == "active").order_by(CountyBudget.created_at.desc()).limit(1))
    b = result.scalar_one_or_none()
    if not b:
        return {"message": "No active county budget found"}
    return {
        "budget_id": b.budget_id, "budget_name": b.budget_name, "budget_period": b.budget_period,
        "start_date": b.start_date.isoformat(), "end_date": b.end_date.isoformat(),
        "total_allocated": b.total_allocated, "total_spent": b.total_spent,
        "total_committed": b.total_committed, "total_remaining": b.total_remaining,
        "spend_percentage": b.spend_percentage,
        "category_allocations": b.category_allocations_json,
        "total_donations_received": b.total_donations_received,
        "total_pledges_outstanding": b.total_pledges_outstanding,
        "self_funding": b.self_funding, "funding_gap": b.funding_gap,
        "status": b.status,
    }


# ── CONSTITUENCY BUDGETS ──────────────────────────────────────────

@router.post("/county/{budget_id}/constituencies", status_code=status.HTTP_201_CREATED)
async def create_constituency_budget(budget_id: str, body: ConstituencyBudgetCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_admin)):
    cb = ConstituencyBudget(
        county_budget_id=budget_id,
        total_remaining=body.total_allocated,
        **body.model_dump(),
    )
    db.add(cb)
    await db.flush()
    return {"const_budget_id": cb.const_budget_id, "message": "Constituency budget created"}


@router.get("/county/{budget_id}/constituencies")
async def list_constituency_budgets(budget_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    from app.models.voters import Constituency
    result = await db.execute(
        select(ConstituencyBudget, Constituency.constituency_name)
        .join(Constituency, ConstituencyBudget.constituency_id == Constituency.constituency_id)
        .where(ConstituencyBudget.county_budget_id == budget_id)
        .order_by(Constituency.constituency_name)
    )
    return [
        {
            "const_budget_id": r[0].const_budget_id, "constituency": r[1],
            "constituency_id": r[0].constituency_id,
            "allocated": r[0].total_allocated, "spent": r[0].total_spent,
            "committed": r[0].total_committed, "remaining": r[0].total_remaining,
            "spend_pct": r[0].spend_percentage,
            "category_allocations": r[0].category_allocations_json,
            "category_spent": r[0].category_spent_json,
            "target_voters": r[0].target_voters_reached, "actual_voters": r[0].actual_voters_reached,
        }
        for r in result.all()
    ]


# ── WARD BUDGETS ──────────────────────────────────────────────────

@router.post("/constituencies/{const_budget_id}/wards", status_code=status.HTTP_201_CREATED)
async def create_ward_budget(const_budget_id: str, body: WardBudgetCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    cb = (await db.execute(select(ConstituencyBudget).where(ConstituencyBudget.const_budget_id == const_budget_id))).scalar_one_or_none()
    if not cb:
        raise HTTPException(status_code=404, detail="Constituency budget not found")
    wb = WardBudget(
        const_budget_id=const_budget_id,
        constituency_id=cb.constituency_id,
        total_remaining=body.total_allocated,
        **body.model_dump(),
    )
    db.add(wb)
    await db.flush()
    return {"ward_budget_id": wb.ward_budget_id, "message": "Ward budget created"}


@router.get("/constituencies/{const_budget_id}/wards")
async def list_ward_budgets(const_budget_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    from app.models.voters import Ward
    result = await db.execute(
        select(WardBudget, Ward.ward_name)
        .join(Ward, WardBudget.ward_id == Ward.ward_id)
        .where(WardBudget.const_budget_id == const_budget_id)
        .order_by(Ward.ward_name)
    )
    return [
        {
            "ward_budget_id": r[0].ward_budget_id, "ward": r[1], "ward_id": r[0].ward_id,
            "allocated": r[0].total_allocated, "spent": r[0].total_spent,
            "committed": r[0].total_committed, "remaining": r[0].total_remaining,
            "spend_pct": r[0].spend_percentage,
            "coordinator": r[0].coordinator_name,
            "category_allocations": r[0].category_allocations_json,
            "category_spent": r[0].category_spent_json,
        }
        for r in result.all()
    ]


# ── LINE ITEMS ────────────────────────────────────────────────────

@router.post("/wards/{ward_budget_id}/line-items", status_code=status.HTTP_201_CREATED)
async def add_line_item(ward_budget_id: str, body: LineItemCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    item = BudgetLineItem(
        ward_budget_id=ward_budget_id,
        remaining_amount=body.allocated_amount,
        approved_by_user_id=user.user_id,
        **body.model_dump(),
    )
    db.add(item)
    await db.flush()
    return {"line_item_id": item.line_item_id, "message": f"Line item '{body.description}' added — KSH {body.allocated_amount:,.0f}"}


@router.get("/wards/{ward_budget_id}/line-items")
async def list_line_items(ward_budget_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(BudgetLineItem).where(BudgetLineItem.ward_budget_id == ward_budget_id).order_by(BudgetLineItem.category)
    )
    return [
        {
            "line_item_id": i.line_item_id, "category": i.category,
            "description": i.description, "quantity": i.quantity, "unit_cost": i.unit_cost,
            "allocated": i.allocated_amount, "spent": i.spent_amount,
            "committed": i.committed_amount, "remaining": i.remaining_amount,
            "spend_pct": i.spend_percentage, "status": i.status,
        }
        for i in result.scalars().all()
    ]


# ── SPENDING TRANSACTIONS ─────────────────────────────────────────

@router.post("/spend", status_code=status.HTTP_201_CREATED)
async def record_spending(body: SpendCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Record a real-time spending transaction. Auto-updates ward → constituency → county totals."""

    # Find ward budget
    wb = (await db.execute(select(WardBudget).where(WardBudget.ward_id == body.ward_id))).scalar_one_or_none()
    if not wb:
        raise HTTPException(status_code=404, detail="No budget found for this ward. Create a ward budget first.")

    txn = SpendingTransaction(
        ward_budget_id=wb.ward_budget_id,
        transaction_date=body.transaction_date or date.today(),
        recorded_by_user_id=user.user_id,
        **body.model_dump(exclude={"transaction_date"}),
    )
    db.add(txn)

    # ── Update ward budget ──
    wb.total_spent = (wb.total_spent or 0) + body.amount
    wb.total_remaining = max(0, wb.total_allocated - wb.total_spent)
    wb.spend_percentage = round(wb.total_spent / wb.total_allocated * 100, 1) if wb.total_allocated else 0

    # Update category spent
    cat_spent = wb.category_spent_json or {}
    cat_spent[body.category] = cat_spent.get(body.category, 0) + body.amount
    wb.category_spent_json = cat_spent

    # Update line item if linked
    if body.line_item_id:
        li = (await db.execute(select(BudgetLineItem).where(BudgetLineItem.line_item_id == body.line_item_id))).scalar_one_or_none()
        if li:
            li.spent_amount = (li.spent_amount or 0) + body.amount
            li.remaining_amount = max(0, li.allocated_amount - li.spent_amount)
            li.spend_percentage = round(li.spent_amount / li.allocated_amount * 100, 1) if li.allocated_amount else 0
            if li.spent_amount > li.allocated_amount:
                li.status = "overspent"
            elif li.spend_percentage >= 100:
                li.status = "completed"
            elif li.spend_percentage > 0:
                li.status = "in_progress"

    # ── Update constituency budget ──
    cb = (await db.execute(select(ConstituencyBudget).where(ConstituencyBudget.const_budget_id == wb.const_budget_id))).scalar_one_or_none()
    if cb:
        cb.total_spent = (cb.total_spent or 0) + body.amount
        cb.total_remaining = max(0, cb.total_allocated - cb.total_spent)
        cb.spend_percentage = round(cb.total_spent / cb.total_allocated * 100, 1) if cb.total_allocated else 0
        c_cat = cb.category_spent_json or {}
        c_cat[body.category] = c_cat.get(body.category, 0) + body.amount
        cb.category_spent_json = c_cat

        # ── Update county budget ──
        county = (await db.execute(select(CountyBudget).where(CountyBudget.budget_id == cb.county_budget_id))).scalar_one_or_none()
        if county:
            county.total_spent = (county.total_spent or 0) + body.amount
            county.total_remaining = max(0, county.total_allocated - county.total_spent)
            county.spend_percentage = round(county.total_spent / county.total_allocated * 100, 1) if county.total_allocated else 0

    # ── Auto-generate alerts ──
    if wb.spend_percentage >= 100:
        alert = BudgetAlert(alert_type="exceeded", level="ward", ward_id=body.ward_id, constituency_id=body.constituency_id, category=body.category,
            message=f"Ward budget EXCEEDED: {wb.spend_percentage:.0f}% used (KSH {wb.total_spent:,.0f} of {wb.total_allocated:,.0f})",
            amount_allocated=wb.total_allocated, amount_spent=wb.total_spent, percentage_used=wb.spend_percentage)
        db.add(alert)
    elif wb.spend_percentage >= 90:
        alert = BudgetAlert(alert_type="near_limit_90", level="ward", ward_id=body.ward_id, constituency_id=body.constituency_id, category=body.category,
            message=f"Ward budget at {wb.spend_percentage:.0f}% — KSH {wb.total_remaining:,.0f} remaining",
            amount_allocated=wb.total_allocated, amount_spent=wb.total_spent, percentage_used=wb.spend_percentage)
        db.add(alert)
    elif wb.spend_percentage >= 80:
        alert = BudgetAlert(alert_type="near_limit_80", level="ward", ward_id=body.ward_id, constituency_id=body.constituency_id, category=body.category,
            message=f"Ward budget at {wb.spend_percentage:.0f}% — monitor spending",
            amount_allocated=wb.total_allocated, amount_spent=wb.total_spent, percentage_used=wb.spend_percentage)
        db.add(alert)

    await db.flush()
    return {
        "transaction_id": txn.transaction_id,
        "message": f"KSH {body.amount:,.0f} recorded for '{body.description}'",
        "ward_budget": {"spent": wb.total_spent, "remaining": wb.total_remaining, "spend_pct": wb.spend_percentage},
    }


@router.get("/spending")
async def list_spending(
    ward_id: Optional[str] = None,
    constituency_id: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), _user=Depends(get_current_user),
):
    query = select(SpendingTransaction)
    if ward_id:
        query = query.where(SpendingTransaction.ward_id == ward_id)
    if constituency_id:
        query = query.where(SpendingTransaction.constituency_id == constituency_id)
    if category:
        query = query.where(SpendingTransaction.category == category)
    if from_date:
        query = query.where(SpendingTransaction.transaction_date >= from_date)
    if to_date:
        query = query.where(SpendingTransaction.transaction_date <= to_date)
    query = query.order_by(SpendingTransaction.transaction_date.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "transaction_id": t.transaction_id, "category": t.category,
            "description": t.description, "amount": t.amount,
            "transaction_date": t.transaction_date.isoformat(),
            "ward_id": t.ward_id, "paid_to": t.paid_to,
            "payment_method": t.payment_method, "receipt_number": t.receipt_number,
            "verified": t.verified,
        }
        for t in result.scalars().all()
    ]


# ── ALERTS ─────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(unread_only: bool = True, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    query = select(BudgetAlert)
    if unread_only:
        query = query.where(BudgetAlert.is_read == False)
    result = await db.execute(query.order_by(BudgetAlert.created_at.desc()).limit(50))
    return [
        {
            "alert_id": a.alert_id, "alert_type": a.alert_type, "level": a.level,
            "message": a.message, "category": a.category,
            "ward_id": a.ward_id, "constituency_id": a.constituency_id,
            "percentage_used": a.percentage_used, "is_read": a.is_read,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(BudgetAlert).where(BudgetAlert.alert_id == alert_id))
    a = result.scalar_one_or_none()
    if a:
        a.is_read = True
        a.read_by_user_id = user.user_id
        a.read_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Alert marked read"}


# ── GOVERNOR'S BUDGET DASHBOARD ────────────────────────────────────

@router.get("/governor-dashboard")
async def governor_budget_dashboard(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    """Real-time budget vs spending across county → constituency → ward."""

    # County level
    county = (await db.execute(select(CountyBudget).where(CountyBudget.status == "active").limit(1))).scalar_one_or_none()
    county_data = None
    if county:
        county_data = {
            "budget_name": county.budget_name, "budget_period": county.budget_period,
            "total_allocated": county.total_allocated, "total_spent": county.total_spent,
            "total_committed": county.total_committed, "total_remaining": county.total_remaining,
            "spend_percentage": county.spend_percentage,
            "category_allocations": county.category_allocations_json,
            "donations_received": county.total_donations_received,
            "funding_gap": county.funding_gap,
        }

    # Constituency breakdown
    from app.models.voters import Constituency, Ward
    const_data = []
    if county:
        const_result = await db.execute(
            select(ConstituencyBudget, Constituency.constituency_name)
            .join(Constituency, ConstituencyBudget.constituency_id == Constituency.constituency_id)
            .where(ConstituencyBudget.county_budget_id == county.budget_id)
            .order_by(Constituency.constituency_name)
        )
        for r in const_result.all():
            const_data.append({
                "constituency": r[1], "constituency_id": r[0].constituency_id,
                "allocated": r[0].total_allocated, "spent": r[0].total_spent,
                "remaining": r[0].total_remaining, "spend_pct": r[0].spend_percentage,
                "category_spent": r[0].category_spent_json,
            })

    # All 30 wards
    ward_data = []
    ward_result = await db.execute(
        select(WardBudget, Ward.ward_name, Constituency.constituency_name)
        .join(Ward, WardBudget.ward_id == Ward.ward_id)
        .join(Constituency, WardBudget.constituency_id == Constituency.constituency_id)
        .order_by(Constituency.constituency_name, Ward.ward_name)
    )
    for r in ward_result.all():
        ward_data.append({
            "ward": r[1], "constituency": r[2], "ward_id": r[0].ward_id,
            "allocated": r[0].total_allocated, "spent": r[0].total_spent,
            "remaining": r[0].total_remaining, "spend_pct": r[0].spend_percentage,
            "coordinator": r[0].coordinator_name,
        })

    # Spending by category (across all)
    cat_result = await db.execute(
        select(SpendingTransaction.category, func.sum(SpendingTransaction.amount), func.count())
        .group_by(SpendingTransaction.category)
        .order_by(func.sum(SpendingTransaction.amount).desc())
    )

    # Today's spending
    today_total = (await db.execute(
        select(func.coalesce(func.sum(SpendingTransaction.amount), 0))
        .where(SpendingTransaction.transaction_date == date.today())
    )).scalar()

    # This week
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_total = (await db.execute(
        select(func.coalesce(func.sum(SpendingTransaction.amount), 0))
        .where(SpendingTransaction.transaction_date >= week_start)
    )).scalar()

    # Unread alerts
    unread_alerts = (await db.execute(
        select(func.count()).select_from(BudgetAlert).where(BudgetAlert.is_read == False)
    )).scalar() or 0

    # Overspent wards
    overspent = (await db.execute(
        select(func.count()).select_from(WardBudget).where(WardBudget.spend_percentage > 100)
    )).scalar() or 0

    return {
        "county_overview": county_data,
        "by_constituency": const_data,
        "all_wards": ward_data,
        "spending_by_category": [
            {"category": r[0], "total_spent": float(r[1]), "transactions": r[2]}
            for r in cat_result.all()
        ],
        "real_time": {
            "today_spent_ksh": float(today_total),
            "this_week_spent_ksh": float(week_total),
            "unread_budget_alerts": unread_alerts,
            "overspent_wards": overspent,
        },
    }

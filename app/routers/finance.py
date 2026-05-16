"""Finance routes: donations, expenses, budget allocations."""

from uuid import UUID
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.messaging_finance import Donation, CampaignExpense, BudgetAllocation
from app.schemas.common import DonationCreate, DonationResponse, ExpenseCreate, BudgetAllocationCreate
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()


# ── Donations ──────────────────────────────────────────────────────

@router.get("/donations", response_model=list[DonationResponse])
async def list_donations(
    payment_method: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Donation)
    if payment_method:
        query = query.where(Donation.payment_method == payment_method)
    query = query.order_by(Donation.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/donations", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def record_donation(body: DonationCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    import secrets
    donation = Donation(receipt_number=f"RCT-{secrets.token_hex(4).upper()}", **body.model_dump())
    db.add(donation)
    await db.flush()
    await db.refresh(donation)
    return donation


@router.get("/donations/summary")
async def donation_summary(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    total = (await db.execute(select(func.sum(Donation.donation_amount)))).scalar() or 0
    count = (await db.execute(select(func.count()).select_from(Donation))).scalar() or 0
    by_method = await db.execute(
        select(Donation.payment_method, func.sum(Donation.donation_amount), func.count())
        .group_by(Donation.payment_method)
    )
    return {
        "total_raised": float(total),
        "total_donations": count,
        "by_payment_method": [
            {"method": str(r[0]), "amount": float(r[1]), "count": r[2]} for r in by_method.all()
        ],
    }


# ── Expenses ───────────────────────────────────────────────────────

@router.get("/expenses")
async def list_expenses(
    category: Optional[str] = None,
    approval_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(CampaignExpense)
    if category:
        query = query.where(CampaignExpense.expense_category == category)
    if approval_status:
        query = query.where(CampaignExpense.approval_status == approval_status)
    query = query.order_by(CampaignExpense.expense_date.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "expense_id": str(e.expense_id),
            "category": str(e.expense_category),
            "amount": float(e.amount),
            "vendor_name": e.vendor_name,
            "approval_status": str(e.approval_status),
            "expense_date": e.expense_date.isoformat(),
        }
        for e in result.scalars().all()
    ]


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
async def record_expense(body: ExpenseCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    expense = CampaignExpense(**body.model_dump())
    db.add(expense)
    await db.flush()
    return {"expense_id": str(expense.expense_id), "message": "Expense recorded"}


@router.patch("/expenses/{expense_id}/approve")
async def approve_expense(expense_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    result = await db.execute(select(CampaignExpense).where(CampaignExpense.expense_id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    expense.approval_status = "approved"
    expense.approved_by_user_id = user.user_id
    return {"message": "Expense approved"}


# ── Budget ─────────────────────────────────────────────────────────

@router.get("/budgets")
async def list_budgets(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(BudgetAllocation).order_by(BudgetAllocation.category))
    return [
        {
            "budget_id": str(b.budget_id),
            "constituency_id": str(b.constituency_id) if b.constituency_id else None,
            "category": b.category,
            "total_amount": float(b.total_amount),
            "spent_amount": float(b.spent_amount) if b.spent_amount else 0,
            "remaining_amount": float(b.remaining_amount) if b.remaining_amount else float(b.total_amount),
        }
        for b in result.scalars().all()
    ]


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
async def create_budget(body: BudgetAllocationCreate, db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    budget = BudgetAllocation(
        created_by_user_id=user.user_id,
        remaining_amount=body.total_amount,
        **body.model_dump(),
    )
    db.add(budget)
    await db.flush()
    return {"budget_id": str(budget.budget_id), "message": "Budget allocation created"}

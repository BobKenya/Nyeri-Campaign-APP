"""Suppliers: profiles, contracts, purchase orders, invoices, payments, deliveries, reporting."""

from typing import Optional
from datetime import datetime, date, timedelta, timezone
import secrets as sec
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from pydantic import BaseModel

from app.database import get_db
from app.models.suppliers import (
    SupplierProfile, SupplierContract, PurchaseOrder,
    SupplierInvoice, SupplierPayment, SupplierDelivery,
)
from app.dependencies import get_current_user, require_coordinator, require_admin

router = APIRouter()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SupplierCreate(BaseModel):
    business_name: str
    contact_person: str
    phone_primary: str
    supply_category: str
    trading_name: Optional[str] = None
    registration_number: Optional[str] = None
    kra_pin: Optional[str] = None
    business_type: Optional[str] = None
    products_services_json: Optional[list] = []
    phone_secondary: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    physical_address: Optional[str] = None
    town: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    mpesa_paybill: Optional[str] = None
    mpesa_till: Optional[str] = None

class ContractCreate(BaseModel):
    contract_title: str
    contract_amount: float
    start_date: date
    end_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    deposit_amount: float = 0
    items_services_json: Optional[list] = []
    description: Optional[str] = None

class OrderCreate(BaseModel):
    supplier_id: str
    contract_id: Optional[str] = None
    order_items_json: list
    total_quantity: int
    order_amount: float
    deposit_required: float = 0
    expected_delivery_date: Optional[date] = None
    delivery_address: Optional[str] = None
    delivery_constituency_id: Optional[str] = None
    delivery_ward_id: Optional[str] = None
    notes: Optional[str] = None

class InvoiceCreate(BaseModel):
    invoice_number: str
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_amount: float
    tax_amount: float = 0
    invoice_document_url: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(BaseModel):
    payment_type: str = "partial"
    amount: float
    payment_method: str = "mpesa"
    mpesa_code: Optional[str] = None
    bank_reference: Optional[str] = None
    cheque_number: Optional[str] = None
    payment_date: Optional[date] = None
    invoice_id: Optional[str] = None
    notes: Optional[str] = None

class DeliveryCreate(BaseModel):
    items_delivered_json: Optional[list] = []
    quantity_delivered: int
    delivery_date: Optional[date] = None
    delivery_location: Optional[str] = None
    delivery_note_number: Optional[str] = None
    photo_evidence_url: Optional[str] = None
    notes: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SUPPLIER PROFILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/")
async def list_suppliers(
    supply_category: Optional[str] = None,
    is_preferred: Optional[bool] = None,
    ward_id: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), _user=Depends(get_current_user),
):
    from sqlalchemy import or_
    query = select(SupplierProfile).where(SupplierProfile.is_active == True, SupplierProfile.is_blacklisted == False)
    if supply_category:
        query = query.where(SupplierProfile.supply_category == supply_category)
    if is_preferred is not None:
        query = query.where(SupplierProfile.is_preferred == is_preferred)
    if ward_id:
        query = query.where(SupplierProfile.ward_id == ward_id)
    if q:
        query = query.where(or_(
            SupplierProfile.business_name.ilike(f"%{q}%"),
            SupplierProfile.contact_person.ilike(f"%{q}%"),
            SupplierProfile.phone_primary.ilike(f"%{q}%"),
        ))
    query = query.order_by(SupplierProfile.business_name).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "supplier_id": s.supplier_id, "business_name": s.business_name,
            "contact_person": s.contact_person, "phone_primary": s.phone_primary,
            "supply_category": s.supply_category,
            "products_services": s.products_services_json,
            "total_contracted": s.total_contracted, "total_paid": s.total_paid,
            "total_unpaid": s.total_unpaid, "total_orders": s.total_orders,
            "overall_rating": s.overall_rating, "is_preferred": s.is_preferred,
            "town": s.town, "ward_id": s.ward_id,
        }
        for s in result.scalars().all()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    supplier = SupplierProfile(approved_by_user_id=user.user_id, **body.model_dump())
    db.add(supplier)
    await db.flush()
    return {"supplier_id": supplier.supplier_id, "message": f"Supplier '{supplier.business_name}' registered"}


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == supplier_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")

    contracts = (await db.execute(select(SupplierContract).where(SupplierContract.supplier_id == supplier_id))).scalars().all()
    orders = (await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id).order_by(PurchaseOrder.order_date.desc()).limit(20)
    )).scalars().all()

    return {
        "supplier_id": s.supplier_id, "business_name": s.business_name,
        "trading_name": s.trading_name, "registration_number": s.registration_number,
        "kra_pin": s.kra_pin, "business_type": s.business_type,
        "supply_category": s.supply_category,
        "products_services": s.products_services_json,
        "contact_person": s.contact_person, "contact_title": s.contact_title,
        "phone_primary": s.phone_primary, "phone_secondary": s.phone_secondary,
        "whatsapp_number": s.whatsapp_number, "email": s.email,
        "physical_address": s.physical_address, "town": s.town,
        "bank_name": s.bank_name, "bank_account_number": s.bank_account_number,
        "mpesa_paybill": s.mpesa_paybill, "mpesa_till": s.mpesa_till,
        "overall_rating": s.overall_rating, "is_preferred": s.is_preferred,
        "total_contracted": s.total_contracted, "total_invoiced": s.total_invoiced,
        "total_paid": s.total_paid, "total_deposits": s.total_deposits,
        "total_unpaid": s.total_unpaid, "total_orders": s.total_orders,
        "contracts": [
            {"contract_id": c.contract_id, "contract_title": c.contract_title,
             "contract_amount": c.contract_amount, "status": c.status,
             "completion_percentage": c.completion_percentage,
             "start_date": c.start_date.isoformat() if c.start_date else None}
            for c in contracts
        ],
        "recent_orders": [
            {"order_id": o.order_id, "order_number": o.order_number,
             "order_amount": o.order_amount, "status": o.status,
             "work_progress": o.work_progress, "progress_percentage": o.progress_percentage,
             "amount_paid": o.amount_paid, "amount_unpaid": o.amount_unpaid,
             "order_date": o.order_date.isoformat() if o.order_date else None}
            for o in orders
        ],
    }


@router.patch("/{supplier_id}/rate")
async def rate_supplier(supplier_id: str, quality: int = 3, reliability: int = 3, price: int = 3, review: Optional[str] = None, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == supplier_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    s.quality_rating = min(5, max(1, quality))
    s.reliability_rating = min(5, max(1, reliability))
    s.price_rating = min(5, max(1, price))
    s.overall_rating = round((quality + reliability + price) / 3, 1)
    if review:
        s.review_notes = review
    await db.flush()
    return {"message": f"Supplier rated {s.overall_rating}/5"}


@router.patch("/{supplier_id}/blacklist")
async def blacklist_supplier(supplier_id: str, reason: str, db: AsyncSession = Depends(get_db), _user=Depends(require_admin)):
    result = await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == supplier_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    s.is_blacklisted = True
    s.is_active = False
    s.blacklist_reason = reason
    await db.flush()
    return {"message": f"Supplier '{s.business_name}' blacklisted"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONTRACTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{supplier_id}/contracts", status_code=status.HTTP_201_CREATED)
async def create_contract(supplier_id: str, body: ContractCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    contract = SupplierContract(
        supplier_id=supplier_id,
        contract_number=f"CON-{sec.token_hex(4).upper()}",
        approved_by_user_id=user.user_id,
        **body.model_dump(),
    )
    db.add(contract)
    supplier = (await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == supplier_id))).scalar_one_or_none()
    if supplier:
        supplier.total_contracted = (supplier.total_contracted or 0) + body.contract_amount
    await db.flush()
    return {"contract_id": contract.contract_id, "contract_number": contract.contract_number, "message": "Contract created"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PURCHASE ORDERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(body: OrderCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    order = PurchaseOrder(
        order_number=f"PO-{sec.token_hex(4).upper()}",
        order_date=date.today(),
        quantity_remaining=body.total_quantity,
        amount_unpaid=body.order_amount,
        ordered_by_user_id=user.user_id,
        **body.model_dump(),
    )
    db.add(order)
    supplier = (await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == body.supplier_id))).scalar_one_or_none()
    if supplier:
        supplier.total_orders = (supplier.total_orders or 0) + 1
    await db.flush()
    return {"order_id": order.order_id, "order_number": order.order_number, "message": "Purchase order created"}


@router.get("/orders")
async def list_orders(
    supplier_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    work_progress: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db), _user=Depends(get_current_user),
):
    query = select(PurchaseOrder, SupplierProfile.business_name).join(
        SupplierProfile, PurchaseOrder.supplier_id == SupplierProfile.supplier_id
    )
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
    if status_filter:
        query = query.where(PurchaseOrder.status == status_filter)
    if work_progress:
        query = query.where(PurchaseOrder.work_progress == work_progress)
    query = query.order_by(PurchaseOrder.order_date.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "order_id": r[0].order_id, "order_number": r[0].order_number,
            "supplier_name": r[1], "order_date": r[0].order_date.isoformat(),
            "order_amount": r[0].order_amount,
            "deposit_required": r[0].deposit_required, "deposit_paid": r[0].deposit_paid,
            "amount_paid": r[0].amount_paid, "amount_unpaid": r[0].amount_unpaid,
            "total_quantity": r[0].total_quantity,
            "quantity_delivered": r[0].quantity_delivered, "quantity_remaining": r[0].quantity_remaining,
            "status": r[0].status, "work_progress": r[0].work_progress,
            "progress_percentage": r[0].progress_percentage,
            "expected_delivery": r[0].expected_delivery_date.isoformat() if r[0].expected_delivery_date else None,
        }
        for r in result.all()
    ]


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.order_id == order_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    invoices = (await db.execute(select(SupplierInvoice).where(SupplierInvoice.order_id == order_id))).scalars().all()
    payments = (await db.execute(select(SupplierPayment).where(SupplierPayment.order_id == order_id))).scalars().all()
    deliveries = (await db.execute(select(SupplierDelivery).where(SupplierDelivery.order_id == order_id))).scalars().all()

    return {
        "order_id": o.order_id, "order_number": o.order_number,
        "supplier_id": o.supplier_id, "contract_id": o.contract_id,
        "order_items": o.order_items_json,
        "total_quantity": o.total_quantity, "quantity_delivered": o.quantity_delivered,
        "quantity_remaining": o.quantity_remaining,
        "order_amount": o.order_amount,
        "deposit_required": o.deposit_required, "deposit_paid": o.deposit_paid,
        "amount_invoiced": o.amount_invoiced, "amount_paid": o.amount_paid,
        "amount_unpaid": o.amount_unpaid,
        "order_date": o.order_date.isoformat(),
        "expected_delivery_date": o.expected_delivery_date.isoformat() if o.expected_delivery_date else None,
        "actual_delivery_date": o.actual_delivery_date.isoformat() if o.actual_delivery_date else None,
        "status": o.status, "work_progress": o.work_progress,
        "progress_percentage": o.progress_percentage, "progress_notes": o.progress_notes,
        "invoices": [
            {"invoice_id": i.invoice_id, "invoice_number": i.invoice_number,
             "total_amount": i.total_amount, "amount_paid": i.amount_paid,
             "amount_unpaid": i.amount_unpaid, "status": i.status,
             "due_date": i.due_date.isoformat() if i.due_date else None}
            for i in invoices
        ],
        "payments": [
            {"payment_id": p.payment_id, "payment_type": p.payment_type,
             "amount": p.amount, "payment_method": p.payment_method,
             "payment_date": p.payment_date.isoformat()}
            for p in payments
        ],
        "deliveries": [
            {"delivery_id": d.delivery_id, "quantity_delivered": d.quantity_delivered,
             "delivery_date": d.delivery_date.isoformat(),
             "quality_status": d.quality_status, "rejected_quantity": d.rejected_quantity}
            for d in deliveries
        ],
    }


@router.patch("/orders/{order_id}/progress")
async def update_order_progress(order_id: str, work_progress: str, progress_percentage: int, progress_notes: Optional[str] = None, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.order_id == order_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.work_progress = work_progress
    o.progress_percentage = min(100, max(0, progress_percentage))
    if progress_notes:
        o.progress_notes = progress_notes
    if work_progress == "delivered":
        o.status = "delivered"
        o.actual_delivery_date = date.today()
    elif work_progress != "not_started":
        o.status = "in_production"
    await db.flush()
    return {"message": f"Progress updated: {work_progress} ({progress_percentage}%)"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INVOICES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/orders/{order_id}/invoices", status_code=status.HTTP_201_CREATED)
async def add_invoice(order_id: str, body: InvoiceCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    order = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    total = body.invoice_amount + body.tax_amount
    invoice = SupplierInvoice(
        order_id=order_id, supplier_id=order.supplier_id,
        total_amount=total, amount_unpaid=total,
        invoice_date=body.invoice_date or date.today(),
        **body.model_dump(exclude={"invoice_date"}),
    )
    db.add(invoice)
    order.amount_invoiced = (order.amount_invoiced or 0) + total
    supplier = (await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == order.supplier_id))).scalar_one_or_none()
    if supplier:
        supplier.total_invoiced = (supplier.total_invoiced or 0) + total
        supplier.total_unpaid = (supplier.total_unpaid or 0) + total
    await db.flush()
    return {"invoice_id": invoice.invoice_id, "message": f"Invoice {body.invoice_number} recorded (KSH {total:,.0f})"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PAYMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/orders/{order_id}/payments", status_code=status.HTTP_201_CREATED)
async def record_payment(order_id: str, body: PaymentCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    order = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment = SupplierPayment(
        order_id=order_id, supplier_id=order.supplier_id,
        payment_date=body.payment_date or date.today(),
        paid_by_user_id=user.user_id,
        **body.model_dump(exclude={"payment_date"}),
    )
    db.add(payment)

    # Update order
    order.amount_paid = (order.amount_paid or 0) + body.amount
    order.amount_unpaid = max(0, order.order_amount - order.amount_paid)
    if body.payment_type == "deposit":
        order.deposit_paid = (order.deposit_paid or 0) + body.amount

    # Update supplier
    supplier = (await db.execute(select(SupplierProfile).where(SupplierProfile.supplier_id == order.supplier_id))).scalar_one_or_none()
    if supplier:
        supplier.total_paid = (supplier.total_paid or 0) + body.amount
        supplier.total_unpaid = max(0, (supplier.total_unpaid or 0) - body.amount)
        if body.payment_type == "deposit":
            supplier.total_deposits = (supplier.total_deposits or 0) + body.amount

    # Update invoice if linked
    if body.invoice_id:
        inv = (await db.execute(select(SupplierInvoice).where(SupplierInvoice.invoice_id == body.invoice_id))).scalar_one_or_none()
        if inv:
            inv.amount_paid = (inv.amount_paid or 0) + body.amount
            inv.amount_unpaid = max(0, inv.total_amount - inv.amount_paid)
            inv.status = "paid" if inv.amount_unpaid <= 0 else "partially_paid"

    await db.flush()
    return {"payment_id": payment.payment_id, "message": f"{body.payment_type.title()} of KSH {body.amount:,.0f} recorded"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DELIVERIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/orders/{order_id}/deliveries", status_code=status.HTTP_201_CREATED)
async def record_delivery(order_id: str, body: DeliveryCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    order = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.order_id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    delivery = SupplierDelivery(
        order_id=order_id, supplier_id=order.supplier_id,
        delivery_date=body.delivery_date or date.today(),
        received_by_user_id=user.user_id,
        **body.model_dump(exclude={"delivery_date"}),
    )
    db.add(delivery)

    order.quantity_delivered = (order.quantity_delivered or 0) + body.quantity_delivered
    order.quantity_remaining = max(0, order.total_quantity - order.quantity_delivered)
    if order.quantity_remaining <= 0:
        order.status = "delivered"
        order.actual_delivery_date = date.today()
    else:
        order.status = "partially_delivered"

    await db.flush()
    return {"delivery_id": delivery.delivery_id, "message": f"Delivery of {body.quantity_delivered} units recorded. Remaining: {order.quantity_remaining}"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GOVERNOR'S SUPPLIER DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/governor-dashboard")
async def governor_supplier_dashboard(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    total_suppliers = (await db.execute(select(func.count()).select_from(SupplierProfile).where(SupplierProfile.is_active == True))).scalar() or 0
    preferred = (await db.execute(select(func.count()).select_from(SupplierProfile).where(SupplierProfile.is_preferred == True))).scalar() or 0
    total_contracted = (await db.execute(select(func.coalesce(func.sum(SupplierProfile.total_contracted), 0)))).scalar()
    total_paid = (await db.execute(select(func.coalesce(func.sum(SupplierProfile.total_paid), 0)))).scalar()
    total_unpaid = (await db.execute(select(func.coalesce(func.sum(SupplierProfile.total_unpaid), 0)))).scalar()
    total_deposits = (await db.execute(select(func.coalesce(func.sum(SupplierProfile.total_deposits), 0)))).scalar()

    # Orders by status
    order_stats = await db.execute(
        select(PurchaseOrder.status, func.count(), func.coalesce(func.sum(PurchaseOrder.order_amount), 0))
        .group_by(PurchaseOrder.status)
    )

    # Work in progress
    wip = await db.execute(
        select(PurchaseOrder.work_progress, func.count())
        .where(PurchaseOrder.status.notin_(["delivered", "cancelled"]))
        .group_by(PurchaseOrder.work_progress)
    )

    # Overdue deliveries
    overdue = (await db.execute(
        select(func.count()).select_from(PurchaseOrder)
        .where(PurchaseOrder.expected_delivery_date < date.today(), PurchaseOrder.status.notin_(["delivered", "cancelled"]))
    )).scalar() or 0

    # Unpaid invoices
    unpaid_invoices = await db.execute(
        select(func.count(), func.coalesce(func.sum(SupplierInvoice.amount_unpaid), 0))
        .where(SupplierInvoice.status.notin_(["paid", "cancelled"]))
    )
    ui = unpaid_invoices.one()

    # By category
    by_category = await db.execute(
        select(SupplierProfile.supply_category, func.count(),
               func.coalesce(func.sum(SupplierProfile.total_contracted), 0),
               func.coalesce(func.sum(SupplierProfile.total_paid), 0))
        .where(SupplierProfile.is_active == True)
        .group_by(SupplierProfile.supply_category)
        .order_by(func.sum(SupplierProfile.total_contracted).desc())
    )

    # Top suppliers by spend
    top = await db.execute(
        select(SupplierProfile.business_name, SupplierProfile.supply_category,
               SupplierProfile.total_contracted, SupplierProfile.total_paid,
               SupplierProfile.total_unpaid, SupplierProfile.overall_rating)
        .where(SupplierProfile.is_active == True)
        .order_by(SupplierProfile.total_contracted.desc())
        .limit(10)
    )

    return {
        "overview": {
            "total_suppliers": total_suppliers, "preferred_suppliers": preferred,
            "total_contracted_ksh": float(total_contracted),
            "total_paid_ksh": float(total_paid),
            "total_deposits_ksh": float(total_deposits),
            "total_unpaid_ksh": float(total_unpaid),
            "overdue_deliveries": overdue,
            "unpaid_invoices": ui[0], "unpaid_invoice_amount_ksh": float(ui[1]),
        },
        "orders_by_status": [
            {"status": r[0], "count": r[1], "amount_ksh": float(r[2])}
            for r in order_stats.all()
        ],
        "work_in_progress": [
            {"stage": r[0], "count": r[1]}
            for r in wip.all()
        ],
        "by_category": [
            {"category": r[0], "suppliers": r[1], "contracted_ksh": float(r[2]), "paid_ksh": float(r[3])}
            for r in by_category.all()
        ],
        "top_10_suppliers": [
            {"name": r[0], "category": r[1], "contracted": float(r[2] or 0),
             "paid": float(r[3] or 0), "unpaid": float(r[4] or 0), "rating": r[5]}
            for r in top.all()
        ],
    }

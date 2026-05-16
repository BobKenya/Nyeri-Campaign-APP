"""Supplier Management: vendors, contracts, purchase orders, invoices, payments, deliveries."""
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())


class SupplierProfile(Base):
    """Every supplier/vendor the campaign works with."""
    __tablename__ = "supplier_profiles"

    supplier_id = Column(String(36), primary_key=True, default=genuuid)

    # Business identity
    business_name = Column(String(300), nullable=False)
    trading_name = Column(String(200))
    registration_number = Column(String(50))
    kra_pin = Column(String(20), index=True)
    business_type = Column(String(50))
    # sole_proprietor, limited, partnership, cooperative, informal

    # What they supply
    supply_category = Column(String(50), nullable=False)
    # printing, apparel, catering, transport, venue, sound_equipment, media,
    # fuel, airtime, security, legal, accounting, consulting, ict, construction, other
    products_services_json = Column(JSON, default=list)
    # ["t-shirts","caps","banners","posters"] or ["bus_hire","fuel"] etc.

    # Contact person
    contact_person = Column(String(200), nullable=False)
    contact_title = Column(String(50))
    phone_primary = Column(String(20), nullable=False, index=True)
    phone_secondary = Column(String(20))
    whatsapp_number = Column(String(20))
    email = Column(String(255))

    # Location
    physical_address = Column(Text)
    town = Column(String(100))
    county = Column(String(50), default="Nyeri")
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    gps_latitude = Column(Float)
    gps_longitude = Column(Float)

    # Bank details
    bank_name = Column(String(100))
    bank_branch = Column(String(100))
    bank_account_number = Column(String(30))
    mpesa_paybill = Column(String(20))
    mpesa_till = Column(String(20))

    # Rating
    quality_rating = Column(Integer, default=3)  # 1-5
    reliability_rating = Column(Integer, default=3)
    price_rating = Column(Integer, default=3)
    overall_rating = Column(Float, default=3.0)
    review_notes = Column(Text)

    # Financial summary (denormalized)
    total_contracted = Column(Float, default=0)
    total_invoiced = Column(Float, default=0)
    total_paid = Column(Float, default=0)
    total_deposits = Column(Float, default=0)
    total_unpaid = Column(Float, default=0)
    total_orders = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(Text)

    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    contracts = relationship("SupplierContract", back_populates="supplier", cascade="all, delete-orphan")
    orders = relationship("PurchaseOrder", back_populates="supplier", order_by="PurchaseOrder.order_date.desc()")

    __table_args__ = (
        Index("ix_supplier_category", "supply_category", "is_active"),
        Index("ix_supplier_ward", "ward_id"),
    )


class SupplierContract(Base):
    """Formal or informal agreement with a supplier for campaign period."""
    __tablename__ = "supplier_contracts"

    contract_id = Column(String(36), primary_key=True, default=genuuid)
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"), nullable=False, index=True)

    contract_number = Column(String(50), unique=True)
    contract_title = Column(String(300), nullable=False)
    description = Column(Text)

    # What's being supplied
    items_services_json = Column(JSON, default=list)
    # [{"item":"T-Shirt","unit_price":350,"quantity":5000,"total":1750000},...]

    # Financial
    contract_amount = Column(Float, nullable=False)
    deposit_amount = Column(Float, default=0)
    deposit_paid = Column(Boolean, default=False)
    deposit_paid_date = Column(Date)

    # Timeline
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    delivery_deadline = Column(Date)

    # Status
    status = Column(String(20), default="draft")
    # draft, active, in_progress, completed, cancelled, disputed
    completion_percentage = Column(Integer, default=0)  # 0-100

    # Documents
    contract_document_url = Column(Text)
    signed = Column(Boolean, default=False)
    signed_date = Column(Date)

    # Approval
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    approved_date = Column(Date)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    supplier = relationship("SupplierProfile", back_populates="contracts")
    orders = relationship("PurchaseOrder", back_populates="contract")


class PurchaseOrder(Base):
    """Individual order placed with a supplier — tracks items, quantities, amounts, and delivery."""
    __tablename__ = "purchase_orders"

    order_id = Column(String(36), primary_key=True, default=genuuid)
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"), nullable=False, index=True)
    contract_id = Column(String(36), ForeignKey("supplier_contracts.contract_id"))
    order_number = Column(String(50), unique=True)

    # What's ordered
    order_items_json = Column(JSON, nullable=False, default=list)
    # [{"item":"Campaign T-Shirt","description":"Red, logo front","unit":"piece",
    #   "quantity":1000,"unit_price":350,"total":350000,"delivered":0,"remaining":1000},...]

    # Quantities
    total_quantity = Column(Integer, default=0)
    quantity_delivered = Column(Integer, default=0)
    quantity_remaining = Column(Integer, default=0)

    # Financial
    order_amount = Column(Float, nullable=False)
    deposit_required = Column(Float, default=0)
    deposit_paid = Column(Float, default=0)
    amount_invoiced = Column(Float, default=0)
    amount_paid = Column(Float, default=0)
    amount_unpaid = Column(Float, default=0)

    # Dates
    order_date = Column(Date, nullable=False, index=True)
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)

    # Status
    status = Column(String(20), default="pending")
    # pending, confirmed, in_production, partially_delivered, delivered, cancelled, disputed
    work_progress = Column(String(20), default="not_started")
    # not_started, design, production, quality_check, packaging, transit, delivered
    progress_percentage = Column(Integer, default=0)
    progress_notes = Column(Text)

    # Delivery location
    delivery_address = Column(Text)
    delivery_constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    delivery_ward_id = Column(String(36), ForeignKey("wards.ward_id"))

    # Approval
    ordered_by_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    supplier = relationship("SupplierProfile", back_populates="orders")
    contract = relationship("SupplierContract", back_populates="orders")
    invoices = relationship("SupplierInvoice", back_populates="order", order_by="SupplierInvoice.invoice_date.desc()")
    payments = relationship("SupplierPayment", back_populates="order", order_by="SupplierPayment.payment_date.desc()")
    deliveries = relationship("SupplierDelivery", back_populates="order", order_by="SupplierDelivery.delivery_date.desc()")

    __table_args__ = (
        Index("ix_po_date_status", "order_date", "status"),
        Index("ix_po_supplier_status", "supplier_id", "status"),
    )


class SupplierInvoice(Base):
    """Invoice received from a supplier against a purchase order."""
    __tablename__ = "supplier_invoices"

    invoice_id = Column(String(36), primary_key=True, default=genuuid)
    order_id = Column(String(36), ForeignKey("purchase_orders.order_id"), nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"), nullable=False)

    invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    invoice_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)

    amount_paid = Column(Float, default=0)
    amount_unpaid = Column(Float)

    status = Column(String(20), default="received")
    # received, verified, approved, partially_paid, paid, disputed, cancelled

    invoice_document_url = Column(Text)
    verified_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    order = relationship("PurchaseOrder", back_populates="invoices")

    __table_args__ = (
        Index("ix_invoice_status", "status", "due_date"),
    )


class SupplierPayment(Base):
    """Payment made to a supplier — deposit, partial, or full."""
    __tablename__ = "supplier_payments"

    payment_id = Column(String(36), primary_key=True, default=genuuid)
    order_id = Column(String(36), ForeignKey("purchase_orders.order_id"), nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    invoice_id = Column(String(36), ForeignKey("supplier_invoices.invoice_id"))

    payment_type = Column(String(20), nullable=False)
    # deposit, partial, milestone, final, refund

    amount = Column(Float, nullable=False)
    payment_method = Column(String(20), nullable=False)
    # mpesa, bank_transfer, cheque, cash
    mpesa_code = Column(String(20))
    bank_reference = Column(String(50))
    cheque_number = Column(String(30))

    payment_date = Column(Date, nullable=False, index=True)
    paid_by_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    receipt_url = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    order = relationship("PurchaseOrder", back_populates="payments")


class SupplierDelivery(Base):
    """Track each delivery from a supplier — partial deliveries, quality checks."""
    __tablename__ = "supplier_deliveries"

    delivery_id = Column(String(36), primary_key=True, default=genuuid)
    order_id = Column(String(36), ForeignKey("purchase_orders.order_id"), nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"), nullable=False)

    # What was delivered
    items_delivered_json = Column(JSON, default=list)
    # [{"item":"T-Shirt","quantity":500,"condition":"good"},...]
    quantity_delivered = Column(Integer, nullable=False)

    delivery_date = Column(Date, nullable=False)
    received_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    delivery_location = Column(String(300))
    delivery_note_number = Column(String(50))
    delivery_note_url = Column(Text)

    # Quality
    quality_status = Column(String(20), default="pending")
    # pending, accepted, partial_reject, rejected
    rejected_quantity = Column(Integer, default=0)
    rejection_reason = Column(Text)
    quality_checked_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    photo_evidence_url = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    order = relationship("PurchaseOrder", back_populates="deliveries")

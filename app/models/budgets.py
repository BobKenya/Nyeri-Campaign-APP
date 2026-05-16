"""Budget Management: county → constituency → ward hierarchy with real-time spend tracking."""
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())


class CountyBudget(Base):
    """Top-level: total campaign budget for all of Nyeri County."""
    __tablename__ = "county_budgets"

    budget_id = Column(String(36), primary_key=True, default=genuuid)
    budget_name = Column(String(200), nullable=False)  # "2026 Campaign Budget"
    budget_period = Column(String(50), nullable=False)  # "Jan 2026 - Aug 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Totals
    total_allocated = Column(Float, nullable=False, default=0)
    total_spent = Column(Float, default=0)
    total_committed = Column(Float, default=0)  # approved POs not yet paid
    total_remaining = Column(Float, default=0)
    spend_percentage = Column(Float, default=0)  # 0-100

    # Category breakdown
    category_allocations_json = Column(JSON, default=dict)
    # {"personnel":5000000,"transport":3000000,"printing":2000000,"events":4000000,...}

    # Funding sources
    total_donations_received = Column(Float, default=0)
    total_pledges_outstanding = Column(Float, default=0)
    self_funding = Column(Float, default=0)
    funding_gap = Column(Float, default=0)  # allocated - (donations + self_funding)

    status = Column(String(20), default="active")  # draft, active, frozen, closed
    approved_by = Column(String(200))
    approved_date = Column(Date)
    notes = Column(Text)

    created_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    constituency_budgets = relationship("ConstituencyBudget", back_populates="county_budget")


class ConstituencyBudget(Base):
    """Budget allocation per constituency — rolls up from wards, rolls into county."""
    __tablename__ = "constituency_budgets"

    const_budget_id = Column(String(36), primary_key=True, default=genuuid)
    county_budget_id = Column(String(36), ForeignKey("county_budgets.budget_id"), nullable=False)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=False)

    total_allocated = Column(Float, nullable=False, default=0)
    total_spent = Column(Float, default=0)
    total_committed = Column(Float, default=0)
    total_remaining = Column(Float, default=0)
    spend_percentage = Column(Float, default=0)

    # Category breakdown
    category_allocations_json = Column(JSON, default=dict)
    category_spent_json = Column(JSON, default=dict)

    # Targets
    target_voters_reached = Column(Integer, default=0)
    actual_voters_reached = Column(Integer, default=0)
    target_events = Column(Integer, default=0)
    actual_events = Column(Integer, default=0)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    county_budget = relationship("CountyBudget", back_populates="constituency_budgets")
    ward_budgets = relationship("WardBudget", back_populates="constituency_budget")

    __table_args__ = (
        Index("ix_const_budget_county", "county_budget_id", "constituency_id", unique=True),
    )


class WardBudget(Base):
    """Budget allocation per ward — the most granular level."""
    __tablename__ = "ward_budgets"

    ward_budget_id = Column(String(36), primary_key=True, default=genuuid)
    const_budget_id = Column(String(36), ForeignKey("constituency_budgets.const_budget_id"), nullable=False)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=False)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False)

    total_allocated = Column(Float, nullable=False, default=0)
    total_spent = Column(Float, default=0)
    total_committed = Column(Float, default=0)
    total_remaining = Column(Float, default=0)
    spend_percentage = Column(Float, default=0)

    # Category breakdown
    category_allocations_json = Column(JSON, default=dict)
    category_spent_json = Column(JSON, default=dict)

    # Coordinator
    coordinator_user_id = Column(String(36), ForeignKey("users.user_id"))
    coordinator_name = Column(String(200))

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    constituency_budget = relationship("ConstituencyBudget", back_populates="ward_budgets")
    line_items = relationship("BudgetLineItem", back_populates="ward_budget", cascade="all, delete-orphan")
    transactions = relationship("SpendingTransaction", back_populates="ward_budget", order_by="SpendingTransaction.transaction_date.desc()")

    __table_args__ = (
        Index("ix_ward_budget_const", "const_budget_id", "ward_id", unique=True),
    )


class BudgetLineItem(Base):
    """Individual budget lines within a ward — e.g. 'T-shirts for Mugunda ward'."""
    __tablename__ = "budget_line_items"

    line_item_id = Column(String(36), primary_key=True, default=genuuid)
    ward_budget_id = Column(String(36), ForeignKey("ward_budgets.ward_budget_id"), nullable=False, index=True)

    category = Column(String(50), nullable=False)
    # personnel, transport, printing, events, catering, media, fuel, airtime,
    # apparel, donations_to_groups, venue, security, equipment, other
    description = Column(String(300), nullable=False)
    quantity = Column(Integer, default=1)
    unit_cost = Column(Float, default=0)
    allocated_amount = Column(Float, nullable=False)
    spent_amount = Column(Float, default=0)
    committed_amount = Column(Float, default=0)
    remaining_amount = Column(Float, default=0)
    spend_percentage = Column(Float, default=0)

    # Linked to PO or supplier
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.order_id"))
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"))

    status = Column(String(20), default="planned")
    # planned, approved, in_progress, completed, overspent, cancelled

    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    ward_budget = relationship("WardBudget", back_populates="line_items")

    __table_args__ = (
        Index("ix_line_item_category", "category", "status"),
    )


class SpendingTransaction(Base):
    """Every KSH spent — ties back to ward budget, category, and source."""
    __tablename__ = "spending_transactions"

    transaction_id = Column(String(36), primary_key=True, default=genuuid)
    ward_budget_id = Column(String(36), ForeignKey("ward_budgets.ward_budget_id"), nullable=False, index=True)
    line_item_id = Column(String(36), ForeignKey("budget_line_items.line_item_id"))

    # What
    category = Column(String(50), nullable=False)
    description = Column(String(300), nullable=False)
    amount = Column(Float, nullable=False)

    # When / Where
    transaction_date = Column(Date, nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False)

    # How
    payment_method = Column(String(20))  # mpesa, cash, bank, cheque
    mpesa_code = Column(String(20))
    bank_reference = Column(String(50))
    receipt_number = Column(String(50))
    receipt_url = Column(Text)

    # Who
    paid_to = Column(String(200))  # vendor name, person name
    supplier_id = Column(String(36), ForeignKey("supplier_profiles.supplier_id"))
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.order_id"))
    recorded_by_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    # Verification
    verified = Column(Boolean, default=False)
    photo_evidence_url = Column(Text)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    ward_budget = relationship("WardBudget", back_populates="transactions")

    __table_args__ = (
        Index("ix_spend_ward_date", "ward_id", "transaction_date"),
        Index("ix_spend_category_date", "category", "transaction_date"),
    )


class BudgetAlert(Base):
    """Auto-generated alerts when spending thresholds are crossed."""
    __tablename__ = "budget_alerts"

    alert_id = Column(String(36), primary_key=True, default=genuuid)
    alert_type = Column(String(30), nullable=False)
    # overspend, near_limit_80, near_limit_90, exceeded, no_activity, unusual_spike

    level = Column(String(20), nullable=False)  # ward, constituency, county
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    category = Column(String(50))

    message = Column(Text, nullable=False)
    amount_allocated = Column(Float)
    amount_spent = Column(Float)
    percentage_used = Column(Float)

    is_read = Column(Boolean, default=False)
    read_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    read_at = Column(DateTime)

    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_alert_type_read", "alert_type", "is_read"),
    )

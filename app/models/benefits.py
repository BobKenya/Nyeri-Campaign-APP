"""Benefits Distribution: track t-shirts, caps, money, and all handouts per person per ward."""
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())


class BenefitItem(Base):
    """Master catalog of distributable items — t-shirts, caps, cash, food, etc."""
    __tablename__ = "benefit_items"

    item_id = Column(String(36), primary_key=True, default=genuuid)
    item_name = Column(String(200), nullable=False)  # T-Shirt, Cap, Cash, Food Hamper, etc.
    item_category = Column(String(50), nullable=False)  # apparel, cash, food, transport, airtime, other
    unit = Column(String(30), default="piece")  # piece, ksh, kg, litre, bundle
    unit_cost = Column(Float, default=0)  # cost per unit in KSH
    total_stock = Column(Integer, default=0)
    distributed_count = Column(Integer, default=0)
    remaining_stock = Column(Integer, default=0)
    description = Column(Text)
    photo_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    distributions = relationship("BenefitDistribution", back_populates="item")


class BenefitRecipient(Base):
    """Every person who receives campaign benefits — full personal details."""
    __tablename__ = "benefit_recipients"

    recipient_id = Column(String(36), primary_key=True, default=genuuid)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"))  # link to voter if registered

    # Personal details
    full_name = Column(String(200), nullable=False)
    id_number = Column(String(20), index=True)
    phone_number = Column(String(20), index=True)
    gender = Column(String(10))
    age = Column(Integer)
    occupation = Column(String(100))
    photo_url = Column(Text)

    # Location
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False, index=True)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"))
    village = Column(String(200))
    home_address = Column(Text)
    gps_latitude = Column(Float)
    gps_longitude = Column(Float)

    # Mobilization info
    support_level = Column(String(20), default="unknown")
    recruited_by_agent_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"))
    is_mobilizer = Column(Boolean, default=False)  # True if this person also mobilizes others
    group_affiliation = Column(String(200))  # youth group, chama, church group, boda boda, etc.
    notes = Column(Text)

    # Totals (denormalized for fast queries)
    total_items_received = Column(Integer, default=0)
    total_cash_received = Column(Float, default=0)
    first_benefit_date = Column(Date)
    last_benefit_date = Column(Date)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    distributions = relationship("BenefitDistribution", back_populates="recipient")

    __table_args__ = (
        Index("ix_recipient_ward_name", "ward_id", "full_name"),
        Index("ix_recipient_constituency", "constituency_id"),
    )


class BenefitDistribution(Base):
    """Every single handout — who got what, when, where, and from whom."""
    __tablename__ = "benefit_distributions"

    distribution_id = Column(String(36), primary_key=True, default=genuuid)
    recipient_id = Column(String(36), ForeignKey("benefit_recipients.recipient_id"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("benefit_items.item_id"), nullable=False, index=True)

    # What was given
    quantity = Column(Integer, nullable=False, default=1)
    cash_amount = Column(Float, default=0)  # if item is cash, the KSH amount
    item_size = Column(String(20))  # S, M, L, XL for apparel
    item_color = Column(String(30))
    serial_or_batch = Column(String(50))  # batch tracking

    # When and where
    distribution_date = Column(Date, nullable=False, index=True)
    distribution_time = Column(String(10))
    distribution_location = Column(String(300))
    event_name = Column(String(300))  # rally, door-to-door, church visit, etc.
    event_id = Column(String(36), ForeignKey("events.event_id"))
    gps_latitude = Column(Float)
    gps_longitude = Column(Float)

    # Who distributed
    distributed_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    distributed_by_agent_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"))

    # Location hierarchy
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False, index=True)

    # Verification
    recipient_signature_url = Column(Text)  # photo of signature or thumbprint
    photo_evidence_url = Column(Text)  # photo of recipient with item
    verified = Column(Boolean, default=False)
    verification_method = Column(String(30))  # id_check, photo, biometric, witness

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    recipient = relationship("BenefitRecipient", back_populates="distributions")
    item = relationship("BenefitItem", back_populates="distributions")

    __table_args__ = (
        Index("ix_dist_date_ward", "distribution_date", "ward_id"),
        Index("ix_dist_date_constituency", "distribution_date", "constituency_id"),
        Index("ix_dist_item_date", "item_id", "distribution_date"),
    )


class DailyDistributionReport(Base):
    """Auto-generated daily summary per ward — feeds the governor's dashboard."""
    __tablename__ = "daily_distribution_reports"

    report_id = Column(String(36), primary_key=True, default=genuuid)
    report_date = Column(Date, nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=False)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False)

    # Counts
    total_recipients = Column(Integer, default=0)
    new_recipients = Column(Integer, default=0)  # first-time recipients that day
    total_items_distributed = Column(Integer, default=0)
    total_cash_distributed = Column(Float, default=0)

    # Breakdown by item category (JSON for flexibility)
    items_breakdown_json = Column(JSON, default=dict)
    # e.g. {"tshirt": 150, "cap": 200, "cash": 45000, "food": 30}

    # Coverage
    unique_villages_reached = Column(Integer, default=0)
    agents_active = Column(Integer, default=0)

    # Budget
    total_cost = Column(Float, default=0)
    budget_remaining = Column(Float)

    # Status
    submitted_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    governor_viewed = Column(Boolean, default=False)
    governor_viewed_at = Column(DateTime)
    governor_notes = Column(Text)

    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_daily_report_date_ward", "report_date", "ward_id", unique=True),
        Index("ix_daily_report_date_const", "report_date", "constituency_id"),
    )


class BenefitBudgetWard(Base):
    """Budget allocation per ward for benefits distribution."""
    __tablename__ = "benefit_budget_wards"

    budget_ward_id = Column(String(36), primary_key=True, default=genuuid)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=False)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=False, unique=True)
    allocated_amount = Column(Float, nullable=False, default=0)
    spent_amount = Column(Float, default=0)
    remaining_amount = Column(Float, default=0)
    target_recipients = Column(Integer, default=0)
    actual_recipients = Column(Integer, default=0)
    last_updated = Column(DateTime, default=utcnow, onupdate=utcnow)

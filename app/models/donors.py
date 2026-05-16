"""Donor Management: profiles, businesses, pledges, payments, ward/constituency organization."""
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())


class DonorProfile(Base):
    """Complete donor profile with personal details, contacts, and location by ward."""
    __tablename__ = "donor_profiles"

    donor_id = Column(String(36), primary_key=True, default=genuuid)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"))

    # Personal details
    full_name = Column(String(200), nullable=False)
    id_number = Column(String(20), index=True)
    kra_pin = Column(String(20))  # Kenya Revenue Authority PIN
    photo_url = Column(Text)
    gender = Column(String(10))
    date_of_birth = Column(Date)
    title = Column(String(50))  # Mr, Mrs, Dr, Hon, Prof, etc.

    # Contacts
    phone_primary = Column(String(20), nullable=False, index=True)
    phone_secondary = Column(String(20))
    whatsapp_number = Column(String(20))
    email = Column(String(255))
    facebook_url = Column(Text)
    twitter_handle = Column(String(100))

    # Location by ward/constituency
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), index=True)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), index=True)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.polling_station_id"))
    home_address = Column(Text)
    home_latitude = Column(Float)
    home_longitude = Column(Float)

    # Donor classification
    donor_category = Column(String(30), default="individual")
    # individual, business_owner, corporate, diaspora, political_ally, religious_leader, professional
    donor_tier = Column(String(20), default="standard")
    # platinum (1M+), gold (500K-1M), silver (100K-500K), bronze (50K-100K), standard (<50K)
    relationship_status = Column(String(20), default="prospect")
    # prospect, contacted, pledged, active_donor, lapsed, declined

    # Financial summary (denormalized)
    total_pledged = Column(Float, default=0)
    total_paid = Column(Float, default=0)
    total_outstanding = Column(Float, default=0)
    first_donation_date = Column(Date)
    last_donation_date = Column(Date)
    donation_count = Column(Integer, default=0)

    # Relationship management
    assigned_coordinator_id = Column(String(36), ForeignKey("users.user_id"))
    recruited_by_agent_id = Column(String(36), ForeignKey("agent_profiles.agent_profile_id"))
    referral_source = Column(String(100))  # rally, door-to-door, church, business_visit, referral, cold_call
    engagement_notes = Column(Text)
    preferred_contact_method = Column(String(20), default="phone")  # phone, whatsapp, email, in_person
    preferred_contact_time = Column(String(50))  # morning, afternoon, evening, weekends

    # Flags
    is_anonymous = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_vip = Column(Boolean, default=False)
    requires_receipt = Column(Boolean, default=True)
    risk_flag = Column(String(20))  # none, low, medium, high (for compliance)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    businesses = relationship("DonorBusiness", back_populates="donor", cascade="all, delete-orphan")
    pledges = relationship("DonorPledge", back_populates="donor", cascade="all, delete-orphan")
    payments = relationship("DonorPayment", back_populates="donor", order_by="DonorPayment.payment_date.desc()")
    interactions = relationship("DonorInteraction", back_populates="donor", order_by="DonorInteraction.interaction_date.desc()")

    __table_args__ = (
        Index("ix_donor_ward_tier", "ward_id", "donor_tier"),
        Index("ix_donor_constituency_status", "constituency_id", "relationship_status"),
        Index("ix_donor_category", "donor_category", "is_active"),
    )


class DonorBusiness(Base):
    """Business details for donor — one donor can own multiple businesses."""
    __tablename__ = "donor_businesses"

    business_id = Column(String(36), primary_key=True, default=genuuid)
    donor_id = Column(String(36), ForeignKey("donor_profiles.donor_id"), nullable=False, index=True)

    # Business info
    business_name = Column(String(300), nullable=False)
    business_type = Column(String(50))
    # retail, wholesale, manufacturing, transport, agriculture, hospitality, real_estate,
    # construction, professional_services, tech, media, health, education, other
    registration_number = Column(String(50))
    kra_pin = Column(String(20))
    industry = Column(String(100))

    # Location
    business_address = Column(Text)
    business_latitude = Column(Float)
    business_longitude = Column(Float)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))

    # Contact
    business_phone = Column(String(20))
    business_email = Column(String(255))
    website = Column(Text)

    # Financial profile
    estimated_annual_revenue = Column(Float)
    employee_count = Column(Integer)
    years_in_operation = Column(Integer)

    # Relationship
    can_provide_venue = Column(Boolean, default=False)
    can_provide_transport = Column(Boolean, default=False)
    can_provide_catering = Column(Boolean, default=False)
    can_provide_printing = Column(Boolean, default=False)
    other_in_kind_support = Column(Text)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    donor = relationship("DonorProfile", back_populates="businesses")


class DonorPledge(Base):
    """A promise to donate — tracks amount, schedule, and fulfillment."""
    __tablename__ = "donor_pledges"

    pledge_id = Column(String(36), primary_key=True, default=genuuid)
    donor_id = Column(String(36), ForeignKey("donor_profiles.donor_id"), nullable=False, index=True)

    # Pledge details
    pledge_type = Column(String(20), nullable=False)
    # cash, in_kind, service, venue, transport, catering, printing, airtime, fuel
    pledge_amount = Column(Float, nullable=False)  # KSH value
    currency = Column(String(5), default="KES")
    in_kind_description = Column(Text)  # for non-cash pledges

    # Schedule
    pledge_date = Column(Date, nullable=False)
    expected_fulfillment_date = Column(Date)
    payment_plan = Column(String(20), default="one_time")
    # one_time, weekly, monthly, quarterly, custom
    installment_amount = Column(Float)
    total_installments = Column(Integer)

    # Status
    status = Column(String(20), default="pledged")
    # pledged, partially_fulfilled, fulfilled, overdue, cancelled, renegotiated
    amount_fulfilled = Column(Float, default=0)
    amount_outstanding = Column(Float)
    last_payment_date = Column(Date)

    # Context
    pledge_occasion = Column(String(200))  # fundraiser event, private meeting, phone call, etc.
    event_id = Column(String(36), ForeignKey("events.event_id"))
    witnessed_by = Column(String(200))
    pledge_document_url = Column(Text)  # scanned pledge form

    # Follow-up
    follow_up_date = Column(Date)
    follow_up_notes = Column(Text)
    assigned_to_user_id = Column(String(36), ForeignKey("users.user_id"))

    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    donor = relationship("DonorProfile", back_populates="pledges")

    __table_args__ = (
        Index("ix_pledge_status", "status", "expected_fulfillment_date"),
        Index("ix_pledge_ward", "ward_id", "status"),
    )


class DonorPayment(Base):
    """Actual payment received from a donor — linked to a pledge if applicable."""
    __tablename__ = "donor_payments"

    payment_id = Column(String(36), primary_key=True, default=genuuid)
    donor_id = Column(String(36), ForeignKey("donor_profiles.donor_id"), nullable=False, index=True)
    pledge_id = Column(String(36), ForeignKey("donor_pledges.pledge_id"))

    # Payment details
    amount = Column(Float, nullable=False)
    payment_method = Column(String(20), nullable=False)
    # mpesa, bank_transfer, cash, cheque, in_kind
    mpesa_code = Column(String(20))
    bank_reference = Column(String(50))
    cheque_number = Column(String(30))
    in_kind_description = Column(Text)
    in_kind_estimated_value = Column(Float)

    payment_date = Column(Date, nullable=False, index=True)
    received_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    # Receipt
    receipt_number = Column(String(50))
    receipt_issued = Column(Boolean, default=False)
    receipt_url = Column(Text)

    # Location
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"))

    # Verification
    verified = Column(Boolean, default=False)
    verified_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    verification_date = Column(Date)

    notes = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    donor = relationship("DonorProfile", back_populates="payments")

    __table_args__ = (
        Index("ix_payment_date_ward", "payment_date", "ward_id"),
        Index("ix_payment_method", "payment_method", "payment_date"),
    )


class DonorInteraction(Base):
    """Every call, visit, or meeting with a donor — CRM-style activity log."""
    __tablename__ = "donor_interactions"

    interaction_id = Column(String(36), primary_key=True, default=genuuid)
    donor_id = Column(String(36), ForeignKey("donor_profiles.donor_id"), nullable=False, index=True)

    interaction_type = Column(String(30), nullable=False)
    # phone_call, whatsapp, visit, meeting, event_attendance, follow_up, thank_you, pledge_reminder
    interaction_date = Column(DateTime, default=utcnow)
    conducted_by_user_id = Column(String(36), ForeignKey("users.user_id"))

    subject = Column(String(300))
    notes = Column(Text)
    outcome = Column(String(30))  # positive, neutral, negative, pledge_made, payment_received, declined
    next_action = Column(Text)
    next_action_date = Column(Date)

    created_at = Column(DateTime, default=utcnow)

    donor = relationship("DonorProfile", back_populates="interactions")

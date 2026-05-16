"""Messaging, Finance, Compliance models."""
import uuid, secrets
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)
def genuuid():
    return str(uuid.uuid4())

# ── Messaging ──────────────────────────────────────────────────────

class MessageTemplate(Base):
    __tablename__ = "message_templates"
    template_id = Column(String(36), primary_key=True, default=genuuid)
    template_name = Column(String(200), nullable=False)
    content_subject = Column(String(300))
    content_body = Column(Text, nullable=False)
    category = Column(String(50))
    created_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=utcnow)
    messages = relationship("Message", back_populates="template")

class RecipientGroup(Base):
    __tablename__ = "recipient_groups"
    group_id = Column(String(36), primary_key=True, default=genuuid)
    group_name = Column(String(200), nullable=False)
    group_description = Column(Text)
    filter_criteria_json = Column(JSON, default=dict)
    member_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    members = relationship("RecipientGroupMember", back_populates="group")
    messages = relationship("Message", back_populates="recipient_group")

class RecipientGroupMember(Base):
    __tablename__ = "recipient_group_members"
    group_id = Column(String(36), ForeignKey("recipient_groups.group_id"), primary_key=True)
    voter_id = Column(String(36), ForeignKey("voters.voter_id"), primary_key=True)
    added_at = Column(DateTime, default=utcnow)
    source = Column(String(50))
    group = relationship("RecipientGroup", back_populates="members")

class Message(Base):
    __tablename__ = "messages"
    message_id = Column(String(36), primary_key=True, default=genuuid)
    message_type = Column(String(20), nullable=False)
    subject = Column(String(300))
    message_content = Column(Text, nullable=False)
    template_id = Column(String(36), ForeignKey("message_templates.template_id"))
    recipient_group_id = Column(String(36), ForeignKey("recipient_groups.group_id"))
    sender_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    scheduled_send_at = Column(DateTime)
    open_rate = Column(Float)
    click_rate = Column(Float)
    sent_date = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    template = relationship("MessageTemplate", back_populates="messages")
    recipient_group = relationship("RecipientGroup", back_populates="messages")
    delivery_logs = relationship("MessageDeliveryLog", back_populates="message")

class MessageDeliveryLog(Base):
    __tablename__ = "message_delivery_log"
    delivery_id = Column(String(36), primary_key=True, default=genuuid)
    message_id = Column(String(36), ForeignKey("messages.message_id"), nullable=False, index=True)
    recipient_voter_id = Column(String(36), ForeignKey("voters.voter_id"), nullable=False)
    delivery_status = Column(String(20), default="pending")
    delivered_at = Column(DateTime)
    opened_at = Column(DateTime)
    error_code = Column(String(50))
    retry_count = Column(Integer, default=0)
    message = relationship("Message", back_populates="delivery_logs")

# ── Finance ────────────────────────────────────────────────────────

class Donation(Base):
    __tablename__ = "donations"
    donation_id = Column(String(36), primary_key=True, default=genuuid)
    donor_voter_id = Column(String(36), ForeignKey("voters.voter_id"))
    donor_name = Column(String(200), nullable=False)
    donation_amount = Column(Float, nullable=False)
    payment_method = Column(String(20), nullable=False)
    mpesa_transaction_code = Column(String(20))
    bank_reference = Column(String(50))
    donor_id_number = Column(String(20))
    donor_phone = Column(String(20))
    is_recurring = Column(Boolean, default=False)
    is_anonymous = Column(Boolean, default=False)
    receipt_number = Column(String(50))
    created_at = Column(DateTime, default=utcnow)

class CampaignExpense(Base):
    __tablename__ = "campaign_expenses"
    expense_id = Column(String(36), primary_key=True, default=genuuid)
    expense_category = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text)
    payment_method = Column(String(20))
    vendor_name = Column(String(200))
    receipt_number = Column(String(50))
    receipt_url = Column(Text)
    approval_status = Column(String(20), default="pending")
    approved_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    expense_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=utcnow)

class BudgetAllocation(Base):
    __tablename__ = "budget_allocations"
    budget_id = Column(String(36), primary_key=True, default=genuuid)
    constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"))
    category = Column(String(100), nullable=False)
    total_amount = Column(Float, nullable=False)
    spent_amount = Column(Float, default=0)
    remaining_amount = Column(Float)
    fiscal_period = Column(String(20))
    created_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

# ── Compliance ─────────────────────────────────────────────────────

class ComplianceDocument(Base):
    __tablename__ = "compliance_documents"
    document_id = Column(String(36), primary_key=True, default=genuuid)
    document_type = Column(String(50), nullable=False)
    document_number = Column(String(50))
    document_name = Column(String(300), nullable=False)
    filing_date = Column(Date)
    iebc_submission_date = Column(Date)
    iebc_acknowledgement = Column(String(100))
    file_url = Column(Text)
    created_at = Column(DateTime, default=utcnow)

class PermitLicense(Base):
    __tablename__ = "permits_licenses"
    permit_id = Column(String(36), primary_key=True, default=genuuid)
    permit_type = Column(String(50), nullable=False)
    issuing_authority = Column(String(200))
    issued_date = Column(Date)
    expiry_date = Column(Date)
    permit_file_url = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=utcnow)

class IEBCReport(Base):
    __tablename__ = "iebc_reports"
    report_id = Column(String(36), primary_key=True, default=genuuid)
    report_type = Column(String(50), nullable=False)
    reporting_period = Column(String(50))
    total_spending = Column(Float)
    total_donations = Column(Float)
    submission_date = Column(Date)
    compliance_status = Column(String(20), default="draft")
    status = Column(String(20), default="draft")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(String(36), primary_key=True, default=genuuid)
    user_id = Column(String(36), ForeignKey("users.user_id"))
    action_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36))
    old_values_json = Column(JSON)
    new_values_json = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=utcnow)

"""SMS broadcast log"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

def genuuid():
    return str(uuid.uuid4())

class SmsBroadcast(Base):
    __tablename__ = "sms_broadcasts"
    broadcast_id = Column(String(36), primary_key=True, default=genuuid)
    title = Column(String(200))
    message = Column(Text, nullable=False)
    sender_id = Column(String(50))
    filter_constituency_id = Column(String(36), ForeignKey("constituencies.constituency_id"), nullable=True)
    filter_ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=True)
    filter_support_level = Column(String(20))
    total_recipients = Column(Integer, default=0)
    successful_sends = Column(Integer, default=0)
    failed_sends = Column(Integer, default=0)
    cost_estimate = Column(String(50))
    api_response = Column(JSON)
    sent_by_user_id = Column(String(36), ForeignKey("users.user_id"))
    sent_at = Column(DateTime, default=utcnow)

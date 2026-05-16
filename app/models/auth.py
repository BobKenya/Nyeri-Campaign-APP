"""Auth: User, Role, UserSession, Notification."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

def genuuid():
    return str(uuid.uuid4())

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(String(36), primary_key=True, default=genuuid)
    role_name = Column(String(50), unique=True, nullable=False)
    role_description = Column(Text)
    permissions_json = Column(JSON, default=dict)
    effective_date = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    user_id = Column(String(36), primary_key=True, default=genuuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.role_id"), nullable=False)
    phone_number = Column(String(20))
    is_active = Column(Boolean, default=True)
    avatar_photo_url = Column(Text)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(64))
    failed_login_count = Column(Integer, default=0)
    account_locked_until = Column(DateTime)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime)
    role = relationship("Role", back_populates="users")
    sessions = relationship("UserSession", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    session_id = Column(String(36), primary_key=True, default=genuuid)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    ip_address = Column(String(45))
    device_info = Column(Text)
    login_timestamp = Column(DateTime, default=utcnow)
    logout_timestamp = Column(DateTime)
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="sessions")

class Notification(Base):
    __tablename__ = "notifications"
    notification_id = Column(String(36), primary_key=True, default=genuuid)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text)
    reference_type = Column(String(50))
    reference_id = Column(String(36))
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    user = relationship("User", back_populates="notifications")

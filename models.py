from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum, Boolean, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
import enum
import re
from database import Base
from datetime import datetime
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(enum.Enum):
    customer = "customer"
    support_agent = "support_agent"
    admin = "admin"

class TicketStatus(enum.Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"
    reopened = "reopened"
    on_hold = "on_hold"

class TicketPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(ENUM(UserRole), nullable=False, default=UserRole.customer)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tickets = relationship("Ticket", back_populates="user", cascade="all, delete-orphan")
    responses = relationship("TicketResponse", back_populates="responder")
    
    # Indexes
    __table_args__ = (
        Index('ix_users_email_role', 'email', 'role'),
    )
    
    @validates('email')
    def validate_email(self, key, email):
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            raise ValueError("Invalid email address")
        return email.lower()
    
    def set_password(self, password: str):
        """Hash and set the user's password"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        return pwd_context.verify(password, self.password_hash)
    
    @hybrid_property
    def ticket_count(self):
        return len(self.tickets)
    
    @hybrid_property
    def response_count(self):
        return len(self.responses)

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(ENUM(TicketPriority), nullable=False, default=TicketPriority.medium)
    status = Column(ENUM(TicketStatus), default=TicketStatus.open, nullable=False)
    category = Column(String(50))
    due_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="tickets")
    responses = relationship("TicketResponse", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_tickets_status_priority', 'status', 'priority'),
        Index('ix_tickets_user_id_created_at', 'user_id', 'created_at'),
    )
    
    @validates('subject')
    def validate_subject(self, key, subject):
        subject = subject.strip()
        if len(subject) < 5:
            raise ValueError("Subject must be at least 5 characters")
        return subject
    
    @hybrid_property
    def response_count(self):
        return len(self.responses)
    
    @hybrid_property
    def age(self):
        return (datetime.now() - self.created_at).days if self.created_at else 0
    
    @hybrid_property
    def is_overdue(self):
        return datetime.now() > self.due_date if self.due_date else False

class TicketResponse(Base):
    __tablename__ = "ticket_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    responder_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    timestamp = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="responses")
    responder = relationship("User", back_populates="responses")
    attachments = relationship("ResponseAttachment", back_populates="response", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_responses_ticket_id_timestamp', 'ticket_id', 'timestamp'),
    )
    
    @validates('message')
    def validate_message(self, key, message):
        message = message.strip()
        if len(message) < 10:
            raise ValueError("Response must be at least 10 characters")
        return message

class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    uploaded_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")

class ResponseAttachment(Base):
    __tablename__ = "response_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("ticket_responses.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    uploaded_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    response = relationship("TicketResponse", back_populates="attachments")
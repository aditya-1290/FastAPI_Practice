from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from typing import ForwardRef

class UserRole(str, Enum):
    customer = "customer"
    support_agent = "support_agent"
    admin = "admin"

class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"
    reopened = "reopened"
    on_hold = "on_hold"

class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

# Base schemas
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.customer

class TicketBase(BaseModel):
    subject: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=10)
    priority: TicketPriority = TicketPriority.medium
    category: Optional[str] = Field(None, max_length=50)
    due_date: Optional[datetime] = None

class TicketResponseBase(BaseModel):
    message: str = Field(..., min_length=10)
    is_internal: bool = False

class AttachmentBase(BaseModel):
    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., max_length=100)
    size: int = Field(..., gt=0)

# Create schemas
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=50)

    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

class TicketCreate(TicketBase):
    pass

class TicketResponseCreate(TicketResponseBase):
    pass

class AttachmentCreate(AttachmentBase):
    pass

# Update schemas
class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    @root_validator
    def check_at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=5, max_length=100)
    description: Optional[str] = Field(None, min_length=10)
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    category: Optional[str] = Field(None, max_length=50)
    due_date: Optional[datetime] = None

    @root_validator
    def check_at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

class TicketResponseUpdate(BaseModel):
    message: Optional[str] = Field(None, min_length=10)
    is_internal: Optional[bool] = None

    @root_validator
    def check_at_least_one_field(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

# Response schemas
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class TicketAttachmentResponse(AttachmentBase):
    id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True

class ResponseAttachmentResponse(AttachmentBase):
    id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True

class TicketResponseResponse(TicketResponseBase):
    id: int
    responder_id: int
    timestamp: datetime
    updated_at: datetime
    attachments: List[ResponseAttachmentResponse] = []

    class Config:
        orm_mode = True

class TicketResponse(TicketBase):
    id: int
    user_id: int
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    responses: List[TicketResponseResponse] = []
    attachments: List[TicketAttachmentResponse] = []

    class Config:
        orm_mode = True

class UserWithTicketsResponse(UserResponse):
    tickets: List[TicketResponse] = []

    class Config:
        orm_mode = True

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None

# Forward references for recursive models
TicketResponse.model_rebuild()
UserWithTicketsResponse.model_rebuild()
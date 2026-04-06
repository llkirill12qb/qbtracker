from pydantic import BaseModel
from datetime import datetime


class EmployeeCreate(BaseModel):
    full_name: str
    card_id: str
    department: str | None = None
    position: str | None = None
    phone: str | None = None
    email: str | None = None
    employee_type: str | None = "full_time"
    status: str | None = "active"
    notes: str | None = None


class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    card_id: str

    department: str | None = None
    position: str | None = None

    phone: str | None = None
    email: str | None = None

    employee_type: str | None = None
    status: str | None = None

    is_active: bool

    photo_url: str | None = None

    notes: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
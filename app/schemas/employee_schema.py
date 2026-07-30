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
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    contractor_company: str | None = None
    job_title: str | None = None
    trade: str | None = None

    employee_type: str | None = None
    status: str | None = None
    onboarding_status: str | None = None

    is_active: bool
    location_id: int | None = None
    location_name: str | None = None

    photo_url: str | None = None

    notes: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True

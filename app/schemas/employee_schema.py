from pydantic import BaseModel
from typing import Optional


class EmployeeCreate(BaseModel):
    full_name: str
    card_id: str
    department: Optional[str] = None


class EmployeeResponse(BaseModel):
    # id: int
    # full_name: str
    # card_id: str
    # department: Optional[str] = None
    # is_active: bool
    id: int
    full_name: str
    card_id: str
    department: str | None = None
    photo_url: str | None = None

    class Config:
        from_attributes = True
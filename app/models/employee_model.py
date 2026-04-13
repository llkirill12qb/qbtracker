from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)
    card_id = Column(String, unique=True, nullable=False)

    department = Column(String, nullable=True)
    position = Column(String, nullable=True)

    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    employee_type = Column(String, default="full_time")
    status = Column(String, default="active")

    is_active = Column(Boolean, default=True)

    photo_filename = Column(String, nullable=True)
    qr_token = Column(String, unique=True, nullable=True, index=True)

    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

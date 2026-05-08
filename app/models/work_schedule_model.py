from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class WorkSchedule(Base):
    __tablename__ = "work_schedules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    shift_start = Column(String, nullable=False, default="09:00")
    shift_end = Column(String, nullable=False, default="17:00")
    lunch_start = Column(String, nullable=True)
    lunch_end = Column(String, nullable=True)
    breaks = Column(String, nullable=True)
    workdays = Column(String, nullable=False, default="0,1,2,3,4")
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

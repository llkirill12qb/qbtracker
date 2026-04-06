from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    card_id = Column(String, index=True)
    event_type = Column(String)  # check-in / check-out
    scanned_at = Column(DateTime, default=datetime.utcnow)
from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey
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
    scan_source = Column(String, nullable=False, default="terminal")
    timezone_used = Column(String, nullable=True)
    timezone_source = Column(String, nullable=True)
    device_timezone = Column(String, nullable=True)
    timezone_abbr = Column(String, nullable=True)
    terminal_id = Column(Integer, nullable=True)
    location_id = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy_meters = Column(Float, nullable=True)
    geo_status = Column(String, nullable=True)

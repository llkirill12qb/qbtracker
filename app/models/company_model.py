from sqlalchemy import Column, Integer, String
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="America/New_York")

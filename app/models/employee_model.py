from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    card_id = Column(String, unique=True, nullable=False, index=True)
    department = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    photo_filename = Column(String, nullable=True)
    
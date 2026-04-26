from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.company_contact_model import CompanyContact
from app.models.company_model import Company
from app.models.employee_model import Employee
from app.models.location_model import Location
from app.models.scan_log_model import ScanLog
from app.models.terminal_model import Terminal
from app.models.user_model import User


def get_all_companies(
    db: Session,
    search: str | None = None,
    sort_by: str = "id",
    direction: str = "asc",
    status: str | None = "non_archived",
):
    query = db.query(Company)

    if status == "non_archived":
        query = query.filter(or_(Company.status.is_(None), Company.status != "archived"))
    elif status:
        query = query.filter(Company.status == status)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(Company.name.ilike(search_pattern))

    sort_column = Company.name if sort_by == "name" else Company.id
    sort_expression = sort_column.desc() if direction == "desc" else sort_column.asc()

    return query.order_by(sort_expression).all()


def get_company_by_id(db: Session, company_id: int):
    return db.query(Company).filter(Company.id == company_id).first()


def create_company(
    db: Session,
    *,
    name: str,
    legal_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    timezone: str = "America/New_York",
    status: str = "active",
):
    company = Company(
        name=name,
        legal_name=legal_name,
        email=email,
        phone=phone,
        timezone=timezone,
        status=status,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company_profile(db: Session, company: Company, **fields):
    for field, value in fields.items():
        if hasattr(company, field):
            setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company


def archive_company(db: Session, company: Company):
    return update_company_profile(db, company, status="archived")


def restore_company(db: Session, company: Company):
    return update_company_profile(db, company, status="active")


def delete_company_cascade(db: Session, company: Company):
    company_id = company.id

    db.query(ScanLog).filter(ScanLog.company_id == company_id).delete(synchronize_session=False)
    db.query(User).filter(User.company_id == company_id).delete(synchronize_session=False)
    db.query(Terminal).filter(Terminal.company_id == company_id).delete(synchronize_session=False)
    db.query(Location).filter(Location.company_id == company_id).delete(synchronize_session=False)
    db.query(CompanyContact).filter(CompanyContact.company_id == company_id).delete(synchronize_session=False)
    db.query(Employee).filter(Employee.company_id == company_id).delete(synchronize_session=False)
    db.delete(company)
    db.commit()

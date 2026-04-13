from sqlalchemy.orm import Session

from app.crud.employee_crud import ensure_employee_qr_token
from app.models.employee_model import Employee


def ensure_employee_qr_tokens(db: Session):
    employees = db.query(Employee).filter(Employee.qr_token.is_(None)).all()

    for employee in employees:
        ensure_employee_qr_token(db, employee)

    return len(employees)

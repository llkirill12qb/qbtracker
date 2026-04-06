from sqlalchemy.orm import Session

from app.models.employee_model import Employee


def get_employee_by_card_id(db: Session, card_id: str):
    return db.query(Employee).filter(Employee.card_id == card_id).first()


def get_employee_by_id(db: Session, employee_id: int):
    return db.query(Employee).filter(Employee.id == employee_id).first()


def get_all_employees(db: Session, company_id: int):
    return db.query(Employee).filter(Employee.company_id == company_id).all()


def create_employee(
    db: Session,
    full_name: str,
    card_id: str,
    department: str = "",
    position: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    employee_type: str = "full_time",
    status: str = "active",
    notes: str | None = None,
    company_id: int | None = None,
    photo_filename: str | None = None,
):
    new_employee = Employee(
        full_name=full_name,
        card_id=card_id,
        department=department,
        position=position,
        phone=phone,
        email=email,
        employee_type=employee_type,
        status=status,
        notes=notes,
        company_id=company_id,
        photo_filename=photo_filename,
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee


def update_employee_photo(db: Session, employee: Employee, photo_filename: str):
    employee.photo_filename = photo_filename
    db.commit()
    db.refresh(employee)
    return employee
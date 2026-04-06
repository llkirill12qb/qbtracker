from sqlalchemy.orm import Session

from app.models.employee_model import Employee


def get_employee_by_card_id(db: Session, card_id: str, company_id: int | None = None):
    query = db.query(Employee).filter(Employee.card_id == card_id)
    if company_id is not None:
        query = query.filter(Employee.company_id == company_id)
    return query.first()


def get_employee_by_id(db: Session, employee_id: int, company_id: int | None = None):
    query = db.query(Employee).filter(Employee.id == employee_id)
    if company_id is not None:
        query = query.filter(Employee.company_id == company_id)
    return query.first()


def get_all_employees(db: Session, company_id: int):
    return (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.is_active.is_(True))
        .all()
    )


def get_archived_employees(db: Session, company_id: int):
    return (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.is_active.is_(False))
        .all()
    )


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


def update_employee(
    db: Session,
    employee: Employee,
    full_name: str,
    card_id: str,
    department: str = "",
    position: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    employee_type: str = "full_time",
    status: str = "active",
    notes: str | None = None,
):
    employee.full_name = full_name
    employee.card_id = card_id
    employee.department = department
    employee.position = position
    employee.phone = phone
    employee.email = email
    employee.employee_type = employee_type
    employee.status = status
    employee.notes = notes
    employee.is_active = status == "active"

    db.commit()
    db.refresh(employee)
    return employee


def soft_delete_employee(db: Session, employee: Employee):
    employee.status = "inactive"
    employee.is_active = False
    db.commit()
    db.refresh(employee)
    return employee


def restore_employee(db: Session, employee: Employee):
    employee.status = "active"
    employee.is_active = True
    db.commit()
    db.refresh(employee)
    return employee

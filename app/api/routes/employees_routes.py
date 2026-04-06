import os

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.schemas.employee_schema import EmployeeResponse
from app.services.photo_service import save_employee_photo
from app.crud.employee_crud import (
    get_employee_by_card_id,
    create_employee as create_employee_crud,
    get_all_employees,
    update_employee_photo,
)

router = APIRouter()

# ВРЕМЕННО:
# пока нет полноценной авторизации компании, используем company_1
DEFAULT_COMPANY_ID = 1


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    full_name: str = Form(...),
    card_id: str = Form(...),
    department: str = Form(""),
    position: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    employee_type: str = Form("full_time"),
    status: str = Form("active"),
    notes: str = Form(""),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    existing_employee = get_employee_by_card_id(db, card_id)
    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="Employee with this card_id already exists"
        )

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(
                status_code=400,
                detail="Only jpg, jpeg, png, webp files are allowed"
            )

    new_employee = create_employee_crud(
        db=db,
        full_name=full_name,
        card_id=card_id,
        department=department,
        position=position or None,
        phone=phone or None,
        email=email or None,
        employee_type=employee_type,
        status=status,
        notes=notes or None,
        company_id=DEFAULT_COMPANY_ID
    )

    if photo and photo.filename:
        saved_path = save_employee_photo(
            upload_file=photo,
            company_id=DEFAULT_COMPANY_ID,
            employee_id=new_employee.id
        )

        photo_filename = os.path.basename(saved_path)

        new_employee = update_employee_photo(
            db=db,
            employee=new_employee,
            photo_filename=photo_filename
        )

    photo_url = None
    if new_employee.photo_filename:
        photo_url = (
            f"/uploads/companies/company_{DEFAULT_COMPANY_ID}/employees/"
            f"{new_employee.photo_filename}"
        )

    return EmployeeResponse(
        id=new_employee.id,
        full_name=new_employee.full_name,
        card_id=new_employee.card_id,
        department=new_employee.department,
        position=new_employee.position,
        phone=new_employee.phone,
        email=new_employee.email,
        employee_type=new_employee.employee_type,
        status=new_employee.status,
        is_active=new_employee.is_active,
        photo_url=photo_url,
        notes=new_employee.notes,
        created_at=new_employee.created_at,
    )


@router.get("/employees", response_model=list[EmployeeResponse])
def get_employees(db: Session = Depends(get_db)):
    employees = get_all_employees(db, DEFAULT_COMPANY_ID)

    result = []
    for emp in employees:
        photo_url = None
        if emp.photo_filename:
            photo_url = (
                f"/uploads/companies/company_{DEFAULT_COMPANY_ID}/employees/"
                f"{emp.photo_filename}"
            )

        result.append(
            EmployeeResponse(
                id=emp.id,
                full_name=emp.full_name,
                card_id=emp.card_id,
                department=emp.department,
                position=emp.position,
                phone=emp.phone,
                email=emp.email,
                employee_type=emp.employee_type,
                status=emp.status,
                is_active=emp.is_active,
                photo_url=photo_url,
                notes=emp.notes,
                created_at=emp.created_at,
            )
        )

    return result
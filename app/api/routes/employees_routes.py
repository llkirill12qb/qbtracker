import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import SessionLocal
from app.core.security import require_company_workspace_access
from app.crud.employee_crud import (
    create_employee as create_employee_crud,
    get_all_employees,
    get_archived_employees,
    get_employee_by_card_id,
    get_employee_by_id,
    restore_employee as restore_employee_crud,
    soft_delete_employee,
    update_employee as update_employee_crud,
    update_employee_photo,
)
from app.schemas.employee_schema import EmployeeResponse
from app.services.photo_service import delete_employee_photo, save_employee_photo

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_photo_extension(photo: UploadFile | None) -> None:
    if not photo or not photo.filename:
        return

    ext = os.path.splitext(photo.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=400,
            detail="Only jpg, jpeg, png, webp files are allowed",
        )


def build_employee_response(employee) -> EmployeeResponse:
    photo_url = None
    if employee.photo_filename:
        photo_url = (
            f"/uploads/companies/company_{employee.company_id}/employees/"
            f"{employee.photo_filename}"
        )

    return EmployeeResponse(
        id=employee.id,
        full_name=employee.full_name,
        card_id=employee.card_id,
        department=employee.department,
        position=employee.position,
        phone=employee.phone,
        email=employee.email,
        employee_type=employee.employee_type,
        status=employee.status,
        is_active=employee.is_active,
        photo_url=photo_url,
        notes=employee.notes,
        created_at=employee.created_at,
    )


@router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    request: Request,
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
    db: Session = Depends(get_db),
):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    existing_employee = get_employee_by_card_id(db, card_id, company_id)
    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="Employee with this card_id already exists",
        )

    validate_photo_extension(photo)

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
        company_id=company_id,
    )

    if photo and photo.filename:
        saved_path = save_employee_photo(
            upload_file=photo,
            company_id=company_id,
            employee_id=new_employee.id,
        )
        photo_filename = os.path.basename(saved_path)
        new_employee = update_employee_photo(
            db=db,
            employee=new_employee,
            photo_filename=photo_filename,
        )

    return build_employee_response(new_employee)


@router.get("/employees", response_model=list[EmployeeResponse])
def get_employees(request: Request, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    employees = get_all_employees(db, company_id)
    return [build_employee_response(emp) for emp in employees]


@router.get("/employees/archived", response_model=list[EmployeeResponse])
def get_archived_employees_list(request: Request, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    employees = get_archived_employees(db, company_id)
    return [build_employee_response(emp) for emp in employees]


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    request: Request,
    employee_id: int,
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
    db: Session = Depends(get_db),
):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    employee = get_employee_by_id(db, employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing_employee = get_employee_by_card_id(db, card_id, company_id)
    if existing_employee and existing_employee.id != employee_id:
        raise HTTPException(
            status_code=400,
            detail="Employee with this card_id already exists",
        )

    validate_photo_extension(photo)

    employee = update_employee_crud(
        db=db,
        employee=employee,
        full_name=full_name,
        card_id=card_id,
        department=department,
        position=position or None,
        phone=phone or None,
        email=email or None,
        employee_type=employee_type,
        status=status,
        notes=notes or None,
    )

    if photo and photo.filename:
        delete_employee_photo(employee.photo_filename, company_id)
        saved_path = save_employee_photo(
            upload_file=photo,
            company_id=company_id,
            employee_id=employee.id,
        )
        photo_filename = os.path.basename(saved_path)
        employee = update_employee_photo(
            db=db,
            employee=employee,
            photo_filename=photo_filename,
        )

    return build_employee_response(employee)


@router.delete("/employees/{employee_id}")
def delete_employee(request: Request, employee_id: int, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    employee = get_employee_by_id(db, employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee = soft_delete_employee(db, employee)

    return {
        "success": True,
        "employee_id": employee_id,
        "archived": True,
        "status": employee.status,
    }


@router.post("/employees/{employee_id}/restore", response_model=EmployeeResponse)
def restore_employee(request: Request, employee_id: int, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    employee = get_employee_by_id(db, employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee = restore_employee_crud(db, employee)
    return build_employee_response(employee)

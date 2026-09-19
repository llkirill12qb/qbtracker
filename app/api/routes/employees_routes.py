import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import SessionLocal
from app.core.roles import PERM_MANAGE_EMPLOYEES
from app.core.security import require_permission
from app.crud.employee_crud import (
    advance_employee_after_photo,
    create_employee as create_employee_crud,
    get_all_employees,
    get_archived_employees,
    get_employee_by_card_id,
    get_employee_by_id,
    mark_employee_badge_issued,
    restore_employee as restore_employee_crud,
    soft_delete_employee,
    update_employee as update_employee_crud,
    update_employee_photo,
)
from app.crud.location_crud import get_location_by_id, get_location_name_by_id
from app.schemas.employee_schema import EmployeeResponse
from app.services.photo_service import (
    delete_employee_photo,
    save_employee_photo,
    save_employee_photo_from_data_url,
)

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


def normalize_captured_photo(captured_photo: str | None) -> str | None:
    if not captured_photo:
        return None

    captured_photo = captured_photo.strip()
    return captured_photo or None


def normalize_location_id(db: Session, company_id: int, location_id: str | None):
    if not location_id:
        return None

    clean_value = location_id.strip()
    if not clean_value:
        return None

    try:
        parsed_location_id = int(clean_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid location")

    location = get_location_by_id(db, parsed_location_id, company_id)
    if not location:
        raise HTTPException(status_code=400, detail="Invalid location")

    return parsed_location_id


def build_employee_response(employee, db: Session | None = None) -> EmployeeResponse:
    photo_url = None
    if employee.photo_filename:
        photo_url = (
            f"/uploads/companies/company_{employee.company_id}/employees/"
            f"{employee.photo_filename}"
        )

    location_name = None
    if db is not None:
        location_name = get_location_name_by_id(db, employee.location_id, employee.company_id)

    return EmployeeResponse(
        id=employee.id,
        full_name=employee.full_name,
        card_id=employee.card_id,
        department=employee.department,
        position=employee.position,
        phone=employee.phone,
        email=employee.email,
        emergency_contact_name=employee.emergency_contact_name,
        emergency_contact_phone=employee.emergency_contact_phone,
        contractor_company=employee.contractor_company,
        job_title=employee.job_title,
        trade=employee.trade,
        employee_type=employee.employee_type,
        status=employee.status,
        onboarding_status=employee.onboarding_status,
        is_active=employee.is_active,
        location_id=employee.location_id,
        location_name=location_name,
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
    location_id: str = Form(""),
    notes: str = Form(""),
    captured_photo: str = Form(""),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company_id = get_current_company_id(request)
    existing_employee = get_employee_by_card_id(db, card_id, company_id)
    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="Employee with this card_id already exists",
        )

    validate_photo_extension(photo)
    captured_photo_value = normalize_captured_photo(captured_photo)
    parsed_location_id = normalize_location_id(db, company_id, location_id)

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
        location_id=parsed_location_id,
    )

    try:
        if captured_photo_value:
            saved_path = save_employee_photo_from_data_url(
                data_url=captured_photo_value,
                company_id=company_id,
                employee_id=new_employee.id,
            )
            photo_filename = os.path.basename(saved_path)
            new_employee = update_employee_photo(
                db=db,
                employee=new_employee,
                photo_filename=photo_filename,
            )
            new_employee = advance_employee_after_photo(db, new_employee)
        elif photo and photo.filename:
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
            new_employee = advance_employee_after_photo(db, new_employee)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_employee_response(new_employee, db)


@router.get("/employees", response_model=list[EmployeeResponse])
def get_employees(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company_id = get_current_company_id(request)
    employees = get_all_employees(db, company_id)
    return [build_employee_response(emp, db) for emp in employees]


@router.get("/employees/archived", response_model=list[EmployeeResponse])
def get_archived_employees_list(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company_id = get_current_company_id(request)
    employees = get_archived_employees(db, company_id)
    return [build_employee_response(emp, db) for emp in employees]


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
    location_id: str = Form(""),
    notes: str = Form(""),
    captured_photo: str = Form(""),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
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
    captured_photo_value = normalize_captured_photo(captured_photo)
    parsed_location_id = normalize_location_id(db, company_id, location_id)

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
        location_id=parsed_location_id,
        notes=notes or None,
    )

    try:
        if captured_photo_value:
            delete_employee_photo(employee.photo_filename, company_id)
            saved_path = save_employee_photo_from_data_url(
                data_url=captured_photo_value,
                company_id=company_id,
                employee_id=employee.id,
            )
            photo_filename = os.path.basename(saved_path)
            employee = update_employee_photo(
                db=db,
                employee=employee,
                photo_filename=photo_filename,
            )
            employee = advance_employee_after_photo(db, employee)
        elif photo and photo.filename:
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
            employee = advance_employee_after_photo(db, employee)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_employee_response(employee, db)


@router.post("/employees/{employee_id}/badge-issued", response_model=EmployeeResponse)
def issue_employee_badge(request: Request, employee_id: int, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company_id = get_current_company_id(request)
    employee = get_employee_by_id(db, employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if employee.status != "pending_badge":
        raise HTTPException(
            status_code=400,
            detail="Employee must be pending badge before issuing a badge",
        )

    employee = mark_employee_badge_issued(db, employee)
    return build_employee_response(employee, db)


@router.delete("/employees/{employee_id}")
def delete_employee(request: Request, employee_id: int, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
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
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company_id = get_current_company_id(request)
    employee = get_employee_by_id(db, employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee = restore_employee_crud(db, employee)
    return build_employee_response(employee, db)

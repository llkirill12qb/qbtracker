# import os
# import shutil
# from uuid import uuid4

# from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
# from sqlalchemy.orm import Session

# from app.database import SessionLocal
# from app.models.employee import Employee
# from app.schemas.employee import EmployeeResponse

# router = APIRouter()

# PHOTOS_DIR = "static/photos"
# os.makedirs(PHOTOS_DIR, exist_ok=True)


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @router.post("/employees", response_model=EmployeeResponse)
# def create_employee(
#     full_name: str = Form(...),
#     card_id: str = Form(...),
#     department: str = Form(""),
#     photo: UploadFile | None = File(None),
#     db: Session = Depends(get_db)
# ):
#     existing_employee = db.query(Employee).filter(Employee.card_id == card_id).first()
#     if existing_employee:
#         raise HTTPException(status_code=400, detail="Employee with this card_id already exists")

#     photo_filename = None

#     if photo and photo.filename:
#         ext = os.path.splitext(photo.filename)[1].lower()
#         if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
#             raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp files are allowed")

#         photo_filename = f"{uuid4().hex}{ext}"
#         file_path = os.path.join(PHOTOS_DIR, photo_filename)

#         # with open(file_path, "wb") as buffer:
#         #     shutil.copyfileobj(photo.file, buffer)

#     new_employee = Employee(
#         full_name=full_name,
#         card_id=card_id,
#         department=department,
#         photo_filename=photo_filename,
#     )

#     db.add(new_employee)
#     db.commit()
#     db.refresh(new_employee)

#     return EmployeeResponse(
#         id=new_employee.id,
#         full_name=new_employee.full_name,
#         card_id=new_employee.card_id,
#         department=new_employee.department,
#         photo_url=f"/static/photos/{new_employee.photo_filename}" if new_employee.photo_filename else None
#     )


# @router.get("/employees", response_model=list[EmployeeResponse])
# def get_employees(db: Session = Depends(get_db)):
#     employees = db.query(Employee).all()

#     result = []
#     for emp in employees:
#         result.append(
#             EmployeeResponse(
#                 id=emp.id,
#                 full_name=emp.full_name,
#                 card_id=emp.card_id,
#                 department=emp.department,
#                 photo_url=f"/static/photos/{emp.photo_filename}" if emp.photo_filename else None
#             )
#         )

#     return result

import os

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.employee import Employee
from app.schemas.employee import EmployeeResponse
from app.services.photo_service import save_employee_photo

router = APIRouter()

# ВРЕМЕННО:
# пока в Employee еще нет company_id, используем company_1
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
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    existing_employee = db.query(Employee).filter(Employee.card_id == card_id).first()
    if existing_employee:
        raise HTTPException(status_code=400, detail="Employee with this card_id already exists")

    photo_filename = None

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(
                status_code=400,
                detail="Only jpg, jpeg, png, webp files are allowed"
            )

    new_employee = Employee(
        full_name=full_name,
        card_id=card_id,
        department=department,
        photo_filename=None,
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    if photo and photo.filename:
        saved_path = save_employee_photo(
            upload_file=photo,
            company_id=DEFAULT_COMPANY_ID,
            employee_id=new_employee.id
        )

        # сохраняем только имя файла
        photo_filename = os.path.basename(saved_path)
        new_employee.photo_filename = photo_filename

        db.commit()
        db.refresh(new_employee)

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
        photo_url=photo_url
    )


@router.get("/employees", response_model=list[EmployeeResponse])
def get_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()

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
                photo_url=photo_url
            )
        )

    return result
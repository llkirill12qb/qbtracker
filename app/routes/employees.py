# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session

# from app.database import SessionLocal
# from app.models.employee import Employee
# from app.schemas.employee import EmployeeCreate, EmployeeResponse

# router = APIRouter()


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @router.post("/employees", response_model=EmployeeResponse)
# def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
#     new_employee = Employee(
#         full_name=employee.full_name,
#         card_id=employee.card_id,
#         department=employee.department,
#     )
#     db.add(new_employee)
#     db.commit()
#     db.refresh(new_employee)
#     return new_employee


# @router.get("/employees", response_model=list[EmployeeResponse])
# def get_employees(db: Session = Depends(get_db)):
#     return db.query(Employee).all()

import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.employee import Employee
from app.schemas.employee import EmployeeResponse

router = APIRouter()

PHOTOS_DIR = "static/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)


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
            raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp files are allowed")

        photo_filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(PHOTOS_DIR, photo_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

    new_employee = Employee(
        full_name=full_name,
        card_id=card_id,
        department=department,
        photo_filename=photo_filename,
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return EmployeeResponse(
        id=new_employee.id,
        full_name=new_employee.full_name,
        card_id=new_employee.card_id,
        department=new_employee.department,
        photo_url=f"/static/photos/{new_employee.photo_filename}" if new_employee.photo_filename else None
    )


@router.get("/employees", response_model=list[EmployeeResponse])
def get_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()

    result = []
    for emp in employees:
        result.append(
            EmployeeResponse(
                id=emp.id,
                full_name=emp.full_name,
                card_id=emp.card_id,
                department=emp.department,
                photo_url=f"/static/photos/{emp.photo_filename}" if emp.photo_filename else None
            )
        )

    return result
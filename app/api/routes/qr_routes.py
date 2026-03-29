import qrcode
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.employee_model import Employee

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/employee/{employee_id}/qr")
def generate_qr(employee_id: int):

    db = SessionLocal()

    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    data = employee.card_id

    img = qrcode.make(data)

    file_path = f"qr_{employee.card_id}.png"
    img.save(file_path)

    return FileResponse(file_path)
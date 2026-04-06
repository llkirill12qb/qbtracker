from io import BytesIO

import qrcode
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.database import SessionLocal
from app.models.employee_model import Employee

router = APIRouter()


@router.get("/employee/{employee_id}/qr")
def generate_qr(employee_id: int):
    db = SessionLocal()
    try:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        img = qrcode.make(employee.card_id)
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    finally:
        db.close()

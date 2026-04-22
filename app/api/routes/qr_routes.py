from io import BytesIO

import qrcode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.company_context import get_current_company_id
from app.core.database import SessionLocal
from app.core.roles import PERM_MANAGE_EMPLOYEES
from app.core.security import require_permission
from app.crud.employee_crud import build_qr_payload, ensure_employee_qr_token
from app.models.employee_model import Employee

router = APIRouter()


@router.get("/employee/{employee_id}/qr")
def generate_qr(employee_id: int, request: Request):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company_id = get_current_company_id(request)
    db = SessionLocal()
    try:
        employee = (
            db.query(Employee)
            .filter(
                Employee.id == employee_id,
                Employee.company_id == company_id,
            )
            .first()
        )
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        employee = ensure_employee_qr_token(db, employee)
        img = qrcode.make(build_qr_payload(employee))
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    finally:
        db.close()

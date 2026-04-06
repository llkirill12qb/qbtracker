from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.crud.employee_crud import get_archived_employees, get_all_employees
from app.crud.scan_crud import get_report_logs

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DEFAULT_COMPANY_ID = 1


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})


@router.get("/api/reports")
def reports_data(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    start_datetime = None
    end_datetime = None

    try:
        if start_date:
            start_datetime = datetime.combine(date.fromisoformat(start_date), time.min)
        if end_date:
            end_datetime = datetime.combine(date.fromisoformat(end_date), time.max)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    active_employees = get_all_employees(db, DEFAULT_COMPANY_ID)
    archived_employees = get_archived_employees(db, DEFAULT_COMPANY_ID)
    company_employees = sorted(
        active_employees + archived_employees,
        key=lambda emp: (emp.full_name or "").lower(),
    )

    if employee_id is not None:
        employee_exists = any(emp.id == employee_id for emp in company_employees)
        if not employee_exists:
            raise HTTPException(status_code=404, detail="Employee not found")

    rows = get_report_logs(
        db=db,
        company_id=DEFAULT_COMPANY_ID,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        employee_id=employee_id,
    )

    report_rows = []
    check_in_count = 0
    check_out_count = 0

    for log, employee in rows:
        if log.event_type == "check-in":
            check_in_count += 1
        elif log.event_type == "check-out":
            check_out_count += 1

        report_rows.append({
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "employee_status": employee.status,
            "card_id": log.card_id,
            "event": log.event_type,
            "time": log.scanned_at.isoformat(),
        })

    employee_options = [
        {
            "id": emp.id,
            "name": emp.full_name,
            "status": emp.status,
            "is_active": emp.is_active,
        }
        for emp in company_employees
    ]

    return {
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "employee_id": employee_id,
        },
        "employees": employee_options,
        "summary": {
            "total_scans": len(report_rows),
            "check_ins": check_in_count,
            "check_outs": check_out_count,
        },
        "rows": report_rows,
    }

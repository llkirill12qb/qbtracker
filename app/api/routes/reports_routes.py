from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import SessionLocal
from app.core.roles import PERM_VIEW_REPORTS
from app.core.security import require_permission
from app.crud.company_crud import get_company_by_id
from app.crud.employee_crud import get_archived_employees, get_all_employees
from app.crud.location_crud import get_location_name_by_id
from app.crud.scan_crud import get_report_logs
from app.crud.terminal_crud import get_terminal_name_by_id
from app.services.company_time_service import (
    format_scan_time,
    format_scan_time_display,
    get_company_timezone,
    get_scan_local_date,
    get_scan_timezone,
    get_timezone_abbr,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_VIEW_REPORTS)
    company = get_company_by_id(db, get_current_company_id(request))
    return templates.TemplateResponse("reports.html", {"request": request, "company": company})


@router.get("/api/reports")
def reports_data(
    request: Request,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_VIEW_REPORTS)
    company_id = get_current_company_id(request)
    start_local_date = None
    end_local_date = None
    timezone_name, _ = get_company_timezone(db, company_id)

    try:
        if start_date:
            start_local_date = date.fromisoformat(start_date)
        if end_date:
            end_local_date = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    event_type_value = event_type.strip() if event_type else None
    if event_type_value == "":
        event_type_value = None
    if event_type_value not in {None, "check-in", "check-out"}:
        raise HTTPException(status_code=400, detail="Invalid event type")

    active_employees = get_all_employees(db, company_id)
    archived_employees = get_archived_employees(db, company_id)
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
        company_id=company_id,
        employee_id=employee_id,
    )

    report_rows = []
    check_in_count = 0
    check_out_count = 0

    for log, employee in rows:
        scan_local_date = get_scan_local_date(log, timezone_name)
        if start_local_date and scan_local_date < start_local_date:
            continue
        if end_local_date and scan_local_date > end_local_date:
            continue
        if event_type_value and log.event_type != event_type_value:
            continue

        _, scan_timezone = get_scan_timezone(log, timezone_name)

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
            "scan_source": log.scan_source,
            "time": format_scan_time(log.scanned_at, scan_timezone),
            "time_display": format_scan_time_display(log.scanned_at, scan_timezone),
            "timezone_abbr": log.timezone_abbr or get_timezone_abbr(log.scanned_at, scan_timezone),
            "location_name": get_location_name_by_id(db, log.location_id, company_id),
            "terminal_name": get_terminal_name_by_id(db, log.terminal_id, company_id),
            "geo_status": log.geo_status,
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
            "event_type": event_type_value,
            "timezone": timezone_name,
            "company_id": company_id,
        },
        "employees": employee_options,
        "summary": {
            "total_scans": len(report_rows),
            "check_ins": check_in_count,
            "check_outs": check_out_count,
        },
        "rows": report_rows,
    }

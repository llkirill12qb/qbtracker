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


@router.get("/reports/day-summary", response_class=HTMLResponse)
def reports_day_summary_page(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_VIEW_REPORTS)
    company = get_company_by_id(db, get_current_company_id(request))
    return templates.TemplateResponse("reports_day_summary.html", {"request": request, "company": company})


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
    daily_summary_map = {}
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

        summary_key = (employee.id, scan_local_date.isoformat())
        day_summary = daily_summary_map.get(summary_key)
        if day_summary is None:
            day_summary = {
                "employee_id": employee.id,
                "employee_name": employee.full_name,
                "employee_status": employee.status,
                "date": scan_local_date.isoformat(),
                "first_check_in_at": None,
                "last_check_out_at": None,
                "events_count": 0,
                "has_check_in": False,
                "has_check_out": False,
                "last_event_type": None,
                "last_event_at": None,
                "timezone_abbr": log.timezone_abbr or get_timezone_abbr(log.scanned_at, scan_timezone),
                "scan_timezone": scan_timezone,
            }
            daily_summary_map[summary_key] = day_summary

        day_summary["events_count"] += 1
        if day_summary["last_event_at"] is None or log.scanned_at > day_summary["last_event_at"]:
            day_summary["last_event_at"] = log.scanned_at
            day_summary["last_event_type"] = log.event_type
        if log.event_type == "check-in":
            day_summary["has_check_in"] = True
            if day_summary["first_check_in_at"] is None or log.scanned_at < day_summary["first_check_in_at"]:
                day_summary["first_check_in_at"] = log.scanned_at
        elif log.event_type == "check-out":
            day_summary["has_check_out"] = True
            if day_summary["last_check_out_at"] is None or log.scanned_at > day_summary["last_check_out_at"]:
                day_summary["last_check_out_at"] = log.scanned_at

    employee_options = [
        {
            "id": emp.id,
            "name": emp.full_name,
            "status": emp.status,
            "is_active": emp.is_active,
        }
        for emp in company_employees
    ]

    day_summaries = []
    for summary in daily_summary_map.values():
        first_check_in_at = summary["first_check_in_at"]
        last_check_out_at = summary["last_check_out_at"]
        worked_minutes = None
        status_label = "Complete"
        last_event_type = summary["last_event_type"]

        if first_check_in_at and last_check_out_at and last_check_out_at >= first_check_in_at:
            worked_minutes = int((last_check_out_at - first_check_in_at).total_seconds() // 60)
        if summary["has_check_in"] and not summary["has_check_out"]:
            status_label = "Missing check-out"
        elif summary["has_check_out"] and not summary["has_check_in"]:
            status_label = "Missing check-in"
        elif last_event_type == "check-in":
            status_label = "Missing final check-out"
        elif worked_minutes is None:
            status_label = "Incomplete"
        else:
            status_label = "Complete"

        if worked_minutes is not None:
            hours = worked_minutes // 60
            minutes = worked_minutes % 60
            worked_duration = f"{hours}h {minutes:02d}m"
        else:
            worked_duration = "-"

        first_display = "-"
        if first_check_in_at is not None:
            first_display = format_scan_time_display(first_check_in_at, summary["scan_timezone"])

        last_display = "-"
        if last_check_out_at is not None:
            last_display = format_scan_time_display(last_check_out_at, summary["scan_timezone"])

        day_summaries.append({
            "employee_id": summary["employee_id"],
            "employee_name": summary["employee_name"],
            "employee_status": summary["employee_status"],
            "date": summary["date"],
            "first_check_in": first_display,
            "last_check_out": last_display,
            "events_count": summary["events_count"],
            "worked_duration": worked_duration,
            "status": status_label,
            "timezone_abbr": summary["timezone_abbr"] or "-",
        })

    day_summaries.sort(key=lambda row: (row["date"], row["employee_name"].lower()), reverse=True)

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
            "day_summaries": len(day_summaries),
        },
        "rows": report_rows,
        "day_summaries": day_summaries,
    }

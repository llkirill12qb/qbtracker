from sqlalchemy.orm import Session

from app.crud.scan_crud import (
    get_employee_by_card_id,
    get_last_scan_log,
    create_scan_log,
    get_all_logs,
    get_employee_by_id
)
from app.services.company_time_service import (
    format_scan_time,
    format_scan_time_display,
    get_company_timezone,
    get_timezone_abbr,
    get_timezone_info,
)

DEFAULT_COMPANY_ID = 1


def process_scan(
    db: Session,
    card_id: str,
    scan_source: str = "terminal_web",
    device_timezone: str | None = None,
    timezone_abbr: str | None = None,
    terminal_id: int | None = None,
    location_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_meters: float | None = None,
):
    employee = get_employee_by_card_id(db, card_id, DEFAULT_COMPANY_ID)

    if not employee:
        return None, "Employee not found"

    company_timezone_name, _ = get_company_timezone(db, DEFAULT_COMPANY_ID)
    scan_timezone_name, scan_timezone = get_timezone_info(device_timezone or company_timezone_name)
    timezone_source = "device" if device_timezone else "company_default"
    geo_status = "pending" if latitude is not None and longitude is not None else None

    last_log = get_last_scan_log(db, employee.id, DEFAULT_COMPANY_ID)

    event_type = "check-in"

    if last_log and last_log.event_type == "check-in":
        event_type = "check-out"

    new_log = create_scan_log(
        db=db,
        employee_id=employee.id,
        company_id=DEFAULT_COMPANY_ID,
        card_id=card_id,
        event_type=event_type,
        scan_source=scan_source,
        timezone_used=scan_timezone_name,
        timezone_source=timezone_source,
        device_timezone=scan_timezone_name,
        timezone_abbr=timezone_abbr,
        terminal_id=terminal_id,
        location_id=location_id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        geo_status=geo_status,
    )
    resolved_timezone_abbr = get_timezone_abbr(new_log.scanned_at, scan_timezone)

    if new_log.timezone_abbr != resolved_timezone_abbr:
        new_log.timezone_abbr = resolved_timezone_abbr
        db.commit()
        db.refresh(new_log)

    return {
        "employee_id": employee.id,
        "employee_name": employee.full_name,
        "event": event_type,
        "scan_source": new_log.scan_source,
        "timestamp": format_scan_time(new_log.scanned_at, scan_timezone),
        "time_display": format_scan_time_display(new_log.scanned_at, scan_timezone),
        "timezone": scan_timezone_name,
        "timezone_abbr": new_log.timezone_abbr,
        "timezone_source": new_log.timezone_source,
        "geo_status": new_log.geo_status,
        "photo_url": (
            f"/uploads/companies/company_{DEFAULT_COMPANY_ID}/employees/{employee.photo_filename}"
            if employee.photo_filename else None
        )
    }, None


def get_logs(db: Session):
    logs = get_all_logs(db, DEFAULT_COMPANY_ID)
    company_timezone_name, _ = get_company_timezone(db, DEFAULT_COMPANY_ID)

    result = []

    for log in logs:
        employee = get_employee_by_id(db, log.employee_id, DEFAULT_COMPANY_ID)
        scan_timezone_name, scan_timezone = get_timezone_info(log.device_timezone or company_timezone_name)

        result.append({
            "employee": employee.full_name if employee else "[Unknown Employee]",
            "card_id": log.card_id,
            "event": log.event_type,
            "scan_source": log.scan_source,
            "time": format_scan_time(log.scanned_at, scan_timezone),
            "time_display": format_scan_time_display(log.scanned_at, scan_timezone),
            "timezone": scan_timezone_name,
            "timezone_abbr": log.timezone_abbr or get_timezone_abbr(log.scanned_at, scan_timezone),
            "timezone_source": log.timezone_source,
            "geo_status": log.geo_status,
            "photo_url": (
                f"/uploads/companies/company_{DEFAULT_COMPANY_ID}/employees/{employee.photo_filename}"
                if employee and employee.photo_filename else None
            )
        })

    return result

from sqlalchemy.orm import Session

from app.crud.scan_crud import (
    get_employee_by_card_id,
    get_last_scan_log,
    create_scan_log,
    get_all_logs,
    get_employee_by_id
)

DEFAULT_COMPANY_ID = 1


def process_scan(db: Session, card_id: str):
    employee = get_employee_by_card_id(db, card_id, DEFAULT_COMPANY_ID)

    if not employee:
        return None, "Employee not found"

    last_log = get_last_scan_log(db, employee.id, DEFAULT_COMPANY_ID)

    event_type = "check-in"

    if last_log and last_log.event_type == "check-in":
        event_type = "check-out"

    new_log = create_scan_log(
        db=db,
        employee_id=employee.id,
        company_id=DEFAULT_COMPANY_ID,
        card_id=card_id,
        event_type=event_type
    )

    return {
        "employee_id": employee.id,
        "employee_name": employee.full_name,
        "event": event_type,
        "timestamp": new_log.scanned_at.isoformat(),
        "photo_url": (
            f"/uploads/companies/company_{DEFAULT_COMPANY_ID}/employees/{employee.photo_filename}"
            if employee.photo_filename else None
        )
    }, None


def get_logs(db: Session):
    logs = get_all_logs(db, DEFAULT_COMPANY_ID)

    result = []

    for log in logs:
        employee = get_employee_by_id(db, log.employee_id, DEFAULT_COMPANY_ID)

        result.append({
            "employee": employee.full_name if employee else "[Unknown Employee]",
            "card_id": log.card_id,
            "event": log.event_type,
            "time": log.scanned_at,
            "photo_url": (
                f"/uploads/companies/company_{DEFAULT_COMPANY_ID}/employees/{employee.photo_filename}"
                if employee and employee.photo_filename else None
            )
        })

    return result
from sqlalchemy.orm import Session
from app.models.employee_model import Employee
from app.models.scan_log_model import ScanLog


def process_scan(db: Session, card_id: str):
    employee = db.query(Employee).filter(Employee.card_id == card_id).first()

    if not employee:
        return None, "Employee not found"

    last_log = (
        db.query(ScanLog)
        .filter(ScanLog.employee_id == employee.id)
        .order_by(ScanLog.scanned_at.desc())
        .first()
    )

    event_type = "check-in"

    if last_log and last_log.event_type == "check-in":
        event_type = "check-out"

    new_log = ScanLog(
        employee_id=employee.id,
        card_id=card_id,
        event_type=event_type
    )

    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {
        "employee_id": employee.id,
        "employee_name": employee.full_name,
        "event": event_type,
        "timestamp": new_log.scanned_at.isoformat(),
        "photo_url": (
            f"/uploads/companies/company_1/employees/{employee.photo_filename}"
            if employee.photo_filename else None
        )
    }, None

def get_logs(db: Session):
    logs = db.query(ScanLog).order_by(ScanLog.scanned_at.desc()).all()

    result = []

    for log in logs:
        employee = db.query(Employee).filter(Employee.id == log.employee_id).first()

        result.append({
            "employee": employee.full_name if employee else "[Unknown Employee]",
            "card_id": log.card_id,
            "event": log.event_type,
            "time": log.scanned_at,
            "photo_url": (
                f"/uploads/companies/company_1/employees/{employee.photo_filename}"
                if employee and employee.photo_filename else None
            )
        })

    return result
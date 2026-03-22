from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.employee import Employee
from app.models.scan_log import ScanLog

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/scan")
def scan_card(card_id: str, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.card_id == card_id).first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

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
        "photo_url": f"/static/photos/{employee.photo_filename}" if employee.photo_filename else None
    }


@router.get("/logs")
def get_logs(db: Session = Depends(get_db)):
    logs = db.query(ScanLog).order_by(ScanLog.scanned_at.desc()).all()

    result = []

    for log in logs:
        employee = db.query(Employee).filter(Employee.id == log.employee_id).first()

        result.append({
            "employee": employee.full_name,
            "card_id": log.card_id,
            "event": log.event_type,
            "time": log.scanned_at,
            "photo_url": f"/static/photos/{employee.photo_filename}" if employee.photo_filename else None
        })

    return result
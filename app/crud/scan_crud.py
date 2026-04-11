from sqlalchemy.orm import Session

from app.models.employee_model import Employee
from app.models.scan_log_model import ScanLog


def get_employee_by_card_id(db: Session, card_id: str, company_id: int):
    return (
        db.query(Employee)
        .filter(Employee.card_id == card_id, Employee.company_id == company_id)
        .first()
    )


def get_last_scan_log(db: Session, employee_id: int, company_id: int):
    return (
        db.query(ScanLog)
        .filter(
            ScanLog.employee_id == employee_id,
            ScanLog.company_id == company_id
        )
        .order_by(ScanLog.scanned_at.desc())
        .first()
    )


def create_scan_log(
    db: Session,
    employee_id: int,
    company_id: int,
    card_id: str,
    event_type: str,
    scan_source: str = "terminal",
    timezone_used: str | None = None,
    timezone_source: str | None = None,
    device_timezone: str | None = None,
    timezone_abbr: str | None = None,
    terminal_id: int | None = None,
    location_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_meters: float | None = None,
    geo_status: str | None = None,
):
    new_log = ScanLog(
        employee_id=employee_id,
        company_id=company_id,
        card_id=card_id,
        event_type=event_type,
        scan_source=scan_source,
        timezone_used=timezone_used,
        timezone_source=timezone_source,
        device_timezone=device_timezone,
        timezone_abbr=timezone_abbr,
        terminal_id=terminal_id,
        location_id=location_id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        geo_status=geo_status,
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log


def get_all_logs(db: Session, company_id: int):
    return (
        db.query(ScanLog)
        .filter(ScanLog.company_id == company_id)
        .order_by(ScanLog.scanned_at.desc())
        .all()
    )


def get_report_logs(
    db: Session,
    company_id: int,
    start_datetime=None,
    end_datetime=None,
    employee_id: int | None = None,
):
    query = (
        db.query(ScanLog, Employee)
        .join(Employee, Employee.id == ScanLog.employee_id)
        .filter(
            ScanLog.company_id == company_id,
            Employee.company_id == company_id,
        )
    )

    if start_datetime is not None:
        query = query.filter(ScanLog.scanned_at >= start_datetime)

    if end_datetime is not None:
        query = query.filter(ScanLog.scanned_at <= end_datetime)

    if employee_id is not None:
        query = query.filter(ScanLog.employee_id == employee_id)

    return query.order_by(ScanLog.scanned_at.desc()).all()


def get_employee_by_id(db: Session, employee_id: int, company_id: int):
    return (
        db.query(Employee)
        .filter(
            Employee.id == employee_id,
            Employee.company_id == company_id
        )
        .first()
    )

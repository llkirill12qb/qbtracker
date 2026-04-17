import asyncio
import logging
import os
import random
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.company_model import Company
from app.models.employee_model import Employee
from app.models.location_model import Location
from app.models.scan_log_model import ScanLog
from app.models.terminal_model import Terminal
from app.services.company_time_service import (
    get_local_date_utc_bounds,
    get_timezone_abbr,
    get_timezone_info,
)


logger = logging.getLogger(__name__)

DEMO_EVENTS_SCAN_SOURCE = "demo_daily"
DEFAULT_DEMO_COMPANY_NAME = "Demo Company"
DEFAULT_MAX_EMPLOYEES = 25
SCHEDULER_INTERVAL_SECONDS = 60 * 60


def is_demo_events_enabled() -> bool:
    return os.getenv("DEMO_EVENTS_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def get_demo_company(db: Session):
    demo_company_id = os.getenv("DEMO_COMPANY_ID", "").strip()
    if demo_company_id:
        try:
            company_id = int(demo_company_id)
        except ValueError:
            logger.warning("Invalid DEMO_COMPANY_ID value: %s", demo_company_id)
        else:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company:
                return company

    demo_company_name = os.getenv("DEMO_COMPANY_NAME", DEFAULT_DEMO_COMPANY_NAME).strip()
    if not demo_company_name:
        return None

    return (
        db.query(Company)
        .filter(func.lower(Company.name) == demo_company_name.lower())
        .first()
    )


def ensure_daily_demo_events(db: Session, target_date: date | None = None):
    if not is_demo_events_enabled():
        return {"created": 0, "skipped": "disabled"}

    company = get_demo_company(db)
    if not company:
        return {"created": 0, "skipped": "demo_company_not_found"}

    timezone_name, company_timezone = get_timezone_info(company.timezone)
    local_date = target_date or datetime.now(company_timezone).date()
    start_utc, end_utc = get_local_date_utc_bounds(local_date, company_timezone)

    if not _try_daily_generation_lock(db, company.id, local_date):
        return {"created": 0, "skipped": "locked"}

    employees = _get_demo_employees(db, company.id)
    if not employees:
        return {"created": 0, "skipped": "no_active_employees"}

    locations = _get_company_locations(db, company.id)
    terminals = _get_company_terminals(db, company.id)
    generator = random.Random(f"{company.id}:{local_date.isoformat()}")
    generation_cutoff_utc = datetime.now(datetime_timezone.utc).replace(tzinfo=None)

    created_logs = []
    for employee in _select_employees_for_day(employees, local_date, generator):
        location = generator.choice(locations) if locations else None
        terminal = _choose_terminal(terminals, location, generator)
        check_in_local, check_out_local = _build_shift_times(local_date, company_timezone, generator)
        latitude, longitude, accuracy_meters, geo_status = _build_geo_values(location, generator)

        candidate_events = [
            ("check-in", _to_utc_naive(check_in_local)),
            ("check-out", _to_utc_naive(check_out_local)),
        ]

        for event_type, scanned_at in candidate_events:
            if scanned_at > generation_cutoff_utc:
                continue

            if _demo_event_exists(db, company.id, employee.id, event_type, start_utc, end_utc):
                continue

            created_logs.append(
                _build_scan_log(
                    employee=employee,
                    company_id=company.id,
                    event_type=event_type,
                    scanned_at=scanned_at,
                    timezone_name=timezone_name,
                    scan_timezone=company_timezone,
                    location=location,
                    terminal=terminal,
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_meters=accuracy_meters,
                    geo_status=geo_status,
                )
            )

    if created_logs:
        db.add_all(created_logs)
        db.commit()

    return {
        "created": len(created_logs),
        "company_id": company.id,
        "local_date": local_date.isoformat(),
    }


async def run_demo_events_scheduler():
    if not is_demo_events_enabled():
        return

    while True:
        try:
            with SessionLocal() as db:
                result = ensure_daily_demo_events(db)
                if result.get("created"):
                    logger.info("Created demo scan events: %s", result)
        except Exception:
            logger.exception("Demo events scheduler failed")

        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)


def _try_daily_generation_lock(db: Session, company_id: int, local_date: date) -> bool:
    lock_key = _build_lock_key(company_id, local_date)
    try:
        return bool(db.execute(text("SELECT pg_try_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key}).scalar())
    except Exception:
        db.rollback()
        return True


def _build_lock_key(company_id: int, local_date: date) -> int:
    date_key = int(local_date.strftime("%Y%m%d"))
    return int(f"{company_id % 100000}{date_key}")


def _get_demo_employees(db: Session, company_id: int):
    max_employees = _get_max_employees()
    return (
        db.query(Employee)
        .filter(
            Employee.company_id == company_id,
            Employee.is_active.is_(True),
            Employee.status == "active",
        )
        .order_by(Employee.id.asc())
        .limit(max_employees)
        .all()
    )


def _demo_event_exists(
    db: Session,
    company_id: int,
    employee_id: int,
    event_type: str,
    start_utc: datetime,
    end_utc: datetime,
) -> bool:
    return (
        db.query(ScanLog.id)
        .filter(
            ScanLog.company_id == company_id,
            ScanLog.employee_id == employee_id,
            ScanLog.event_type == event_type,
            ScanLog.scan_source == DEMO_EVENTS_SCAN_SOURCE,
            ScanLog.scanned_at >= start_utc,
            ScanLog.scanned_at <= end_utc,
        )
        .first()
        is not None
    )


def _get_max_employees() -> int:
    value = os.getenv("DEMO_EVENTS_MAX_EMPLOYEES", str(DEFAULT_MAX_EMPLOYEES)).strip()
    try:
        return max(1, int(value))
    except ValueError:
        return DEFAULT_MAX_EMPLOYEES


def _get_company_locations(db: Session, company_id: int):
    return (
        db.query(Location)
        .filter(Location.company_id == company_id, Location.is_active.is_(True))
        .order_by(Location.id.asc())
        .all()
    )


def _get_company_terminals(db: Session, company_id: int):
    return (
        db.query(Terminal)
        .filter(
            Terminal.company_id == company_id,
            Terminal.is_active.is_(True),
            Terminal.status == "active",
        )
        .order_by(Terminal.id.asc())
        .all()
    )


def _select_employees_for_day(employees, local_date: date, generator: random.Random):
    if len(employees) <= 3:
        return employees

    is_weekend = local_date.weekday() >= 5
    attendance_rate = generator.uniform(0.12, 0.35) if is_weekend else generator.uniform(0.72, 0.95)
    employee_count = max(1, round(len(employees) * attendance_rate))
    return generator.sample(employees, employee_count)


def _choose_terminal(terminals, location, generator: random.Random):
    if not terminals:
        return None

    if location:
        location_terminals = [terminal for terminal in terminals if terminal.location_id == location.id]
        if location_terminals:
            return generator.choice(location_terminals)

    return generator.choice(terminals)


def _build_shift_times(local_date: date, company_timezone, generator: random.Random):
    check_in_minutes = generator.randint(7 * 60 + 35, 9 * 60 + 45)
    shift_minutes = generator.randint(7 * 60 + 15, 9 * 60 + 20)
    break_minutes = generator.choice([0, 15, 30, 45])

    check_in = datetime.combine(local_date, time.min, tzinfo=company_timezone) + timedelta(minutes=check_in_minutes)
    check_out = check_in + timedelta(minutes=shift_minutes + break_minutes)
    return check_in, check_out


def _build_geo_values(location, generator: random.Random):
    if not location or location.latitude is None or location.longitude is None:
        return None, None, None, None

    latitude = location.latitude + generator.uniform(-0.00025, 0.00025)
    longitude = location.longitude + generator.uniform(-0.00025, 0.00025)
    accuracy_meters = round(generator.uniform(6, 28), 1)
    return latitude, longitude, accuracy_meters, "demo"


def _build_scan_log(
    employee: Employee,
    company_id: int,
    event_type: str,
    scanned_at: datetime,
    timezone_name: str,
    scan_timezone,
    location,
    terminal,
    latitude: float | None,
    longitude: float | None,
    accuracy_meters: float | None,
    geo_status: str | None,
):
    return ScanLog(
        employee_id=employee.id,
        company_id=company_id,
        card_id=employee.card_id,
        event_type=event_type,
        scanned_at=scanned_at,
        scan_source=DEMO_EVENTS_SCAN_SOURCE,
        timezone_used=timezone_name,
        timezone_source="company_default",
        device_timezone=timezone_name,
        timezone_abbr=get_timezone_abbr(scanned_at, scan_timezone),
        terminal_id=terminal.id if terminal else None,
        location_id=location.id if location else None,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        geo_status=geo_status,
    )


def _to_utc_naive(value: datetime):
    return value.astimezone(datetime_timezone.utc).replace(tzinfo=None)

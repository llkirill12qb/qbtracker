from datetime import date, datetime, time, timezone as datetime_timezone

from dateutil import tz
from sqlalchemy.orm import Session

from app.models.company_model import Company


DEFAULT_TIMEZONE = "America/New_York"


def get_company_timezone(db: Session, company_id: int):
    company = db.query(Company).filter(Company.id == company_id).first()
    timezone_name = company.timezone if company and company.timezone else DEFAULT_TIMEZONE

    return get_timezone_info(timezone_name)


def get_timezone_info(timezone_name: str | None):
    timezone_name = timezone_name or DEFAULT_TIMEZONE
    company_timezone = tz.gettz(timezone_name)

    if company_timezone is None:
        timezone_name = DEFAULT_TIMEZONE
        company_timezone = tz.gettz(DEFAULT_TIMEZONE) or datetime_timezone.utc

    return timezone_name, company_timezone


def get_local_day_utc_bounds(company_timezone):
    local_today = datetime.now(company_timezone).date()
    return get_local_date_utc_bounds(local_today, company_timezone)


def get_local_date_utc_bounds(local_date: date, company_timezone):
    start_local = datetime.combine(local_date, time.min, tzinfo=company_timezone)
    end_local = datetime.combine(local_date, time.max, tzinfo=company_timezone)

    return (
        start_local.astimezone(datetime_timezone.utc).replace(tzinfo=None),
        end_local.astimezone(datetime_timezone.utc).replace(tzinfo=None),
    )


def format_scan_time(scanned_at: datetime, company_timezone):
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=datetime_timezone.utc)

    return scanned_at.astimezone(company_timezone).isoformat()


def format_scan_time_display(scanned_at: datetime, scan_timezone):
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=datetime_timezone.utc)

    return scanned_at.astimezone(scan_timezone).strftime("%b %d, %Y, %I:%M:%S %p")


def get_timezone_abbr(scanned_at: datetime, scan_timezone):
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=datetime_timezone.utc)

    return scanned_at.astimezone(scan_timezone).tzname()


def get_scan_timezone(log, fallback_timezone_name: str):
    scan_timezone_name = (
        getattr(log, "timezone_used", None)
        or getattr(log, "device_timezone", None)
        or fallback_timezone_name
    )
    return get_timezone_info(scan_timezone_name)


def is_scan_today_in_own_timezone(log, fallback_timezone_name: str):
    _, scan_timezone = get_scan_timezone(log, fallback_timezone_name)
    scanned_at = log.scanned_at

    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=datetime_timezone.utc)

    return scanned_at.astimezone(scan_timezone).date() == datetime.now(scan_timezone).date()


def get_scan_local_date(log, fallback_timezone_name: str):
    _, scan_timezone = get_scan_timezone(log, fallback_timezone_name)
    scanned_at = log.scanned_at

    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=datetime_timezone.utc)

    return scanned_at.astimezone(scan_timezone).date()

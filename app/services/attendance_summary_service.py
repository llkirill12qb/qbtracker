from datetime import datetime, time, timedelta


DEFAULT_SHIFT_START = time(hour=9, minute=0)
DEFAULT_SHIFT_END = time(hour=17, minute=0)
DEFAULT_LATE_GRACE_MINUTES = 15


def parse_schedule_time(value: str | None, fallback: time):
    if not value:
        return fallback
    try:
        hours, minutes = value.split(":")
        return time(hour=int(hours), minute=int(minutes))
    except (TypeError, ValueError):
        return fallback


def _to_local(scan_at: datetime | None, scan_timezone):
    if scan_at is None:
        return None
    return scan_at.astimezone(scan_timezone)


def build_day_attendance_status(
    *,
    first_check_in_at: datetime | None,
    last_check_out_at: datetime | None,
    has_check_in: bool,
    has_check_out: bool,
    last_event_type: str | None,
    scan_timezone,
    use_work_schedules: bool = False,
    shift_start: str | None = None,
    shift_end: str | None = None,
):
    worked_minutes = None
    if first_check_in_at and last_check_out_at and last_check_out_at >= first_check_in_at:
        worked_minutes = int((last_check_out_at - first_check_in_at).total_seconds() // 60)

    if has_check_in and not has_check_out:
        return {"status": "Missing check-out", "worked_minutes": worked_minutes}
    if has_check_out and not has_check_in:
        return {"status": "Missing check-in", "worked_minutes": worked_minutes}
    if last_event_type == "check-in":
        return {"status": "Missing final check-out", "worked_minutes": worked_minutes}
    if worked_minutes is None:
        return {"status": "Incomplete", "worked_minutes": worked_minutes}
    if not use_work_schedules:
        return {"status": "Complete", "worked_minutes": worked_minutes}

    first_local = _to_local(first_check_in_at, scan_timezone)
    last_local = _to_local(last_check_out_at, scan_timezone)

    resolved_shift_start = parse_schedule_time(shift_start, DEFAULT_SHIFT_START)
    resolved_shift_end = parse_schedule_time(shift_end, DEFAULT_SHIFT_END)

    late_cutoff = datetime.combine(first_local.date(), resolved_shift_start, tzinfo=first_local.tzinfo) + timedelta(
        minutes=DEFAULT_LATE_GRACE_MINUTES
    )
    early_leave_cutoff = datetime.combine(last_local.date(), resolved_shift_end, tzinfo=last_local.tzinfo)

    flags = []
    if first_local > late_cutoff:
        flags.append("Late")
    if last_local < early_leave_cutoff:
        flags.append("Early leave")

    if not flags:
        status = "Complete"
    else:
        status = " / ".join(flags)

    return {"status": status, "worked_minutes": worked_minutes}

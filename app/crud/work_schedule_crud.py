from sqlalchemy.orm import Session

from app.models.employee_model import Employee
from app.models.work_schedule_model import WorkSchedule

DEFAULT_WORKDAYS = "0,1,2,3,4"
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def normalize_workdays(workdays: list[int] | str | None):
    if isinstance(workdays, str):
        raw_values = [part.strip() for part in workdays.split(",") if part.strip()]
    elif workdays is None:
        raw_values = []
    else:
        raw_values = [str(value).strip() for value in workdays if str(value).strip()]

    if not raw_values:
        return DEFAULT_WORKDAYS

    normalized = []
    for value in raw_values:
        if not value.isdigit():
            continue
        day_index = int(value)
        if 0 <= day_index <= 6 and day_index not in normalized:
            normalized.append(day_index)

    if not normalized:
        return DEFAULT_WORKDAYS

    normalized.sort()
    return ",".join(str(day_index) for day_index in normalized)


def parse_workdays(workdays: str | None):
    normalized = normalize_workdays(workdays)
    return [int(value) for value in normalized.split(",") if value.strip()]


def format_workdays_label(workdays: str | None):
    indices = parse_workdays(workdays)
    if indices == [0, 1, 2, 3, 4]:
        return "Mon-Fri"
    if indices == [5, 6]:
        return "Sat-Sun"
    return ", ".join(WEEKDAY_LABELS[index] for index in indices)


def get_work_schedules(db: Session, company_id: int):
    schedules = (
        db.query(WorkSchedule)
        .filter(WorkSchedule.company_id == company_id)
        .order_by(WorkSchedule.is_default.desc(), WorkSchedule.name.asc(), WorkSchedule.id.asc())
        .all()
    )
    count_map = get_schedule_employee_counts(db, company_id)
    for schedule in schedules:
        schedule.workdays = normalize_workdays(schedule.workdays)
        schedule.workdays_label = format_workdays_label(schedule.workdays)
        schedule.assigned_employees_count = count_map.get(schedule.id, 0)
    return schedules


def get_work_schedule_by_id(db: Session, schedule_id: int, company_id: int):
    return (
        db.query(WorkSchedule)
        .filter(WorkSchedule.id == schedule_id, WorkSchedule.company_id == company_id)
        .first()
    )


def get_default_work_schedule(db: Session, company_id: int):
    return (
        db.query(WorkSchedule)
        .filter(WorkSchedule.company_id == company_id, WorkSchedule.is_default.is_(True))
        .first()
    )


def ensure_default_work_schedule(db: Session, company_id: int):
    default_schedule = get_default_work_schedule(db, company_id)
    if default_schedule:
        return default_schedule

    default_schedule = WorkSchedule(
        company_id=company_id,
        name="Default Schedule",
        shift_start="09:00",
        shift_end="17:00",
        lunch_start="12:00",
        lunch_end="13:00",
        breaks=None,
        workdays=DEFAULT_WORKDAYS,
        is_default=True,
    )
    db.add(default_schedule)
    db.commit()
    db.refresh(default_schedule)
    return default_schedule


def create_work_schedule(
    db: Session,
    *,
    company_id: int,
    name: str,
    shift_start: str,
    shift_end: str,
    lunch_start: str | None = None,
    lunch_end: str | None = None,
    breaks: str | None = None,
    workdays: str | None = None,
    is_default: bool = False,
):
    schedule = WorkSchedule(
        company_id=company_id,
        name=name,
        shift_start=shift_start,
        shift_end=shift_end,
        lunch_start=lunch_start,
        lunch_end=lunch_end,
        breaks=breaks,
        workdays=normalize_workdays(workdays),
        is_default=is_default,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_work_schedule(
    db: Session,
    schedule: WorkSchedule,
    *,
    name: str,
    shift_start: str,
    shift_end: str,
    lunch_start: str | None = None,
    lunch_end: str | None = None,
    breaks: str | None = None,
    workdays: str | None = None,
):
    schedule.name = name
    schedule.shift_start = shift_start
    schedule.shift_end = shift_end
    schedule.lunch_start = lunch_start
    schedule.lunch_end = lunch_end
    schedule.breaks = breaks
    schedule.workdays = normalize_workdays(workdays)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_work_schedule(db: Session, schedule: WorkSchedule):
    db.delete(schedule)
    db.commit()


def assign_default_schedule_to_unassigned_employees(db: Session, company_id: int, default_schedule_id: int):
    updated = (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.work_schedule_id.is_(None))
        .update({Employee.work_schedule_id: default_schedule_id}, synchronize_session=False)
    )
    db.commit()
    return updated


def assign_schedule_to_employees(db: Session, company_id: int, schedule_id: int, employee_ids: list[int]):
    if not employee_ids:
        return 0

    updated = (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.id.in_(employee_ids))
        .update({Employee.work_schedule_id: schedule_id}, synchronize_session=False)
    )
    db.commit()
    return updated


def reassign_schedule_to_default(db: Session, company_id: int, schedule_id: int, default_schedule_id: int):
    updated = (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.work_schedule_id == schedule_id)
        .update({Employee.work_schedule_id: default_schedule_id}, synchronize_session=False)
    )
    db.commit()
    return updated


def get_schedule_employee_counts(db: Session, company_id: int):
    rows = (
        db.query(Employee.work_schedule_id)
        .filter(Employee.company_id == company_id, Employee.is_active.is_(True))
        .all()
    )
    counts = {}
    for (schedule_id,) in rows:
        if schedule_id is None:
            continue
        counts[schedule_id] = counts.get(schedule_id, 0) + 1
    return counts


def get_employee_schedule_map(db: Session, company_id: int):
    rows = (
        db.query(Employee.id, WorkSchedule.name)
        .outerjoin(WorkSchedule, WorkSchedule.id == Employee.work_schedule_id)
        .filter(Employee.company_id == company_id, Employee.is_active.is_(True))
        .all()
    )
    return {employee_id: schedule_name for employee_id, schedule_name in rows}


def get_schedule_map_by_id(db: Session, company_id: int):
    schedules = get_work_schedules(db, company_id)
    return {schedule.id: schedule for schedule in schedules}

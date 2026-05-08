from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import PERM_MANAGE_COMPANY_SETTINGS, PLATFORM_ROLES
from app.core.security import require_permission
from app.crud.company_crud import get_company_by_id, update_company_profile
from app.crud.employee_crud import get_all_employees
from app.crud.work_schedule_crud import (
    assign_schedule_to_employees,
    assign_default_schedule_to_unassigned_employees,
    create_work_schedule,
    delete_work_schedule,
    ensure_default_work_schedule,
    format_workdays_label,
    get_employee_schedule_map,
    get_default_work_schedule,
    get_work_schedule_by_id,
    get_work_schedules,
    normalize_workdays,
    reassign_schedule_to_default,
    update_work_schedule,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
WEEKDAY_OPTIONS = [
    (0, "Mon"),
    (1, "Tue"),
    (2, "Wed"),
    (3, "Thu"),
    (4, "Fri"),
    (5, "Sat"),
    (6, "Sun"),
]


def redirect_with_query(request: Request, **params):
    if request.session.get("role") in PLATFORM_ROLES:
        params["zone"] = "platform"

    return RedirectResponse(url=f"/company/schedules?{urlencode(params)}", status_code=303)


def get_company_context_or_404(request: Request, db: Session):
    company_id = get_current_company_id(request)
    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company_id, company


def normalize_time_value(value: str | None):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) != 5 or value[2] != ":":
        raise HTTPException(status_code=400, detail="Invalid time format")
    hours, minutes = value.split(":")
    if not (hours.isdigit() and minutes.isdigit()):
        raise HTTPException(status_code=400, detail="Invalid time format")
    hour_value = int(hours)
    minute_value = int(minutes)
    if hour_value < 0 or hour_value > 23 or minute_value < 0 or minute_value > 59:
        raise HTTPException(status_code=400, detail="Invalid time format")
    return f"{hour_value:02d}:{minute_value:02d}"


@router.get("/company/schedules", response_class=HTMLResponse)
def company_schedules_page(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_COMPANY_SETTINGS)
    company_id, company = get_company_context_or_404(request, db)
    default_schedule = ensure_default_work_schedule(db, company_id)
    assign_default_schedule_to_unassigned_employees(db, company_id, default_schedule.id)
    schedules = get_work_schedules(db, company_id)
    employees = sorted(
        get_all_employees(db, company_id),
        key=lambda employee: (employee.full_name or "").lower(),
    )
    employee_schedule_map = get_employee_schedule_map(db, company_id)

    return templates.TemplateResponse(
        "company_schedules.html",
        {
            "request": request,
            "company": company,
            "schedules": schedules,
            "employees": employees,
            "employee_schedule_map": employee_schedule_map,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
            "default_schedule_id": default_schedule.id,
            "weekday_options": WEEKDAY_OPTIONS,
        },
    )


@router.post("/company/schedules/settings")
def update_schedule_usage_setting(
    request: Request,
    use_work_schedules: str = Form(default="off"),
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_MANAGE_COMPANY_SETTINGS)
    _, company = get_company_context_or_404(request, db)
    update_company_profile(
        db,
        company,
        use_work_schedules=use_work_schedules == "on",
    )
    message = "Schedule-based attendance enabled" if company.use_work_schedules else "Schedule-based attendance disabled"
    return redirect_with_query(request, message=message)


@router.post("/company/schedules")
def save_company_schedule(
    request: Request,
    action_mode: str = Form(default="save"),
    schedule_id: str = Form(default=""),
    name: str = Form(default=""),
    shift_start: str = Form(default=""),
    shift_end: str = Form(default=""),
    lunch_start: str = Form(default=""),
    lunch_end: str = Form(default=""),
    breaks: str = Form(default=""),
    workdays: list[int] = Form(default=[]),
    employee_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_MANAGE_COMPANY_SETTINGS)
    company_id, _ = get_company_context_or_404(request, db)
    selected_employee_ids = [int(employee_id) for employee_id in employee_ids]
    default_schedule = ensure_default_work_schedule(db, company_id)

    if action_mode == "apply":
        if not schedule_id.strip():
            return redirect_with_query(request, error="Choose an existing schedule before applying it")

        schedule = get_work_schedule_by_id(db, int(schedule_id), company_id)
        if not schedule:
            return redirect_with_query(request, error="Schedule not found")

        assigned_count = assign_schedule_to_employees(db, company_id, schedule.id, selected_employee_ids)
        if not assigned_count:
            return redirect_with_query(request, error="Select at least one employee to apply the schedule")

        return redirect_with_query(
            request,
            message=f'Schedule "{schedule.name}" applied to {assigned_count} employees',
        )

    name = name.strip()
    if not name:
        return redirect_with_query(request, error="Schedule name is required")
    if not shift_start.strip() or not shift_end.strip():
        return redirect_with_query(request, error="Shift start and shift end are required")

    normalized_shift_start = normalize_time_value(shift_start)
    normalized_shift_end = normalize_time_value(shift_end)
    normalized_lunch_start = normalize_time_value(lunch_start)
    normalized_lunch_end = normalize_time_value(lunch_end)
    breaks_value = breaks.strip() or None
    normalized_workdays = normalize_workdays(workdays)

    if schedule_id.strip():
        schedule = get_work_schedule_by_id(db, int(schedule_id), company_id)
        if not schedule:
            return redirect_with_query(request, error="Schedule not found")
        schedule = update_work_schedule(
            db,
            schedule,
            name=name,
            shift_start=normalized_shift_start,
            shift_end=normalized_shift_end,
            lunch_start=normalized_lunch_start,
            lunch_end=normalized_lunch_end,
            breaks=breaks_value,
            workdays=normalized_workdays,
        )
        message = "Schedule updated"
    else:
        schedule = create_work_schedule(
            db,
            company_id=company_id,
            name=name,
            shift_start=normalized_shift_start,
            shift_end=normalized_shift_end,
            lunch_start=normalized_lunch_start,
            lunch_end=normalized_lunch_end,
            breaks=breaks_value,
            workdays=normalized_workdays,
        )
        message = "Schedule created"

    if schedule.id == default_schedule.id:
        message += " (default)"
    message += f" • {format_workdays_label(schedule.workdays)}"

    return redirect_with_query(request, message=message)


@router.post("/company/schedules/{schedule_id}/delete")
def remove_company_schedule(
    schedule_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_MANAGE_COMPANY_SETTINGS)
    company_id, _ = get_company_context_or_404(request, db)
    default_schedule = ensure_default_work_schedule(db, company_id)
    schedule = get_work_schedule_by_id(db, schedule_id, company_id)

    if not schedule:
        return redirect_with_query(request, error="Schedule not found")
    if schedule.is_default:
        return redirect_with_query(request, error="Default schedule cannot be deleted")

    reassigned_count = reassign_schedule_to_default(db, company_id, schedule.id, default_schedule.id)
    delete_work_schedule(db, schedule)

    message = "Schedule deleted"
    if reassigned_count:
        message += f" and {reassigned_count} employees moved to default schedule"
    return redirect_with_query(request, message=message)

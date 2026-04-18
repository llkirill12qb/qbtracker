from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import PLATFORM_ROLES
from app.core.security import require_company_workspace_access
from app.crud.company_crud import get_company_by_id
from app.crud.location_crud import get_location_by_id, get_locations
from app.crud.terminal_crud import (
    create_terminal,
    get_terminal_by_id,
    get_terminals,
    update_terminal,
)
from app.services.timezone_options_service import get_timezone_options

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def redirect_with_query(request: Request, **params):
    if request.session.get("role") in PLATFORM_ROLES:
        params["zone"] = "platform"

    return RedirectResponse(url=f"/company/terminals?{urlencode(params)}", status_code=303)


def normalize_optional(value: str | None):
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None


def normalize_location_id(db: Session, company_id: int, location_id: str | None):
    clean_value = normalize_optional(location_id)
    if clean_value is None:
        return None

    try:
        parsed_location_id = int(clean_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid location")

    location = get_location_by_id(db, parsed_location_id, company_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    return parsed_location_id


def get_company_context_or_404(request: Request, db: Session):
    company_id = get_current_company_id(request)
    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company_id, company


@router.get("/company/terminals", response_class=HTMLResponse)
def company_terminals_page(request: Request, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id, company = get_company_context_or_404(request, db)
    terminals = get_terminals(db, company_id, include_inactive=True)
    locations = get_locations(db, company_id, include_inactive=True)
    location_names_by_id = {location.id: location.name for location in locations}

    return templates.TemplateResponse(
        "company_terminals.html",
        {
            "request": request,
            "company": company,
            "terminals": terminals,
            "locations": locations,
            "location_names_by_id": location_names_by_id,
            "timezone_options": get_timezone_options(company.timezone),
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/company/terminals")
def create_company_terminal(
    request: Request,
    name: str = Form(...),
    location_id: str = Form(default=""),
    device_name: str = Form(default=""),
    timezone: str = Form(default=""),
    status: str = Form(default="active"),
    is_active: str = Form(default="off"),
    db: Session = Depends(get_db),
):
    require_company_workspace_access(request)
    company_id, _ = get_company_context_or_404(request, db)
    name = name.strip()

    if not name:
        return redirect_with_query(request, error="Terminal name is required")

    create_terminal(
        db=db,
        company_id=company_id,
        name=name,
        location_id=normalize_location_id(db, company_id, location_id),
        device_name=normalize_optional(device_name),
        timezone=normalize_optional(timezone),
        status=status.strip() or "active",
        is_active=is_active == "on",
    )

    return redirect_with_query(request, message="Terminal created")


@router.post("/company/terminals/{terminal_id}/update")
def update_company_terminal(
    terminal_id: int,
    request: Request,
    name: str = Form(...),
    location_id: str = Form(default=""),
    device_name: str = Form(default=""),
    timezone: str = Form(default=""),
    status: str = Form(default="active"),
    is_active: str = Form(default="off"),
    db: Session = Depends(get_db),
):
    require_company_workspace_access(request)
    company_id, _ = get_company_context_or_404(request, db)
    terminal = get_terminal_by_id(db, terminal_id, company_id)

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    name = name.strip()
    if not name:
        return redirect_with_query(request, error="Terminal name is required")

    update_terminal(
        db,
        terminal,
        name=name,
        location_id=normalize_location_id(db, company_id, location_id),
        device_name=normalize_optional(device_name),
        timezone=normalize_optional(timezone),
        status=status.strip() or "active",
        is_active=is_active == "on",
    )

    return redirect_with_query(request, message="Terminal updated")

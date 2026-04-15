from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.security import require_company_workspace_access
from app.crud.company_crud import get_company_by_id
from app.crud.location_crud import (
    create_location,
    get_location_by_id,
    get_locations,
    update_location,
)
from app.services.timezone_options_service import get_timezone_options

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def redirect_with_query(**params):
    return RedirectResponse(url=f"/company/locations?{urlencode(params)}", status_code=303)


def normalize_optional(value: str | None):
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None


def normalize_float(value: str | None):
    clean_value = normalize_optional(value)
    if clean_value is None:
        return None

    try:
        return float(clean_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid number format",
        )


def get_company_context_or_404(request: Request, db: Session):
    company_id = get_current_company_id(request)
    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company_id, company


@router.get("/company/locations", response_class=HTMLResponse)
def company_locations_page(request: Request, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id, company = get_company_context_or_404(request, db)
    locations = get_locations(db, company_id, include_inactive=True)

    return templates.TemplateResponse(
        "company_locations.html",
        {
            "request": request,
            "company": company,
            "locations": locations,
            "timezone_options": get_timezone_options(company.timezone),
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/company/locations")
def create_company_location(
    request: Request,
    name: str = Form(...),
    timezone: str = Form(default="America/New_York"),
    country: str = Form(default=""),
    state: str = Form(default=""),
    city: str = Form(default=""),
    address_line1: str = Form(default=""),
    address_line2: str = Form(default=""),
    postal_code: str = Form(default=""),
    latitude: str = Form(default=""),
    longitude: str = Form(default=""),
    geo_radius_meters: str = Form(default=""),
    is_active: str = Form(default="off"),
    db: Session = Depends(get_db),
):
    require_company_workspace_access(request)
    company_id, _ = get_company_context_or_404(request, db)
    name = name.strip()

    if not name:
        return redirect_with_query(error="Location name is required")

    create_location(
        db=db,
        company_id=company_id,
        name=name,
        timezone=timezone.strip() or "America/New_York",
        country=normalize_optional(country),
        state=normalize_optional(state),
        city=normalize_optional(city),
        address_line1=normalize_optional(address_line1),
        address_line2=normalize_optional(address_line2),
        postal_code=normalize_optional(postal_code),
        latitude=normalize_float(latitude),
        longitude=normalize_float(longitude),
        geo_radius_meters=normalize_float(geo_radius_meters),
        is_active=is_active == "on",
    )

    return redirect_with_query(message="Location created")


@router.post("/company/locations/{location_id}/update")
def update_company_location(
    location_id: int,
    request: Request,
    name: str = Form(...),
    timezone: str = Form(default="America/New_York"),
    country: str = Form(default=""),
    state: str = Form(default=""),
    city: str = Form(default=""),
    address_line1: str = Form(default=""),
    address_line2: str = Form(default=""),
    postal_code: str = Form(default=""),
    latitude: str = Form(default=""),
    longitude: str = Form(default=""),
    geo_radius_meters: str = Form(default=""),
    is_active: str = Form(default="off"),
    db: Session = Depends(get_db),
):
    require_company_workspace_access(request)
    company_id, _ = get_company_context_or_404(request, db)
    location = get_location_by_id(db, location_id, company_id)

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    name = name.strip()
    if not name:
        return redirect_with_query(error="Location name is required")

    update_location(
        db,
        location,
        name=name,
        timezone=timezone.strip() or "America/New_York",
        country=normalize_optional(country),
        state=normalize_optional(state),
        city=normalize_optional(city),
        address_line1=normalize_optional(address_line1),
        address_line2=normalize_optional(address_line2),
        postal_code=normalize_optional(postal_code),
        latitude=normalize_float(latitude),
        longitude=normalize_float(longitude),
        geo_radius_meters=normalize_float(geo_radius_meters),
        is_active=is_active == "on",
    )

    return redirect_with_query(message="Location updated")

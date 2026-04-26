from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import PLATFORM_ROLES
from app.core.roles import PERM_MANAGE_COMPANY_SETTINGS
from app.core.security import require_permission
from app.crud.company_contact_crud import get_primary_company_contact, upsert_primary_company_contact
from app.crud.company_crud import get_company_by_id, update_company_profile
from app.services.timezone_options_service import get_timezone_options

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_current_company_or_404(request: Request, db: Session):
    company_id = get_current_company_id(request)
    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return company


@router.get("/company/settings", response_class=HTMLResponse)
def company_settings_page(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_COMPANY_SETTINGS)
    company = get_current_company_or_404(request, db)
    primary_contact = get_primary_company_contact(db, company.id)

    return templates.TemplateResponse(
        "company_settings.html",
        {
            "request": request,
            "company": company,
            "primary_contact": primary_contact,
            "timezone_options": get_timezone_options(company.timezone),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("/company/settings")
def update_company_settings(
    request: Request,
    name: str = Form(...),
    legal_name: str = Form(default=""),
    email: str = Form(default=""),
    phone: str = Form(default=""),
    website: str = Form(default=""),
    country: str = Form(default=""),
    state: str = Form(default=""),
    city: str = Form(default=""),
    address_line1: str = Form(default=""),
    address_line2: str = Form(default=""),
    postal_code: str = Form(default=""),
    timezone: str = Form(default="America/New_York"),
    status: str = Form(default="active"),
    primary_contact_name: str = Form(default=""),
    primary_contact_position: str = Form(default=""),
    primary_contact_email: str = Form(default=""),
    primary_contact_phone: str = Form(default=""),
    primary_contact_notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_permission(request, PERM_MANAGE_COMPANY_SETTINGS)
    company = get_current_company_or_404(request, db)

    update_company_profile(
        db,
        company,
        name=name.strip(),
        legal_name=legal_name.strip() or None,
        email=email.strip() or None,
        phone=phone.strip() or None,
        website=website.strip() or None,
        country=country.strip() or None,
        state=state.strip() or None,
        city=city.strip() or None,
        address_line1=address_line1.strip() or None,
        address_line2=address_line2.strip() or None,
        postal_code=postal_code.strip() or None,
        timezone=timezone.strip() or "America/New_York",
        status=status.strip() or "active",
    )
    upsert_primary_company_contact(
        db,
        company.id,
        full_name=primary_contact_name,
        position=primary_contact_position,
        email=primary_contact_email,
        phone=primary_contact_phone,
        notes=primary_contact_notes,
    )

    zone_query = "&zone=platform" if request.session.get("role") in PLATFORM_ROLES else ""
    return RedirectResponse(url=f"/company/settings?saved=1{zone_query}", status_code=303)

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.core.company_context import set_selected_company_id
from app.core.database import get_db
from app.core.roles import ROLE_SUPER_ADMIN
from app.core.security import require_platform_access
from app.core.zoned_sessions import ZONE_PLATFORM, write_zone_session
from app.crud.company_crud import (
    archive_company,
    create_company,
    delete_company_cascade,
    get_all_companies,
    get_company_by_id,
    restore_company,
)
from app.services.photo_service import delete_company_upload_dir
from app.services.timezone_options_service import get_timezone_options

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def require_platform_user(request: Request):
    return require_platform_access(request)


def normalize_optional(value: str | None):
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None


def redirect_platform_companies(request: Request, **params):
    role_context = request.session.get("role")
    if role_context:
        params["role_context"] = role_context

    return RedirectResponse(url=f"/platform/companies?{urlencode(params)}", status_code=303)


def redirect_platform_archive(request: Request, **params):
    role_context = request.session.get("role")
    if role_context:
        params["role_context"] = role_context

    return RedirectResponse(url=f"/platform/companies/archive?{urlencode(params)}", status_code=303)


@router.get("/platform/companies", response_class=HTMLResponse)
def platform_companies_page(
    request: Request,
    q: str = Query(default=""),
    sort: str = Query(default="id"),
    direction: str = Query(default="asc"),
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    sort = sort if sort in {"id", "name"} else "id"
    direction = direction if direction in {"asc", "desc"} else "asc"
    search = q.strip()
    companies = get_all_companies(db, search=search, sort_by=sort, direction=direction, status="non_archived")

    return templates.TemplateResponse(
        "platform_companies.html",
        {
            "request": request,
            "user": user,
            "companies": companies,
            "q": search,
            "sort": sort,
            "direction": direction,
            "selected_company_id": request.session.get("selected_company_id"),
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/platform/companies/new", response_class=HTMLResponse)
def new_platform_company_page(request: Request, db: Session = Depends(get_db)):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can create companies")

    return templates.TemplateResponse(
        "platform_company_create.html",
        {
            "request": request,
            "user": user,
            "timezone_options": get_timezone_options("America/New_York"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/platform/companies/delete", response_class=HTMLResponse)
def delete_platform_company_page(
    request: Request,
    q: str = Query(default=""),
    sort: str = Query(default="id"),
    direction: str = Query(default="asc"),
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can delete companies")

    sort = sort if sort in {"id", "name"} else "id"
    direction = direction if direction in {"asc", "desc"} else "asc"
    search = q.strip()
    companies = get_all_companies(db, search=search, sort_by=sort, direction=direction, status="non_archived")

    return templates.TemplateResponse(
        "platform_company_delete.html",
        {
            "request": request,
            "user": user,
            "companies": companies,
            "q": search,
            "sort": sort,
            "direction": direction,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/platform/companies/archive", response_class=HTMLResponse)
def archived_platform_companies_page(
    request: Request,
    q: str = Query(default=""),
    sort: str = Query(default="id"),
    direction: str = Query(default="asc"),
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can manage archived companies")

    sort = sort if sort in {"id", "name"} else "id"
    direction = direction if direction in {"asc", "desc"} else "asc"
    search = q.strip()
    companies = get_all_companies(db, search=search, sort_by=sort, direction=direction, status="archived")

    return templates.TemplateResponse(
        "platform_company_archive.html",
        {
            "request": request,
            "user": user,
            "companies": companies,
            "q": search,
            "sort": sort,
            "direction": direction,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/platform/companies")
def create_platform_company(
    request: Request,
    name: str = Form(...),
    legal_name: str = Form(default=""),
    email: str = Form(default=""),
    phone: str = Form(default=""),
    timezone: str = Form(default="America/New_York"),
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can create companies")

    company_name = name.strip()
    timezone_name = timezone.strip() or "America/New_York"

    if not company_name:
        role_context = request.session.get("role")
        query = f"?error=Company+name+is+required&role_context={role_context}" if role_context else "?error=Company+name+is+required"
        return RedirectResponse(url=f"/platform/companies/new{query}", status_code=303)

    create_company(
        db,
        name=company_name,
        legal_name=normalize_optional(legal_name),
        email=normalize_optional(email),
        phone=normalize_optional(phone),
        timezone=timezone_name,
        status="active",
    )
    return redirect_platform_companies(request, message="Company created")


@router.post("/platform/companies/{company_id}/archive")
def archive_platform_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can delete companies")

    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.status == "archived":
        return redirect_platform_companies(request, error="Company is already archived")

    archive_company(db, company)

    if request.session.get("selected_company_id") == company_id:
        request.session.pop("selected_company_id", None)

    response = redirect_platform_companies(request, message="Company moved to archive")
    write_zone_session(response, ZONE_PLATFORM, request.session)
    return response


@router.post("/platform/companies/{company_id}/restore")
def restore_platform_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can restore companies")

    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.status != "archived":
        response = redirect_platform_archive(request, error="Only archived companies can be restored")
        write_zone_session(response, ZONE_PLATFORM, request.session)
        return response

    restore_company(db, company)
    response = redirect_platform_archive(request, message="Company restored")
    write_zone_session(response, ZONE_PLATFORM, request.session)
    return response


@router.post("/platform/companies/{company_id}/delete")
def delete_archived_platform_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    if user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admin can delete companies")

    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.status != "archived":
        response = redirect_platform_archive(request, error="Only archived companies can be deleted permanently")
        write_zone_session(response, ZONE_PLATFORM, request.session)
        return response

    delete_company_cascade(db, company)
    delete_company_upload_dir(company_id)

    if request.session.get("selected_company_id") == company_id:
        request.session.pop("selected_company_id", None)

    response = redirect_platform_archive(request, message="Company deleted permanently")
    write_zone_session(response, ZONE_PLATFORM, request.session)
    return response


@router.post("/platform/companies/{company_id}/open")
def open_company_context(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_platform_user(request)

    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.status == "archived":
        response = redirect_platform_companies(request, error="Archived company cannot be opened")
        write_zone_session(response, ZONE_PLATFORM, request.session)
        return response

    set_selected_company_id(request, company_id)
    response = RedirectResponse(
        url=f"/dashboard?zone=platform&role_context={request.session.get('role')}",
        status_code=303,
    )
    write_zone_session(response, ZONE_PLATFORM, request.session)
    return response

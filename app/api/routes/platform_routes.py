from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import set_selected_company_id
from app.core.database import get_db
from app.core.roles import PLATFORM_ROLES
from app.core.security import get_current_session_user
from app.crud.company_crud import get_all_companies, get_company_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def require_platform_user(request: Request):
    user = get_current_session_user(request)
    if user.get("role") not in PLATFORM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform access required",
        )

    return user


@router.get("/platform/companies", response_class=HTMLResponse)
def platform_companies_page(
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_platform_user(request)
    companies = get_all_companies(db)

    return templates.TemplateResponse(
        "platform_companies.html",
        {
            "request": request,
            "user": user,
            "companies": companies,
            "selected_company_id": request.session.get("selected_company_id"),
        },
    )


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

    set_selected_company_id(request, company_id)
    return RedirectResponse(url="/dashboard", status_code=303)

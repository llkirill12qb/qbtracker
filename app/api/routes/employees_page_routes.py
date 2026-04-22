from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import PERM_MANAGE_EMPLOYEES
from app.core.security import require_permission
from app.crud.company_crud import get_company_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/employees-page", response_class=HTMLResponse)
def employees_page(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company = get_company_by_id(db, get_current_company_id(request))
    return templates.TemplateResponse(
        "employees_page.html",
        {"request": request, "company": company}
    )


@router.get("/employees-archive", response_class=HTMLResponse)
def employees_archive_page(request: Request, db: Session = Depends(get_db)):
    require_permission(request, PERM_MANAGE_EMPLOYEES)
    company = get_company_by_id(db, get_current_company_id(request))
    return templates.TemplateResponse(
        "employees_archive.html",
        {"request": request, "company": company}
    )

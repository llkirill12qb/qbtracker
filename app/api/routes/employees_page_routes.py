from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.security import require_company_workspace_access

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/employees-page", response_class=HTMLResponse)
def employees_page(request: Request):
    require_company_workspace_access(request)
    return templates.TemplateResponse(
        "employees_page.html",
        {"request": request}
    )


@router.get("/employees-archive", response_class=HTMLResponse)
def employees_archive_page(request: Request):
    require_company_workspace_access(request)
    return templates.TemplateResponse(
        "employees_archive.html",
        {"request": request}
    )

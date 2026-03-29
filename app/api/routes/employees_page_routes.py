from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.models.employee_model import Employee

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/employees-page", response_class=HTMLResponse)
def employees_page(request: Request):
    return templates.TemplateResponse(
        "employees_page.html",
        {"request": request}
    )
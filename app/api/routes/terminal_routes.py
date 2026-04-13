from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.security import require_terminal_access

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/terminal", response_class=HTMLResponse)
def terminal_page(request: Request):
    require_terminal_access(request)
    return templates.TemplateResponse("terminal.html", {"request": request})


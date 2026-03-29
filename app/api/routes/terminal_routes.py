from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/terminal", response_class=HTMLResponse)
def terminal_page(request: Request):
    return templates.TemplateResponse("terminal.html", {"request": request})


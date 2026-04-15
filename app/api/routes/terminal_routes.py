from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import ROLE_TERMINAL_USER
from app.core.security import require_terminal_access
from app.crud.terminal_crud import get_terminals

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/terminal", response_class=HTMLResponse)
def terminal_page(request: Request, db: Session = Depends(get_db)):
    require_terminal_access(request)
    terminals = []

    if request.session.get("role") != ROLE_TERMINAL_USER:
        company_id = get_current_company_id(request)
        terminals = get_terminals(db, company_id, include_inactive=False)

    return templates.TemplateResponse(
        "terminal.html",
        {
            "request": request,
            "terminals": terminals,
        },
    )


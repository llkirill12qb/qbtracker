from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import ROLE_TERMINAL_USER
from app.core.security import require_terminal_access
from app.crud.terminal_crud import get_terminal_by_id, get_terminals
from app.models.company_model import Company
from app.services.company_time_service import get_company_timezone

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/terminal", response_class=HTMLResponse)
def terminal_page(request: Request, db: Session = Depends(get_db)):
    require_terminal_access(request)
    company_id = get_current_company_id(request)
    company = db.query(Company).filter(Company.id == company_id).first()
    company_timezone_name, _ = get_company_timezone(db, company_id)
    active_terminal = None
    terminals = []

    if request.session.get("role") != ROLE_TERMINAL_USER:
        terminals = get_terminals(db, company_id, include_inactive=False)
        active_terminal = terminals[0] if terminals else None
    else:
        terminal_id = request.session.get("terminal_id")
        if terminal_id is not None:
            try:
                active_terminal = get_terminal_by_id(db, int(terminal_id), company_id)
            except (TypeError, ValueError):
                active_terminal = None

    return templates.TemplateResponse(
        "terminal.html",
        {
            "request": request,
            "terminals": terminals,
            "active_company": company,
            "company_timezone": company_timezone_name,
            "active_terminal": active_terminal,
        },
    )


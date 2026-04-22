from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.company_context import set_selected_company_id
from app.core.database import get_db
from app.core.security import require_platform_access
from app.core.zoned_sessions import ZONE_PLATFORM, write_zone_session
from app.crud.company_crud import get_all_companies, get_company_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def require_platform_user(request: Request):
    return require_platform_access(request)


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
    companies = get_all_companies(db, search=search, sort_by=sort, direction=direction)

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
    response = RedirectResponse(
        url=f"/dashboard?zone=platform&role_context={request.session.get('role')}",
        status_code=303,
    )
    write_zone_session(response, ZONE_PLATFORM, request.session)
    return response

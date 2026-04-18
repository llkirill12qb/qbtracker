from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.company_context import (
    get_current_session_user_or_401,
    is_platform_user,
    set_selected_company_id,
)
from app.core.database import get_db
from app.core.zoned_sessions import ZONE_PLATFORM, write_zone_session
from app.crud.company_crud import get_company_by_id

router = APIRouter()


@router.post("/api/context/company/{company_id}")
def select_company_context(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_session_user_or_401(request)

    if not is_platform_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform users can switch company context",
        )

    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    set_selected_company_id(request, company_id)

    response = JSONResponse(
        {
            "selected_company_id": company_id,
            "company_name": company.name,
        }
    )
    write_zone_session(response, ZONE_PLATFORM, request.session)
    return response

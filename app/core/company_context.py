from fastapi import HTTPException, Request, status

from app.core.auth import get_session_user
from app.core.roles import PLATFORM_ROLES


DEFAULT_SELECTED_COMPANY_ID = 1


def get_current_session_user_or_401(request: Request):
    user = get_session_user(request.session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return user


def is_platform_user(user: dict) -> bool:
    return user.get("role") in PLATFORM_ROLES


def get_selected_company_id(request: Request) -> int | None:
    selected_company_id = request.session.get("selected_company_id")

    if selected_company_id is None:
        return None

    try:
        return int(selected_company_id)
    except (TypeError, ValueError):
        return None


def set_selected_company_id(request: Request, company_id: int):
    request.session["selected_company_id"] = int(company_id)


def get_current_company_id(request: Request) -> int:
    user = get_current_session_user_or_401(request)

    if is_platform_user(user):
        return get_selected_company_id(request) or DEFAULT_SELECTED_COMPANY_ID

    company_id = user.get("company_id")
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to a company",
        )

    return int(company_id)


def get_current_company_scope(request: Request):
    user = get_current_session_user_or_401(request)
    company_id = get_current_company_id(request)

    return {
        "company_id": company_id,
        "is_platform_user": is_platform_user(user),
        "user": user,
    }

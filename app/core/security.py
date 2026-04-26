from fastapi import HTTPException, Request, status

from app.core.auth import get_session_user
from app.core.database import SessionLocal
from app.core.roles import (
    PERM_MANAGE_EMPLOYEES,
    PERM_MANAGE_PLATFORM,
    PERM_MANAGE_USERS,
    PERM_USE_TERMINAL,
    PERM_VIEW_DASHBOARD,
    PLATFORM_ROLES,
    ROLE_PERMISSIONS,
)
from app.models.company_model import Company


def get_current_session_user(request: Request):
    user = get_session_user(request.session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return user


def require_roles(*allowed_roles: str):
    def dependency(request: Request):
        user = get_current_session_user(request)
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return dependency


def require_current_user_role(request: Request, allowed_roles: set[str] | tuple[str, ...]):
    user = get_current_session_user(request)
    if user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


def has_permission(user: dict, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.get("role"), set())


def ensure_company_workspace_is_active(request: Request, user: dict, permission: str):
    if permission == PERM_MANAGE_PLATFORM:
        return

    role = user.get("role")
    company_id = request.session.get("selected_company_id") if role in PLATFORM_ROLES else user.get("company_id")
    if company_id is None:
        return

    try:
        company_id = int(company_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid company context",
        )

    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
    finally:
        db.close()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    if company.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Archived company is not available in this workspace",
        )


def require_permission(request: Request, permission: str):
    user = get_current_session_user(request)
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    ensure_company_workspace_is_active(request, user, permission)
    return user


def require_company_workspace_access(request: Request):
    return require_permission(request, PERM_VIEW_DASHBOARD)


def require_user_management_access(request: Request):
    return require_permission(request, PERM_MANAGE_USERS)


def require_terminal_access(request: Request):
    return require_permission(request, PERM_USE_TERMINAL)


def require_platform_access(request: Request):
    return require_permission(request, PERM_MANAGE_PLATFORM)


def require_employee_management_access(request: Request):
    return require_permission(request, PERM_MANAGE_EMPLOYEES)

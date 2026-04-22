from fastapi import HTTPException, Request, status

from app.core.auth import get_session_user
from app.core.roles import (
    PERM_MANAGE_EMPLOYEES,
    PERM_MANAGE_PLATFORM,
    PERM_MANAGE_USERS,
    PERM_USE_TERMINAL,
    PERM_VIEW_DASHBOARD,
    ROLE_PERMISSIONS,
)


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


def require_permission(request: Request, permission: str):
    user = get_current_session_user(request)
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

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

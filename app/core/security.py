from fastapi import HTTPException, Request, status

from app.core.auth import get_session_user
from app.core.roles import COMPANY_WORKSPACE_ROLES, TERMINAL_ACCESS_ROLES, USER_MANAGEMENT_ROLES


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


def require_company_workspace_access(request: Request):
    return require_current_user_role(request, COMPANY_WORKSPACE_ROLES)


def require_user_management_access(request: Request):
    return require_current_user_role(request, USER_MANAGEMENT_ROLES)


def require_terminal_access(request: Request):
    return require_current_user_role(request, TERMINAL_ACCESS_ROLES)

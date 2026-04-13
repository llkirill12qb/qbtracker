from fastapi import HTTPException, Request, status

from app.core.auth import get_session_user


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

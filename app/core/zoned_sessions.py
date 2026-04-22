from itsdangerous import BadSignature, URLSafeSerializer
from starlette.requests import Request
from starlette.responses import Response

from app.core.auth import SESSION_SECRET
from app.core.roles import (
    ALL_ROLES,
    PLATFORM_ROLES,
    ROLE_COMPANY_ADMIN,
    ROLE_COMPANY_OWNER,
    ROLE_EMPLOYEE,
    ROLE_SITE_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_TERMINAL_USER,
)


PLATFORM_SESSION_COOKIE = "qbtracker_platform_session"
COMPANY_SESSION_COOKIE = "qbtracker_company_session"
TERMINAL_SESSION_COOKIE = "qbtracker_terminal_session"
EMPLOYEE_SESSION_COOKIE = "qbtracker_employee_session"

ROLE_SESSION_COOKIE_NAMES = {
    ROLE_SUPER_ADMIN: "qbtracker_super_admin_session",
    ROLE_SITE_ADMIN: "qbtracker_site_admin_session",
    ROLE_COMPANY_OWNER: "qbtracker_company_owner_session",
    ROLE_COMPANY_ADMIN: "qbtracker_company_admin_session",
    ROLE_TERMINAL_USER: "qbtracker_terminal_user_session",
    ROLE_EMPLOYEE: "qbtracker_employee_session_v2",
}

ZONE_PLATFORM = "platform"
ZONE_COMPANY = "company"
ZONE_TERMINAL = "terminal"
ZONE_EMPLOYEE = "employee"

ZONE_COOKIE_NAMES = {
    ZONE_PLATFORM: PLATFORM_SESSION_COOKIE,
    ZONE_COMPANY: COMPANY_SESSION_COOKIE,
    ZONE_TERMINAL: TERMINAL_SESSION_COOKIE,
    ZONE_EMPLOYEE: EMPLOYEE_SESSION_COOKIE,
}

serializer = URLSafeSerializer(SESSION_SECRET, salt="qbtracker-zoned-session")


def build_session_payload(
    *,
    user_id,
    username: str,
    role: str,
    company_id=None,
    location_id=None,
    terminal_id=None,
    auth_source: str,
):
    return {
        "authenticated": True,
        "user_id": user_id,
        "username": username,
        "role": role,
        "company_id": company_id,
        "location_id": location_id,
        "terminal_id": terminal_id,
        "auth_source": auth_source,
    }


def get_zone_for_role(role: str) -> str:
    if role in PLATFORM_ROLES:
        return ZONE_PLATFORM
    if role == ROLE_TERMINAL_USER:
        return ZONE_TERMINAL
    if role == ROLE_EMPLOYEE:
        return ZONE_EMPLOYEE
    return ZONE_COMPANY


def get_roles_for_zone(zone: str | None):
    if zone == ZONE_PLATFORM:
        return [ROLE_SUPER_ADMIN, ROLE_SITE_ADMIN]
    if zone == ZONE_COMPANY:
        return [ROLE_COMPANY_OWNER, ROLE_COMPANY_ADMIN]
    if zone == ZONE_TERMINAL:
        return [ROLE_TERMINAL_USER]
    if zone == ZONE_EMPLOYEE:
        return [ROLE_EMPLOYEE]
    return []


def get_requested_role_context(request: Request):
    requested_role = request.query_params.get("role_context")
    return requested_role if requested_role in ALL_ROLES else None


def get_zone_for_path(path: str) -> str | None:
    if path.startswith("/platform"):
        return ZONE_PLATFORM
    if path.startswith("/api/context/company"):
        return ZONE_PLATFORM
    if path.startswith("/terminal") or path in {"/scan", "/logs"}:
        return ZONE_TERMINAL
    if path.startswith("/employee/"):
        return ZONE_COMPANY
    if (
        path.startswith("/company")
        or path.startswith("/dashboard")
        or path.startswith("/reports")
        or path.startswith("/employees")
        or path.startswith("/api/dashboard")
        or path.startswith("/api/reports")
    ):
        return ZONE_COMPANY
    return None


def read_role_session(request: Request, role: str | None):
    if not role:
        return None

    cookie_name = ROLE_SESSION_COOKIE_NAMES.get(role)
    if not cookie_name:
        return None

    cookie_value = request.cookies.get(cookie_name)
    if not cookie_value:
        return None

    try:
        session = serializer.loads(cookie_value)
    except BadSignature:
        return None

    if not isinstance(session, dict) or not session.get("authenticated"):
        return None

    if session.get("role") != role:
        return None

    return session


def read_zone_session(request: Request, zone: str | None, role_context: str | None = None):
    if not zone:
        return None

    if role_context:
        if get_zone_for_role(role_context) != zone:
            return None

        return read_role_session(request, role_context)

    role_sessions = [
        session
        for role in get_roles_for_zone(zone)
        for session in [read_role_session(request, role)]
        if session
    ]

    if len(role_sessions) == 1:
        return role_sessions[0]

    if len(role_sessions) > 1:
        return None

    cookie_name = ZONE_COOKIE_NAMES.get(zone)
    if not cookie_name:
        return None

    cookie_value = request.cookies.get(cookie_name)
    if not cookie_value:
        return None

    try:
        session = serializer.loads(cookie_value)
    except BadSignature:
        return None

    if not isinstance(session, dict) or not session.get("authenticated"):
        return None

    if get_zone_for_role(session.get("role")) != zone:
        return None

    return session


def write_zone_session(response: Response, zone: str, session: dict):
    cookie_name = ZONE_COOKIE_NAMES[zone]
    response.set_cookie(
        key=cookie_name,
        value=serializer.dumps(session),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    write_role_session(response, session)


def write_role_session(response: Response, session: dict):
    cookie_name = ROLE_SESSION_COOKIE_NAMES[session["role"]]
    response.set_cookie(
        key=cookie_name,
        value=serializer.dumps(session),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


def clear_zone_session(response: Response, zone: str):
    response.delete_cookie(ZONE_COOKIE_NAMES[zone])
    for role in get_roles_for_zone(zone):
        response.delete_cookie(ROLE_SESSION_COOKIE_NAMES[role])


def clear_role_session(response: Response, role: str):
    cookie_name = ROLE_SESSION_COOKIE_NAMES.get(role)
    if cookie_name:
        response.delete_cookie(cookie_name)


def clear_all_zone_sessions(response: Response):
    for zone in ZONE_COOKIE_NAMES:
        clear_zone_session(response, zone)
    for cookie_name in ROLE_SESSION_COOKIE_NAMES.values():
        response.delete_cookie(cookie_name)

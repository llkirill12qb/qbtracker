from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import parse_qs, urlparse

from app.core.auth import authenticate_user, is_login_allowed_for_user, verify_superadmin
from app.core.database import get_db
from app.core.roles import PLATFORM_ROLES, ROLE_SUPER_ADMIN, ROLE_TERMINAL_USER
from app.core.zoned_sessions import (
    build_session_payload,
    clear_all_zone_sessions,
    clear_role_session,
    clear_zone_session,
    get_zone_for_role,
    get_zone_for_path,
    get_requested_role_context,
    read_zone_session,
    write_zone_session,
    ZONE_COMPANY,
    ZONE_PLATFORM,
    ZONE_TERMINAL,
)
from app.crud.user_crud import update_last_login

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_post_login_redirect(role: str) -> str:
    if role in PLATFORM_ROLES:
        return f"/platform/companies?role_context={role}"

    if role == ROLE_TERMINAL_USER:
        return f"/terminal?role_context={role}"

    return f"/dashboard?role_context={role}"


def clear_legacy_session(request: Request):
    request.session.clear()


def get_logout_zone(request: Request):
    referrer = request.headers.get("referer", "")
    parsed_referrer = urlparse(referrer) if referrer else None
    path = parsed_referrer.path if parsed_referrer else ""
    requested_zone = parse_qs(parsed_referrer.query).get("zone", [None])[0] if parsed_referrer else None
    zone = get_zone_for_path(path)

    if requested_zone in {"platform", "admin"} and zone in {ZONE_COMPANY, ZONE_TERMINAL}:
        return ZONE_PLATFORM if read_zone_session(request, ZONE_PLATFORM) else zone

    if zone == ZONE_COMPANY and not read_zone_session(request, ZONE_COMPANY):
        return ZONE_PLATFORM if read_zone_session(request, ZONE_PLATFORM) else ZONE_COMPANY

    if zone == ZONE_TERMINAL:
        if read_zone_session(request, ZONE_TERMINAL):
            return ZONE_TERMINAL
        if read_zone_session(request, ZONE_COMPANY):
            return ZONE_COMPANY
        if read_zone_session(request, ZONE_PLATFORM):
            return ZONE_PLATFORM

    return zone


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": request.query_params.get("error"),
        },
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)

    if user:
        if not is_login_allowed_for_user(db, user):
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Company is archived. Login is disabled.",
                },
                status_code=403,
            )

        update_last_login(db, user)
        session_payload = build_session_payload(
            user_id=user.id,
            username=user.username,
            role=user.role,
            company_id=user.company_id,
            location_id=user.location_id,
            terminal_id=user.terminal_id,
            auth_source="database",
        )
        clear_legacy_session(request)
        response = RedirectResponse(url=get_post_login_redirect(user.role), status_code=303)
        write_zone_session(response, get_zone_for_role(user.role), session_payload)
        return response

    if not verify_superadmin(username, password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password",
            },
            status_code=401,
        )

    session_payload = build_session_payload(
        user_id=None,
        username=username,
        role=ROLE_SUPER_ADMIN,
        company_id=None,
        location_id=None,
        terminal_id=None,
        auth_source="env",
    )
    clear_legacy_session(request)
    response = RedirectResponse(url=get_post_login_redirect(ROLE_SUPER_ADMIN), status_code=303)
    write_zone_session(response, get_zone_for_role(ROLE_SUPER_ADMIN), session_payload)
    return response


@router.post("/logout")
def logout(request: Request):
    logout_zone = get_logout_zone(request)
    role_context = get_requested_role_context(request)
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=303)
    if role_context:
        clear_role_session(response, role_context)
    elif logout_zone:
        clear_zone_session(response, logout_zone)
    else:
        clear_all_zone_sessions(response)
    return response

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.core.auth import hash_password
from app.core.company_context import get_current_company_id
from app.core.database import get_db
from app.core.roles import (
    PLATFORM_ROLES,
    ROLE_COMPANY_ADMIN,
    ROLE_COMPANY_OWNER,
    ROLE_EMPLOYEE,
    ROLE_TERMINAL_USER,
)
from app.core.security import get_current_session_user
from app.crud.company_crud import get_company_by_id
from app.crud.location_crud import get_location_by_id, get_locations
from app.crud.terminal_crud import get_terminal_by_id, get_terminals
from app.crud.user_crud import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_users_by_company,
    update_user_password,
    update_user_profile,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

COMPANY_USER_MANAGER_ROLES = PLATFORM_ROLES | {ROLE_COMPANY_OWNER, ROLE_COMPANY_ADMIN}
COMPANY_USER_ROLES = (
    ROLE_COMPANY_OWNER,
    ROLE_COMPANY_ADMIN,
    ROLE_TERMINAL_USER,
    ROLE_EMPLOYEE,
)


def require_company_user_manager(request: Request):
    user = get_current_session_user(request)
    if user.get("role") not in COMPANY_USER_MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User management access required",
        )

    return user


def normalize_optional(value: str | None):
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None


def normalize_location_id(db: Session, company_id: int, location_id: str | None):
    clean_value = normalize_optional(location_id)
    if clean_value is None:
        return None

    try:
        parsed_location_id = int(clean_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid location")

    location = get_location_by_id(db, parsed_location_id, company_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    return parsed_location_id


def normalize_terminal_id(db: Session, company_id: int, terminal_id: str | None):
    clean_value = normalize_optional(terminal_id)
    if clean_value is None:
        return None

    try:
        parsed_terminal_id = int(clean_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid terminal")

    terminal = get_terminal_by_id(db, parsed_terminal_id, company_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    return terminal


def redirect_with_query(request: Request, **params):
    if request.session.get("role") in PLATFORM_ROLES:
        params["zone"] = "platform"

    return RedirectResponse(url=f"/company/users?{urlencode(params)}", status_code=303)


def get_company_context_or_404(request: Request, db: Session):
    company_id = get_current_company_id(request)
    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company_id, company


@router.get("/company/users", response_class=HTMLResponse)
def company_users_page(request: Request, db: Session = Depends(get_db)):
    current_user = require_company_user_manager(request)
    company_id, company = get_company_context_or_404(request, db)
    users = get_users_by_company(db, company_id)
    locations = get_locations(db, company_id, include_inactive=True)
    terminals = get_terminals(db, company_id, include_inactive=True)
    location_names_by_id = {location.id: location.name for location in locations}
    terminal_names_by_id = {terminal.id: terminal.name for terminal in terminals}

    return templates.TemplateResponse(
        "company_users.html",
        {
            "request": request,
            "company": company,
            "users": users,
            "locations": locations,
            "terminals": terminals,
            "location_names_by_id": location_names_by_id,
            "terminal_names_by_id": terminal_names_by_id,
            "roles": COMPANY_USER_ROLES,
            "current_user": current_user,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/company/users")
def create_company_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    email: str = Form(default=""),
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    phone: str = Form(default=""),
    location_id: str = Form(default=""),
    terminal_id: str = Form(default=""),
    language: str = Form(default="en"),
    db: Session = Depends(get_db),
):
    require_company_user_manager(request)
    company_id, _ = get_company_context_or_404(request, db)

    username = username.strip()
    email_value = normalize_optional(email)

    if role not in COMPANY_USER_ROLES:
        return redirect_with_query(request, error="Invalid role")
    if not username or not password:
        return redirect_with_query(request, error="Username and password are required")
    if get_user_by_username(db, username):
        return redirect_with_query(request, error="Username already exists")
    if email_value and get_user_by_email(db, email_value):
        return redirect_with_query(request, error="Email already exists")

    parsed_location_id = normalize_location_id(db, company_id, location_id)
    terminal = normalize_terminal_id(db, company_id, terminal_id)
    parsed_terminal_id = terminal.id if terminal else None
    if terminal and terminal.location_id:
        parsed_location_id = terminal.location_id
    if role != ROLE_TERMINAL_USER:
        parsed_location_id = None
        parsed_terminal_id = None

    create_user(
        db=db,
        username=username,
        password_hash=hash_password(password),
        role=role,
        email=email_value,
        first_name=normalize_optional(first_name),
        last_name=normalize_optional(last_name),
        phone=normalize_optional(phone),
        company_id=company_id,
        location_id=parsed_location_id,
        terminal_id=parsed_terminal_id,
        language=language.strip() or "en",
        is_active=True,
    )

    return redirect_with_query(request, message="User created")


@router.post("/company/users/{user_id}/update")
def update_company_user(
    user_id: int,
    request: Request,
    role: str = Form(...),
    email: str = Form(default=""),
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    phone: str = Form(default=""),
    location_id: str = Form(default=""),
    terminal_id: str = Form(default=""),
    language: str = Form(default="en"),
    is_active: str = Form(default="off"),
    db: Session = Depends(get_db),
):
    require_company_user_manager(request)
    company_id, _ = get_company_context_or_404(request, db)
    user = get_user_by_id(db, user_id, company_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in COMPANY_USER_ROLES:
        return redirect_with_query(request, error="Invalid role")

    email_value = normalize_optional(email)
    existing_email_user = get_user_by_email(db, email_value) if email_value else None
    if existing_email_user and existing_email_user.id != user.id:
        return redirect_with_query(request, error="Email already exists")

    parsed_location_id = normalize_location_id(db, company_id, location_id)
    terminal = normalize_terminal_id(db, company_id, terminal_id)
    parsed_terminal_id = terminal.id if terminal else None
    if terminal and terminal.location_id:
        parsed_location_id = terminal.location_id
    if role != ROLE_TERMINAL_USER:
        parsed_location_id = None
        parsed_terminal_id = None

    update_user_profile(
        db=db,
        user=user,
        email=email_value,
        first_name=normalize_optional(first_name),
        last_name=normalize_optional(last_name),
        phone=normalize_optional(phone),
        role=role,
        location_id=parsed_location_id,
        terminal_id=parsed_terminal_id,
        language=language.strip() or "en",
        is_active=is_active == "on",
    )

    return redirect_with_query(request, message="User updated")


@router.post("/company/users/{user_id}/password")
def reset_company_user_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    require_company_user_manager(request)
    company_id, _ = get_company_context_or_404(request, db)
    user = get_user_by_id(db, user_id, company_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not password.strip():
        return redirect_with_query(request, error="Password is required")

    update_user_password(db, user, hash_password(password))
    return redirect_with_query(request, message="Password updated")

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


def redirect_with_query(**params):
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

    return templates.TemplateResponse(
        "company_users.html",
        {
            "request": request,
            "company": company,
            "users": users,
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
    language: str = Form(default="en"),
    db: Session = Depends(get_db),
):
    require_company_user_manager(request)
    company_id, _ = get_company_context_or_404(request, db)

    username = username.strip()
    email_value = normalize_optional(email)

    if role not in COMPANY_USER_ROLES:
        return redirect_with_query(error="Invalid role")
    if not username or not password:
        return redirect_with_query(error="Username and password are required")
    if get_user_by_username(db, username):
        return redirect_with_query(error="Username already exists")
    if email_value and get_user_by_email(db, email_value):
        return redirect_with_query(error="Email already exists")

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
        language=language.strip() or "en",
        is_active=True,
    )

    return redirect_with_query(message="User created")


@router.post("/company/users/{user_id}/update")
def update_company_user(
    user_id: int,
    request: Request,
    role: str = Form(...),
    email: str = Form(default=""),
    first_name: str = Form(default=""),
    last_name: str = Form(default=""),
    phone: str = Form(default=""),
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
        return redirect_with_query(error="Invalid role")

    email_value = normalize_optional(email)
    existing_email_user = get_user_by_email(db, email_value) if email_value else None
    if existing_email_user and existing_email_user.id != user.id:
        return redirect_with_query(error="Email already exists")

    update_user_profile(
        db=db,
        user=user,
        email=email_value,
        first_name=normalize_optional(first_name),
        last_name=normalize_optional(last_name),
        phone=normalize_optional(phone),
        role=role,
        language=language.strip() or "en",
        is_active=is_active == "on",
    )

    return redirect_with_query(message="User updated")


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
        return redirect_with_query(error="Password is required")

    update_user_password(db, user, hash_password(password))
    return redirect_with_query(message="Password updated")

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import authenticate_user, verify_superadmin
from app.core.database import get_db
from app.core.roles import PLATFORM_ROLES, ROLE_SUPER_ADMIN, ROLE_TERMINAL_USER
from app.crud.user_crud import update_last_login

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_post_login_redirect(role: str) -> str:
    if role in PLATFORM_ROLES:
        return "/platform/companies"

    if role == ROLE_TERMINAL_USER:
        return "/terminal"

    return "/dashboard"


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
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
        update_last_login(db, user)
        request.session["authenticated"] = True
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["role"] = user.role
        request.session["company_id"] = user.company_id
        request.session["location_id"] = user.location_id
        request.session["terminal_id"] = user.terminal_id
        request.session["auth_source"] = "database"
        return RedirectResponse(url=get_post_login_redirect(user.role), status_code=303)

    if not verify_superadmin(username, password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password",
            },
            status_code=401,
        )

    request.session["authenticated"] = True
    request.session["user_id"] = None
    request.session["username"] = username
    request.session["role"] = ROLE_SUPER_ADMIN
    request.session["company_id"] = None
    request.session["location_id"] = None
    request.session["terminal_id"] = None
    request.session["auth_source"] = "env"
    return RedirectResponse(url=get_post_login_redirect(ROLE_SUPER_ADMIN), status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

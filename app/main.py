import asyncio
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import dashboard_routes as dashboard
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.company_context_routes import router as company_context_router
from app.api.routes.company_locations_routes import router as company_locations_router
from app.api.routes.company_settings_routes import router as company_settings_router
from app.api.routes.company_terminals_routes import router as company_terminals_router
from app.api.routes.company_users_routes import router as company_users_router
from app.api.routes.employees_page_routes import router as employees_page_router
from app.api.routes.employees_routes import router as employees_router
from app.api.routes.platform_routes import router as platform_router
from app.api.routes.qr_routes import router as qr_router
from app.api.routes.reports_routes import router as reports_router
from app.api.routes.scan_routes import router as scan_router
from app.api.routes.terminal_routes import router as terminal_router
from app.core.auth import is_authenticated, SESSION_SECRET
from app.core.database import Base, SessionLocal, engine
from app.core.zoned_sessions import (
    ZONE_COMPANY,
    ZONE_PLATFORM,
    ZONE_TERMINAL,
    clear_role_session,
    clear_zone_session,
    get_requested_role_context,
    get_zone_for_path,
    read_zone_session,
)
from app.models.company_contact_model import CompanyContact
from app.models.company_model import Company
from app.models.employee_model import Employee
from app.models.location_model import Location
from app.models.scan_log_model import ScanLog
from app.models.terminal_model import Terminal
from app.models.user_model import User
from app.services.demo_company_seed_service import ensure_demo_company_seed
from app.services.demo_events_service import run_demo_events_scheduler
from app.services.employee_bootstrap_service import ensure_employee_qr_tokens
from app.services.schema_upgrade_service import ensure_schema_upgrades
from app.services.user_bootstrap_service import ensure_superadmin_user


PUBLIC_PATHS = {"/", "/login", "/logout", "/favicon.ico"}
PUBLIC_PREFIXES = ("/static",)
API_PREFIXES = ("/api",)
DIRECT_API_PATHS = {"/scan", "/logs"}
ARCHIVED_COMPANY_ERROR = "Archived company is not available in this workspace"


def is_api_request_path(path: str) -> bool:
    return (
        path in DIRECT_API_PATHS
        or path.startswith("/employee/")
        or (path.startswith("/employees") and path not in {"/employees-page", "/employees-archive"})
        or any(path.startswith(prefix) for prefix in API_PREFIXES)
    )


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_public = path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
        if is_public:
            return await call_next(request)

        zone = get_zone_for_path(path)
        requested_zone = request.query_params.get("zone")
        role_context = get_requested_role_context(request)
        zone_session = None
        session_source_zone = zone

        if zone == ZONE_COMPANY and requested_zone in {"platform", "admin"}:
            zone_session = read_zone_session(request, ZONE_PLATFORM, role_context)
            session_source_zone = ZONE_PLATFORM
        elif zone == ZONE_TERMINAL and requested_zone == "platform":
            zone_session = read_zone_session(request, ZONE_PLATFORM, role_context)
            session_source_zone = ZONE_PLATFORM
        elif zone == ZONE_TERMINAL and requested_zone == "admin":
            zone_session = read_zone_session(request, ZONE_COMPANY, role_context)
            session_source_zone = ZONE_COMPANY
        else:
            zone_session = read_zone_session(request, zone, role_context)

        if zone_session:
            request.scope["session"] = zone_session
            request.state.session_zone = session_source_zone

        if zone and not zone_session:
            is_api_request = is_api_request_path(path)
            if is_api_request:
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})
            return RedirectResponse(url="/login", status_code=303)

        if is_authenticated(request.session):
            return await call_next(request)

        is_api_request = is_api_request_path(path)

        if is_api_request:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        return RedirectResponse(url="/login", status_code=303)


app = FastAPI()
app.add_middleware(AuthRequiredMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

ensure_schema_upgrades()

with SessionLocal() as db:
    ensure_superadmin_user(db)
    ensure_demo_company_seed(db)
    ensure_employee_qr_tokens(db)

app.include_router(auth_router)
app.include_router(company_context_router)
app.include_router(company_locations_router)
app.include_router(company_settings_router)
app.include_router(company_terminals_router)
app.include_router(company_users_router)
app.include_router(platform_router)
app.include_router(employees_router)
app.include_router(scan_router)
app.include_router(terminal_router)
app.include_router(qr_router)
app.include_router(reports_router)
app.include_router(dashboard.router)
app.include_router(employees_page_router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 403 and exc.detail == ARCHIVED_COMPANY_ERROR and not is_api_request_path(request.url.path):
        error_message = quote_plus("Company is archived. Access has been closed for this workspace.")
        response = RedirectResponse(url=f"/login?error={error_message}", status_code=303)
        role_context = request.session.get("role")
        session_zone = getattr(request.state, "session_zone", None)
        if role_context:
            clear_role_session(response, role_context)
        if session_zone:
            clear_zone_session(response, session_zone)
        request.session.clear()
        return response

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.on_event("startup")
async def start_demo_events_scheduler():
    asyncio.create_task(run_demo_events_scheduler())


@app.get("/")
def home(request: Request):
    return RedirectResponse(url="/login", status_code=303)

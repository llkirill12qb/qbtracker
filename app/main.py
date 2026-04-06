from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import dashboard_routes as dashboard
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.employees_page_routes import router as employees_page_router
from app.api.routes.employees_routes import router as employees_router
from app.api.routes.qr_routes import router as qr_router
from app.api.routes.reports_routes import router as reports_router
from app.api.routes.scan_routes import router as scan_router
from app.api.routes.terminal_routes import router as terminal_router
from app.core.auth import is_authenticated, SESSION_SECRET
from app.core.database import Base, engine
from app.models.company_model import Company
from app.models.employee_model import Employee
from app.models.scan_log_model import ScanLog


PUBLIC_PATHS = {"/", "/login", "/favicon.ico"}
PUBLIC_PREFIXES = ("/static",)
API_PREFIXES = ("/api",)
DIRECT_API_PATHS = {"/scan", "/logs"}


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        is_public = path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
        if is_public or is_authenticated(request.session):
            return await call_next(request)

        is_api_request = (
            path in DIRECT_API_PATHS
            or path.startswith("/employee/")
            or (path.startswith("/employees") and path not in {"/employees-page", "/employees-archive"})
            or any(path.startswith(prefix) for prefix in API_PREFIXES)
        )

        if is_api_request:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        return RedirectResponse(url="/login", status_code=303)


app = FastAPI()
app.add_middleware(AuthRequiredMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(scan_router)
app.include_router(terminal_router)
app.include_router(qr_router)
app.include_router(reports_router)
app.include_router(dashboard.router)
app.include_router(employees_page_router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home(request: Request):
    return RedirectResponse(url="/login", status_code=303)

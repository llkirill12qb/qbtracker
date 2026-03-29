
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.database import engine, Base
from app.models.employee_model import Employee
from app.models.scan_log_model import ScanLog
from app.api.routes.employees_routes import router as employees_router
from app.api.routes.scan_routes import router as scan_router
from app.api.routes.terminal_routes import router as terminal_router
from app.api.routes.qr_routes import router as qr_router
from app.api.routes import dashboard_routes as dashboard
from app.api.routes.employees_page_routes import router as employees_page_router
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

app.include_router(employees_router)
app.include_router(scan_router)
app.include_router(terminal_router)
app.include_router(qr_router)
app.include_router(dashboard.router)
app.include_router(employees_page_router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home():
    return {"message": "Employee Tracker API is running"}
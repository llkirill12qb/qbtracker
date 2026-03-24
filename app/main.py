# from fastapi import FastAPI

# app = FastAPI()

# @app.get("/")
# def home():
#     return {"message": "Employee Tracker API is running"}

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# from fastapi import FastAPI
# from app.database import engine, Base
# from app.models.employee import Employee

# app = FastAPI()

# Base.metadata.create_all(bind=engine)

# @app.get("/")
# def home():
#     return {"message": "Employee Tracker API is running"}

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# from fastapi import FastAPI
# from app.database import engine, Base
# from app.models.employee import Employee
# from app.models.scan_log import ScanLog
# from app.routes.employees import router as employees_router
# from app.routes.scan import router as scan_router

# app = FastAPI()

# Base.metadata.create_all(bind=engine)

# app.include_router(employees_router)
# app.include_router(scan_router)

# @app.get("/")
# def home():
#     return {"message": "Employee Tracker API is running"}

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# запуск виртуально окружения
# .\.venv\Scripts\Activate.ps1
# перезапуск сервера
# uvicorn app.main:app пока этот запуск использовать для стабильности на win
# uvicorn app.main:app --reload --reload-dir app
# C:\Users\Kirill\Documents\New Best Life\employee-tracker> uvicorn app.main:app --reload --reload-dir app

# github
# git branch -M main
# git remote add origin https://github.com/llkirill12qb/qbtracker.git
# 

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.models.employee import Employee
from app.models.scan_log import ScanLog
from app.routes.employees import router as employees_router
from app.routes.scan import router as scan_router
from app.routes.terminal import router as terminal_router
from app.routes.qr import router as qr_router
from app.routes import dashboard
from app.routes.employees_page import router as employees_page_router
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

app.include_router(employees_router)
app.include_router(scan_router)
app.include_router(terminal_router)
app.include_router(qr_router)
app.include_router(dashboard.router)
app.include_router(employees_page_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home():
    return {"message": "Employee Tracker API is running"}
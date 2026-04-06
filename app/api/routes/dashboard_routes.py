from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, time

from app.core.database import SessionLocal
from app.models.employee_model import Employee
from app.models.scan_log_model import ScanLog

router = APIRouter()

DEFAULT_COMPANY_ID = 1


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/api/dashboard")
def dashboard_data(db: Session = Depends(get_db)):
    today = date.today()
    start_today = datetime.combine(today, time.min)
    end_today = datetime.combine(today, time.max)

    total_employees = (
        db.query(func.count(Employee.id))
        .filter(Employee.company_id == DEFAULT_COMPANY_ID)
        .scalar()
    )

    scans_today = (
        db.query(func.count(ScanLog.id))
        .filter(ScanLog.company_id == DEFAULT_COMPANY_ID)
        .filter(ScanLog.scanned_at >= start_today)
        .filter(ScanLog.scanned_at <= end_today)
        .scalar()
    )

    recent_logs = (
        db.query(ScanLog, Employee)
        .join(Employee, Employee.id == ScanLog.employee_id)
        .filter(ScanLog.company_id == DEFAULT_COMPANY_ID)
        .filter(Employee.company_id == DEFAULT_COMPANY_ID)
        .order_by(ScanLog.scanned_at.desc())
        .limit(10)
        .all()
    )

    recent = []
    for log, emp in recent_logs:
        recent.append({
            "employee_name": emp.full_name,
            "card_id": emp.card_id,
            "time": log.scanned_at.isoformat()
        })

    return {
        "employees": total_employees or 0,
        "scans_today": scans_today or 0,
        "currently_inside": 0,
        "recent": recent
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                color: #111827;
            }

            .navbar {
                background: #111827;
                color: white;
                padding: 16px 28px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .navbar .title {
                font-size: 22px;
                font-weight: bold;
            }

            .navbar .links a {
                color: white;
                text-decoration: none;
                margin-left: 20px;
                font-weight: bold;
            }

            .container {
                max-width: 1200px;
                margin: 30px auto;
                padding: 0 20px;
            }

            h1 {
                margin-bottom: 24px;
            }

            .cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .card {
                background: white;
                border-radius: 14px;
                padding: 24px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
            }

            .card h3 {
                margin: 0;
                color: #6b7280;
                font-size: 16px;
            }

            .card .value {
                margin-top: 12px;
                font-size: 34px;
                font-weight: bold;
            }

            .table-box {
                background: white;
                border-radius: 14px;
                padding: 24px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }

            th, td {
                text-align: left;
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
            }

            th {
                background: #f9fafb;
            }

            .empty {
                color: #6b7280;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="title">Time Tracking SaaS</div>
            <div class="links">
                <a href="/dashboard">Dashboard</a>
                <a href="/employees-page">Employees</a>
                <a href="/terminal">Terminal</a>
            </div>
        </div>

        <div class="container">
            <h1>Company Dashboard</h1>

            <div class="cards">
                <div class="card">
                    <h3>Total Employees</h3>
                    <div class="value" id="employees">0</div>
                </div>

                <div class="card">
                    <h3>Scans Today</h3>
                    <div class="value" id="scans">0</div>
                </div>

                <div class="card">
                    <h3>Currently Inside</h3>
                    <div class="value" id="inside">0</div>
                </div>
            </div>

            <div class="table-box">
                <h2>Recent Scans</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th>Card ID</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody id="recentTable"></tbody>
                </table>

                <div class="empty" id="emptyMsg" style="display:none;">
                    No scans yet
                </div>
            </div>
        </div>

        <script>
            async function loadDashboard() {
                try {
                    const response = await fetch("/api/dashboard");
                    const data = await response.json();

                    document.getElementById("employees").innerText = data.employees;
                    document.getElementById("scans").innerText = data.scans_today;
                    document.getElementById("inside").innerText = data.currently_inside;

                    const table = document.getElementById("recentTable");
                    const emptyMsg = document.getElementById("emptyMsg");

                    table.innerHTML = "";

                    if (!data.recent || data.recent.length === 0) {
                        emptyMsg.style.display = "block";
                        return;
                    }

                    emptyMsg.style.display = "none";

                    data.recent.forEach(item => {
                        const row = document.createElement("tr");
                        const localTime = new Date(item.time).toLocaleString();

                        row.innerHTML = `
                            <td>${item.employee_name}</td>
                            <td>${item.card_id}</td>
                            <td>${localTime}</td>
                        `;

                        table.appendChild(row);
                    });
                } catch (error) {
                    console.error("Dashboard load error:", error);
                }
            }

            loadDashboard();
            setInterval(loadDashboard, 5000);
        </script>
    </body>
    </html>
    """
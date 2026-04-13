from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.company_context import get_current_company_id
from app.core.database import SessionLocal
from app.core.security import require_company_workspace_access
from app.models.employee_model import Employee
from app.models.scan_log_model import ScanLog
from app.services.company_time_service import (
    format_scan_time,
    format_scan_time_display,
    get_company_timezone,
    get_scan_timezone,
    get_timezone_abbr,
    is_scan_today_in_own_timezone,
)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_scan_row(log: ScanLog, employee: Employee, fallback_timezone_name: str):
    _, scan_timezone = get_scan_timezone(log, fallback_timezone_name)

    return {
        "employee_name": employee.full_name,
        "card_id": employee.card_id,
        "event": log.event_type,
        "scan_source": log.scan_source,
        "time": format_scan_time(log.scanned_at, scan_timezone),
        "time_display": format_scan_time_display(log.scanned_at, scan_timezone),
        "timezone_abbr": log.timezone_abbr or get_timezone_abbr(log.scanned_at, scan_timezone),
    }


@router.get("/api/dashboard")
def dashboard_data(request: Request, db: Session = Depends(get_db)):
    require_company_workspace_access(request)
    company_id = get_current_company_id(request)
    timezone_name, _ = get_company_timezone(db, company_id)

    active_employees = (
        db.query(func.count(Employee.id))
        .filter(Employee.company_id == company_id)
        .filter(Employee.is_active.is_(True))
        .scalar()
    )

    archived_employees = (
        db.query(func.count(Employee.id))
        .filter(Employee.company_id == company_id)
        .filter(Employee.is_active.is_(False))
        .scalar()
    )

    company_logs = (
        db.query(ScanLog)
        .filter(ScanLog.company_id == company_id)
        .all()
    )
    scans_today = sum(
        1
        for log in company_logs
        if is_scan_today_in_own_timezone(log, timezone_name)
    )

    latest_scan_subquery = (
        db.query(
            ScanLog.employee_id.label("employee_id"),
            func.max(ScanLog.scanned_at).label("last_scanned_at"),
        )
        .filter(ScanLog.company_id == company_id)
        .group_by(ScanLog.employee_id)
        .subquery()
    )

    latest_scan_rows = (
        db.query(ScanLog, Employee)
        .join(
            latest_scan_subquery,
            and_(
                ScanLog.employee_id == latest_scan_subquery.c.employee_id,
                ScanLog.scanned_at == latest_scan_subquery.c.last_scanned_at,
            ),
        )
        .join(Employee, Employee.id == ScanLog.employee_id)
        .filter(ScanLog.company_id == company_id)
        .filter(Employee.company_id == company_id)
        .filter(Employee.is_active.is_(True))
        .order_by(ScanLog.scanned_at.desc())
        .all()
    )
    currently_inside = sum(1 for log, _ in latest_scan_rows if log.event_type == "check-in")

    recent_logs = (
        db.query(ScanLog, Employee)
        .join(Employee, Employee.id == ScanLog.employee_id)
        .filter(ScanLog.company_id == company_id)
        .filter(Employee.company_id == company_id)
        .order_by(ScanLog.scanned_at.desc())
        .limit(10)
        .all()
    )

    recent = []
    for log, emp in recent_logs:
        recent.append(build_scan_row(log, emp, timezone_name))

    inside_employees = []
    checked_out_employees = []
    for log, emp in latest_scan_rows:
        row = build_scan_row(log, emp, timezone_name)
        if log.event_type == "check-in":
            inside_employees.append(row)
        elif log.event_type == "check-out":
            checked_out_employees.append(row)

    return {
        "employees": active_employees or 0,
        "archived_employees": archived_employees or 0,
        "scans_today": scans_today or 0,
        "currently_inside": currently_inside or 0,
        "company_id": company_id,
        "timezone": timezone_name,
        "recent": recent,
        "inside_employees": inside_employees,
        "checked_out_employees": checked_out_employees
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    require_company_workspace_access(request)
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
                padding: 18px 28px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
                flex-wrap: wrap;
            }

            .navbar .brand {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }

            .navbar .title {
                font-size: 22px;
                font-weight: bold;
            }

            .navbar .subtitle {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.72);
            }

            .navbar .links {
                display: flex;
                gap: 18px;
                flex-wrap: wrap;
            }

            .navbar .links a {
                color: white;
                text-decoration: none;
                font-weight: bold;
            }

            .navbar .logout-form {
                margin: 0;
            }

            .navbar .logout-button {
                padding: 0;
                border: none;
                background: transparent;
                color: white;
                font: inherit;
                font-weight: bold;
                cursor: pointer;
            }

            .navbar .links a:hover {
                color: #bfdbfe;
            }

            .navbar .logout-button:hover {
                color: #bfdbfe;
            }

            .container {
                max-width: 1200px;
                margin: 30px auto;
                padding: 0 20px;
            }

            h1 {
                margin-bottom: 8px;
            }

            .page-note {
                margin: 0 0 24px;
                color: #6b7280;
                font-size: 14px;
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

            .table-head {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                flex-wrap: wrap;
            }

            .table-title {
                margin: 0;
            }

            .filter-tabs {
                display: inline-flex;
                gap: 8px;
                padding: 5px;
                border-radius: 999px;
                background: #f3f4f6;
            }

            .filter-tab {
                border: none;
                border-radius: 999px;
                padding: 9px 13px;
                background: transparent;
                color: #4b5563;
                font-weight: 700;
                cursor: pointer;
            }

            .filter-tab.active {
                background: #111827;
                color: white;
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

            .event-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }

            .event-badge.check-in {
                background: #dcfce7;
                color: #166534;
            }

            .event-badge.check-out {
                background: #fee2e2;
                color: #991b1b;
            }
        </style>
    </head>
    <body>
        <div class="navbar">
            <div class="brand">
                <div class="title">Time Tracking SaaS</div>
                <div class="subtitle">Company dashboard</div>
            </div>
            <div class="links">
                <a href="/platform/companies">Companies</a>
                <a href="/dashboard">Dashboard</a>
                <a href="/employees-page">Employees</a>
                <a href="/employees-archive">Archive</a>
                <a href="/reports">Reports</a>
                <a href="/terminal">Terminal</a>
                <a href="/company/users">Users</a>
                <a href="/company/settings">Settings</a>
                <form class="logout-form" method="post" action="/logout">
                    <button class="logout-button" type="submit">Logout</button>
                </form>
            </div>
        </div>

        <div class="container">
            <h1>Company Dashboard</h1>
            <p class="page-note">
                Default company timezone: <strong id="companyTimezone">Loading...</strong>.
                Scan rows use the timezone captured from the scanning device when available.
            </p>

            <div class="cards">
                <div class="card">
                    <h3>Active Employees</h3>
                    <div class="value" id="employees">0</div>
                </div>

                <div class="card">
                    <h3>Archived Employees</h3>
                    <div class="value" id="archivedEmployees">0</div>
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
                <div class="table-head">
                    <h2 class="table-title" id="tableTitle">Recent Scans</h2>
                    <div class="filter-tabs" aria-label="Dashboard scan filters">
                        <button class="filter-tab active" type="button" data-view="all">All Events</button>
                        <button class="filter-tab" type="button" data-view="inside">Checked In</button>
                        <button class="filter-tab" type="button" data-view="out">Checked Out</button>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th>Card ID</th>
                            <th>Event</th>
                            <th>Time</th>
                            <th>TZ</th>
                            <th>Source</th>
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
            let dashboardData = null;
            let currentView = "all";

            const viewConfig = {
                all: {
                    title: "Recent Scans",
                    empty: "No scans yet"
                },
                inside: {
                    title: "Employees Checked In",
                    empty: "No employees are currently checked in"
                },
                out: {
                    title: "Employees Checked Out",
                    empty: "No employees are currently checked out"
                }
            };

            function getRowsForView(data) {
                if (currentView === "inside") {
                    return data.inside_employees || [];
                }
                if (currentView === "out") {
                    return data.checked_out_employees || [];
                }
                return data.recent || [];
            }

            function renderDashboardTable() {
                if (!dashboardData) {
                    return;
                }

                const table = document.getElementById("recentTable");
                const emptyMsg = document.getElementById("emptyMsg");
                const tableTitle = document.getElementById("tableTitle");
                const rows = getRowsForView(dashboardData);
                const config = viewConfig[currentView];

                tableTitle.innerText = config.title;
                emptyMsg.innerText = config.empty;
                table.innerHTML = "";

                if (!rows.length) {
                    emptyMsg.style.display = "block";
                    return;
                }

                emptyMsg.style.display = "none";

                rows.forEach(item => {
                    const row = document.createElement("tr");
                    const localTime = item.time_display || new Date(item.time).toLocaleString();
                    const eventClass = item.event === "check-in" ? "check-in" : "check-out";

                    row.innerHTML = `
                        <td>${item.employee_name}</td>
                        <td>${item.card_id}</td>
                        <td><span class="event-badge ${eventClass}">${item.event}</span></td>
                        <td>${localTime}</td>
                        <td>${item.timezone_abbr || "-"}</td>
                        <td>${item.scan_source || "-"}</td>
                    `;

                    table.appendChild(row);
                });
            }

            async function loadDashboard() {
                try {
                    const response = await fetch("/api/dashboard");
                    const data = await response.json();
                    dashboardData = data;

                    document.getElementById("employees").innerText = data.employees;
                    document.getElementById("archivedEmployees").innerText = data.archived_employees;
                    document.getElementById("scans").innerText = data.scans_today;
                    document.getElementById("inside").innerText = data.currently_inside;
                    document.getElementById("companyTimezone").innerText = data.timezone || "Not configured";

                    renderDashboardTable();
                } catch (error) {
                    console.error("Dashboard load error:", error);
                }
            }

            document.querySelectorAll(".filter-tab").forEach(button => {
                button.addEventListener("click", () => {
                    currentView = button.dataset.view;
                    document.querySelectorAll(".filter-tab").forEach(tab => {
                        tab.classList.toggle("active", tab === button);
                    });
                    renderDashboardTable();
                });
            });

            loadDashboard();
            setInterval(loadDashboard, 5000);
        </script>
    </body>
    </html>
    """

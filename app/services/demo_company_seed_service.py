import os
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.employee_crud import generate_qr_token
from app.models.company_contact_model import CompanyContact
from app.models.company_model import Company
from app.models.employee_model import Employee
from app.models.location_model import Location
from app.models.terminal_model import Terminal
from app.services.company_time_service import get_timezone_info
from app.services.demo_events_service import DEFAULT_DEMO_COMPANY_NAME, ensure_daily_demo_events


DEMO_COMPANY_SEED_ENABLED_ENV = "DEMO_COMPANY_SEED_ENABLED"
DEMO_HISTORY_DAYS_ENV = "DEMO_COMPANY_HISTORY_DAYS"
DEFAULT_DEMO_HISTORY_DAYS = 7
DEFAULT_DEMO_TIMEZONE = "America/New_York"

DEMO_EMPLOYEES = [
    {
        "full_name": "Sofia Martinez",
        "card_id": "DEMO-1001",
        "department": "Operations",
        "position": "Operations Lead",
        "email": "sofia.martinez@example.com",
    },
    {
        "full_name": "Daniel Brooks",
        "card_id": "DEMO-1002",
        "department": "Operations",
        "position": "Shift Supervisor",
        "email": "daniel.brooks@example.com",
    },
    {
        "full_name": "Maya Chen",
        "card_id": "DEMO-1003",
        "department": "Customer Success",
        "position": "Customer Success Manager",
        "email": "maya.chen@example.com",
    },
    {
        "full_name": "Liam Carter",
        "card_id": "DEMO-1004",
        "department": "Customer Success",
        "position": "Support Specialist",
        "email": "liam.carter@example.com",
    },
    {
        "full_name": "Olivia Nguyen",
        "card_id": "DEMO-1005",
        "department": "Warehouse",
        "position": "Inventory Coordinator",
        "email": "olivia.nguyen@example.com",
    },
    {
        "full_name": "Ethan Wilson",
        "card_id": "DEMO-1006",
        "department": "Warehouse",
        "position": "Fulfillment Associate",
        "email": "ethan.wilson@example.com",
    },
    {
        "full_name": "Ava Thompson",
        "card_id": "DEMO-1007",
        "department": "Finance",
        "position": "Payroll Specialist",
        "email": "ava.thompson@example.com",
    },
    {
        "full_name": "Noah Patel",
        "card_id": "DEMO-1008",
        "department": "IT",
        "position": "Systems Technician",
        "email": "noah.patel@example.com",
    },
    {
        "full_name": "Isabella Rossi",
        "card_id": "DEMO-1009",
        "department": "HR",
        "position": "People Coordinator",
        "email": "isabella.rossi@example.com",
    },
    {
        "full_name": "Lucas Johnson",
        "card_id": "DEMO-1010",
        "department": "Sales",
        "position": "Account Executive",
        "email": "lucas.johnson@example.com",
    },
    {
        "full_name": "Emma Davis",
        "card_id": "DEMO-1011",
        "department": "Sales",
        "position": "Sales Development Rep",
        "email": "emma.davis@example.com",
    },
    {
        "full_name": "Mason Lee",
        "card_id": "DEMO-1012",
        "department": "Management",
        "position": "General Manager",
        "email": "mason.lee@example.com",
    },
]


def is_demo_company_seed_enabled() -> bool:
    return os.getenv(DEMO_COMPANY_SEED_ENABLED_ENV, "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def ensure_demo_company_seed(db: Session):
    if not is_demo_company_seed_enabled():
        return {"created": False, "skipped": "disabled"}

    company = _ensure_demo_company(db)
    location = _ensure_demo_location(db, company)
    _ensure_demo_terminal(db, company, location)
    created_employees = _ensure_demo_employees(db, company)
    _ensure_demo_contact(db, company)
    created_events = _ensure_demo_history(db, company)

    return {
        "company_id": company.id,
        "created_employees": created_employees,
        "created_events": created_events,
    }


def _get_demo_company_name() -> str:
    return os.getenv("DEMO_COMPANY_NAME", DEFAULT_DEMO_COMPANY_NAME).strip() or DEFAULT_DEMO_COMPANY_NAME


def _ensure_demo_company(db: Session):
    demo_company_id = os.getenv("DEMO_COMPANY_ID", "").strip()
    if demo_company_id:
        try:
            company_id = int(demo_company_id)
        except ValueError:
            company_id = None

        if company_id is not None:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company:
                return company

    company_name = _get_demo_company_name()
    company = (
        db.query(Company)
        .filter(func.lower(Company.name) == company_name.lower())
        .first()
    )
    if company:
        return company

    company = Company(
        name=company_name,
        legal_name=f"{company_name} LLC",
        email="demo@example.com",
        phone="+1 555 010 2400",
        website="https://example.com",
        country="United States",
        state="NY",
        city="New York",
        address_line1="125 Demo Street",
        postal_code="10001",
        timezone=DEFAULT_DEMO_TIMEZONE,
        status="active",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _ensure_demo_location(db: Session, company: Company):
    location = (
        db.query(Location)
        .filter(
            Location.company_id == company.id,
            func.lower(Location.name) == "demo hq",
        )
        .first()
    )
    if location:
        return location

    location = Location(
        company_id=company.id,
        name="Demo HQ",
        timezone=company.timezone or DEFAULT_DEMO_TIMEZONE,
        country="United States",
        state="NY",
        city="New York",
        address_line1="125 Demo Street",
        postal_code="10001",
        latitude=40.7549,
        longitude=-73.9840,
        geo_radius_meters=120,
        is_active=True,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def _ensure_demo_terminal(db: Session, company: Company, location: Location):
    terminal = (
        db.query(Terminal)
        .filter(
            Terminal.company_id == company.id,
            func.lower(Terminal.name) == "front desk demo terminal",
        )
        .first()
    )
    if terminal:
        return terminal

    terminal = Terminal(
        company_id=company.id,
        location_id=location.id,
        name="Front Desk Demo Terminal",
        device_name="Demo Kiosk 01",
        timezone=location.timezone,
        status="active",
        is_active=True,
    )
    db.add(terminal)
    db.commit()
    db.refresh(terminal)
    return terminal


def _ensure_demo_employees(db: Session, company: Company) -> int:
    created_count = 0
    for employee_data in DEMO_EMPLOYEES:
        employee = (
            db.query(Employee)
            .filter(
                Employee.company_id == company.id,
                func.lower(Employee.email) == employee_data["email"].lower(),
            )
            .first()
        )
        if employee:
            continue

        card_id = _get_available_card_id(db, company, employee_data["card_id"])
        employee = Employee(
            company_id=company.id,
            full_name=employee_data["full_name"],
            card_id=card_id,
            department=employee_data["department"],
            position=employee_data["position"],
            email=employee_data["email"],
            employee_type="full_time",
            status="active",
            is_active=True,
            qr_token=generate_qr_token(),
            notes="Seeded demo employee",
        )
        db.add(employee)
        created_count += 1

    if created_count:
        db.commit()

    return created_count


def _get_available_card_id(db: Session, company: Company, preferred_card_id: str) -> str:
    existing_employee = db.query(Employee).filter(Employee.card_id == preferred_card_id).first()
    if not existing_employee:
        return preferred_card_id

    if existing_employee.company_id == company.id:
        return preferred_card_id

    suffix = preferred_card_id.removeprefix("DEMO-")
    company_card_id = f"DEMO-{company.id}-{suffix}"
    existing_employee = db.query(Employee).filter(Employee.card_id == company_card_id).first()
    if not existing_employee:
        return company_card_id

    counter = 2
    while True:
        candidate = f"{company_card_id}-{counter}"
        existing_employee = db.query(Employee).filter(Employee.card_id == candidate).first()
        if not existing_employee:
            return candidate
        counter += 1


def _ensure_demo_contact(db: Session, company: Company):
    contact = (
        db.query(CompanyContact)
        .filter(
            CompanyContact.company_id == company.id,
            func.lower(CompanyContact.email) == "admin.demo@example.com",
        )
        .first()
    )
    if contact:
        return contact

    contact = CompanyContact(
        company_id=company.id,
        contact_type="admin",
        full_name="Alex Morgan",
        position="Demo Account Owner",
        email="admin.demo@example.com",
        phone="+1 555 010 2401",
        is_primary=True,
        notes="Seeded demo contact",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def _ensure_demo_history(db: Session, company: Company) -> int:
    history_days = _get_history_days()
    if history_days <= 0:
        return 0

    _, company_timezone = get_timezone_info(company.timezone)
    today = datetime.now(company_timezone).date()
    created_events = 0

    for days_ago in range(history_days, 0, -1):
        result = ensure_daily_demo_events(db, target_date=today - timedelta(days=days_ago))
        created_events += result.get("created", 0)

    return created_events


def _get_history_days() -> int:
    value = os.getenv(DEMO_HISTORY_DAYS_ENV, str(DEFAULT_DEMO_HISTORY_DAYS)).strip()
    try:
        return max(0, int(value))
    except ValueError:
        return DEFAULT_DEMO_HISTORY_DAYS

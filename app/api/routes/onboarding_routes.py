from io import BytesIO
import secrets

import qrcode
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.company_crud import get_company_by_id
from app.crud.employee_crud import create_employee, get_employee_by_card_id
from app.crud.location_crud import get_location_by_onboarding_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_public_onboarding_context(token: str, db: Session):
    location = get_location_by_onboarding_token(db, token)
    if not location:
        raise HTTPException(status_code=404, detail="Onboarding link not found")

    company = get_company_by_id(db, location.company_id)
    if not company or company.status == "archived":
        raise HTTPException(status_code=404, detail="Onboarding link not found")

    if not location.is_active or not location.onboarding_enabled:
        raise HTTPException(status_code=404, detail="Onboarding link is disabled")

    return company, location


def normalize_optional(value: str | None):
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None


def build_onboarding_card_id(db: Session, company_id: int, location_id: int) -> str:
    while True:
        card_id = f"ONB-{company_id}-{location_id}-{secrets.token_hex(3).upper()}"
        if not get_employee_by_card_id(db, card_id):
            return card_id


def build_onboarding_notes(
    location_name: str,
    emergency_contact_name: str | None,
    emergency_contact_phone: str | None,
    trade: str | None,
    medical_notes: str | None,
) -> str:
    parts = [
        "Created from public onboarding.",
        f"Location: {location_name}",
    ]
    if emergency_contact_name or emergency_contact_phone:
        parts.append(
            "Emergency contact: "
            f"{emergency_contact_name or '-'} / {emergency_contact_phone or '-'}"
        )
    if trade:
        parts.append(f"Trade: {trade}")
    if medical_notes:
        parts.append(f"Medical notes: {medical_notes}")

    return "\n".join(parts)


@router.get("/onboarding/{token}", response_class=HTMLResponse)
def public_onboarding_page(token: str, request: Request, db: Session = Depends(get_db)):
    company, location = get_public_onboarding_context(token, db)
    return templates.TemplateResponse(
        "public_onboarding.html",
        {
            "request": request,
            "company": company,
            "location": location,
        },
    )


@router.post("/onboarding/{token}", response_class=HTMLResponse)
def submit_public_onboarding(
    token: str,
    request: Request,
    first_name: str = Form(...),
    middle_name: str = Form(default=""),
    last_name: str = Form(...),
    birth_date: str = Form(...),
    phone: str = Form(...),
    email: str = Form(default=""),
    emergency_contact_name: str = Form(...),
    emergency_contact_phone: str = Form(...),
    contractor_company: str = Form(...),
    job_title: str = Form(...),
    trade: str = Form(...),
    medical_notes: str = Form(default=""),
    document_ack: str = Form(default="off"),
    signature_data: str = Form(default=""),
    db: Session = Depends(get_db),
):
    company, location = get_public_onboarding_context(token, db)
    first_name = first_name.strip()
    last_name = last_name.strip()
    contractor_company_value = contractor_company.strip()
    job_title_value = job_title.strip()
    trade_value = trade.strip()
    phone_value = phone.strip()
    emergency_contact_name_value = emergency_contact_name.strip()
    emergency_contact_phone_value = emergency_contact_phone.strip()

    missing_required = not all(
        [
            first_name,
            last_name,
            birth_date.strip(),
            phone_value,
            emergency_contact_name_value,
            emergency_contact_phone_value,
            contractor_company_value,
            job_title_value,
            trade_value,
            document_ack == "on",
        ]
    )
    if missing_required:
        return templates.TemplateResponse(
            "public_onboarding.html",
            {
                "request": request,
                "company": company,
                "location": location,
                "error": "Please fill all required fields and confirm the documents.",
            },
            status_code=400,
        )

    full_name = f"{first_name} {last_name}"
    card_id = build_onboarding_card_id(db, company.id, location.id)
    clean_medical_notes = normalize_optional(medical_notes)

    employee = create_employee(
        db=db,
        full_name=full_name,
        card_id=card_id,
        department=contractor_company_value,
        position=job_title_value,
        phone=phone_value,
        email=normalize_optional(email),
        employee_type="contractor",
        status="pending_photo",
        notes=build_onboarding_notes(
            location_name=location.name,
            emergency_contact_name=emergency_contact_name_value,
            emergency_contact_phone=emergency_contact_phone_value,
            trade=trade_value,
            medical_notes=clean_medical_notes,
        ),
        company_id=company.id,
        location_id=location.id,
        middle_name=normalize_optional(middle_name),
        birth_date=birth_date.strip(),
        emergency_contact_name=emergency_contact_name_value,
        emergency_contact_phone=emergency_contact_phone_value,
        contractor_company=contractor_company_value,
        job_title=job_title_value,
        trade=trade_value,
        medical_notes=clean_medical_notes,
        onboarding_status="pending_photo",
        onboarding_signature=normalize_optional(signature_data),
        onboarding_completed_at=func.now(),
    )

    return templates.TemplateResponse(
        "public_onboarding_complete.html",
        {
            "request": request,
            "company": company,
            "location": location,
            "employee": employee,
        },
    )


@router.get("/onboarding/{token}/qr")
def public_onboarding_qr(token: str, request: Request, db: Session = Depends(get_db)):
    get_public_onboarding_context(token, db)
    onboarding_url = str(request.url_for("public_onboarding_page", token=token))
    img = qrcode.make(onboarding_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )

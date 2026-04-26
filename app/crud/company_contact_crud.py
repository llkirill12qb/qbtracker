from sqlalchemy.orm import Session

from app.models.company_contact_model import CompanyContact


def get_company_contacts(db: Session, company_id: int):
    return (
        db.query(CompanyContact)
        .filter(CompanyContact.company_id == company_id)
        .order_by(CompanyContact.contact_type.asc(), CompanyContact.full_name.asc())
        .all()
    )


def get_primary_company_contact(db: Session, company_id: int):
    return (
        db.query(CompanyContact)
        .filter(
            CompanyContact.company_id == company_id,
            CompanyContact.is_primary.is_(True),
        )
        .order_by(CompanyContact.id.asc())
        .first()
    )


def create_company_contact(
    db: Session,
    company_id: int,
    full_name: str,
    contact_type: str = "general",
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    is_primary: bool = False,
    notes: str | None = None,
):
    contact = CompanyContact(
        company_id=company_id,
        full_name=full_name,
        contact_type=contact_type,
        position=position,
        email=email,
        phone=phone,
        is_primary=is_primary,
        notes=notes,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_company_contact(db: Session, contact: CompanyContact, **fields):
    for field, value in fields.items():
        if hasattr(contact, field):
            setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


def upsert_primary_company_contact(
    db: Session,
    company_id: int,
    *,
    full_name: str | None = None,
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
):
    full_name = (full_name or "").strip()
    position = (position or "").strip() or None
    email = (email or "").strip() or None
    phone = (phone or "").strip() or None
    notes = (notes or "").strip() or None

    primary_contact = get_primary_company_contact(db, company_id)
    has_contact_data = bool(full_name or position or email or phone or notes)

    existing_contacts = (
        db.query(CompanyContact)
        .filter(CompanyContact.company_id == company_id)
        .all()
    )
    for contact in existing_contacts:
        if contact.is_primary:
            contact.is_primary = False
    db.commit()

    if not has_contact_data:
        return None

    if primary_contact:
        return update_company_contact(
            db,
            primary_contact,
            full_name=full_name or primary_contact.full_name,
            contact_type="primary",
            position=position,
            email=email,
            phone=phone,
            is_primary=True,
            notes=notes,
        )

    return create_company_contact(
        db=db,
        company_id=company_id,
        full_name=full_name or "Primary Contact",
        contact_type="primary",
        position=position,
        email=email,
        phone=phone,
        is_primary=True,
        notes=notes,
    )

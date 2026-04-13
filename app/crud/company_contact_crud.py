from sqlalchemy.orm import Session

from app.models.company_contact_model import CompanyContact


def get_company_contacts(db: Session, company_id: int):
    return (
        db.query(CompanyContact)
        .filter(CompanyContact.company_id == company_id)
        .order_by(CompanyContact.contact_type.asc(), CompanyContact.full_name.asc())
        .all()
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

from sqlalchemy.orm import Session

from app.models.company_model import Company


def get_all_companies(db: Session):
    return db.query(Company).order_by(Company.name.asc()).all()


def get_company_by_id(db: Session, company_id: int):
    return db.query(Company).filter(Company.id == company_id).first()


def update_company_profile(db: Session, company: Company, **fields):
    for field, value in fields.items():
        if hasattr(company, field):
            setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company

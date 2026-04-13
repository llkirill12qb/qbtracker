from sqlalchemy.orm import Session

from app.models.company_model import Company


def get_all_companies(
    db: Session,
    search: str | None = None,
    sort_by: str = "id",
    direction: str = "asc",
):
    query = db.query(Company)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(Company.name.ilike(search_pattern))

    sort_column = Company.name if sort_by == "name" else Company.id
    sort_expression = sort_column.desc() if direction == "desc" else sort_column.asc()

    return query.order_by(sort_expression).all()


def get_company_by_id(db: Session, company_id: int):
    return db.query(Company).filter(Company.id == company_id).first()


def update_company_profile(db: Session, company: Company, **fields):
    for field, value in fields.items():
        if hasattr(company, field):
            setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company

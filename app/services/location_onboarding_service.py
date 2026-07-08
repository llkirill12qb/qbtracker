import secrets

from sqlalchemy.orm import Session


def generate_location_onboarding_token(db: Session) -> str:
    from app.models.location_model import Location

    while True:
        token = secrets.token_urlsafe(24)
        exists = db.query(Location.id).filter(Location.onboarding_token == token).first()
        if not exists:
            return token


def ensure_location_onboarding_token(db: Session, location):
    if location.onboarding_token:
        return location

    location.onboarding_token = generate_location_onboarding_token(db)
    db.commit()
    db.refresh(location)
    return location


def ensure_all_location_onboarding_tokens(db: Session) -> int:
    from app.models.location_model import Location

    locations = db.query(Location).filter(Location.onboarding_token.is_(None)).all()
    for location in locations:
        location.onboarding_token = generate_location_onboarding_token(db)

    if locations:
        db.commit()

    return len(locations)

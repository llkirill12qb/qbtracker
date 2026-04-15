from sqlalchemy.orm import Session

from app.models.location_model import Location


def get_locations(db: Session, company_id: int, include_inactive: bool = False):
    query = db.query(Location).filter(Location.company_id == company_id)

    if not include_inactive:
        query = query.filter(Location.is_active.is_(True))

    return query.order_by(Location.name.asc()).all()


def get_location_by_id(db: Session, location_id: int, company_id: int):
    return (
        db.query(Location)
        .filter(
            Location.id == location_id,
            Location.company_id == company_id,
        )
        .first()
    )


def get_location_name_by_id(db: Session, location_id: int | None, company_id: int):
    if location_id is None:
        return None

    location = get_location_by_id(db, location_id, company_id)
    return location.name if location else None


def create_location(
    db: Session,
    company_id: int,
    name: str,
    timezone: str = "America/New_York",
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    address_line1: str | None = None,
    address_line2: str | None = None,
    postal_code: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    geo_radius_meters: float | None = None,
    is_active: bool = True,
):
    location = Location(
        company_id=company_id,
        name=name,
        timezone=timezone,
        country=country,
        state=state,
        city=city,
        address_line1=address_line1,
        address_line2=address_line2,
        postal_code=postal_code,
        latitude=latitude,
        longitude=longitude,
        geo_radius_meters=geo_radius_meters,
        is_active=is_active,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def update_location(db: Session, location: Location, **fields):
    for field, value in fields.items():
        if hasattr(location, field):
            setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.scan_service import process_scan, get_logs
from app.core.database import SessionLocal
from app.services.scan_service import process_scan

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/scan")
def scan_card(
    card_id: str,
    scan_source: str = "terminal_web",
    device_timezone: str | None = None,
    timezone_abbr: str | None = None,
    terminal_id: int | None = None,
    location_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_meters: float | None = None,
    db: Session = Depends(get_db),
):
    result, error = process_scan(
        db=db,
        card_id=card_id,
        scan_source=scan_source,
        device_timezone=device_timezone,
        timezone_abbr=timezone_abbr,
        terminal_id=terminal_id,
        location_id=location_id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
    )

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result

@router.get("/logs")
def logs(db: Session = Depends(get_db)):
    return get_logs(db)

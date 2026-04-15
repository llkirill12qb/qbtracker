from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.services.scan_service import process_scan, get_logs
from app.core.company_context import get_current_company_id
from app.core.database import SessionLocal
from app.core.security import require_terminal_access
from app.crud.terminal_crud import get_terminal_by_id, update_terminal_last_seen

router = APIRouter()


def resolve_scan_location_id(request: Request, location_id: int | None):
    if location_id is not None:
        return location_id

    session_location_id = request.session.get("location_id")
    if session_location_id is None:
        return None

    try:
        return int(session_location_id)
    except (TypeError, ValueError):
        return None


def resolve_scan_terminal_id(request: Request, terminal_id: int | None):
    if terminal_id is not None:
        return terminal_id

    session_terminal_id = request.session.get("terminal_id")
    if session_terminal_id is None:
        return None

    try:
        return int(session_terminal_id)
    except (TypeError, ValueError):
        return None


def resolve_scan_terminal(db: Session, company_id: int, terminal_id: int | None):
    if terminal_id is None:
        return None

    terminal = get_terminal_by_id(db, terminal_id, company_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    if not terminal.is_active:
        raise HTTPException(status_code=400, detail="Terminal is inactive")

    return terminal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/scan")
def scan_card(
    request: Request,
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
    require_terminal_access(request)
    company_id = get_current_company_id(request)
    scan_location_id = resolve_scan_location_id(request, location_id)
    scan_terminal_id = resolve_scan_terminal_id(request, terminal_id)
    scan_terminal = resolve_scan_terminal(db, company_id, scan_terminal_id)

    if scan_terminal and scan_terminal.location_id:
        scan_location_id = scan_terminal.location_id

    result, error = process_scan(
        db=db,
        card_id=card_id,
        company_id=company_id,
        scan_source=scan_source,
        device_timezone=device_timezone,
        timezone_abbr=timezone_abbr,
        terminal_id=scan_terminal_id,
        location_id=scan_location_id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
    )

    if error:
        raise HTTPException(status_code=404, detail=error)

    if scan_terminal:
        update_terminal_last_seen(db, scan_terminal)

    return result

@router.get("/logs")
def logs(request: Request, db: Session = Depends(get_db)):
    require_terminal_access(request)
    company_id = get_current_company_id(request)
    return get_logs(db, company_id)

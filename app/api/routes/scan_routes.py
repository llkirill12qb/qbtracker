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
def scan_card(card_id: str, db: Session = Depends(get_db)):
    result, error = process_scan(db, card_id)

    if error:
        raise HTTPException(status_code=404, detail=error)

    return result

@router.get("/logs")
def logs(db: Session = Depends(get_db)):
    return get_logs(db)
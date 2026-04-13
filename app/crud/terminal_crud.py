from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.terminal_model import Terminal


def get_terminals(db: Session, company_id: int, include_inactive: bool = False):
    query = db.query(Terminal).filter(Terminal.company_id == company_id)

    if not include_inactive:
        query = query.filter(Terminal.is_active.is_(True))

    return query.order_by(Terminal.name.asc()).all()


def get_terminal_by_id(db: Session, terminal_id: int, company_id: int):
    return (
        db.query(Terminal)
        .filter(
            Terminal.id == terminal_id,
            Terminal.company_id == company_id,
        )
        .first()
    )


def create_terminal(
    db: Session,
    company_id: int,
    name: str,
    location_id: int | None = None,
    device_name: str | None = None,
    timezone: str | None = None,
    status: str = "active",
    is_active: bool = True,
):
    terminal = Terminal(
        company_id=company_id,
        location_id=location_id,
        name=name,
        device_name=device_name,
        timezone=timezone,
        status=status,
        is_active=is_active,
    )
    db.add(terminal)
    db.commit()
    db.refresh(terminal)
    return terminal


def update_terminal(db: Session, terminal: Terminal, **fields):
    for field, value in fields.items():
        if hasattr(terminal, field):
            setattr(terminal, field, value)

    db.commit()
    db.refresh(terminal)
    return terminal


def update_terminal_last_seen(db: Session, terminal: Terminal):
    terminal.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(terminal)
    return terminal

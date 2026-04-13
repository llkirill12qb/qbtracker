from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user_model import User


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int, company_id: int | None = None):
    query = db.query(User).filter(User.id == user_id)
    if company_id is not None:
        query = query.filter(User.company_id == company_id)
    return query.first()


def get_users_by_company(db: Session, company_id: int):
    return (
        db.query(User)
        .filter(User.company_id == company_id)
        .order_by(User.role.asc(), User.username.asc())
        .all()
    )


def create_user(
    db: Session,
    username: str,
    password_hash: str,
    role: str,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    company_id: int | None = None,
    language: str = "en",
    is_active: bool = True,
):
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=role,
        company_id=company_id,
        language=language,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    user: User,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    role: str | None = None,
    language: str | None = None,
    is_active: bool | None = None,
):
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.phone = phone

    if role is not None:
        user.role = role
    if language is not None:
        user.language = language
    if is_active is not None:
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user: User, password_hash: str):
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return user


def update_last_login(db: Session, user: User):
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user

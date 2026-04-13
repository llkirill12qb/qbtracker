from sqlalchemy.orm import Session

from app.core.auth import SUPERADMIN_PASSWORD, SUPERADMIN_USERNAME, hash_password
from app.core.roles import ROLE_SUPER_ADMIN
from app.crud.user_crud import create_user, get_user_by_username


def ensure_superadmin_user(db: Session):
    existing_user = get_user_by_username(db, SUPERADMIN_USERNAME)
    if existing_user:
        return existing_user

    return create_user(
        db=db,
        username=SUPERADMIN_USERNAME,
        password_hash=hash_password(SUPERADMIN_PASSWORD),
        role=ROLE_SUPER_ADMIN,
        company_id=None,
        language="en",
        is_active=True,
    )

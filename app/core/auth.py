import os
import hashlib
import hmac
import secrets

from dotenv import load_dotenv

from app.core.roles import PLATFORM_ROLES
from app.crud.user_crud import get_user_by_username
from app.models.company_model import Company

load_dotenv()

SUPERADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME")
SUPERADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD")
SESSION_SECRET = os.getenv("SESSION_SECRET")


missing_env = [
    name
    for name, value in {
        "SUPERADMIN_USERNAME": SUPERADMIN_USERNAME,
        "SUPERADMIN_PASSWORD": SUPERADMIN_PASSWORD,
        "SESSION_SECRET": SESSION_SECRET,
    }.items()
    if not value
]

if missing_env:
    raise ValueError(
        "Missing required auth environment variables: " + ", ".join(missing_env)
    )


def verify_superadmin(username: str, password: str) -> bool:
    return username == SUPERADMIN_USERNAME and password == SUPERADMIN_PASSWORD


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        260000,
    ).hex()

    return f"pbkdf2_sha256$260000${salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, password_hash = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()

    return hmac.compare_digest(calculated_hash, password_hash)


def authenticate_user(db, username: str, password: str):
    user = get_user_by_username(db, username)

    if user and user.is_active and verify_password(password, user.password_hash):
        return user

    return None


def is_login_allowed_for_user(db, user) -> bool:
    if not user:
        return False

    if user.role in PLATFORM_ROLES or user.company_id is None:
        return True

    company = db.query(Company).filter(Company.id == user.company_id).first()
    return bool(company and company.status != "archived")


def is_authenticated(session: dict) -> bool:
    return bool(session.get("authenticated"))


def get_session_user(session: dict):
    if not is_authenticated(session):
        return None

    return {
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "role": session.get("role"),
        "company_id": session.get("company_id"),
        "location_id": session.get("location_id"),
        "terminal_id": session.get("terminal_id"),
        "auth_source": session.get("auth_source"),
    }

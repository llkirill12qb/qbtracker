import os

from dotenv import load_dotenv

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


def is_authenticated(session: dict) -> bool:
    return bool(session.get("authenticated"))

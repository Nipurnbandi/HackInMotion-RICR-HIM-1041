"""Create the first administrator from environment variables, if asked.

Hosted platforms often give no shell access, so `python -m scripts.create_admin`
isn't reachable on a fresh deploy. Setting ADMIN_EMAIL and ADMIN_PASSWORD lets
the container provision that first account on startup instead.

Safe to run on every boot: it does nothing when the variables are unset and
nothing when the account already exists.
"""
import os
import sys

from app.core.database import SessionLocal
from app.core.roles import Role
from app.core.security import hash_password
from app.models import User

MIN_PASSWORD_LENGTH = 8


def main() -> None:
    email = (os.getenv("ADMIN_EMAIL") or "").strip()
    password = os.getenv("ADMIN_PASSWORD") or ""

    if not email or not password:
        print("· admin bootstrap skipped (ADMIN_EMAIL / ADMIN_PASSWORD not set)")
        return

    if len(password) < MIN_PASSWORD_LENGTH:
        print(
            f"· admin bootstrap skipped: ADMIN_PASSWORD must be at least "
            f"{MIN_PASSWORD_LENGTH} characters",
            file=sys.stderr,
        )
        return

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"· admin bootstrap skipped: {email} already exists")
            return

        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                role=Role.ADMIN,
            )
        )
        db.commit()
        print(f"· created administrator {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

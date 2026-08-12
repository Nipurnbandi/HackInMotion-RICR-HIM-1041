"""Create an admin user via controlled server-side mechanism.

Usage:
    python -m scripts.create_admin admin@example.com SecurePass123
"""
import sys

from app.core.database import SessionLocal
from app.services.auth import create_admin_user


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_admin <email> <password>")
        sys.exit(1)

    email, password = sys.argv[1], sys.argv[2]
    db = SessionLocal()
    try:
        user = create_admin_user(db, email, password)
        print(f"Admin created: {user.email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()

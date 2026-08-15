"""Block until the configured database accepts connections.

A container starts in parallel with its database, and managed Postgres can
briefly refuse connections during a restart or failover. Alembic fails hard on
that, so establish a real connection before migrating.
"""
import sys
import time

from sqlalchemy import text

from app.core.database import engine

TIMEOUT_SECONDS = 60
RETRY_DELAY_SECONDS = 1.0


def main() -> None:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # driver, DNS and auth errors all retry alike
            last_error = exc
            time.sleep(RETRY_DELAY_SECONDS)
        else:
            print("· database is accepting connections")
            return

    print(
        f"· database unreachable after {TIMEOUT_SECONDS}s: {last_error}",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()

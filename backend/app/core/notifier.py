import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import settings


class Notifier(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleNotifier:
    def send(self, *, to: str, subject: str, body: str) -> None:
        print(f"[notification] to={to}")
        print(f"[notification] subject={subject}")
        print(body)


class EmailNotifier:
    def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)


def get_notifier() -> Notifier:
    if settings.notifier == "email":
        return EmailNotifier()
    return ConsoleNotifier()

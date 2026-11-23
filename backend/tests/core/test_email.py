import logging

import pytest

from app.config import settings
from app.core.email import ConsoleEmailSender, build_email_sender


def test_build_email_sender_returns_configured_console_sender(monkeypatch):
    monkeypatch.setattr(settings, "email_backend", "console")

    sender = build_email_sender()

    assert isinstance(sender, ConsoleEmailSender)


def test_build_email_sender_rejects_unknown_backend(monkeypatch):
    monkeypatch.setattr(settings, "email_backend", "smtp")

    with pytest.raises(ValueError, match="Unknown EMAIL_BACKEND"):
        build_email_sender()


async def test_console_sender_logs_verification_in_development(monkeypatch, caplog):
    monkeypatch.setattr(settings, "environment", "development")

    with caplog.at_level(logging.INFO):
        await ConsoleEmailSender().send_email_verification(
            to="joao@example.com",
            name="Joao",
            token="opaque-token",
        )

    assert "joao@example.com" in caplog.text
    assert "opaque-token" in caplog.text


async def test_console_sender_does_not_log_token_in_production(monkeypatch, caplog):
    monkeypatch.setattr(settings, "environment", "production")

    with caplog.at_level(logging.WARNING):
        await ConsoleEmailSender().send_email_verification(
            to="joao@example.com",
            name="Joao",
            token="opaque-token",
        )

    assert "No email provider configured" in caplog.text
    assert "opaque-token" not in caplog.text

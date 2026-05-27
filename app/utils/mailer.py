# app/utils/mailer.py
import ssl
import smtplib
from email.message import EmailMessage
from app.core.config import settings

async def send_email(subject: str, recipients: list[str], body: str):
    """
    Sends a plain-text email via SMTP. Falls back cleanly on errors.
    """
    # Build the message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = settings.mail_from
    msg["To"]      = ", ".join(recipients)
    msg.set_content(body)

    # SSL context
    ctx = ssl.create_default_context()

    try:
        if settings.mail_ssl_tls:
            # SSL on connect (port 465)
            with smtplib.SMTP_SSL(
                settings.mail_server,
                settings.mail_port,
                context=ctx,
            ) as server:
                server.login(settings.mail_username, settings.mail_password)
                server.send_message(msg)
        else:
            # STARTTLS (port 587)
            with smtplib.SMTP(
                settings.mail_server,
                settings.mail_port,
            ) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
                server.login(settings.mail_username, settings.mail_password)
                server.send_message(msg)
    except Exception as e:
        # In production you’d log this; for now, just print
        print("❌ SMTP send failed:", e)

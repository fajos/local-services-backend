# app/utils/mailer.py
import ssl
import smtplib
from email.message import EmailMessage
from app.core.config import settings

def send_email(subject: str, recipients: list[str], body: str):
    """
    Sends a plain-text email via SMTP using synchronous smtplib.
    FastAPI BackgroundTasks will handle running this in a thread.
    """
    # Build the message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = f"Local Service Finder <{settings.mail_from}>"
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
                timeout=20, # Increased timeout
            ) as server:
                server.login(settings.mail_username, settings.mail_password)
                server.send_message(msg)
        else:
            # STARTTLS (port 587)
            with smtplib.SMTP(
                settings.mail_server,
                settings.mail_port,
                timeout=20, # Increased timeout
            ) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
                server.login(settings.mail_username, settings.mail_password)
                server.send_message(msg)
        print(f"✅ Email sent successfully to {recipients}")
    except Exception as e:
        print(f"❌ SMTP send failed to {recipients}: {e}")

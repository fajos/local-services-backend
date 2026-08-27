# app/utils/mailer.py
import ssl
import smtplib
from email.message import EmailMessage
from app.core.config import settings

def send_email(subject: str, recipients: list[str], body: str):
    """
    Sends a plain-text email via SMTP.
    Includes debug logging to help identify where the connection hangs.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = f"Local Service Finder <{settings.mail_from}>"
    msg["To"]      = ", ".join(recipients)
    msg.set_content(body)

    ctx = ssl.create_default_context()
    server = None

    try:
        print(f"📧 Attempting to send email to {recipients} via {settings.mail_server}:{settings.mail_port}...")

        if settings.mail_ssl_tls:
            server = smtplib.SMTP_SSL(settings.mail_server, settings.mail_port, context=ctx, timeout=30)
        else:
            server = smtplib.SMTP(settings.mail_server, settings.mail_port, timeout=30)

        # Enable detailed debug output in Render logs
        server.set_debuglevel(1)

        if not settings.mail_ssl_tls:
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls(context=ctx)
                server.ehlo()

        server.login(settings.mail_username, settings.mail_password)
        server.send_message(msg)
        server.quit()

        print(f"✅ Email sent successfully to {recipients}")

    except Exception as e:
        print(f"❌ SMTP Error for {recipients}: {type(e).__name__}: {e}")
    finally:
        if server:
            try:
                server.close()
            except:
                pass

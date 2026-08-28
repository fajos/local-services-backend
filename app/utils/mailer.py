# app/utils/mailer.py
import emails
from app.core.config import settings

def send_email(subject: str, recipients: list[str], body: str):
    """
    Sends an email using the 'emails' library.
    Works perfectly with Brevo SMTP relay.
    """
    try:
        print(f"📧 Sending email to {recipients} via {settings.mail_server}:{settings.mail_port}...")

        # Create the email message
        message = emails.html(
            subject=subject,
            html=f"<p>{body.replace('\n', '<br>')}</p>",
            text=body,
            mail_from=("Local Service Finder", settings.mail_from)
        )

        # SMTP configuration
        smtp_params = {
            "host": settings.mail_server,
            "port": settings.mail_port,
            "user": settings.mail_username,
            "password": settings.mail_password,
            "tls": settings.mail_starttls,
            "ssl": settings.mail_ssl_tls,
            "timeout": 20
        }

        # Send the email
        response = message.send(to=recipients, smtp=smtp_params)

        if response.status_code == 250:
            print(f"✅ Email sent successfully to {recipients}")
        else:
            print(f"❌ SMTP Error: Status {response.status_code} - {response.error}")

    except Exception as e:
        print(f"❌ Failed to send email to {recipients}: {e}")

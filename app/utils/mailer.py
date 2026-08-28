# app/utils/mailer.py
import httpx
from app.core.config import settings

def send_email(subject: str, recipients: list[str], body: str):
    """
    Sends an email using Brevo's REST API v3.
    This bypasses SMTP port blocks on cloud platforms like Render.
    """
    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": settings.brevo_api_key
    }

    payload = {
        "sender": {"name": "Local Service Finder", "email": settings.mail_from},
        "to": [{"email": r} for r in recipients],
        "subject": subject,
        "htmlContent": f"<p>{body.replace('\n', '<br>')}</p>",
        "textContent": body
    }

    try:
        print(f"📧 Sending email to {recipients} via Brevo HTTP API...")

        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=20.0)

        if response.status_code in [201, 200, 202]:
            print(f"✅ Email sent successfully to {recipients}")
        else:
            print(f"❌ Brevo API Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Failed to send email to {recipients}: {e}")

import sys
import os

# Add the app directory to the path so we can import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.utils.mailer import send_email

def test_connection():
    print("--- Brevo HTTP API Diagnostic Tool ---")
    print(f"API Key: {settings.brevo_api_key[:10]}...{settings.brevo_api_key[-5:] if settings.brevo_api_key else ''}")
    print(f"From: {settings.mail_from}")
    print("---------------------------")

    recipient = input("Enter a test recipient email address: ")

    try:
        send_email(
            subject="Brevo API Diagnostic Test",
            recipients=[recipient],
            body="This is a test email to verify your Brevo HTTP API configuration."
        )
        print("\nCheck the console output above. If it shows '✅ Email sent successfully', you are good to go!")
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")

if __name__ == "__main__":
    test_connection()

import africastalking
from app.core.config import settings

# initialize once at startup
africastalking.initialize(
    username=settings.at_username,
    api_key=settings.at_api_key,
)
sms = africastalking.SMS

async def send_sms(to_number: str, body: str):
    """
    Send an SMS via Africa’s Talking.
    """
    # africastalking is sync, but safe in BackgroundTasks
    try:
        response = sms.send(
            message=body,
            recipients=[to_number],
            # optional: sender_id="YourBrand"
        )
        print("AT SMS response:", response)
    except Exception as e:
        print("❌ AT SMS failed:", e)

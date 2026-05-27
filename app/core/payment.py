import os, httpx, stripe
from typing import Literal

# Pick ONE gateway at runtime via env var
GatewayType = Literal["stripe", "paystack"]
GATEWAY: GatewayType = os.getenv("PAYOUT_GATEWAY", "stripe")

# ------------ Stripe Connect ------------
if GATEWAY == "stripe":
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    async def send_payout(
        amount_kobo: int,
        currency: str,
        provider_stripe_account: str,
        reference: str,
    ):
        """
        amount_kobo -> 100₦ == 10000 kobo
        currency    -> "ngn", "usd", …
        provider_stripe_account -> Connect account ID (acct_***)
        """
        try:
            payout = stripe.Transfer.create(
                amount     = amount_kobo,
                currency   = currency,
                destination= provider_stripe_account,
                metadata   = {"booking_ref": reference},
            )
            return True, payout.id
        except stripe.error.StripeError as e:
            return False, str(e)

# ------------ Paystack -------------
else:
    PAYSTACK_SK   = os.getenv("PAYSTACK_SECRET_KEY")
    PAYSTACK_URL  = "https://api.paystack.co/transfer"

    async def send_payout(
        amount_kobo: int,
        currency: str,
        provider_recipient_code: str,
        reference: str,
    ):
        """
        provider_recipient_code comes from Paystack Transfer Recipient API
        """
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SK}",
            "Content-Type": "application/json",
        }
        payload = {
            "source": "balance",
            "amount": amount_kobo,
            "currency": currency,
            "recipient": provider_recipient_code,
            "reference": reference,
            "reason": "Service payout",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(PAYSTACK_URL, json=payload, headers=headers)
        if r.status_code == 200 and r.json().get("status"):
            return True, r.json()["data"]["transfer_code"]
        return False, r.text

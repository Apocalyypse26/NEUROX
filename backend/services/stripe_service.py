import os
import stripe
from typing import Dict, Any, Optional

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

CREDIT_PACKAGES = {
    "credits_10": {"name": "10 Scans", "credits": 10, "price_cents": 1500, "price_display": "$15"},
    "credits_50": {"name": "50 Scans", "credits": 50, "price_cents": 4900, "price_display": "$49"},
    "credits_200": {"name": "200 Scans", "credits": 200, "price_cents": 9900, "price_display": "$99"},
}

SUBSCRIPTION_PLANS = {
    "prime_monthly": {"name": "Prime Operator", "credits_per_month": 999, "price_cents": 2900, "price_display": "$29/mo"},
}


class StripeService:
    def __init__(self):
        self.enabled = bool(stripe.api_key)
        if self.enabled:
            print("[STRIPE] Initialized with API key")
        else:
            print("[STRIPE] No API key found - payment features disabled")

    def create_checkout_session(
        self,
        package_id: str,
        user_id: str,
        email: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY.")

        if package_id not in CREDIT_PACKAGES:
            raise ValueError(f"Invalid package: {package_id}")

        pkg = CREDIT_PACKAGES[package_id]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"NEUROX {pkg['name']}",
                            "description": f"Add {pkg['credits']} analysis scans to your NEUROX account",
                        },
                        "unit_amount": pkg["price_cents"],
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            customer_email=email,
            metadata={
                "user_id": user_id,
                "package_id": package_id,
                "credits": pkg["credits"],
            },
        )

        return {"url": session.url, "session_id": session.id}

    def create_subscription_checkout(
        self,
        plan_id: str,
        user_id: str,
        email: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY.")

        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {plan_id}")

        plan = SUBSCRIPTION_PLANS[plan_id]

        # Create or retrieve Stripe price
        price = stripe.Price.create(
            currency="usd",
            unit_amount=plan["price_cents"],
            recurring={"interval": "month"},
            product_data={"name": f"NEUROX {plan['name']}"},
        )

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price.id, "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            customer_email=email,
            metadata={
                "user_id": user_id,
                "plan_id": plan_id,
            },
        )

        return {"url": session.url, "session_id": session.id}

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        if not self.enabled:
            raise ValueError("Stripe is not configured")

        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET not set")

        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            metadata = session.get("metadata", {})
            return {
                "event": "credits_purchased",
                "user_id": metadata.get("user_id"),
                "credits": int(metadata.get("credits", 0)),
                "package_id": metadata.get("package_id"),
                "session_id": session["id"],
            }

        elif event["type"] == "invoice.paid":
            invoice = event["data"]["object"]
            return {
                "event": "subscription_renewed",
                "customer_email": invoice.get("customer_email"),
                "amount": invoice.get("amount_paid"),
            }

        elif event["type"] == "customer.subscription.deleted":
            return {
                "event": "subscription_cancelled",
                "subscription_id": event["data"]["object"]["id"],
            }

        return {"event": event["type"]}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        if not self.enabled:
            raise ValueError("Stripe is not configured")
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "status": session.status,
            "payment_status": session.payment_status,
            "metadata": session.metadata,
        }


stripe_service = StripeService()

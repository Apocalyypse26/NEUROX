import os
import asyncio
import httpx
import stripe
from typing import Dict, Any, Optional
import threading
from datetime import datetime
import logging

logger = logging.getLogger("neurox.stripe")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_processed_webhooks: Dict[str, float] = {}
_webhook_lock = threading.Lock()
_WEBHOOK_EXPIRY_SECONDS = 86400

_cached_prices: Dict[str, str] = {}
_price_cache_lock = threading.Lock()


async def _activate_subscription(user_id: str, subscription_data: Dict[str, Any]) -> bool:
    """Activate/update user subscription in Supabase"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("[SUBSCRIPTION] Supabase credentials not configured")
        return False
    
    try:
        sub = subscription_data
        plan_info = SUBSCRIPTION_PLANS.get(sub.get("plan_id", ""), {})
        
        period_start = datetime.fromtimestamp(sub.get("current_period_start", 0))
        period_end = datetime.fromtimestamp(sub.get("current_period_end", 0))
        
        payload = {
            "p_user_id": user_id,
            "p_stripe_subscription_id": sub.get("subscription_id", ""),
            "p_stripe_customer_id": sub.get("customer_id", ""),
            "p_plan_id": sub.get("plan_id", ""),
            "p_plan_name": plan_info.get("name", "Unknown"),
            "p_scans_per_month": plan_info.get("scans_per_month", 0),
            "p_is_unlimited": plan_info.get("is_unlimited", False),
            "p_period_start": period_start.isoformat(),
            "p_period_end": period_end.isoformat()
        }
        
        async with asyncio.timeout(10):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/activate_subscription",
                    headers={
                        "apikey": SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code in (200, 201):
                    logger.info("[SUBSCRIPTION] Activated subscription for user %s: %s", user_id, sub.get("plan_id"))
                    return True
                else:
                    logger.error("[SUBSCRIPTION] Failed to activate: %s", response.text)
                    return False
    except Exception as e:
        logger.error("[SUBSCRIPTION] Error activating subscription: %s", e)
        return False


async def _cancel_subscription(user_id: str, subscription_id: str) -> bool:
    """Cancel user subscription in Supabase"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return False
    
    try:
        async with asyncio.timeout(10):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/cancel_subscription_immediately",
                    headers={
                        "apikey": SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "p_user_id": user_id,
                        "p_stripe_subscription_id": subscription_id
                    }
                )
                return response.status_code in (200, 201)
    except Exception as e:
        logger.error("[SUBSCRIPTION] Error cancelling: %s", e)
        return False


async def _add_credits_to_user(user_id: str, credits: int) -> bool:
    """Add credits to user account via Supabase RPC (service role)"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("[STRIPE] Supabase credentials not configured for credit addition")
        return False
    
    try:
        async with asyncio.timeout(10):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/buy_credits",
                    headers={
                        "apikey": SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={"amount": credits}
                )
                
                if response.status_code in (200, 201):
                    logger.info("[STRIPE] Added %s credits to user %s", credits, user_id)
                    return True
                else:
                    logger.error("[STRIPE] Failed to add credits: %s", response.text)
                    return False
    except Exception as e:
        logger.error("[STRIPE] Error adding credits: %s", e)
        return False


def _cleanup_expired_webhooks():
    import time
    current_time = time.time()
    expired = [
        event_id for event_id, timestamp in _processed_webhooks.items()
        if current_time - timestamp > _WEBHOOK_EXPIRY_SECONDS
    ]
    for event_id in expired:
        del _processed_webhooks[event_id]


def _is_webhook_processed(event_id: str) -> bool:
    return event_id in _processed_webhooks


def _mark_webhook_processed(event_id: str):
    import time
    _processed_webhooks[event_id] = time.time()
    _cleanup_expired_webhooks()


def _get_or_create_price(plan_id: str, price_cents: int, product_name: str) -> str:
    with _price_cache_lock:
        if plan_id in _cached_prices:
            return _cached_prices[plan_id]
        
        # Look up existing product first to avoid duplicates on restart
        existing_products = stripe.Product.list(
            active=True,
            limit=100
        )
        
        product_id = None
        for product in existing_products.auto_paging_iter():
            if product.name == f"NEUROX {product_name}":
                product_id = product.id
                break
        
        if not product_id:
            product = stripe.Product.create(
                name=f"NEUROX {product_name}",
                active=True,
            )
            product_id = product.id
        
        # Look up existing price
        existing_prices = stripe.Price.list(
            product=product_id,
            active=True,
            limit=100
        )
        
        for price in existing_prices.auto_paging_iter():
            if price.unit_amount == price_cents:
                _cached_prices[plan_id] = price.id
                return price.id
        
        # Create new price
        price = stripe.Price.create(
            currency="usd",
            unit_amount=price_cents,
            recurring={"interval": "month"},
            product=product_id,
        )
        
        _cached_prices[plan_id] = price.id
        
        return price.id

CREDIT_PACKAGES = {
    "starter": {"name": "Starter", "credits": 5, "price_cents": 999, "price_display": "$9.99"},
    "popular": {"name": "Popular", "credits": 20, "price_cents": 2499, "price_display": "$24.99"},
    "value": {"name": "Value", "credits": 50, "price_cents": 3999, "price_display": "$39.99"},
    "pro": {"name": "Pro", "credits": 100, "price_cents": 5999, "price_display": "$59.99"},
}

SUBSCRIPTION_PLANS = {
    "hobby_monthly": {
        "name": "Hobby",
        "scans_per_month": 50,
        "price_cents": 999,
        "price_display": "$9.99/mo",
        "is_unlimited": False
    },
    "pro_monthly": {
        "name": "Pro",
        "scans_per_month": 200,
        "price_cents": 2499,
        "price_display": "$24.99/mo",
        "is_unlimited": False
    },
    "enterprise_monthly": {
        "name": "Enterprise",
        "scans_per_month": 999999,
        "price_cents": 4999,
        "price_display": "$49.99/mo",
        "is_unlimited": True
    },
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

        price_id = _get_or_create_price(plan_id, plan["price_cents"], plan["name"])

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
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

    async def handle_webhook_async(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Async webhook handler - use this for async contexts"""
        if not self.enabled:
            raise ValueError("Stripe is not configured")

        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET not set")

        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

        event_id = event.get("id", "")
        
        with _webhook_lock:
            if _is_webhook_processed(event_id):
                logger.info("[WEBHOOK] Duplicate event: %s", event_id)
                return {"event": "duplicate", "message": "Event already processed"}
            
            _mark_webhook_processed(event_id)

        # Handle checkout.session.completed (both credits and subscriptions)
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            metadata = session.get("metadata", {})
            user_id = metadata.get("user_id")
            
            # Check if it's a subscription purchase
            plan_id = metadata.get("plan_id")
            if plan_id and plan_id in SUBSCRIPTION_PLANS:
                plan = SUBSCRIPTION_PLANS[plan_id]
                stripe_sub_id = session.get("subscription")
                stripe_customer_id = session.get("customer")
                
                # Get subscription details for period dates
                if stripe_sub_id:
                    try:
                        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                        current_period_start = stripe_sub.get("current_period_start", 0)
                        current_period_end = stripe_sub.get("current_period_end", 0)
                        
                        await _activate_subscription(user_id, {
                            "subscription_id": stripe_sub_id,
                            "customer_id": stripe_customer_id,
                            "plan_id": plan_id,
                            "current_period_start": current_period_start,
                            "current_period_end": current_period_end
                        })
                    except Exception as e:
                        logger.error("[WEBHOOK] Failed to activate subscription: %s", e)
                
                return {
                    "event": "subscription_purchased",
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "plan_name": plan.get("name"),
                    "session_id": session["id"],
                }
            
            # Handle credit purchase (one-time)
            credits = int(metadata.get("credits", 0))
            if user_id and credits > 0:
                await _add_credits_to_user(user_id, credits)
            
            return {
                "event": "credits_purchased",
                "user_id": user_id,
                "credits": credits,
                "package_id": metadata.get("package_id"),
                "session_id": session["id"],
            }

        # Handle subscription renewal (invoice paid)
        elif event["type"] == "invoice.paid":
            invoice = event["data"]["object"]
            stripe_sub_id = invoice.get("subscription")
            stripe_customer_id = invoice.get("customer")
            
            if stripe_sub_id:
                try:
                    stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                    plan_id = stripe_sub.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")
                    
                    # Find matching plan
                    matched_plan = None
                    sub_items = stripe_sub.get("items", {}).get("data", [])
                    if sub_items:
                        unit_amount = sub_items[0].get("price", {}).get("unit_amount", 0)
                        for pid, pinfo in SUBSCRIPTION_PLANS.items():
                            if str(pinfo.get("price_cents")) == str(unit_amount):
                                matched_plan = pid
                                break
                    
                    if matched_plan:
                        current_period_start = stripe_sub.get("current_period_start", 0)
                        current_period_end = stripe_sub.get("current_period_end", 0)
                        
                        # Find user by customer ID (need to query subscriptions table)
                        # For now, we log - in production you'd lookup user_id from customer_id
                        logger.info("[WEBHOOK] Subscription renewed: %s", stripe_sub_id)
                        
                except Exception as e:
                    logger.error("[WEBHOOK] Failed to process renewal: %s", e)
            
            return {
                "event": "subscription_renewed",
                "customer_email": invoice.get("customer_email"),
                "amount": invoice.get("amount_paid"),
            }

        # Handle subscription cancellation
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            stripe_sub_id = subscription.get("id")
            
            # Find and cancel subscription in our DB
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/cancel_subscription_immediately",
                        headers={
                            "apikey": SUPABASE_SERVICE_ROLE_KEY,
                            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "p_stripe_subscription_id": stripe_sub_id
                        }
                    )
            except Exception as e:
                logger.error("[WEBHOOK] Failed to cancel subscription: %s", e)
            
            return {
                "event": "subscription_cancelled",
                "subscription_id": stripe_sub_id,
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

    async def verify_session_and_credit(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Verify payment and add credits/subscription without webhooks.
        Called by frontend after Stripe redirect.
        """
        if not self.enabled:
            return {"success": False, "error": "Stripe not configured"}

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status != "paid":
                return {"success": False, "error": "Payment not completed", "status": session.payment_status}

            metadata = session.metadata or {}
            session_user_id = metadata.get("user_id")
            
            # Verify user matches
            if session_user_id != user_id:
                return {"success": False, "error": "User mismatch"}

            # Check if it's a subscription
            plan_id = metadata.get("plan_id")
            if plan_id and plan_id in SUBSCRIPTION_PLANS:
                plan = SUBSCRIPTION_PLANS[plan_id]
                stripe_sub_id = session.subscription
                stripe_customer_id = session.customer

                if stripe_sub_id:
                    try:
                        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                        current_period_start = stripe_sub.current_period_start
                        current_period_end = stripe_sub.current_period_end
                        
                        period_start = datetime.fromtimestamp(current_period_start)
                        period_end = datetime.fromtimestamp(current_period_end)

                        await _activate_subscription(user_id, {
                            "subscription_id": stripe_sub_id,
                            "customer_id": stripe_customer_id,
                            "plan_id": plan_id,
                            "current_period_start": current_period_start,
                            "current_period_end": current_period_end
                        })

                        return {
                            "success": True,
                            "type": "subscription",
                            "plan_id": plan_id,
                            "plan_name": plan.get("name"),
                            "scans_per_month": plan.get("scans_per_month"),
                            "is_unlimited": plan.get("is_unlimited")
                        }
                    except Exception as e:
                        logger.error("[VERIFY] Failed to activate subscription: %s", e)
                        return {"success": False, "error": str(e)}

            # Handle credit purchase
            credits = int(metadata.get("credits", 0))
            if credits > 0:
                success = await _add_credits_to_user(user_id, credits)
                if success:
                    return {
                        "success": True,
                        "type": "credits",
                        "credits": credits
                    }
                else:
                    return {"success": False, "error": "Failed to add credits"}

            return {"success": False, "error": "No credits or subscription found"}

        except stripe.error.InvalidRequestError:
            return {"success": False, "error": "Invalid session ID"}
        except stripe.error.AuthenticationError:
            return {"success": False, "error": "Stripe authentication failed"}
        except Exception as e:
            logger.error("[VERIFY] Error verifying session: %s", e)
            return {"success": False, "error": str(e)}


stripe_service = StripeService()

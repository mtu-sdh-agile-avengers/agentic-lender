"""Checks that the Stripe sandbox is set up (ALG4-101): keys, a test payment, and the webhook secret.

Reads STRIPE_* from `api/.env` (or the environment), refuses live keys, then asks Stripe for two €1 test payments with
Stripe's test payment methods: one that succeeds (`pm_card_visa`) and one that is declined
(`pm_card_chargeDeclined`). Only test money is involved; nothing is written to Firestore.

Usage (from `api/`):
    uv run python -m src.scripts.stripe_sandbox_check

If `stripe listen` is running, the two payments also show up there as webhook events.
"""

import asyncio
import os
import sys

import stripe

from src.payments.gateway import (
    TEST_PUBLISHABLE_PREFIX,
    TEST_SECRET_PREFIXES,
    LiveStripeKeyError,
    ensure_sandbox_keys,
)


async def _try_payment(client: stripe.StripeClient, payment_method: str) -> str:
    """Creates and confirms a €1 PaymentIntent; returns its status or the decline message."""
    try:
        intent = await client.v1.payment_intents.create_async(
            params={
                "amount": 100,
                "currency": "eur",
                "payment_method": payment_method,
                "confirm": True,
                "description": "Agentic Lender sandbox check",
                "metadata": {"source": "stripe_sandbox_check"},
                # test payment methods need no redirect; without this Stripe asks for a return_url
                "automatic_payment_methods": {
                    "enabled": True,
                    "allow_redirects": "never",
                },
            }
        )
        return f"{intent['status']} ({intent['id']})"
    except stripe.CardError as exc:
        return f"declined: {exc.user_message}"


async def check() -> int:
    os.environ.setdefault("RUN_MODE", "dev")
    os.environ.setdefault("CORS_ORIGINS", "[]")
    from src.config import get_config

    config = get_config()
    ok = True

    def line(passed: bool, text: str) -> None:
        nonlocal ok
        ok = ok and passed
        print(f"[{'ok' if passed else 'FAIL'}] {text}")

    try:
        ensure_sandbox_keys(config)
    except LiveStripeKeyError as exc:
        line(False, str(exc))
        return 1

    secret, publishable = config.stripe_secret_key, config.stripe_publishable_key
    line(
        secret.startswith(TEST_SECRET_PREFIXES), "STRIPE_SECRET_KEY is a test-mode key"
    )
    line(
        publishable.startswith(TEST_PUBLISHABLE_PREFIX),
        "STRIPE_PUBLISHABLE_KEY is a test-mode key",
    )
    line(
        config.stripe_webhook_secret.startswith("whsec_"),
        "STRIPE_WEBHOOK_SECRET is set (from `stripe listen` or the Dashboard)",
    )
    if not secret.startswith(TEST_SECRET_PREFIXES):
        print("Set the keys first: docs/api/payments.md, 'Set up the sandbox'.")
        return 1

    client = stripe.StripeClient(secret, http_client=stripe.HTTPXClient())
    try:
        succeeded = await _try_payment(client, "pm_card_visa")
        declined = await _try_payment(client, "pm_card_chargeDeclined")
    except stripe.AuthenticationError:
        line(False, "Stripe rejected STRIPE_SECRET_KEY (wrong or revoked key)")
        return 1
    except stripe.APIConnectionError:
        line(False, "Stripe could not be reached (network or proxy)")
        return 1

    line(
        succeeded.startswith("succeeded"),
        f"test payment with 4242 4242 4242 4242: {succeeded}",
    )
    line(
        declined.startswith("declined"),
        f"test payment with a declined card: {declined}",
    )
    print(
        "Both payments are in the Dashboard: https://dashboard.stripe.com/test/payments"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(check()))

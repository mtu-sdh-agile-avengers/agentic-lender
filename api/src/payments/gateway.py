"""Stripe sandbox (ALG4-101): the only place AL-Core talks to Stripe.

Flow for the mobile app (Stripe PaymentSheet):
1. AL-Core creates a PaymentIntent for the fee (`create_payment_intent`) and gives the app its `client_secret` and the
   publishable key; the secret key never leaves AL-Core.
2. The app shows Stripe's payment sheet; the card goes straight from the phone to Stripe.
3. Stripe tells AL-Core the outcome through a signed webhook (`parse_webhook`, then `payments.webhooks.to_update`).

Outside production only test-mode keys are accepted, so the sandbox can never move real money.
"""

from dataclasses import dataclass
from typing import Any

import stripe

from src.config import Config, RunMode
from src.payments.exceptions import (
    PaymentProviderError,
    PaymentsNotConfiguredError,
    PaymentWebhookSignatureError,
)

TEST_SECRET_PREFIXES = ("sk_test_", "rk_test_")  # secret or restricted test key
TEST_PUBLISHABLE_PREFIX = "pk_test_"


class LiveStripeKeyError(ValueError):
    """A live (real money) Stripe key was configured outside production."""


def ensure_sandbox_keys(config: Config) -> None:
    """Refuses live Stripe keys unless AL-Core runs in production.

    Raises:
        LiveStripeKeyError: if RUN_MODE is not `prod` and a key is not a test-mode key.
    """
    if config.run_mode == RunMode.PROD:
        return
    secret, publishable = config.stripe_secret_key, config.stripe_publishable_key
    if secret and not secret.startswith(TEST_SECRET_PREFIXES):
        raise LiveStripeKeyError(
            "STRIPE_SECRET_KEY must be a test-mode key (sk_test_...) outside production"
        )
    if publishable and not publishable.startswith(TEST_PUBLISHABLE_PREFIX):
        raise LiveStripeKeyError(
            "STRIPE_PUBLISHABLE_KEY must be a test-mode key (pk_test_...) outside production"
        )


@dataclass(frozen=True)
class StripeIntent:
    """The part of a Stripe PaymentIntent AL-Core needs."""

    id: str  # pi_...
    client_secret: str  # given to the mobile app only, to open the payment sheet
    status: str  # Stripe's own status, e.g. requires_payment_method, succeeded
    amount: int  # in cents
    currency: str


def _intent(raw: Any) -> StripeIntent:
    return StripeIntent(
        id=raw["id"],
        client_secret=raw["client_secret"],
        status=raw["status"],
        amount=raw["amount"],
        currency=raw["currency"],
    )


class StripeGateway:
    def __init__(
        self,
        secret_key: str,
        publishable_key: str,
        webhook_secret: str = "",
        *,
        client: Any = None,  # tests pass a fake with `.v1.payment_intents` and `.construct_event`
    ) -> None:
        self.publishable_key = publishable_key
        self._webhook_secret = webhook_secret
        self._client = client
        if self._client is None and secret_key:
            self._client = stripe.StripeClient(
                secret_key, http_client=stripe.HTTPXClient(), max_network_retries=2
            )

    @classmethod
    def from_config(cls, config: Config) -> StripeGateway:
        ensure_sandbox_keys(config)
        return cls(
            config.stripe_secret_key,
            config.stripe_publishable_key,
            config.stripe_webhook_secret,
        )

    @property
    def configured(self) -> bool:
        return self._client is not None and bool(self.publishable_key)

    def _require_client(self) -> Any:
        if not self.configured:
            raise PaymentsNotConfiguredError
        return self._client

    async def create_payment_intent(
        self,
        *,
        payment_id: str,
        amount_cents: int,
        currency: str,
        description: str,
        metadata: dict[str, str],
    ) -> StripeIntent:
        """Creates the PaymentIntent of one payment.

        The payment ID is the idempotency key, so a retried request (e.g. after a timeout) returns the same
        PaymentIntent instead of charging twice; it is also in the metadata, so the Dashboard shows which payment
        an intent belongs to.

        Raises:
            PaymentsNotConfiguredError: if no Stripe keys are set (503).
            PaymentProviderError: if Stripe rejects the request or cannot be reached (502).
        """
        client = self._require_client()
        params = {
            "amount": amount_cents,
            "currency": currency,
            "description": description,
            "metadata": {**metadata, "payment_id": payment_id},
            # card plus whatever the Dashboard enables (Google Pay, ...); the payment sheet shows them
            "automatic_payment_methods": {"enabled": True},
        }
        try:
            raw = await client.v1.payment_intents.create_async(
                params=params, options={"idempotency_key": f"payment-{payment_id}"}
            )
        except stripe.StripeError as exc:
            raise PaymentProviderError(exc.user_message or type(exc).__name__) from exc
        return _intent(raw)

    async def retrieve_payment_intent(self, payment_intent_id: str) -> StripeIntent:
        """Reads a PaymentIntent again, e.g. to give the app its client secret for a payment that is still open."""
        client = self._require_client()
        try:
            raw = await client.v1.payment_intents.retrieve_async(payment_intent_id)
        except stripe.StripeError as exc:
            raise PaymentProviderError(exc.user_message or type(exc).__name__) from exc
        return _intent(raw)

    def parse_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        """Verifies a webhook request and returns the event.

        Stripe signs every webhook with the endpoint's secret (`Stripe-Signature` header); anything without a valid,
        recent signature is rejected, so nobody can mark a payment as paid by calling the endpoint directly.

        Returns:
            dict[str, Any]: the event (`id`, `type`, `created`, `data.object`, ...).

        Raises:
            PaymentsNotConfiguredError: if STRIPE_WEBHOOK_SECRET is not set (503).
            PaymentWebhookSignatureError: if the signature is missing, wrong or too old (400).
        """
        if not self._webhook_secret:
            raise PaymentsNotConfiguredError
        try:
            event = stripe.Webhook.construct_event(
                payload, signature or "", self._webhook_secret
            )
        except (stripe.SignatureVerificationError, ValueError) as exc:
            raise PaymentWebhookSignatureError from exc
        return event.to_dict()

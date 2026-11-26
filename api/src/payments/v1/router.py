from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, Response, status

from src.auth.dependencies import BorrowerDep
from src.config import get_config
from src.payments.dependencies import PaymentServiceDep
from src.payments.v1.schemas import (
    PaymentCheckoutResponse,
    PaymentCreateBody,
    PaymentFilterQuery,
    PaymentResponse,
    WebhookAckResponse,
)
from src.rate_limiting import limiter
from src.schemas import PaginatedResponse

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


# POST /api/v1/payments
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description=(
        "Starts paying a fee of one of the borrower's loan applications (retail borrower). Returns the pending "
        "payment and what Stripe's PaymentSheet needs. If this fee has an unpaid payment already, that payment is "
        "returned (200) instead of a new one (201), so retrying never charges twice. The amount is set by AL-Core."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "An unpaid payment of this fee was reused",
            "model": PaymentCheckoutResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Loan application not found among the borrower's"
        },
        status.HTTP_409_CONFLICT: {
            "description": "Fee already paid, or the application is closed"
        },
        status.HTTP_502_BAD_GATEWAY: {"description": "Stripe rejected the request"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Payments are not configured (no Stripe keys)"
        },
    },
)
@limiter.limit("10/minute")
async def start_payment(
    request: Request,
    response: Response,
    data: PaymentCreateBody,
    current_user: BorrowerDep,
    service: PaymentServiceDep,
) -> PaymentCheckoutResponse:
    checkout = await service.start(
        current_user,
        loan_application_id=data.loan_application_id,
        fee_type=data.fee_type,
    )
    if not checkout.created:
        response.status_code = status.HTTP_200_OK
    return PaymentCheckoutResponse.from_checkout(
        checkout, get_config().payments_merchant_name
    )


# GET /api/v1/payments
@router.get(
    "",
    description="Returns the borrower's payment history, newest first; optionally of one loan application.",
)
@limiter.limit("60/minute")
async def get_payment_history(
    request: Request,
    filters: Annotated[PaymentFilterQuery, Query()],
    current_user: BorrowerDep,
    service: PaymentServiceDep,
) -> PaginatedResponse[PaymentResponse]:
    page = await service.get_history(current_user, **filters.model_dump())
    return PaginatedResponse[PaymentResponse].build(
        items=[PaymentResponse.from_model(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
    )


# GET /api/v1/payments/{payment_id}
@router.get(
    "/{payment_id}",
    description="Returns one of the borrower's payments; the app polls it after Stripe's payment sheet closes.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Payment not found among the borrower's"
        }
    },
)
@limiter.limit("120/minute")
async def get_payment(
    request: Request,
    payment_id: str,
    current_user: BorrowerDep,
    service: PaymentServiceDep,
) -> PaymentResponse:
    return PaymentResponse.from_model(await service.get(current_user, payment_id))


# POST /api/v1/payments/webhooks/stripe
@router.post(
    "/webhooks/stripe",
    description=(
        "Stripe webhook (called by Stripe, not by clients). No bearer token: accepted only with a valid "
        "`Stripe-Signature` header. Events about unknown payments are acknowledged and ignored."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Missing or invalid Stripe-Signature"
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "STRIPE_WEBHOOK_SECRET is not set"
        },
    },
)
async def stripe_webhook(
    request: Request,
    service: PaymentServiceDep,
    stripe_signature: Annotated[str | None, Header()] = None,
) -> WebhookAckResponse:
    # the raw body: the signature is computed over the exact bytes Stripe sent
    await service.handle_webhook(await request.body(), stripe_signature)
    return WebhookAckResponse()

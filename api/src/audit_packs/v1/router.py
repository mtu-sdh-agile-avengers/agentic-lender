from typing import Annotated

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response

from src.audit_packs.content import build_content
from src.audit_packs.dependencies import AuditPackServiceDep
from src.audit_packs.enums import AuditPackFormat
from src.audit_packs.rendering import render_csv, render_pdf
from src.audit_packs.v1.schemas import AuditPackQuery
from src.auth.dependencies import BankOfficerDep
from src.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/loan-applications", tags=["audit-packs"])

FINGERPRINT_HEADER = "X-Audit-Pack-SHA256"

_MEDIA_TYPES = {
    AuditPackFormat.PDF: "application/pdf",
    AuditPackFormat.CSV: "text/csv; charset=utf-8",
}


# GET /api/v1/loan-applications/{loan_application_id}/audit-pack
@router.get(
    "/{loan_application_id}/audit-pack",
    response_class=Response,
    description=(
        "Downloads the audit pack of a decided loan application (assigned bank officer): the application, "
        "borrower, status history, lending decision, the AI committee's decision, votes, verified figures and "
        f"reasoning steps, and a SHA-256 fingerprint of the record (also in the `{FINGERPRINT_HEADER}` header). "
        "`format=pdf` (default) or `format=csv`."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "The audit pack as a file attachment",
            "content": {"application/pdf": {}, "text/csv": {}},
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "The bank officer is not assigned to the application"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Loan application does not exist"},
        status.HTTP_409_CONFLICT: {
            "description": "No lending decision has been made yet"
        },
    },
)
@limiter.limit("20/minute")
async def download_audit_pack(
    request: Request,
    loan_application_id: str,
    query: Annotated[AuditPackQuery, Query()],
    current_user: BankOfficerDep,
    service: AuditPackServiceDep,
) -> Response:
    pack = await service.build(current_user, loan_application_id)
    content = build_content(pack)
    body = (
        render_pdf(content)
        if query.format is AuditPackFormat.PDF
        else render_csv(content)
    )
    filename = f"audit-pack-{loan_application_id}.{query.format}"
    return Response(
        content=body,
        media_type=_MEDIA_TYPES[query.format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            FINGERPRINT_HEADER: pack.fingerprint,
            "Cache-Control": "no-store",  # personal data: do not keep copies in shared caches
        },
    )

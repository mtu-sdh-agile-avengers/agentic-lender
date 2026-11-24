from src.audit_packs.enums import AuditPackFormat
from src.schemas import QuerySchema


class AuditPackQuery(QuerySchema):
    """Query parameters of `GET /api/v1/loan-applications/{id}/audit-pack`."""

    format: AuditPackFormat = AuditPackFormat.PDF

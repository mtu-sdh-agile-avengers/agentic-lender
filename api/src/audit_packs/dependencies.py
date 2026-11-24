from typing import Annotated

from fastapi import Depends

from src.assessments.repository import AssessmentFirestoreRepository
from src.audit_packs.service import AuditPackService
from src.firebase.dependencies import FirestoreDep
from src.loan_applications.gateways import UserInfoSearchGateway
from src.loan_applications.repository import LoanApplicationFirestoreRepository
from src.users.repository import UserProfileFirestoreRepository


def get_audit_pack_service(db: FirestoreDep) -> AuditPackService:
    return AuditPackService(
        LoanApplicationFirestoreRepository(db),
        UserInfoSearchGateway(UserProfileFirestoreRepository(db)),
        AssessmentFirestoreRepository(db),
    )


AuditPackServiceDep = Annotated[AuditPackService, Depends(get_audit_pack_service)]

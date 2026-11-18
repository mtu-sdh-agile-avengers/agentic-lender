from typing import Annotated

from fastapi import Depends

from src.firebase.dependencies import FirestoreDep
from src.loan_applications.gateways import UserInfoSearchGateway
from src.loan_applications.repository import LoanApplicationFirestoreRepository
from src.loan_applications.service import LoanApplicationService
from src.users.repository import UserProfileFirestoreRepository


def get_loan_application_service(db: FirestoreDep) -> LoanApplicationService:
    return LoanApplicationService(
        LoanApplicationFirestoreRepository(db),
        UserInfoSearchGateway(UserProfileFirestoreRepository(db)),
    )


LoanApplicationServiceDep = Annotated[
    LoanApplicationService, Depends(get_loan_application_service)
]

from typing import Annotated

from fastapi import Depends

from src.firebase.dependencies import FirestoreDep
from src.loan_applications.repository import LoanApplicationFirestoreRepository
from src.stress_tests.repository import StressTestFirestoreRepository
from src.stress_tests.service import StressTestService


def get_stress_test_service(db: FirestoreDep) -> StressTestService:
    return StressTestService(
        LoanApplicationFirestoreRepository(db),
        StressTestFirestoreRepository(db),
    )


StressTestServiceDep = Annotated[StressTestService, Depends(get_stress_test_service)]

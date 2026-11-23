from typing import Annotated

from fastapi import Depends

from src.ai_engine_client.dependencies import AIEngineClientDep
from src.assessments.repository import AssessmentFirestoreRepository
from src.assessments.service import AssessmentService
from src.firebase.dependencies import FirestoreDep
from src.loan_applications.repository import LoanApplicationFirestoreRepository


def get_assessment_service(
    db: FirestoreDep, ai_engine: AIEngineClientDep
) -> AssessmentService:
    return AssessmentService(
        LoanApplicationFirestoreRepository(db),
        AssessmentFirestoreRepository(db),
        ai_engine,
    )


AssessmentServiceDep = Annotated[AssessmentService, Depends(get_assessment_service)]

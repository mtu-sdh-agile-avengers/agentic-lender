from src.audit_packs.exceptions import AuditPackNotAvailableError
from src.audit_packs.models import AuditPackModel
from src.audit_packs.ports import AuditAssessmentReaderPort
from src.auth.models import CurrentUserModel
from src.loan_applications.access import has_modify_access
from src.loan_applications.exceptions import (
    LoanApplicationAccessError,
    LoanApplicationNotFoundError,
)
from src.loan_applications.ports import (
    LoanApplicationRepositoryPort,
    UserInfoSearchGatewayPort,
)


class AuditPackService:
    def __init__(
        self,
        applications: LoanApplicationRepositoryPort,
        users: UserInfoSearchGatewayPort,
        assessments: AuditAssessmentReaderPort,
    ) -> None:
        self._applications = applications
        self._users = users
        self._assessments = assessments

    async def build(
        self, current_user: CurrentUserModel, loan_application_id: str
    ) -> AuditPackModel:
        """Collects the audit pack of a decided loan application (ALG4-237).

        Args:
            current_user: underwriting bank officer assigned to the application.
            loan_application_id: ID of the loan application.

        Returns:
            AuditPackModel: the application, the borrower, the latest AI committee run with its reasoning steps.

        Raises:
            LoanApplicationNotFoundError: if the application does not exist (404).
            LoanApplicationAccessError: if the officer is not assigned to it (403).
            AuditPackNotAvailableError: if no lending decision has been made yet (409).
        """
        application = await self._applications.get_loan_application(loan_application_id)
        if application is None:
            raise LoanApplicationNotFoundError(loan_application_id)

        if not has_modify_access(current_user, application):
            raise LoanApplicationAccessError(loan_application_id)

        if application.decision is None:
            raise AuditPackNotAvailableError(loan_application_id)

        assessment, steps = None, []
        if application.assessment_id is not None:
            assessment = await self._assessments.get_assessment(
                loan_application_id, application.assessment_id
            )
            if assessment is not None:
                steps = await self._assessments.get_agent_steps(
                    loan_application_id, application.assessment_id
                )

        return AuditPackModel(
            application=application,
            borrower=await self._users.find_user(application.borrower_id),
            assessment=assessment,
            agent_steps=steps,
            generated_by_id=current_user.uid,
        )

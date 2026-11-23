from typing import Protocol

from src.assessments.models import AgentStepModel, AssessmentModel


class AuditAssessmentReaderPort(Protocol):
    async def get_assessment(
        self, loan_application_id: str, assessment_id: str
    ) -> AssessmentModel | None: ...
    async def get_agent_steps(
        self, loan_application_id: str, assessment_id: str
    ) -> list[AgentStepModel]: ...

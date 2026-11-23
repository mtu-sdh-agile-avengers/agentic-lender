from typing import Any, Protocol

from src.ai_engine_client.client import DeliberationJob
from src.assessments.models import AgentStepModel, AssessmentModel


class AssessmentRepositoryPort(Protocol):
    def next_id(self, loan_application_id: str) -> str: ...

    async def add_assessment(self, assessment: AssessmentModel) -> None: ...
    async def get_assessment(
        self, loan_application_id: str, assessment_id: str
    ) -> AssessmentModel | None: ...

    async def get_agent_steps(
        self, loan_application_id: str, assessment_id: str
    ) -> list[AgentStepModel]: ...
    async def save_result(
        self,
        loan_application_id: str,
        assessment_id: str,
        fields: dict[str, Any],
        steps: list[AgentStepModel],
    ) -> None: ...


# the part of AIEngineClient the assessment service needs (tests pass a fake)
class CommitteeGatewayPort(Protocol):
    async def start_deliberation(
        self, application: dict[str, Any]
    ) -> DeliberationJob: ...
    async def get_deliberation(self, job_id: str) -> DeliberationJob | None: ...

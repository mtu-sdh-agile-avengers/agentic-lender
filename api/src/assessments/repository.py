from typing import Any

from google.cloud.firestore import AsyncClient, AsyncDocumentReference, AsyncWriteBatch

from src.assessments.models import AgentStepModel, AssessmentModel
from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository

# upper bound of reasoning steps read for one run (the committee graph has about six nodes)
MAX_AGENT_STEPS = 50


class AssessmentCollectionRepository(FirestoreRepository[AssessmentModel]):
    """Runs of one loan application: `loan_applications/{loan_application_id}/assessments`.

    A short-lived object: created for one loan application whenever it is needed (no network call).
    """

    col = CollectionPath.ASSESSMENTS

    def __init__(self, db: AsyncClient, loan_application_id: str) -> None:
        super().__init__(
            db,
            parent=db.collection(CollectionPath.LOAN_APPLICATIONS).document(
                loan_application_id
            ),
        )
        self._loan_application_id = loan_application_id

    def _to_doc(self, entity: AssessmentModel) -> dict[str, Any]:
        # both IDs are in the path: the document name and the parent document
        return entity.model_dump(exclude={"assessment_id", "loan_application_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> AssessmentModel:
        return AssessmentModel.model_validate(
            {
                **data,
                "assessment_id": doc_id,
                "loan_application_id": self._loan_application_id,
            }
        )

    def next_id(self) -> str:
        """Generates a new assessment ID locally (no network call, nothing is written)."""
        return self._col_ref.document().id

    def document(self, assessment_id: str) -> AsyncDocumentReference:
        """Reference to one assessment document (no network call)."""
        return self._col_ref.document(assessment_id)

    async def add(self, assessment: AssessmentModel) -> None:
        """Creates the assessment document; raises `Conflict` if it already exists."""
        await self._add(assessment.assessment_id, assessment)

    async def get(self, assessment_id: str) -> AssessmentModel | None:
        """Reads one assessment; `None` if it does not exist."""
        return await self._get(assessment_id)

    def steps(self, assessment_id: str) -> AgentStepCollectionRepository:
        """Reasoning steps of one assessment of this application."""
        return AgentStepCollectionRepository(
            self._db, parent=self.document(assessment_id)
        )


class AgentStepCollectionRepository(FirestoreRepository[AgentStepModel]):
    """Reasoning steps of one run: `.../assessments/{assessment_id}/agent_steps`."""

    col = CollectionPath.AGENT_STEPS

    def _to_doc(self, entity: AgentStepModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"agent_step_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> AgentStepModel:
        return AgentStepModel.model_validate({**data, "agent_step_id": doc_id})

    async def ordered(self) -> list[AgentStepModel]:
        """Reads all steps in the order the agents ran."""
        return await self._stream(
            self._col_ref.order_by("step_number").limit(MAX_AGENT_STEPS)
        )

    def write(self, batch: AsyncWriteBatch, step: AgentStepModel) -> None:
        """Adds one step to a batch (written on `batch.commit()`).

        The ID comes from the step number (`001`, `002`, ...), so saving the same result twice
        (two concurrent polls) overwrites the steps instead of duplicating them.
        """
        batch.set(self._col_ref.document(f"{step.step_number:03d}"), self._to_doc(step))


class AssessmentFirestoreRepository:
    """`AssessmentRepositoryPort` takes the loan application ID in every method, while a `FirestoreRepository` is bound
    to one collection; so this class builds a short-lived `AssessmentCollectionRepository` per call and delegates.
    """

    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _of(self, loan_application_id: str) -> AssessmentCollectionRepository:
        return AssessmentCollectionRepository(self._db, loan_application_id)

    def next_id(self, loan_application_id: str) -> str:
        """Generates a new assessment ID without writing anything (no network call)."""
        return self._of(loan_application_id).next_id()

    async def add_assessment(self, assessment: AssessmentModel) -> None:
        """Creates the assessment document.

        Raises:
            google.cloud.exceptions.Conflict: if a document with this ID already exists.
        """
        await self._of(assessment.loan_application_id).add(assessment)

    async def get_assessment(
        self, loan_application_id: str, assessment_id: str
    ) -> AssessmentModel | None:
        """Reads one assessment; `None` if the document does not exist."""
        return await self._of(loan_application_id).get(assessment_id)

    async def get_agent_steps(
        self, loan_application_id: str, assessment_id: str
    ) -> list[AgentStepModel]:
        """Reads the reasoning steps of one assessment, ordered by `step_number`; empty until it is done."""
        return await self._of(loan_application_id).steps(assessment_id).ordered()

    async def save_result(
        self,
        loan_application_id: str,
        assessment_id: str,
        fields: dict[str, Any],
        steps: list[AgentStepModel],
    ) -> None:
        """Updates the assessment and writes its reasoning steps in one atomic batch.

        Either everything is written or nothing is: a verdict is never stored without its steps.
        Also used for partial updates (status change, failure) with an empty `steps` list.

        Raises:
            google.cloud.exceptions.NotFound: if the assessment document does not exist.
        """
        assessments = self._of(loan_application_id)
        step_collection = assessments.steps(assessment_id)

        batch = self._db.batch()
        batch.update(assessments.document(assessment_id), fields)
        for step in steps:
            step_collection.write(batch, step)
        await batch.commit()

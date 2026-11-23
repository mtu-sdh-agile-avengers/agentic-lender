from typing import Any

from google.cloud.firestore import FieldFilter

from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository
from src.stress_tests.models import StressTestModel

# upper bound of runs read for one user before sorting in memory (no composite index needed)
MAX_STRESS_TESTS_SCAN = 200


class StressTestFirestoreRepository(FirestoreRepository[StressTestModel]):
    col = CollectionPath.STRESS_TESTS

    def _to_doc(self, entity: StressTestModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"stress_test_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> StressTestModel:
        return StressTestModel.model_validate({**data, "stress_test_id": doc_id})

    def next_id(self) -> str:
        return self._col_ref.document().id  # generated locally by SDK

    async def add_stress_test(self, stress_test: StressTestModel) -> None:
        """Stores a new stress test run.

        Args:
            stress_test: the run to store; its `stress_test_id` comes from `next_id`.

        Raises:
            google.cloud.exceptions.Conflict: if a document with this ID already exists.
        """
        await self._add(stress_test.stress_test_id, stress_test)

    async def get_stress_test(self, stress_test_id: str) -> StressTestModel | None:
        """Reads one stress test run.

        Ownership is not checked here: the service compares `user_id` with the current user.

        Args:
            stress_test_id: ID of the stress test.

        Returns:
            StressTestModel | None: the run with its results; `None` if it does not exist.
        """
        return await self._get(stress_test_id)

    async def get_stress_tests(self, user_id: str, limit: int) -> list[StressTestModel]:
        """Returns the user's latest stress tests, newest first.

        Args:
            user_id: uid of the user who ran the stress tests.
            limit: maximum number of stress tests to return.

        Returns:
            list[StressTestModel]: at most `limit` stress tests, newest `created_at` first.
        """
        query = self._col_ref.where(filter=FieldFilter("user_id", "==", user_id))
        runs = await self._stream(query.limit(MAX_STRESS_TESTS_SCAN))
        return sorted(runs, key=lambda run: run.created_at, reverse=True)[:limit]

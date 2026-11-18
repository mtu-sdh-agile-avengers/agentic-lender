from typing import Any, Callable

from google.cloud.firestore import (
    FieldFilter,
    Query,
    AsyncTransaction,
    async_transactional,
)

from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository
from src.loan_applications.exceptions import LoanApplicationNotFoundError
from src.loan_applications.models import LoanApplicationModel
from src.loan_applications.ports import LoanApplicationQuery
from src.schemas import PaginatedResponse


class LoanApplicationFirestoreRepository(FirestoreRepository[LoanApplicationModel]):
    col = CollectionPath.LOAN_APPLICATIONS

    def _to_doc(self, entity: LoanApplicationModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"loan_application_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> LoanApplicationModel:
        return LoanApplicationModel.model_validate(
            {**data, "loan_application_id": doc_id}
        )

    def next_id(self) -> str:
        return (
            self._col_ref.document().id
        )  # Firestore auto-IDs are generated locally by SDK

    async def add_loan_application(self, application: LoanApplicationModel) -> None:
        await self._add(application.loan_application_id, application)

    async def get_loan_application(
        self, application_id: str
    ) -> LoanApplicationModel | None:
        return await self._get(application_id)

    async def get_loan_applications(
        self, query: LoanApplicationQuery
    ) -> PaginatedResponse[LoanApplicationModel]:
        filtered = self._col_ref

        # 0. filter collection
        for field, value in self._equality_filters(query):
            filtered = filtered.where(filter=FieldFilter(field, "==", value))

        # 1. count all matching documents (the result is a list of rows, a row is a list of values)
        [[count]] = await filtered.count(alias="total").get()
        total = count.value

        # 2. order by creation time stamp
        page_query = (
            filtered.order_by("created_at", direction=Query.DESCENDING)
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )

        # 3. execute query and get results
        page_query_snapshots = [snap async for snap in page_query.stream()]

        # 4. convert results to list of LoanApplicationModel
        return PaginatedResponse.build(
            items=[
                self._from_doc(snap.id, snap.to_dict() or {})
                for snap in page_query_snapshots
            ],
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def update_loan_application(
        self, application_id: str, mutator: Callable[[LoanApplicationModel], None]
    ) -> LoanApplicationModel:
        doc_ref = self._col_ref.document(application_id)

        @async_transactional
        async def run(transaction: AsyncTransaction):
            snap = await doc_ref.get(transaction=transaction)

            if not snap.exists:
                raise LoanApplicationNotFoundError(application_id)

            application = self._from_doc(snap.id, snap.to_dict() or {})
            mutator(application)

            transaction.set(doc_ref, self._to_doc(application))
            return application

        return await run(self._db.transaction())

    @staticmethod
    def _equality_filters(query: LoanApplicationQuery) -> list[tuple[str, Any]]:
        """Fetches existing filters from a query.

        Returns:
            list[tuple[str, Any]]: List of filters that query contains.
        """
        filters: list[tuple[str, Any]] = [
            ("borrower_id", query.borrower_id),
            ("broker_id", query.broker_id),
            ("bank_officer_id", query.bank_officer_id),
            ("status", query.status),
            ("ltv_group", query.ltv_group),
            ("risk_tier", query.risk_tier),
        ]
        query_filters = [
            (field, value) for field, value in filters if value is not None
        ]

        if query.unclaimed_only:
            query_filters.append(("broker_id", None))

        return query_filters

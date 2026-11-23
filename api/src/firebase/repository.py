from abc import ABC, abstractmethod
from typing import Any, ClassVar

from google.cloud.firestore import AsyncClient, AsyncCollectionReference
from google.cloud.firestore_v1 import AsyncQuery


class FirestoreRepository[T](ABC):
    """Generic repository implementation (base class) for the Cloud Firestore database, that
    interacts with entities (documents) of type `T` in one collection."""

    col: ClassVar[str]  # indicates a collection (path)
    _db: AsyncClient  # database client, required for transactions
    _col_ref: AsyncCollectionReference  # actual reference to access collection

    def __init__(self, db: AsyncClient) -> None:
        self._db = db
        self._col_ref = db.collection(self.col)

    # Document in Firestore represented as a dictionary, therefore conversion methods are required.
    @abstractmethod
    def _to_doc(self, entity: T) -> dict:
        """Converts an entity (i.e., model) into the dictionary stored in Firestore; document ID
        is not field inside the document - it's a document name.

        Args:
            entity (T): entity to store.

        Returns:
            dict: document fields.
        """

    @abstractmethod
    def _from_doc(self, doc_id: str, data: dict) -> T:
        """Builds an entity from a stored document.

        Args:
            doc_id: document ID (i.e., name), put back into the entity (i.e., model).
            data: document fields as returned by Firestore.
        """

    async def _get(self, doc_id: str) -> T | None:
        """Reads one document by its ID.

        Args:
            doc_id: document ID.

        Returns:
            T | None: the entity built by `_from_doc`, or None if document does not exist (not found).
        """
        doc_snap = await self._col_ref.document(doc_id).get()
        data = doc_snap.to_dict()

        if data is None:
            return None

        return self._from_doc(doc_snap.id, data)

    async def _get_many(self, doc_ids: list[str]) -> dict[str, T]:
        """Reads several documents by ids.

        Args:
            doc_ids: IDs of the documents to read; duplicates are read once.

        Returns:
            dict[str, T]: entities by document ID; missing documents are skipped.
        """
        unique_ids = list(dict.fromkeys(doc_ids))
        if not unique_ids:
            return {}

        doc_refs = [self._col_ref.document(doc_id) for doc_id in unique_ids]
        found: dict[str, T] = {}

        async for doc_snap in self._db.get_all(doc_refs):
            data = doc_snap.to_dict()
            if data is not None:
                found[doc_snap.id] = self._from_doc(doc_snap.id, data)

        return found

    async def _add(self, doc_id: str | None, entity: T) -> str:
        """Creates a new document with specified ID (i.e., `doc_id`); never overwrites existing ones.

        Args:
            doc_id: document ID; if None, Firestore generates an auto ID.
            entity: entity to store.

        Returns:
            str: ID of the created document.

        Raises:
            google.cloud.exceptions.Conflict: a document with this ID already exists.
        """
        doc_ref = self._col_ref.document(doc_id)
        await doc_ref.create(self._to_doc(entity))
        return doc_ref.id

    async def _update(self, doc_id: str, field_updates: dict[str, Any]) -> None:
        """Updates an existing document.

        Args:
            doc_id: ID of the document to update.
            field_updates: Fields of the document and their new values.

        Raises:
            google.cloud.exceptions.NotFound: If the document does not exist.
        """
        await self._col_ref.document(doc_id).update(field_updates)

    async def _delete(self, doc_id: str) -> None:
        """Deletes an existing document with specified ID (i.e., `doc_id`). Has no
        effect if document does not exist.

        Args:
            doc_id: document ID.

        """
        await self._col_ref.document(doc_id).delete()

    async def _stream(self, query: AsyncQuery | AsyncCollectionReference) -> list[T]:
        """Reads the query and converts every returned document into an entity.

        The query is built lazily (`where`, `order_by`, `limit` do not touch the network); it is executed
        here, and the results are streamed from Firestore and collected into memory. Always apply `.limit()`
        before calling this method (otherwise, stack overflow may occur).

        Args:
            query: Firestore query or collection reference (a collection without filters means all of its documents).

        Returns:
            list[T]: entities built by `_from_doc`, in the order Firestore returned them; empty list if nothing matched.

        Raises:
            pydantic.ValidationError: if a stored document does not match the entity model.
            google.api_core.exceptions.GoogleAPICallError: if the request to Firestore fails.
        """
        return [
            self._from_doc(doc_snap.id, doc_snap.to_dict() or {})
            async for doc_snap in query.stream()
        ]

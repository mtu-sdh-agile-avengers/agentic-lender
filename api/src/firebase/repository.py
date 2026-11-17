from abc import ABC, abstractmethod
from typing import ClassVar

from google.cloud.firestore import AsyncClient, AsyncCollectionReference


class FirestoreRepository[T](ABC):
    """Generic repository implementation (base class) for the Cloud Firestore database, that
    interacts with entities (documents) of type `T` in one collection."""

    col: ClassVar[str]  # indicates a collection (path)
    _db: AsyncClient  # database client, required for transactions
    _col_ref: AsyncCollectionReference  # actual reference to access collection

    def __init__(self, db: AsyncClient) -> None:
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
            T | None: the entity, or None if document doe not exists (not found).
        """
        doc_snap = await self._col_ref.document(doc_id).get()
        data = doc_snap.to_dict()

        if data is None:
            return None

        return self._from_doc(doc_snap.id, data)

    async def _add(self, doc_id: str | None, entity: T) -> None:
        """Creates a new document with specified ID (i.e., `doc_id`); never overwrites existing ones.

        Args:
            doc_id: document ID; if None, Firestore generates an auto ID.
            entity: entity to store.

        Raises:
            google.cloud.exceptions.Conflict: a document with this ID already exists.
        """
        await self._col_ref.document(doc_id).create(self._to_doc(entity))

    async def _delete(self, doc_id: str) -> None:
        """Deletes an existing document with specified ID (i.e., `doc_id`). Has no
        effect if document does not exist.

        Args:
            doc_id: document ID.

        """
        await self._col_ref.document(doc_id).delete()

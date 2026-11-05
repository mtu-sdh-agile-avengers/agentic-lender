from abc import ABC, abstractmethod
from typing import ClassVar, Optional, TypeVar, Generic
from google.cloud.firestore import AsyncClient, AsyncCollectionReference

T = TypeVar('T')

class FirestoreRepository(ABC, Generic[T]):
    col: ClassVar[str]                      # indicates a collection (path)
    _col_ref: AsyncCollectionReference      # actual reference to access collection
    
    # Document in Firestore represented as a dictionary, therefore conversion methods are required.
    @abstractmethod
    def _to_doc(self, entity: T) -> dict: ...
    
    @abstractmethod
    def _from_doc(self, doc_id: str, data: dict) -> T: ...
    
    
    def __init__(self, db: AsyncClient) -> None:
       self._col_ref = db.collection(self.col)
        
    async def _get(self, doc_id: str) -> Optional[T]:
        doc_snap = await self._col_ref.document(doc_id).get()                
        data = doc_snap.to_dict()
        
        if data is None:
            return None
        
        return self._from_doc(doc_snap.id, data)
        
    async def _add(self, doc_id: Optional[str], entity: T) -> None:
        await self._col_ref.document(doc_id).create(self._to_doc(entity))
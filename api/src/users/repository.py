from typing import Any, Optional

from src.users.exceptions import UserProfileAlreadyExistsError
from src.enums import CollectionPath
from src.users.models import UserProfileModel
from src.firebase.repository import FirestoreRepository
from google.cloud.exceptions import Conflict

class UserProfileFirestoreRepository(FirestoreRepository[UserProfileModel]):
    col = CollectionPath.USERS
    
    def _to_doc(self, entity: UserProfileModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"uid"})
        
    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> UserProfileModel:
        return UserProfileModel.model_validate({**data, "uid": doc_id})
        
    
    async def get_user_profile(self, uid:str) -> Optional[UserProfileModel]:
        return await self._get(uid)
    
    async def add_user_profile(self, user_model: UserProfileModel) -> None:
        try:
            await self._add(user_model.uid, user_model)
        except Conflict:
            raise UserProfileAlreadyExistsError(user_model.uid)
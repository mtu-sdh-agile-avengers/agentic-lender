from typing import Annotated

from fastapi import Depends
from google.cloud.firestore import AsyncClient

from src.firebase.connection import get_firestore

def get_config_firestore() -> AsyncClient:
    return get_firestore()

FirestoreDep = Annotated[AsyncClient, Depends(get_config_firestore)]
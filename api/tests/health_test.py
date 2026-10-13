from fastapi.testclient import TestClient
from fastapi import status
from src.main import api

client = TestClient(api)

def test_health():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
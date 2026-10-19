from fastapi import status
from fastapi.testclient import TestClient

from src.main import app

with TestClient(app) as client:

    def test_health():
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

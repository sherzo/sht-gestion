import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.db
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requiere DATABASE_URL")
def test_health_db_conecta_con_postgres() -> None:
    response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

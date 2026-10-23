from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_rejects_unsupported_content_type():
    response = client.post(
        "/ocr",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415

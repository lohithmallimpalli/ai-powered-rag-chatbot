import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"
client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "provider" in data
    assert "total_documents" in data
    assert "total_chunks" in data

def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_chunks" in data

def test_upload_invalid_file_extension():
    fake_file = io.BytesIO(b"malicious script")
    response = client.post(
        "/api/upload",
        files={"file": ("virus.exe", fake_file, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "Unsupported format" in response.json()["detail"]

def test_upload_and_delete_document_workflow():
    txt_path = SAMPLE_DIR / "Global_AI_Security_Policy.txt"
    assert txt_path.exists()

    with open(txt_path, "rb") as f:
        file_bytes = f.read()

    # Upload document
    response = client.post(
        "/api/upload",
        files={"file": ("Global_AI_Security_Policy.txt", io.BytesIO(file_bytes), "text/plain")}
    )
    assert response.status_code == 200
    upload_data = response.json()
    assert upload_data["success"] is True
    doc_id = upload_data["document"]["doc_id"]
    assert doc_id.startswith("doc_")
    assert upload_data["document"]["chunk_count"] > 0

    # Test Duplicate Prevention
    dup_response = client.post(
        "/api/upload",
        files={"file": ("Global_AI_Security_Policy.txt", io.BytesIO(file_bytes), "text/plain")}
    )
    assert dup_response.status_code == 409
    assert "already indexed" in dup_response.json()["message"]

    # Test List Documents
    list_response = client.get("/api/documents")
    assert list_response.status_code == 200
    docs = list_response.json()["documents"]
    assert any(d["doc_id"] == doc_id for d in docs)

    # Test History Workflow
    hist_response = client.get("/api/history?session_id=test_session")
    assert hist_response.status_code == 200

    del_hist_response = client.delete("/api/history?session_id=test_session")
    assert del_hist_response.status_code == 200
    assert del_hist_response.json()["success"] is True

    # Clean up: Delete Document
    del_response = client.delete(f"/api/documents/{doc_id}")
    assert del_response.status_code == 200
    assert del_response.json()["success"] is True

def test_chat_without_api_key_returns_informative_error():
    # If no API key configured, /api/chat should gracefully return 401 with instructions
    response = client.post(
        "/api/chat",
        json={"message": "What is the policy?"}
    )
    # If no documents are uploaded yet, it tells user to upload
    # If documents exist but API key is missing, it returns 401
    assert response.status_code in [200, 401]
    if response.status_code == 401:
        assert "API key is not configured" in response.json()["detail"]
    elif response.status_code == 200:
        assert "No documents have been uploaded" in response.json()["answer"]

def test_settings_update():
    response = client.post(
        "/api/settings",
        json={"provider": "gemini", "model": "gemini-1.5-flash"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-1.5-flash"

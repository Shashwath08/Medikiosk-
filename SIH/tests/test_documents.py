import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_document_upload_and_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Doc Patient",
            "gender": "female",
            "phone_number": "9812345674"
        })
        session_id = reg.json()["session_id"]

        # Valid upload (PNG image)
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        files = {"file": ("rx_slip.png", fake_png, "image/png")}
        data = {"session_id": session_id, "document_type": "prescription"}

        res = await ac.post("/api/documents/upload", data=data, files=files)
        assert res.status_code == 201
        up_data = res.json()
        doc_id = up_data["document_id"]
        assert doc_id.startswith("doc_")
        assert up_data["status"] == "uploaded"

        # Poll status
        status_res = await ac.get(f"/api/documents/{doc_id}/status")
        assert status_res.status_code == 200
        st_data = status_res.json()
        assert st_data["status"] in ["uploaded", "processing", "completed"]

        # List session documents
        list_res = await ac.get(f"/api/documents/session/{session_id}")
        assert list_res.status_code == 200
        assert len(list_res.json()["documents"]) >= 1

@pytest.mark.asyncio
async def test_unsupported_document_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Bad File Patient",
            "gender": "male",
            "phone_number": "9812345675"
        })
        session_id = reg.json()["session_id"]

        fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
        files = {"file": ("virus.exe", fake_exe, "application/octet-stream")}
        data = {"session_id": session_id, "document_type": "other"}

        res = await ac.post("/api/documents/upload", data=data, files=files)
        assert res.status_code == 415  # Unsupported Media Type

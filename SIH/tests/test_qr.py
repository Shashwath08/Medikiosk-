import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.services.qr_service import qr_service

@pytest.mark.asyncio
async def test_qr_generation_and_opaque_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "QR Patient",
            "gender": "other",
            "phone_number": "9812345676"
        })
        session_id = reg.json()["session_id"]
        token = reg.json()["token"]

        # Check payload format
        payload = qr_service.generate_qr_payload(token)
        assert payload == f"MEDIKIOSK:{token}"
        # Assert no sensitive patient information inside the QR string
        assert "QR Patient" not in payload
        assert "9812345676" not in payload

        # Test PNG image retrieval endpoint
        qr_img_res = await ac.get(f"/api/patients/{session_id}/qr")
        assert qr_img_res.status_code == 200
        assert qr_img_res.headers["content-type"] == "image/png"
        assert len(qr_img_res.content) > 100

        # Test session completion endpoint
        comp_res = await ac.post(f"/api/sessions/{session_id}/complete")
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert comp_data["status"] == "completed"
        assert comp_data["qr_token"] == token
        assert comp_data["qr_data_uri"].startswith("data:image/png;base64,")

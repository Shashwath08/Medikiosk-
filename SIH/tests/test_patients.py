import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_patient_registration_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "full_name": "Aarav Sharma",
            "age": 34,
            "gender": "male",
            "phone_number": "9876543210",
            "preferred_language": "hi",
            "is_new_patient": True
        }
        res = await ac.post("/api/patients/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["full_name"] == "Aarav Sharma"
        assert data["session_id"].startswith("sess_")
        assert data["token"] is not None
        assert data["preferred_language"] == "hi"

@pytest.mark.asyncio
async def test_patient_registration_invalid_phone():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "full_name": "Short Phone",
            "age": 25,
            "gender": "female",
            "phone_number": "123",  # invalid
            "preferred_language": "en",
            "is_new_patient": True
        }
        res = await ac.post("/api/patients/register", json=payload)
        assert res.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_abha_verification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Valid 14 digit format
        res = await ac.post("/api/patients/verify-abha", json={"abha_id": "91-1234-5678-9012"})
        assert res.status_code == 200
        data = res.json()
        assert data["verified"] is True
        assert data["profile"]["full_name"] is not None

        # Valid PHR address format
        res_phr = await ac.post("/api/patients/verify-abha", json={"abha_id": "patient@abdm"})
        assert res_phr.status_code == 200
        assert res_phr.json()["verified"] is True

        # Invalid format
        res_inv = await ac.post("/api/patients/verify-abha", json={"abha_id": "bad_id"})
        assert res_inv.status_code == 200
        assert res_inv.json()["verified"] is False

@pytest.mark.asyncio
async def test_language_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Sunita Patel",
            "gender": "female",
            "phone_number": "9123456780",
            "preferred_language": "en"
        })
        session_id = reg.json()["session_id"]

        # Valid language update to Malayalam
        res = await ac.post(f"/api/patients/{session_id}/language", json={"language": "ml"})
        assert res.status_code == 200
        assert res.json()["language"] == "ml"

        # Invalid language
        res_inv = await ac.post(f"/api/patients/{session_id}/language", json={"language": "fr"})
        assert res_inv.status_code == 400

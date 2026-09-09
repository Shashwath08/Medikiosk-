import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_consent_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register patient
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Consent Tester",
            "gender": "male",
            "phone_number": "9812345678"
        })
        session_id = reg.json()["session_id"]

        # Accept consent
        res = await ac.post("/api/consent", json={
            "session_id": session_id,
            "consent_given": True,
            "consent_version": "v1.0"
        })
        assert res.status_code == 200
        assert res.json()["consent_given"] is True
        assert res.json()["status"] == "active"

        # Check status
        status_res = await ac.get(f"/api/consent/{session_id}")
        assert status_res.status_code == 200
        assert status_res.json()["consent_given"] is True

@pytest.mark.asyncio
async def test_consent_declined():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Decline Tester",
            "gender": "female",
            "phone_number": "9812345679"
        })
        session_id = reg.json()["session_id"]

        # Decline consent
        res = await ac.post("/api/consent", json={
            "session_id": session_id,
            "consent_given": False
        })
        assert res.status_code == 200
        assert res.json()["consent_given"] is False
        assert res.json()["status"] == "terminated_consent_declined"

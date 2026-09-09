import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_doctor_qr_case_retrieval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Patient registers and provides consent
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Doctor Test Case",
            "age": 42,
            "gender": "male",
            "phone_number": "9812345677",
            "abha_id": "91-1234-5678-9012"
        })
        session_id = reg.json()["session_id"]
        token = reg.json()["token"]

        await ac.post("/api/consent", json={"session_id": session_id, "consent_given": True})

        # 2. Patient records chief complaint
        await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_chief_complaint",
            "answer": "stomach_pain",
            "input_method": "touch"
        })

        # 3. Patient records pain location
        await ac.post("/api/history/pain-location", json={
            "session_id": session_id,
            "view": "front",
            "locations": [{"region": "abdomen", "side": "center", "pain": True}],
            "pain_intensity": 7,
            "pain_types": ["cramping"]
        })

        # 4. Doctor scans QR code and retrieves case by token
        doc_res = await ac.get(f"/api/patients/qr/{token}")
        assert doc_res.status_code == 200
        case = doc_res.json()
        assert case["full_name"] == "Doctor Test Case"
        assert case["session_id"] == session_id
        assert case["chief_complaint"] == "stomach_pain"
        assert case["pain_data"]["pain_intensity"] == 7
        assert case["abha_id"] == "91-1234-5678-9012"

        # 5. Doctor scans QR code with MEDIKIOSK: prefix
        doc_res_prefix = await ac.get(f"/api/patients/qr/MEDIKIOSK:{token}")
        assert doc_res_prefix.status_code == 200
        assert doc_res_prefix.json()["patient_id"] == case["patient_id"]

        # 6. Invalid token returns 404
        bad_res = await ac.get("/api/patients/qr/non_existent_token_123")
        assert bad_res.status_code == 404

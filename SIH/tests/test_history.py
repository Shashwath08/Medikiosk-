import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_history_flow_and_questions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register and consent
        reg = await ac.post("/api/patients/register", json={
            "full_name": "History Patient",
            "gender": "male",
            "phone_number": "9812345670",
            "preferred_language": "en"
        })
        session_id = reg.json()["session_id"]
        await ac.post("/api/consent", json={"session_id": session_id, "consent_given": True})

        # 1. Get Initial Question (Chief Complaint)
        q_res = await ac.get(f"/api/history/next-question?session_id={session_id}")
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert q_data["completed"] is False
        assert q_data["question"]["question_id"] == "q_chief_complaint"

        # 2. Answer Chief Complaint with Fever
        ans_res = await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_chief_complaint",
            "answer": "fever",
            "input_method": "touch"
        })
        assert ans_res.status_code == 200
        assert ans_res.json()["recorded"] is True
        assert ans_res.json()["next_question"]["question_id"] == "q_duration"

@pytest.mark.asyncio
async def test_pain_location_submission():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Pain Patient",
            "gender": "female",
            "phone_number": "9812345671",
            "preferred_language": "en"
        })
        session_id = reg.json()["session_id"]
        await ac.post("/api/consent", json={"session_id": session_id, "consent_given": True})

        # Submit structured pain map
        pain_payload = {
            "session_id": session_id,
            "view": "front",
            "locations": [
                {"region": "abdomen", "side": "center", "pain": True, "severity": 6},
                {"region": "knee", "side": "left", "pain": True, "severity": 4}
            ],
            "pain_intensity": 6,
            "pain_types": ["dull", "throbbing"],
            "duration": "3 days"
        }

        res = await ac.post("/api/history/pain-location", json=pain_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["recorded"] is True
        assert data["red_flag"] is False
        assert data["next_question"] is not None

@pytest.mark.asyncio
async def test_voice_upload_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Voice Patient",
            "gender": "male",
            "phone_number": "9812345672"
        })
        session_id = reg.json()["session_id"]
        await ac.post("/api/consent", json={"session_id": session_id, "consent_given": True})

        fake_audio = b"RIFF....WAVEfmt ....data...."
        files = {"audio_file": ("test.webm", fake_audio, "audio/webm")}
        data = {"session_id": session_id, "language": "en"}

        res = await ac.post("/api/history/voice", data=data, files=files)
        assert res.status_code == 200
        v_data = res.json()
        assert v_data["input_type"] == "voice"
        assert v_data["transcript"] is not None
        assert v_data["confidence"] > 0.9

@pytest.mark.asyncio
async def test_red_flag_alert_trigger():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        reg = await ac.post("/api/patients/register", json={
            "full_name": "Emergency Patient",
            "gender": "male",
            "phone_number": "9812345673"
        })
        session_id = reg.json()["session_id"]
        await ac.post("/api/consent", json={"session_id": session_id, "consent_given": True})

        # Submit critical answer: severe chest pain with emergency intensity
        pain_payload = {
            "session_id": session_id,
            "view": "front",
            "locations": [{"region": "chest", "side": "center", "pain": True}],
            "pain_intensity": 10,
            "pain_types": ["sharp", "crushing"]
        }

        res = await ac.post("/api/history/pain-location", json=pain_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["red_flag"] is True
        assert data["severity"] in ["high", "emergency"]
        assert "alert" in data["message"].lower() or "stay seated" in data["message"].lower() or "seated" in data["message"].lower()

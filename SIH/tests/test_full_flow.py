import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_complete_patient_journey_e2e():
    """
    End-to-End simulation of the 10-step patient journey:
    1. Kiosk Health Check
    2. ABHA Verification (Pre-check)
    3. Patient Registration
    4. Language Selection (Hindi)
    5. Clinical & AI Consent
    6. Adaptive History Questionnaire (Chief complaint -> Duration -> Severity -> Allergies)
    7. Interactive Anatomy Pain Location Map
    8. Document Upload & OCR Ingestion
    9. Session Finalization & QR Code Generation
    10. Doctor Dashboard Case Retrieval via QR Token
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Health check
        health = await ac.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"

        # Step 2: ABHA verification
        abha_check = await ac.post("/api/patients/verify-abha", json={"abha_id": "91-1234-5678-9012"})
        assert abha_check.status_code == 200
        assert abha_check.json()["verified"] is True
        prof = abha_check.json()["profile"]

        # Step 3: Patient Registration
        reg = await ac.post("/api/patients/register", json={
            "full_name": prof["full_name"],
            "age": 38,
            "gender": prof["gender"],
            "phone_number": prof["phone_number"],
            "abha_id": prof["abha_id"],
            "preferred_language": "hi",
            "is_new_patient": False
        })
        assert reg.status_code == 201
        reg_data = reg.json()
        session_id = reg_data["session_id"]
        token = reg_data["token"]

        # Step 4: Language Selection
        lang_res = await ac.post(f"/api/patients/{session_id}/language", json={"language": "hi"})
        assert lang_res.status_code == 200
        assert lang_res.json()["language"] == "hi"

        # Step 5: Consent
        consent_res = await ac.post("/api/consent", json={
            "session_id": session_id,
            "consent_given": True,
            "consent_version": "v1.0",
            "consent_items": {
                "clinical_history": True,
                "ai_processing": True,
                "document_analysis": True,
                "physician_access": True
            }
        })
        assert consent_res.status_code == 200
        assert consent_res.json()["status"] == "active"

        # Step 6: First Dynamic Question (Chief Complaint)
        q1 = await ac.get(f"/api/history/next-question?session_id={session_id}&language=hi")
        assert q1.status_code == 200
        assert q1.json()["question"]["question_id"] == "q_chief_complaint"

        # Answer chief complaint
        a1 = await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_chief_complaint",
            "answer": "body_pain",
            "input_method": "touch"
        })
        assert a1.status_code == 200
        # AI branches to pain map
        assert a1.json()["next_question"]["question_id"] == "q_pain_map"

        # Step 7: Interactive Anatomy Pain Location Map
        pain_payload = {
            "session_id": session_id,
            "view": "front",
            "locations": [
                {"region": "shoulder", "side": "left", "pain": True, "severity": 5},
                {"region": "arm", "side": "left", "pain": True, "severity": 4}
            ],
            "pain_intensity": 5,
            "pain_types": ["dull", "aching"],
            "duration": "2 to 3 days"
        }
        pain_res = await ac.post("/api/history/pain-location", json=pain_payload)
        assert pain_res.status_code == 200
        assert pain_res.json()["next_question"]["question_id"] == "q_duration"

        # Answer duration
        a2 = await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_duration",
            "answer": "few_days",
            "input_method": "touch"
        })
        assert a2.status_code == 200
        assert a2.json()["next_question"]["question_id"] == "q_severity"

        # Answer severity slider
        a3 = await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_severity",
            "answer": 6,
            "input_method": "touch"
        })
        assert a3.status_code == 200
        assert a3.json()["next_question"]["question_id"] == "q_prior_meds"

        # Answer prior meds
        a4 = await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_prior_meds",
            "answer": "no",
            "input_method": "touch"
        })
        assert a4.status_code == 200
        assert a4.json()["next_question"]["question_id"] == "q_allergies"

        # Answer allergies
        a5 = await ac.post("/api/history/answer", json={
            "session_id": session_id,
            "question_id": "q_allergies",
            "answer": "None",
            "input_method": "touch"
        })
        assert a5.status_code == 200
        assert a5.json()["completed"] is True

        # Step 8: Document Upload
        fake_doc = b"%PDF-1.4 ... test pdf payload ..."
        files = {"file": ("discharge_summary.pdf", fake_doc, "application/pdf")}
        data = {"session_id": session_id, "document_type": "discharge_summary"}
        doc_res = await ac.post("/api/documents/upload", data=data, files=files)
        assert doc_res.status_code == 201
        doc_id = doc_res.json()["document_id"]

        # Check OCR status
        ocr_status = await ac.get(f"/api/documents/{doc_id}/status")
        assert ocr_status.status_code == 200

        # Step 9: Finalize Session & Generate QR
        comp = await ac.post(f"/api/sessions/{session_id}/complete")
        assert comp.status_code == 200
        comp_data = comp.json()
        assert comp_data["status"] == "completed"
        assert comp_data["qr_token"] == token
        assert "data:image/png;base64," in comp_data["qr_data_uri"]

        # Step 10: Doctor Scans QR Token & Retrieves Complete Case
        doc_case = await ac.get(f"/api/patients/qr/{token}")
        assert doc_case.status_code == 200
        case_data = doc_case.json()
        assert case_data["full_name"] == prof["full_name"]
        assert case_data["session_id"] == session_id
        assert case_data["language"] == "hi"
        assert case_data["consent_given"] is True
        assert case_data["pain_data"]["pain_intensity"] == 5
        assert len(case_data["pain_data"]["locations"]) == 2
        assert case_data["documents_count"] == 1

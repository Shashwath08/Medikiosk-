from fastapi import APIRouter, HTTPException, status
from backend.schemas.session import DoctorPatientView
from backend.services.session_store import session_store

router = APIRouter(prefix="/patients", tags=["Doctor Dashboard Integration (Member 5)"])

@router.get(
    "/qr/{token}",
    response_model=DoctorPatientView,
    summary="Retrieve Patient Case via Scanned QR Token (Member 5)",
    description="""
    **Doctor Dashboard Retrieval Point**:
    1. Doctor scans patient's printed or on-screen QR code (encoding `MEDIKIOSK:<token>`).
    2. Doctor app extracts the `<token>` and calls this endpoint.
    3. Backend verifies doctor authentication (in production by Member 6) and returns the clinical case.
    4. Ensures no patient health information was leaked inside the QR code itself.
    """
)
async def get_patient_by_qr_token(token: str):
    # Strip protocol prefix if present
    clean_token = token.replace("MEDIKIOSK:", "").strip()
    session = session_store.get_session_by_token(clean_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid QR token or patient session expired."
        )

    # Extract chief complaint from answers if available
    chief_complaint = None
    if "q_chief_complaint" in session.answers:
        chief_complaint = str(session.answers["q_chief_complaint"].get("answer", ""))

    return DoctorPatientView(
        patient_id=session.patient_id,
        session_id=session.session_id,
        full_name=session.full_name,
        age=session.age,
        gender=session.gender,
        phone_number=session.phone_number,
        abha_id=session.abha_id,
        language=session.language,
        consent_given=session.consent_given,
        triage_status=session.triage_status,
        red_flag=session.red_flag,
        chief_complaint=chief_complaint,
        pain_data=session.pain_data,
        answers=session.answers,
        documents_count=len(session.documents_uploaded),
        documents=session.documents_uploaded,
        session_status=session.status,
        session_created_at=session.created_at
    )

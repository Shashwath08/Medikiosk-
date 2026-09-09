from fastapi import APIRouter, HTTPException, status
from backend.schemas.session import PatientSessionData, SessionCompletionResponse
from backend.services.session_store import session_store
from backend.services.qr_service import qr_service

router = APIRouter(prefix="/sessions", tags=["Session Lifecycle (Member 1 / 4)"])

@router.get(
    "/{session_id}",
    response_model=PatientSessionData,
    summary="Get Full Session State",
    description="Returns the active patient session state, answered history, pain map, and uploaded documents."
)
async def get_session_state(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return session

@router.post(
    "/{session_id}/complete",
    response_model=SessionCompletionResponse,
    summary="Complete Patient Kiosk Session",
    description="Finalizes the patient session and generates the safe opaque QR code for the doctor dashboard."
)
async def complete_session(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    session_store.complete_session(session_id)
    qr_data_uri = qr_service.generate_qr_data_uri(session.token)

    return SessionCompletionResponse(
        session_id=session.session_id,
        patient_ref=session.patient_id,
        qr_token=session.token,
        qr_data_uri=qr_data_uri,
        status="completed",
        message="Patient session completed successfully. Doctor may scan the QR code to access clinical history."
    )

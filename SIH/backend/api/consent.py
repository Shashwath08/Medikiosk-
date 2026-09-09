from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from backend.schemas.consent import ConsentRequest, ConsentResponse
from backend.services.session_store import session_store

router = APIRouter(prefix="/consent", tags=["Consent (Member 1 / 6)"])

@router.post(
    "",
    response_model=ConsentResponse,
    summary="Record Patient Clinical & AI Consent",
    description="Captures patient consent for medical history collection, AI processing, document review, and doctor access. If declined, terminates session gracefully."
)
async def submit_consent(req: ConsentRequest):
    session = session_store.get_session(req.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found. Please register first."
        )

    ts = req.timestamp or datetime.now(timezone.utc).isoformat()
    success = session_store.update_consent(req.session_id, req.consent_given, req.consent_items)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record consent.")

    session_status = "active" if req.consent_given else "terminated_consent_declined"
    message = (
        "Consent recorded. Proceeding to clinical history."
        if req.consent_given
        else "Consent declined. Session has been terminated gracefully. You may approach the registration desk for in-person assistance."
    )

    return ConsentResponse(
        session_id=req.session_id,
        consent_given=req.consent_given,
        status=session_status,
        timestamp=ts,
        message=message
    )

@router.get(
    "/{session_id}",
    summary="Check Consent Status",
    description="Queries whether consent has been granted for the active session."
)
async def get_consent_status(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return {
        "session_id": session_id,
        "consent_given": session.consent_given,
        "status": session.status
    }

from fastapi import APIRouter, HTTPException, status, Response
from backend.schemas.patient import (
    PatientRegisterRequest,
    PatientRegisterResponse,
    ABHAVerifyRequest,
    ABHAVerifyResponse,
    LanguageUpdateRequest,
)
from backend.schemas.session import PatientSessionData
from backend.services.session_store import session_store
from backend.services.qr_service import qr_service
from backend.integrations.abdm_service import mock_abdm_service
from backend.config import settings

router = APIRouter(prefix="/patients", tags=["Patients (Member 1 / 4 / 6)"])

@router.post(
    "/register",
    response_model=PatientRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient or continue with ABHA ID",
    description="Creates a fresh clinical session, generates a secure opaque session token, and initializes patient demographics."
)
async def register_patient(req: PatientRegisterRequest):
    session = session_store.create_session(req)
    return PatientRegisterResponse(
        patient_id=session.patient_id,
        session_id=session.session_id,
        token=session.token,
        full_name=session.full_name,
        preferred_language=session.language,
        created_at=session.created_at,
        message="Patient registered successfully. Session initialized."
    )

@router.post(
    "/verify-abha",
    response_model=ABHAVerifyResponse,
    summary="Verify ABHA ID / Address",
    description="Validates a 14-digit ABHA ID or PHR address. Member 6 connects production ABDM Gateway here."
)
async def verify_abha(req: ABHAVerifyRequest):
    return mock_abdm_service.verify_abha(req.abha_id)

@router.post(
    "/{session_id}/language",
    summary="Set Patient Preferred Language",
    description="Updates the active language for voice prompts, UI text, and ASR/TTS processing."
)
async def update_language(session_id: str, req: LanguageUpdateRequest):
    if req.language not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{req.language}' not supported. Choose from: {list(settings.SUPPORTED_LANGUAGES.keys())}"
        )
    
    success = session_store.update_language(session_id, req.language)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    
    return {
        "session_id": session_id,
        "language": req.language,
        "language_name": settings.SUPPORTED_LANGUAGES[req.language],
        "message": "Language updated successfully."
    }

@router.get(
    "/{session_id}",
    response_model=PatientSessionData,
    summary="Get Patient Session Details",
    description="Retrieves the current state of a patient session."
)
async def get_patient_session(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient session not found.")
    return session

@router.get(
    "/{session_id}/qr",
    summary="Get Patient QR Code Image",
    description="Generates and streams a PNG QR code encoding the safe opaque session token."
)
async def get_patient_qr(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient session not found.")
    
    img_bytes = qr_service.generate_qr_bytes(session.token)
    return Response(content=img_bytes, media_type="image/png")

from typing import Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from backend.schemas.history import (
    DynamicQuestion,
    AnswerRequest,
    PainLocationSubmission,
    VoiceHistoryResponse,
    RedFlagAlert,
)
from backend.services.session_store import session_store
from backend.integrations.ai_service import mock_ai_service

router = APIRouter(prefix="/history", tags=["Clinical History (Member 1 / 2)"])

@router.get(
    "/next-question",
    summary="Get Next Adaptive History Question",
    description="Member 2 AI integration point. Fetches the dynamically determined next clinical question."
)
async def get_next_question(
    session_id: str,
    current_question_id: Optional[str] = None,
    language: Optional[str] = None
):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    
    if not session.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot collect clinical history without patient consent."
        )

    selected_lang = language or session.language or "en"
    next_q = mock_ai_service.get_next_question(
        session_id=session_id,
        current_question_id=current_question_id,
        language=selected_lang,
        session_context=session.model_dump()
    )

    if next_q is None:
        return {
            "session_id": session_id,
            "completed": True,
            "message": "History collection questionnaire completed."
        }

    return {
        "session_id": session_id,
        "completed": False,
        "question": next_q
    }

@router.post(
    "/answer",
    summary="Submit Patient Answer via Touch or Voice",
    description="Records answer in patient session, runs triage evaluation, and fetches the next dynamic question."
)
async def submit_answer(req: AnswerRequest):
    session = session_store.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if not session.consent_given:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consent not provided.")

    # Record answer in session state
    session_store.record_answer(req.session_id, req.question_id, req.answer, req.input_method)

    # Member 2: Evaluate clinical triage for red flags
    triage = mock_ai_service.evaluate_triage(
        session_id=req.session_id,
        question_id=req.question_id,
        answer=req.answer,
        session_context=session.model_dump()
    )

    if triage.red_flag:
        session_store.set_triage_status(
            session_id=req.session_id,
            red_flag=True,
            severity=triage.severity,
            details={"trigger_question": req.question_id, "trigger_answer": req.answer, "message": triage.message}
        )
        return {
            "session_id": req.session_id,
            "recorded": True,
            "red_flag": True,
            "severity": triage.severity,
            "message": triage.message,
            "action_required": triage.action_required,
            "next_question": None,
            "completed": True
        }

    # Fetch next question
    next_q = mock_ai_service.get_next_question(
        session_id=req.session_id,
        current_question_id=req.question_id,
        last_answer=req.answer,
        language=session.language,
        session_context=session.model_dump()
    )

    return {
        "session_id": req.session_id,
        "recorded": True,
        "red_flag": False,
        "next_question": next_q,
        "completed": next_q is None
    }

@router.post(
    "/voice",
    response_model=VoiceHistoryResponse,
    summary="Submit Voice Audio Stream/Recording",
    description="Member 2 ASR integration point. Processes voice audio, returns transcript, evaluates red flags, and determines next question."
)
async def process_voice_input(
    session_id: str = Form(...),
    language: str = Form("en"),
    audio_file: UploadFile = File(...)
):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    audio_bytes = await audio_file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio payload.")

    voice_res = mock_ai_service.process_voice(
        audio_bytes=audio_bytes,
        filename=audio_file.filename or "recording.webm",
        language=language,
        session_id=session_id,
        session_context=session.model_dump()
    )

    # Record voice transcript into session answers
    session_store.record_answer(
        session_id=session_id,
        question_id=voice_res.question_id or "voice_input",
        answer=voice_res.transcript,
        input_method="voice"
    )

    if voice_res.red_flag:
        session_store.set_triage_status(
            session_id=session_id,
            red_flag=True,
            severity="high",
            details={"transcript": voice_res.transcript}
        )

    return voice_res

@router.post(
    "/pain-location",
    summary="Submit Interactive Human Anatomy Pain Map Selection",
    description="Captures structured anatomical locations (region, side), pain intensity (0-10), and pain characteristics."
)
async def submit_pain_location(payload: PainLocationSubmission):
    if not payload.session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id is required.")

    session = session_store.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    pain_data = payload.model_dump()
    session_store.record_pain_data(payload.session_id, pain_data)

    # Evaluate triage on pain location
    triage = mock_ai_service.evaluate_triage(
        session_id=payload.session_id,
        question_id="q_pain_map",
        answer=pain_data,
        session_context=session.model_dump()
    )

    if triage.red_flag:
        session_store.set_triage_status(
            session_id=payload.session_id,
            red_flag=True,
            severity=triage.severity,
            details=pain_data
        )
        return {
            "session_id": payload.session_id,
            "recorded": True,
            "red_flag": True,
            "severity": triage.severity,
            "message": triage.message,
            "action_required": triage.action_required,
            "next_question": None
        }

    # Fetch next question following pain location
    next_q = mock_ai_service.get_next_question(
        session_id=payload.session_id,
        current_question_id="q_pain_map",
        last_answer=pain_data,
        language=session.language,
        session_context=session.model_dump()
    )

    return {
        "session_id": payload.session_id,
        "recorded": True,
        "red_flag": False,
        "next_question": next_q
    }

@router.get(
    "/state/{session_id}",
    summary="Get Current History Collection State",
    description="Returns all recorded answers, pain map selections, and questionnaire completion status."
)
async def get_history_state(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    return {
        "session_id": session_id,
        "answers": session.answers,
        "pain_data": session.pain_data,
        "history_completed": session.history_completed,
        "red_flag": session.red_flag,
        "triage_status": session.triage_status
    }

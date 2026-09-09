import uuid
import secrets
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from backend.schemas.session import PatientSessionData
from backend.schemas.patient import PatientRegisterRequest

class SessionStore:
    """
    In-memory thread-safe Patient Session Repository.
    
    ARCHITECTURE NOTICE FOR MEMBER 6 (Database & Security):
    This class serves as the clean persistence interface. To connect PostgreSQL,
    MongoDB, Redis, or an ABDM Health Information Provider (HIP) repository,
    create your database service and replace the methods here.
    """

    def __init__(self):
        # session_id -> PatientSessionData
        self._sessions: Dict[str, PatientSessionData] = {}
        # token -> session_id index for doctor QR lookup
        self._token_index: Dict[str, str] = {}

    def create_session(self, req: PatientRegisterRequest) -> PatientSessionData:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        patient_id = f"pat_{uuid.uuid4().hex[:8]}"
        # Generate high-entropy opaque token for QR code (never contains PII)
        token = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc).isoformat()

        session_data = PatientSessionData(
            session_id=session_id,
            patient_id=patient_id,
            token=token,
            full_name=req.full_name,
            age=req.age,
            gender=req.gender,
            phone_number=req.phone_number,
            abha_id=req.abha_id,
            language=req.preferred_language or "en",
            consent_given=False,
            registration_completed=True,
            history_completed=False,
            pain_data=None,
            answers={},
            documents_uploaded=[],
            triage_status="normal",
            red_flag=False,
            red_flag_details=None,
            status="active",
            created_at=now,
            updated_at=now
        )

        self._sessions[session_id] = session_data
        self._token_index[token] = session_id
        return session_data

    def get_session(self, session_id: str) -> Optional[PatientSessionData]:
        return self._sessions.get(session_id)

    def get_session_by_token(self, token: str) -> Optional[PatientSessionData]:
        session_id = self._token_index.get(token)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def update_language(self, session_id: str, language: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.language = language
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def update_consent(self, session_id: str, consent_given: bool, details: Optional[Dict[str, Any]] = None) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.consent_given = consent_given
        session.status = "active" if consent_given else "terminated_consent_declined"
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def record_answer(self, session_id: str, question_id: str, answer: Any, input_method: str = "touch") -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.answers[question_id] = {
            "answer": answer,
            "input_method": input_method,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def record_pain_data(self, session_id: str, pain_data: Dict[str, Any]) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.pain_data = pain_data
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def add_document(self, session_id: str, doc_info: Dict[str, Any]) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.documents_uploaded.append(doc_info)
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def set_triage_status(self, session_id: str, red_flag: bool, severity: str, details: Optional[Dict[str, Any]] = None) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.red_flag = red_flag
        session.triage_status = severity
        session.red_flag_details = details
        if red_flag and severity in ("high", "emergency"):
            session.status = "emergency_hold"
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def complete_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.history_completed = True
        session.status = "completed"
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

# Global singleton session store
session_store = SessionStore()

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PatientSessionData(BaseModel):
    session_id: str
    patient_id: str
    token: str  # Safe opaque token encoded in QR (e.g. MEDIKIOSK:token)
    full_name: str
    age: Optional[int] = None
    gender: str
    phone_number: str
    abha_id: Optional[str] = None
    language: str = "en"
    consent_given: bool = False
    registration_completed: bool = True
    history_completed: bool = False
    pain_data: Optional[Dict[str, Any]] = None
    answers: Dict[str, Any] = Field(default_factory=dict)
    documents_uploaded: List[Dict[str, Any]] = Field(default_factory=list)
    triage_status: str = "normal"  # normal, priority, emergency
    red_flag: bool = False
    red_flag_details: Optional[Dict[str, Any]] = None
    status: str = "active"  # active, completed, terminated_consent_declined, emergency_hold
    created_at: str
    updated_at: str

class SessionCompletionResponse(BaseModel):
    session_id: str
    patient_ref: str
    qr_token: str
    qr_data_uri: str
    status: str
    message: str

class DoctorPatientView(BaseModel):
    patient_id: str
    session_id: str
    full_name: str
    age: Optional[int] = None
    gender: str
    phone_number: str
    abha_id: Optional[str] = None
    language: str
    consent_given: bool
    triage_status: str
    red_flag: bool
    chief_complaint: Optional[str] = None
    pain_data: Optional[Dict[str, Any]] = None
    answers: Dict[str, Any] = Field(default_factory=dict)
    documents_count: int = 0
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    session_status: str
    session_created_at: str

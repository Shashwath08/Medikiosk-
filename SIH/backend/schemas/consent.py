from typing import Optional, Dict
from pydantic import BaseModel, Field

class ConsentRequest(BaseModel):
    session_id: str = Field(..., description="Active patient session ID")
    consent_given: bool = Field(..., description="True if patient accepted consent terms, False if declined")
    consent_version: str = Field("v1.0", description="Version of clinical consent terms")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of consent action")
    consent_items: Optional[Dict[str, bool]] = Field(
        default_factory=lambda: {
            "clinical_history": True,
            "ai_processing": True,
            "document_analysis": True,
            "physician_access": True
        },
        description="Granular consent flags for individual processing activities"
    )

class ConsentResponse(BaseModel):
    session_id: str
    consent_given: bool
    status: str = Field(..., description="active, terminated_consent_declined")
    timestamp: str
    message: str

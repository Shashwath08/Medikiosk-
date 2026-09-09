from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

class PatientRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of patient")
    age: Optional[int] = Field(None, ge=0, le=130, description="Age in years")
    dob: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    gender: str = Field(..., description="Gender (male, female, other, prefer_not_to_say)")
    phone_number: str = Field(..., description="10-digit Indian phone number")
    abha_id: Optional[str] = Field(None, description="Optional 14-digit ABHA number or PHR address (e.g. user@abdm)")
    preferred_language: str = Field("en", description="Preferred language code (e.g. en, hi, ml, ta, kn, te)")
    is_new_patient: bool = Field(True, description="Whether patient is new or existing")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Normalize digits
        cleaned = re.sub(r"[^\d]", "", v)
        if len(cleaned) < 10:
            raise ValueError("Phone number must contain at least 10 digits")
        if len(cleaned) > 10:
            cleaned = cleaned[-10:]  # extract last 10 digits if country code +91 was attached
        return cleaned

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        valid_genders = {"male", "female", "other", "prefer_not_to_say"}
        normalized = v.strip().lower()
        if normalized not in valid_genders:
            raise ValueError(f"Gender must be one of: {', '.join(valid_genders)}")
        return normalized

class ABHAVerifyRequest(BaseModel):
    abha_id: str = Field(..., min_length=5, max_length=50, description="14-digit ABHA ID (e.g. 12-3456-7890-1234) or PHR address (e.g. name@abdm)")

    @field_validator("abha_id")
    @classmethod
    def clean_abha(cls, v: str) -> str:
        return v.strip()

class ABHAPatientProfile(BaseModel):
    abha_id: str
    full_name: str
    gender: str
    dob: str
    phone_number: str
    address: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None

class ABHAVerifyResponse(BaseModel):
    verified: bool
    message: str
    profile: Optional[ABHAPatientProfile] = None

class LanguageUpdateRequest(BaseModel):
    language: str = Field(..., min_length=2, max_length=5, description="ISO language code (e.g. en, hi, ml, ta, kn, te)")

class PatientRegisterResponse(BaseModel):
    patient_id: str
    session_id: str
    token: str
    full_name: str
    preferred_language: str
    created_at: str
    message: str

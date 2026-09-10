"""
Clinical history schema + JSON contract for MediKiosk (Member 2).

Rules enforced here:
  * missing string  -> None (null)
  * missing list    -> []
  * no invented data: cleaning only, never filling
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --------------------------------------------------------------------------
# Field groups
# --------------------------------------------------------------------------

STRING_FIELDS: List[str] = [
    "chief_complaint",
    "onset",
    "duration",
    "severity",
    "character",
    "location",
    "radiation",
    "aggravating_factors",
    "relieving_factors",
    "personal_history",
]

LIST_FIELDS: List[str] = [
    "associated_symptoms",
    "past_medical_history",
    "past_surgical_history",
    "medications",
    "allergies",
    "family_history",
    "review_of_systems",
]

ALL_FIELDS: List[str] = STRING_FIELDS + LIST_FIELDS

# Values that a small model likes to emit when it has nothing. Never store these.
NULL_TOKENS = {
    "", "-", "--", "n/a", "na", "none", "null", "nil", "nothing", "no",
    "not mentioned", "not specified", "not stated", "not provided",
    "unknown", "unclear", "undefined", "unspecified", "no information",
    "not applicable", "not available", "patient did not say", "string",
    "no complaints", "no history",
    # bare affirmations carry no information - "yes" is not a symptom
    "yes", "yeah", "yep", "yup", "ok", "okay", "sure", "fine", "haan", "ha",
    "hmm", "hm", "correct", "true", "yes sir", "yes madam", "theek hai",
    "yes i have", "i have", "i do", "affirmative",
}


def _clean_string(value: Any) -> Optional[str]:
    """Normalise one string value; return None if it carries no information."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        parts = [p for p in (_clean_string(v) for v in value) if p]
        value = ", ".join(parts)
    if not isinstance(value, str):
        value = str(value)
    value = " ".join(value.split()).strip(" .,;:\u2022-")
    if not value or value.lower() in NULL_TOKENS:
        return None
    return value


def _clean_list(value: Any) -> List[str]:
    """Normalise a list value: flatten, clean, drop nulls, dedupe (case-insensitive)."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if isinstance(value, dict):
        value = list(value.values())
    if not isinstance(value, (list, tuple, set)):
        value = [value]

    out: List[str] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, dict):
            item = " ".join(str(v) for v in item.values())
        cleaned = _clean_string(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


class ClinicalHistory(BaseModel):
    """Full structured clinical history. This is the object the backend gets."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    chief_complaint: Optional[str] = None
    onset: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None
    character: Optional[str] = None
    location: Optional[str] = None
    radiation: Optional[str] = None
    aggravating_factors: Optional[str] = None
    relieving_factors: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    past_medical_history: List[str] = Field(default_factory=list)
    past_surgical_history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    personal_history: Optional[str] = None
    review_of_systems: List[str] = Field(default_factory=list)

    @field_validator(*STRING_FIELDS, mode="before")
    @classmethod
    def _v_strings(cls, v: Any) -> Optional[str]:
        return _clean_string(v)

    @field_validator(*LIST_FIELDS, mode="before")
    @classmethod
    def _v_lists(cls, v: Any) -> List[str]:
        return _clean_list(v)

    # ---------------------------------------------------------------- helpers
    def is_field_answered(self, field: str) -> bool:
        value = getattr(self, field, None)
        if isinstance(value, list):
            return len(value) > 0
        return value is not None

    def answered_fields(self) -> List[str]:
        return [f for f in ALL_FIELDS if self.is_field_answered(f)]

    def to_json_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class PartialHistory(BaseModel):
    """
    What ONE patient answer produced. Every field is optional so that a single
    answer never wipes previously collected information.
    """

    model_config = ConfigDict(extra="ignore")

    chief_complaint: Optional[str] = None
    onset: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None
    character: Optional[str] = None
    location: Optional[str] = None
    radiation: Optional[str] = None
    aggravating_factors: Optional[str] = None
    relieving_factors: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    past_medical_history: List[str] = Field(default_factory=list)
    past_surgical_history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    personal_history: Optional[str] = None
    review_of_systems: List[str] = Field(default_factory=list)

    @field_validator(*STRING_FIELDS, mode="before")
    @classmethod
    def _v_strings(cls, v: Any) -> Optional[str]:
        return _clean_string(v)

    @field_validator(*LIST_FIELDS, mode="before")
    @classmethod
    def _v_lists(cls, v: Any) -> List[str]:
        return _clean_list(v)

    def non_empty(self) -> Dict[str, Any]:
        data = self.model_dump()
        return {
            k: v for k, v in data.items()
            if (v not in (None, [])) and not (isinstance(v, list) and not v)
        }


class TurnRecord(BaseModel):
    """Auditability: what was asked, what was said, what was stored."""

    model_config = ConfigDict(extra="ignore")

    question_id: Optional[str] = None
    question_text: Optional[str] = None
    target_field: Optional[str] = None
    input_mode: str = "text"          # "text" | "speech"
    raw_text: str = ""                # exactly what the patient said/typed
    normalised_text: str = ""         # cleaned text sent to the LLM
    correction_applied: bool = False
    extracted: Dict[str, Any] = Field(default_factory=dict)
    dropped_values: Dict[str, Any] = Field(default_factory=dict)


class ModuleResponse(BaseModel):
    """The exact envelope Member 4 will consume."""

    model_config = ConfigDict(extra="ignore")

    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: Dict[str, Any]) -> "ModuleResponse":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, message: str) -> "ModuleResponse":
        return cls(success=False, data={}, error=message)


# --------------------------------------------------------------------------
# Merge
# --------------------------------------------------------------------------


def merge_history(
    current: ClinicalHistory,
    update: PartialHistory,
    overwrite_strings: bool = False,
) -> ClinicalHistory:
    """
    Merge one answer into the running history.

    Strings : filled only if currently empty (unless overwrite_strings=True,
              used when the patient is explicitly correcting a field).
    Lists   : union, case-insensitive dedupe, order preserved.
    """
    merged = current.model_dump()
    new = update.model_dump()

    for field in STRING_FIELDS:
        value = new.get(field)
        if value is None:
            continue
        if merged.get(field) is None or overwrite_strings:
            merged[field] = value

    for field in LIST_FIELDS:
        incoming = new.get(field) or []
        if not incoming:
            continue
        existing = merged.get(field) or []
        seen = {v.lower() for v in existing}
        for item in incoming:
            if item.lower() not in seen:
                existing.append(item)
                seen.add(item.lower())
        merged[field] = existing

    return ClinicalHistory(**merged)


def empty_history_dict() -> Dict[str, Any]:
    return ClinicalHistory().model_dump()
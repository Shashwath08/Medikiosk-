from typing import Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field

class QuestionType(str, Enum):
    YES_NO = "yes_no"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    PAIN_LOCATION = "pain_location"
    BODY_MAP = "body_map"
    VOICE = "voice"
    MIXED = "mixed"
    SLIDER = "slider"

class OptionItem(BaseModel):
    id: str
    label: str
    subtext: Optional[str] = None
    icon: Optional[str] = None

class DynamicQuestion(BaseModel):
    question_id: str
    question: str
    question_type: QuestionType
    options: List[OptionItem] = Field(default_factory=list)
    allow_voice: bool = True
    allow_touch: bool = True
    language: str = "en"
    helper_text: Optional[str] = None
    min_val: Optional[int] = None
    max_val: Optional[int] = None
    unit: Optional[str] = None
    is_final: bool = False
    red_flag_warning: Optional[str] = None

class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: Any = Field(..., description="Answer data: boolean, string, list of strings, number, or pain map dict")
    input_method: str = Field("touch", description="'touch' or 'voice'")
    timestamp: Optional[str] = None

class PainLocationItem(BaseModel):
    region: str = Field(..., description="Anatomical region identifier (e.g. chest, abdomen, head, shoulder, knee)")
    side: str = Field("center", description="'left', 'right', 'center', or 'both'")
    pain: bool = True
    severity: Optional[int] = Field(None, ge=0, le=10, description="Severity for this specific region")

class PainLocationSubmission(BaseModel):
    session_id: Optional[str] = None
    view: str = Field("front", description="'front' or 'back'")
    locations: List[PainLocationItem] = Field(default_factory=list)
    pain_intensity: int = Field(5, ge=0, le=10, description="Overall pain intensity score 0-10")
    pain_types: List[str] = Field(default_factory=list, description="Characteristics e.g. sharp, dull, throbbing, burning, aching")
    duration: Optional[str] = Field(None, description="Reported duration (e.g. 2 days, 1 week)")
    notes: Optional[str] = None

class VoiceHistoryResponse(BaseModel):
    transcript: str
    detected_language: str
    confidence: float
    next_question: Optional[DynamicQuestion] = None
    question_id: Optional[str] = None
    input_type: str = "voice"
    red_flag: bool = False

class RedFlagAlert(BaseModel):
    red_flag: bool = False
    severity: str = "none"  # none, low, medium, high, emergency
    message: str = ""
    action_required: str = ""

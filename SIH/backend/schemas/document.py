from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    SCAN_REPORT = "scan_report"
    PREVIOUS_RECORD = "previous_record"
    OTHER = "other"

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentUploadResponse(BaseModel):
    document_id: str
    session_id: str
    filename: str
    file_size_bytes: int
    document_type: DocumentType
    status: DocumentStatus
    upload_time: str
    message: str

class DocumentStatusResponse(BaseModel):
    document_id: str
    session_id: str
    filename: str
    status: DocumentStatus
    progress_percent: int
    message: str
    parsed_preview: Optional[Dict[str, Any]] = None

class DocumentResultResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    status: DocumentStatus
    raw_text: Optional[str] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    ocr_confidence: Optional[float] = None

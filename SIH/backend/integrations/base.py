from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from backend.schemas.history import DynamicQuestion, VoiceHistoryResponse, RedFlagAlert
from backend.schemas.document import DocumentStatusResponse, DocumentResultResponse, DocumentType
from backend.schemas.patient import ABHAVerifyResponse

class BaseAIService(ABC):
    """
    Integration Contract for Member 2 (AI, Voice & Triage Engine).
    Implement this interface to replace MockAIService with your real
    LLM, ASR (Automatic Speech Recognition) and Medical Triage models.
    """
    @abstractmethod
    def get_next_question(
        self,
        session_id: str,
        current_question_id: Optional[str] = None,
        last_answer: Optional[Any] = None,
        language: str = "en",
        session_context: Optional[Dict[str, Any]] = None
    ) -> Optional[DynamicQuestion]:
        """Returns the next adaptive question based on patient's prior answers."""
        pass

    @abstractmethod
    def process_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str,
        session_id: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> VoiceHistoryResponse:
        """Converts patient voice input to text and determines next question."""
        pass

    @abstractmethod
    def evaluate_triage(
        self,
        session_id: str,
        question_id: str,
        answer: Any,
        session_context: Optional[Dict[str, Any]] = None
    ) -> RedFlagAlert:
        """Evaluates clinical emergency red flags without making formal medical diagnosis."""
        pass


class BaseOCRService(ABC):
    """
    Integration Contract for Member 3 (OCR & Document Digitization).
    Implement this interface to connect your Tesseract / PaddleOCR /
    Vision LLM pipeline for medical prescriptions and reports.
    """
    @abstractmethod
    def queue_document_processing(
        self,
        document_id: str,
        file_path: str,
        doc_type: DocumentType,
        session_id: str
    ) -> None:
        """Queues document for asynchronous OCR processing."""
        pass

    @abstractmethod
    def get_document_status(self, document_id: str) -> DocumentStatusResponse:
        """Returns the current OCR processing state (uploaded, processing, completed, failed)."""
        pass

    @abstractmethod
    def get_document_result(self, document_id: str) -> DocumentResultResponse:
        """Returns structured extracted text, medical entities, and confidence."""
        pass


class BaseABDMService(ABC):
    """
    Integration Contract for Member 6 (ABDM / Ayushman Bharat Digital Mission).
    Implement this interface with official ABDM M1/M2 APIs, Gateway authentication,
    and Consent Manager integration.
    """
    @abstractmethod
    def verify_abha(self, abha_id: str) -> ABHAVerifyResponse:
        """Validates ABHA ID or PHR address against ABDM registry."""
        pass

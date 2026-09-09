import time
from typing import Dict, Any
from backend.integrations.base import BaseOCRService
from backend.schemas.document import (
    DocumentStatusResponse,
    DocumentResultResponse,
    DocumentType,
    DocumentStatus
)

class MockOCRService(BaseOCRService):
    """
    Simulates Member 3's OCR and Document Intelligence Service.
    In real deployment, Member 3 replaces this with their OCR pipeline
    (Tesseract, PaddleOCR, LayoutLM, or specialized Medical OCR models).
    """

    def __init__(self):
        # document_id -> metadata dictionary
        self._documents: Dict[str, Dict[str, Any]] = {}

    def queue_document_processing(
        self,
        document_id: str,
        file_path: str,
        doc_type: DocumentType,
        session_id: str
    ) -> None:
        self._documents[document_id] = {
            "document_id": document_id,
            "session_id": session_id,
            "file_path": file_path,
            "doc_type": doc_type,
            "queued_at": time.time(),
            "status": DocumentStatus.UPLOADED,
            "filename": file_path.split("/")[-1].split("\\")[-1]
        }

    def get_document_status(self, document_id: str) -> DocumentStatusResponse:
        doc = self._documents.get(document_id)
        if not doc:
            return DocumentStatusResponse(
                document_id=document_id,
                session_id="",
                filename="unknown",
                status=DocumentStatus.FAILED,
                progress_percent=0,
                message="Document ID not found in OCR ingestion queue."
            )

        elapsed = time.time() - doc["queued_at"]
        
        # Simulate realistic multi-stage OCR pipeline progression
        if elapsed < 2.0:
            status = DocumentStatus.UPLOADED
            progress = 25
            msg = "Document received and queued for preprocessing."
            preview = None
        elif elapsed < 5.0:
            status = DocumentStatus.PROCESSING
            progress = 65
            msg = "Extracting text, layout analysis, and medical entity recognition..."
            preview = None
        else:
            status = DocumentStatus.COMPLETED
            progress = 100
            msg = "OCR extraction completed successfully."
            preview = {
                "institution": "District Civil Hospital / AIIMS",
                "consultant": "Dr. R. K. Verma, MD",
                "date": "2026-08-10",
                "extracted_rx": [
                    "Tab Paracetamol 650mg - 1-0-1 (3 days)",
                    "Tab Cetirizine 10mg - 0-0-1 (5 days)"
                ],
                "clinical_impression": "Acute viral febrile illness with mild bronchitis",
                "ocr_confidence": 0.94
            }

        doc["status"] = status
        return DocumentStatusResponse(
            document_id=document_id,
            session_id=doc["session_id"],
            filename=doc["filename"],
            status=status,
            progress_percent=progress,
            message=msg,
            parsed_preview=preview
        )

    def get_document_result(self, document_id: str) -> DocumentResultResponse:
        doc = self._documents.get(document_id)
        if not doc:
            return DocumentResultResponse(
                document_id=document_id,
                document_type=DocumentType.OTHER,
                status=DocumentStatus.FAILED,
                raw_text=None,
                extracted_fields=None,
                ocr_confidence=0.0
            )

        status_info = self.get_document_status(document_id)
        return DocumentResultResponse(
            document_id=document_id,
            document_type=doc.get("doc_type", DocumentType.OTHER),
            status=status_info.status,
            raw_text="Rx\nTab Paracetamol 650mg TDS x 3 days\nTab Cetirizine 10mg OD x 5 days\nAdv: Warm fluids, review in 3 days if fever persists.",
            extracted_fields=status_info.parsed_preview,
            ocr_confidence=0.94
        )

mock_ocr_service = MockOCRService()

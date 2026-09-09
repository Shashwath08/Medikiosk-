from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from backend.schemas.document import (
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentResultResponse,
    DocumentType,
    DocumentStatus
)
from backend.services.session_store import session_store
from backend.integrations.ocr_service import mock_ocr_service
from backend.utils.file_handler import save_uploaded_file

router = APIRouter(prefix="/documents", tags=["Documents & OCR (Member 1 / 3)"])

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Medical Document (Prescription / Lab / Scan)",
    description="Accepts document images (JPEG/PNG) or PDFs, stores them safely, and triggers Member 3 OCR pipeline."
)
async def upload_document(
    session_id: str = Form(...),
    document_type: DocumentType = Form(DocumentType.PRESCRIPTION),
    file: UploadFile = File(...)
):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    # Validate, sanitize, and save file locally
    document_id, file_path, file_size = await save_uploaded_file(file)

    now = datetime.now(timezone.utc).isoformat()
    doc_meta = {
        "document_id": document_id,
        "filename": file.filename,
        "file_size_bytes": file_size,
        "document_type": document_type.value,
        "status": DocumentStatus.UPLOADED.value,
        "upload_time": now
    }

    # Record in session
    session_store.add_document(session_id, doc_meta)

    # Queue in Member 3 OCR Service
    mock_ocr_service.queue_document_processing(
        document_id=document_id,
        file_path=file_path,
        doc_type=document_type,
        session_id=session_id
    )

    return DocumentUploadResponse(
        document_id=document_id,
        session_id=session_id,
        filename=file.filename or "uploaded_document",
        file_size_bytes=file_size,
        document_type=document_type,
        status=DocumentStatus.UPLOADED,
        upload_time=now,
        message="Document uploaded successfully and queued for OCR processing."
    )

@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Poll OCR Processing Status",
    description="Member 3 OCR status polling. Frontend polls this to track progress (uploaded -> processing -> completed)."
)
async def get_document_ocr_status(document_id: str):
    return mock_ocr_service.get_document_status(document_id)

@router.get(
    "/{document_id}/result",
    response_model=DocumentResultResponse,
    summary="Get Extracted OCR Text & Entities",
    description="Member 3 OCR results. Returns parsed medications, diagnoses, and medical data."
)
async def get_document_ocr_result(document_id: str):
    return mock_ocr_service.get_document_result(document_id)

@router.get(
    "/session/{session_id}",
    summary="List All Documents for a Session",
    description="Retrieves metadata of all documents uploaded during this kiosk session."
)
async def list_session_documents(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return {
        "session_id": session_id,
        "documents": session.documents_uploaded
    }

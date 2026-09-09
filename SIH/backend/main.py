import os
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings
from backend.api.patients import router as patients_router
from backend.api.consent import router as consent_router
from backend.api.history import router as history_router
from backend.api.documents import router as documents_router
from backend.api.sessions import router as sessions_router
from backend.api.doctor import router as doctor_router

# Base project path
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="MediKiosk — AI-Powered Clinical History-Taking Platform",
    description="""
    ## Smart India Hackathon (SIH) — Member 1: Patient Frontend & Experience
    
    This platform provides the complete digital kiosk interface for patients in Indian public & private hospitals:
    * **Patient Registration** & ABHA ID Verification (ABDM stub ready for Member 6)
    * **Language Selection** across 6 Indian Languages (EN, HI, ML, TA, KN, TE)
    * **Clinical & AI Consent** with graceful session management
    * **Conversational Voice + Touch History Taking** (Ready for Member 2 ASR/LLM)
    * **Interactive Human Anatomy Pain Map** with multi-region selection & severity scoring
    * **Adaptive Dynamic Questions Engine** with emergency triage / red-flag alerts
    * **Medical Document Upload & Scan UI** with OCR pipeline polling (Ready for Member 3)
    * **Server-Side Safe QR Code Generation** (Ready for Member 5 Doctor Dashboard retrieval)
    """,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(patients_router, prefix=settings.API_PREFIX)
app.include_router(consent_router, prefix=settings.API_PREFIX)
app.include_router(history_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(sessions_router, prefix=settings.API_PREFIX)
app.include_router(doctor_router, prefix=settings.API_PREFIX)

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "MediKiosk Member 1 Patient Frontend & Backend Service",
        "version": settings.VERSION,
        "mock_services": {
            "member_2_ai_voice": "active_mock",
            "member_3_ocr": "active_mock",
            "member_5_doctor_qr": "active_ready",
            "member_6_abdm": "active_mock"
        }
    }

# Global friendly error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal MediKiosk Server Error",
            "detail": str(exc),
            "hint": "Please check backend logs or contact hospital IT staff."
        }
    )

# Mount frontend static assets if directory exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", tags=["Kiosk UI"])
    async def serve_kiosk_app():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend index.html not yet initialized"}

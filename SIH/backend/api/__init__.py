from backend.api.patients import router as patients_router
from backend.api.consent import router as consent_router
from backend.api.history import router as history_router
from backend.api.documents import router as documents_router
from backend.api.sessions import router as sessions_router
from backend.api.doctor import router as doctor_router

__all__ = [
    "patients_router",
    "consent_router",
    "history_router",
    "documents_router",
    "sessions_router",
    "doctor_router",
]

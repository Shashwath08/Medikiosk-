# MediKiosk — AI-Powered Digital Clinical History Kiosk
### Smart India Hackathon (SIH) | Member 1: Patient Frontend & Patient Experience

MediKiosk is an interactive, multi-modal clinical history-taking platform designed for outpatient departments (OPD) in Indian government and private hospitals.

This repository contains the complete implementation for **Member 1 (Patient Frontend / Patient Experience)**, providing an accessible, bilingual kiosk interface, touch + voice question collection, interactive human anatomy pain mapping, document scanning, session persistence, and server-side safe QR code generation, together with clean API contracts and mock integration adapters for Members 2 through 6.

---

## Table of Contents
1. [Project Overview & Member 1 Scope](#project-overview--member-1-scope)
2. [Modular Architecture](#modular-architecture)
3. [Folder Structure](#folder-structure)
4. [Quickstart & Running Locally](#quickstart--running-locally)
5. [Environment Variables](#environment-variables)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Patient Frontend Journey](#patient-frontend-journey)
8. [Interactive Human Anatomy Component](#interactive-human-anatomy-component)
9. [QR Code Security Architecture & Scan Flow](#qr-code-security-architecture--scan-flow)
10. [Replaceable Mock Services & Integration Guide for Members 2–6](#replaceable-mock-services--integration-guide-for-members-26)
    - [Member 2: AI, Voice & Triage Engine](#member-2--ai-voice--triage-engine)
    - [Member 3: OCR & Document Digitization](#member-3--ocr--document-digitization)
    - [Member 4: Core Backend Sync](#member-4--core-backend-sync)
    - [Member 5: Doctor Dashboard QR Case Retrieval](#member-5--doctor-dashboard-qr-case-retrieval)
    - [Member 6: ABDM, Database & Production Security](#member-6--abdm-database--production-security)
11. [Testing Suite](#testing-suite)
12. [Docker Deployment](#docker-deployment)

---

## Project Overview & Member 1 Scope

### Overall System Context
The complete MediKiosk platform enables a patient visiting a hospital OPD to:
1. Identify themselves via ABHA or as a new patient
2. Choose their regional language
3. Provide informed consent for digital history collection and AI processing
4. Engage in an adaptive, conversational interview using voice or touch
5. Mark exact pain locations on an interactive anatomical map
6. Scan or upload previous physical prescriptions and lab reports
7. Complete the session and receive a unique, safe QR code
8. Allow the consulting physician to scan the QR code to instantly access a clinical summary

### Member 1 Deliverables
* **Zero Hardcoded Fakes:** Frontend talks exclusively via REST APIs and Pydantic schemas.
* **Accessible Kiosk UI:** Built with large touch targets, high contrast, clean typography, and zero hover dependencies for touchscreens.
* **Multilingual UI (6 Indian Languages):** English, Hindi (हिन्दी), Malayalam (മലയാളം), Tamil (தமிழ்), Kannada (ಕನ್ನಡ), Telugu (తెలుగు).
* **Dual Voice + Touch Input:** Built-in microphone controller with waveform visualizer and audio playback preview, with on-screen touch fallbacks for all questions.
* **Interactive Anatomy Component:** Front and Back vector body map with selectable anatomical regions, pain intensity slider (0–10), and pain descriptors.
* **Emergency Red-Flag Interceptor:** Halts questioning and provides a calm, prominent staff assistance takeover when priority symptoms are reported.
* **Document Uploader:** Supports camera capture, device files (PDF, PNG, JPEG), size enforcement, and live OCR status polling (`uploaded` → `processing` → `completed`).
* **Safe Server-Side QR Generation:** Encodes strictly an opaque token (`MEDIKIOSK:<token>`) with zero leaked PII or medical records.
* **Clean API Contracts:** Abstract base classes (`BaseAIService`, `BaseOCRService`, `BaseABDMService`) ready for team integration.

---

## Modular Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Patient UI (Kiosk Touch Display)                     │
│  (index.html, styles.css, anatomy.css, app.js, question_renderer.js)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON / Multipart REST APIs
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                Frontend API Client & State Manager                     │
│               (frontend/js/api.js, frontend/js/state.js)               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Requests
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   FastAPI Application & Routers                        │
│   ├── /api/patients   (Registration, ABHA Verification, Language, QR)  │
│   ├── /api/consent    (Grant / Decline Consent)                        │
│   ├── /api/history    (Adaptive Q&A, Voice Upload, Anatomy Pain Map)   │
│   ├── /api/documents  (File Upload, OCR Status Polling, OCR Results)   │
│   ├── /api/sessions   (Session State, Finalize & Generate QR)          │
│   └── /api/patients/qr/{token} (Doctor Dashboard Retrieval Endpoint)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Clean Service Interfaces
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Service Layer & Mock Integration Adapters                  │
│                                                                        │
│  ├── SessionStore: Thread-safe in-memory store (Replaceable by Member 6)│
│  ├── QRService: Server-side PNG/Data URI QR generator                  │
│  ├── BaseAIService  ──► MockAIService   (Replaceable by Member 2)      │
│  ├── BaseOCRService ──► MockOCRService  (Replaceable by Member 3)      │
│  └── BaseABDMService──► MockABDMService (Replaceable by Member 6)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
medikiosk/
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, CORS, routes, static mount
│   ├── config.py                   # App settings, limits, supported languages
│   ├── api/
│   │   ├── __init__.py
│   │   ├── patients.py             # Patient registration, ABHA verify, language
│   │   ├── consent.py              # Consent recording & session termination
│   │   ├── history.py              # Dynamic Q&A, voice processing, pain location
│   │   ├── documents.py            # Document upload & OCR status polling
│   │   ├── sessions.py             # Session lifecycle & completion
│   │   └── doctor.py               # Member 5 Doctor QR case resolution
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── patient.py              # Registration, ABHA, and language schemas
│   │   ├── consent.py              # Consent grant/decline schemas
│   │   ├── history.py              # Dynamic question models, pain JSON, voice
│   │   ├── document.py             # File upload and OCR status schemas
│   │   └── session.py              # Session data & DoctorPatientView schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_store.py        # In-memory store (Member 6 DB boundary)
│   │   └── qr_service.py           # QR generation with safe opaque tokens
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract Base Classes (Contracts)
│   │   ├── ai_service.py           # Member 2 mock implementation
│   │   ├── ocr_service.py          # Member 3 mock implementation
│   │   └── abdm_service.py         # Member 6 mock implementation
│   └── utils/
│       ├── __init__.py
│       └── file_handler.py         # File validation, size limits, sanitation
│
├── frontend/
│   ├── index.html                  # Kiosk SPA entrypoint
│   ├── css/
│   │   ├── styles.css              # Kiosk theme, high-contrast buttons, voice bar
│   │   └── anatomy.css             # Vector body map styling and pain indicators
│   └── js/
│       ├── api.js                  # REST API client with error handling
│       ├── state.js                # Reactive session state manager
│       ├── i18n.js                 # 6 Indian language translations
│       ├── audio.js                # Web Audio API microphone controller
│       ├── anatomy.js              # Interactive SVG human anatomy component
│       ├── question_renderer.js    # Reusable dynamic question engine
│       ├── doc_uploader.js         # Camera & file uploader with OCR progress
│       └── app.js                  # Master application step orchestrator
│
├── tests/
│   ├── __init__.py
│   ├── test_patients.py            # Registration, phone validation, ABHA check
│   ├── test_consent.py             # Consent accept / decline flows
│   ├── test_history.py             # Dynamic questions, voice upload, red flags
│   ├── test_documents.py          # Document upload & OCR status polling
│   ├── test_qr.py                  # QR code image generation & payload safety
│   ├── test_doctor_access.py       # Doctor dashboard token retrieval
│   └── test_full_flow.py           # End-to-end 10-step patient journey test
│
├── uploads/                        # Local temporary document storage
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── Dockerfile                      # Containerization definition
├── docker-compose.yml              # Single-command launch configuration
└── README.md                       # Complete documentation & integration guide
```

---

## Quickstart & Running Locally

### Prerequisites
* Python 3.10+ (Tested on Python 3.14)
* pip

### Installation Steps

1. **Clone or navigate to the repository:**
   ```bash
   cd c:\Users\Admin\Downloads\SIH
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the MediKiosk Server:**
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Access the Application:**
   * **Patient Kiosk UI:** Open `http://127.0.0.1:8000/` in your browser.
   * **Interactive Swagger API Documentation:** Open `http://127.0.0.1:8000/docs`.
   * **Alternative ReDoc Documentation:** Open `http://127.0.0.1:8000/redoc`.

---

## Environment Variables

Copy `.env.example` to `.env` to customize settings:

| Variable | Default | Purpose |
|---|---|---|
| `PROJECT_NAME` | `"MediKiosk Patient Experience"` | App title in OpenAPI docs |
| `DEBUG` | `True` | Enables debug logs and error details |
| `API_PREFIX` | `"/api"` | Base API router prefix |
| `MAX_FILE_SIZE_MB` | `10` | Maximum uploaded document size in MB |
| `ALLOWED_ORIGINS` | `"*"` | CORS allowed domains |
| `ENABLE_MOCK_AI` | `True` | Use MockAIService vs real Member 2 microservice |
| `ENABLE_MOCK_OCR` | `True` | Use MockOCRService vs real Member 3 pipeline |
| `ENABLE_MOCK_ABDM` | `True` | Use MockABDMService vs official ABDM Gateway |

---

## API Endpoints Reference

All endpoints accept and return `application/json` unless marked as `multipart/form-data` or image stream.

### 1. Patients & Registration
* `POST /api/patients/register` — Registers patient demographics; returns session ID and opaque token.
* `POST /api/patients/verify-abha` — Validates 14-digit ABHA ID or PHR address (`name@abdm`).
* `POST /api/patients/{session_id}/language` — Updates preferred language (`en`, `hi`, `ml`, `ta`, `kn`, `te`).
* `GET /api/patients/{session_id}` — Retrieves current patient session profile.
* `GET /api/patients/{session_id}/qr` — Generates and streams a PNG QR code image.

### 2. Consent
* `POST /api/consent` — Records patient acceptance or graceful decline of clinical AI consent.
* `GET /api/consent/{session_id}` — Queries active consent status.

### 3. Clinical History & AI (Member 2 integration points)
* `GET /api/history/next-question` — Fetches the dynamically determined next clinical question.
* `POST /api/history/answer` — Submits patient answer (touch or text), checks red flags, and returns next question.
* `POST /api/history/voice` (`multipart/form-data`) — Submits voice audio stream; returns transcript, red flags, and next question.
* `POST /api/history/pain-location` — Submits structured anatomy pain map selection (region, side, severity, descriptors).
* `GET /api/history/state/{session_id}` — Returns all answered questions and pain records.
* `GET /api/triage/status/{session_id}` — Queries clinical priority and red flag state.

### 4. Documents & OCR (Member 3 integration points)
* `POST /api/documents/upload` (`multipart/form-data`) — Uploads image/PDF prescription; queues for OCR.
* `GET /api/documents/{document_id}/status` — Polls OCR processing stage (`uploaded` → `processing` → `completed`).
* `GET /api/documents/{document_id}/result` — Retrieves extracted text, medications, and clinical impression.
* `GET /api/documents/session/{session_id}` — Lists all uploaded documents for this kiosk session.

### 5. Session Lifecycle & Doctor Retrieval (Members 4 & 5 integration points)
* `GET /api/sessions/{session_id}` — Retrieves complete session state.
* `POST /api/sessions/{session_id}/complete` — Finalizes session, locks records, and returns base64 QR code.
* `GET /api/patients/qr/{token}` — **Member 5 Doctor Dashboard endpoint**: Retrieves the patient's clinical file by scanning the QR code token.

---

## Patient Frontend Journey

```
[ 1. Landing Screen ]
        │  (Touch to Begin)
        ▼
[ 2. Language Selection ]
        │  (EN, HI, ML, TA, KN, TE)
        ▼
[ 3. Registration / ABHA ]
        │  (Verify existing ABHA or register as New Patient)
        ▼
[ 4. Clinical & AI Consent ]
        │  (Accept terms → proceed; Decline → graceful exit)
        ▼
[ 5. Adaptive History Interview ]
        │  (Chief Complaint via Touch or Voice)
        ▼
[ 6. Interactive Anatomy Pain Map ]
        │  (Front/Back body selection + Pain severity slider 0-10)
        ▼
[ 7. Dynamic Follow-up Questions ]
        │  (Duration, severity, medications, allergies)
        │  * Emergency Red-Flag detection halts flow if chest pain/critical symptoms arise
        ▼
[ 8. Document Upload & OCR Scan ]
        │  (Camera capture or file browser; live OCR progress polling)
        ▼
[ 9. Completion & Safe QR Code ]
        │  (Server-generated QR code displayed for physician scan)
        ▼
[ 10. Doctor Case Retrieval ]
        (Doctor scans QR from their dashboard to open clinical file)
```

---

## Interactive Human Anatomy Component

Implemented in `frontend/js/anatomy.js` and `frontend/css/anatomy.css`.

### Features
* **Identifiable SVG Regions:** Every body region has a semantic ID (`body-head`, `body-chest`, `body-abdomen`, `body-shoulder-left`, `body-knee-right`, etc.).
* **Front and Back Views:** One-touch toggle between anterior (front) and posterior (back) body perspectives.
* **Multi-Region Selection:** Patients can tap multiple areas (e.g. chest and left arm).
* **Pain Severity Slider:** 0 to 10 visual scale with color shift (Green 0–3 → Amber 4–6 → Red 7–10).
* **Pain Character Descriptors:** Sharp, Dull, Throbbing, Burning, Cramping, Shooting.
* **Structured JSON Output:**
  ```json
  {
    "view": "front",
    "locations": [
      {
        "region": "chest",
        "side": "center",
        "pain": true
      },
      {
        "region": "arm",
        "side": "left",
        "pain": true
      }
    ],
    "pain_intensity": 8,
    "pain_types": ["sharp", "throbbing"],
    "duration": "2 days"
  }
  ```

---

## QR Code Security Architecture & Scan Flow

> [!IMPORTANT]
> **Zero Health Information in QR Matrix:**
> Generating QR codes containing raw medical diagnoses or patient Aadhaar/ABHA numbers directly is a major privacy and compliance violation. If a bystander snaps a photo of the patient's screen or paper slip, raw data would be leaked.

### MediKiosk QR Architecture
1. Upon registration, MediKiosk generates a cryptographically random, opaque token (e.g., `token = secrets.token_urlsafe(16)`).
2. The server-side QR generator strictly encodes:
   ```
   MEDIKIOSK:1b4df89c_token
   ```
3. When the patient reaches the consultation room:
   ```
   Doctor scans QR code on Doctor Dashboard
                  │
                  ▼
   Dashboard extracts opaque token
                  │
                  ▼
   GET /api/patients/qr/{token}
   (Backend validates doctor authentication & authorization)
                  │
                  ▼
   Backend returns sanitized DoctorPatientView JSON
   (Demographics, Chief Complaint, Pain Map, Answers, Document Links)
   ```

---

## Replaceable Mock Services & Integration Guide for Members 2–6

All mock implementations reside in `backend/integrations/` and implement the abstract contracts in `backend/integrations/base.py`.

### Member 2 — AI, Voice & Triage Engine
* **Integration Contract:** `BaseAIService` in `backend/integrations/base.py`
* **Current Mock:** `backend/integrations/ai_service.py` (`MockAIService`)
* **How to Connect Your Real Model:**
  1. Create your service class implementing `BaseAIService`:
     ```python
     from backend.integrations.base import BaseAIService
     from backend.schemas.history import DynamicQuestion, VoiceHistoryResponse, RedFlagAlert

     class RealMember2AIService(BaseAIService):
         def get_next_question(self, session_id, current_question_id, last_answer, language, session_context):
             # Call your fine-tuned LLM or clinical rule engine
             ...
         def process_voice(self, audio_bytes, filename, language, session_id, session_context):
             # Send audio to Whisper / Bhashini / Google Speech API
             ...
         def evaluate_triage(self, session_id, question_id, answer, session_context):
             # Evaluate medical red flags & vitals
             ...
     ```
  2. In `backend/api/history.py`, replace `mock_ai_service` with your new instance:
     ```python
     from backend.integrations.real_ai_service import real_ai_service as ai_service
     ```
  3. No frontend changes are needed.

### Member 3 — OCR & Document Digitization
* **Integration Contract:** `BaseOCRService` in `backend/integrations/base.py`
* **Current Mock:** `backend/integrations/ocr_service.py` (`MockOCRService`)
* **How to Connect Your Real Pipeline:**
  1. Implement `queue_document_processing`, `get_document_status`, and `get_document_result`.
  2. When `POST /api/documents/upload` receives a file, pass `file_path` to your OCR pipeline (Tesseract, PaddleOCR, LayoutLM, or Vision model).
  3. Update status to `completed` and return extracted medications and diagnoses in `parsed_preview`.
  4. The frontend will automatically poll `GET /api/documents/{id}/status` and render your extracted details in the patient preview card.

### Member 4 — Core Backend Sync
* **Routes Implemented:** All routes in `backend/api/` are fully functional and documented in Swagger (`/docs`).
* **Schemas:** All request and response bodies use strict Pydantic v2 models in `backend/schemas/`.
* **How to Extend:** If additional clinical fields are needed, update `backend/schemas/patient.py` or `backend/schemas/history.py`.

### Member 5 — Doctor Dashboard QR Case Retrieval
* **Target Endpoint:** `GET /api/patients/qr/{token}`
* **How to Integrate:**
  1. In your doctor web/mobile app, scan the patient's QR code.
  2. Parse the string: if it starts with `MEDIKIOSK:`, strip the prefix to obtain the `<token>`.
  3. Send an authenticated HTTP GET request to `http://<server-ip>:8000/api/patients/qr/<token>`.
  4. The endpoint returns `DoctorPatientView` with complete structured data:
     * `full_name`, `age`, `gender`, `phone_number`, `abha_id`
     * `chief_complaint`, `triage_status`, `red_flag`
     * `pain_data` (interactive anatomy selections and pain score)
     * `answers` (all questionnaire questions & responses)
     * `documents` (uploaded prescription slips and OCR results)

### Member 6 — ABDM, Database & Production Security
* **Persistence Boundary:** `backend/services/session_store.py`
* **ABHA Verification Boundary:** `backend/integrations/abdm_service.py`
* **Tasks for Member 6:**
  1. **Database:** Replace the in-memory dictionary in `SessionStore` with PostgreSQL / MongoDB tables using SQLAlchemy or Tortoise ORM.
  2. **ABDM Gateway:** Replace `MockABDMService.verify_abha` with official NHA M1/M2/M3 API calls, client certificates, and OTP verification.
  3. **Consent Artifacts:** In `backend/api/consent.py`, sign and store official FHIR Consent artifacts conforming to ABDM specifications.
  4. **Security Hardening:** Add rate limiting (`slowapi`), JWT authorization headers for the doctor endpoints, and audit trail logging.

---

## Testing Suite

A comprehensive test suite with 15 test cases verifies every layer of the Member 1 implementation:

```bash
pytest -v tests/
```

### Test Coverage Breakdown
| Test File | Verified Behavior |
|---|---|
| `test_patients.py` | Registration validation, 10-digit phone normalization, ABHA 14-digit and PHR parsing, language switching |
| `test_consent.py` | Granular consent recording, active state transition, graceful termination when declined |
| `test_history.py` | Adaptive question traversal, touch answer submission, voice audio upload, anatomy pain JSON, red-flag emergency alert trigger |
| `test_documents.py` | PNG and PDF upload handling, OCR status lifecycle polling, rejection of dangerous file types (e.g. `.exe`) |
| `test_qr.py` | Server-side PNG QR code generation, opaque payload check (`MEDIKIOSK:<token>`), verifying zero PII leakage |
| `test_doctor_access.py` | Doctor dashboard QR token resolution, patient case reconstruction, 404 on expired token |
| `test_full_flow.py` | End-to-end simulation of the complete 10-step patient journey |

---

## Docker Deployment

To build and run MediKiosk in an isolated Docker container:

```bash
docker-compose up --build
```

The kiosk will be available at `http://localhost:8000`.
Uploaded files will be persisted in the local `./uploads` directory mounted to the container.

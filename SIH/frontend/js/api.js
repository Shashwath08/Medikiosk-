/**
 * MediKiosk Frontend API Client (Member 1)
 *
 * Encapsulates all backend REST communications.
 * Provides resilient error handling, JSON serialization, and multipart uploads.
 */

const BASE_URL = window.location.origin + "/api";

class ApiClient {
  async request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const defaultHeaders = {};

    if (!(options.body instanceof FormData)) {
      defaultHeaders["Content-Type"] = "application/json";
    }

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMsg = data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`;
        return {
          success: false,
          status: response.status,
          error: errorMsg,
          data: data
        };
      }

      return {
        success: true,
        status: response.status,
        data: data
      };
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      return {
        success: false,
        status: 0,
        error: "Cannot connect to MediKiosk server. Please ensure the backend is running.",
        data: null
      };
    }
  }

  // 1. Patient Registration & ABHA
  async registerPatient(patientData) {
    return this.request("/patients/register", {
      method: "POST",
      body: JSON.stringify(patientData)
    });
  }

  async verifyABHA(abhaId) {
    return this.request("/patients/verify-abha", {
      method: "POST",
      body: JSON.stringify({ abha_id: abhaId })
    });
  }

  async updateLanguage(sessionId, language) {
    return this.request(`/patients/${sessionId}/language`, {
      method: "POST",
      body: JSON.stringify({ language })
    });
  }

  // 2. Consent
  async submitConsent(sessionId, consentGiven, items = {}) {
    return this.request("/consent", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        consent_given: consentGiven,
        consent_version: "v1.0",
        consent_items: items
      })
    });
  }

  // 3. Clinical History Q&A
  async getNextQuestion(sessionId, currentQuestionId = null, language = null) {
    let qUrl = `/history/next-question?session_id=${encodeURIComponent(sessionId)}`;
    if (currentQuestionId) qUrl += `&current_question_id=${encodeURIComponent(currentQuestionId)}`;
    if (language) qUrl += `&language=${encodeURIComponent(language)}`;
    return this.request(qUrl, { method: "GET" });
  }

  async submitAnswer(sessionId, questionId, answer, inputMethod = "touch") {
    return this.request("/history/answer", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        question_id: questionId,
        answer: answer,
        input_method: inputMethod
      })
    });
  }

  async uploadVoice(sessionId, audioBlob, language = "en") {
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("language", language);
    formData.append("audio_file", audioBlob, "patient_recording.webm");

    return this.request("/history/voice", {
      method: "POST",
      body: formData
    });
  }

  async submitPainLocation(painData) {
    return this.request("/history/pain-location", {
      method: "POST",
      body: JSON.stringify(painData)
    });
  }

  // 4. Documents & OCR
  async uploadDocument(sessionId, file, documentType = "prescription") {
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("document_type", documentType);
    formData.append("file", file);

    return this.request("/documents/upload", {
      method: "POST",
      body: formData
    });
  }

  async getDocumentStatus(documentId) {
    return this.request(`/documents/${documentId}/status`, { method: "GET" });
  }

  async getDocumentResult(documentId) {
    return this.request(`/documents/${documentId}/result`, { method: "GET" });
  }

  // 5. Session Lifecycle & QR
  async getSessionState(sessionId) {
    return this.request(`/sessions/${sessionId}`, { method: "GET" });
  }

  async completeSession(sessionId) {
    return this.request(`/sessions/${sessionId}/complete`, {
      method: "POST"
    });
  }

  // 6. Doctor Dashboard Integration (Member 5 endpoint)
  async getDoctorPatientView(qrToken) {
    return this.request(`/patients/qr/${encodeURIComponent(qrToken)}`, {
      method: "GET"
    });
  }
}

export const api = new ApiClient();

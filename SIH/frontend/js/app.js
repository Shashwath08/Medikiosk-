/**
 * MediKiosk Master Patient Experience Orchestrator (Member 1)
 */

import { api } from "./api.js";
import { stateManager } from "./state.js";
import { LANGUAGES, getTranslation } from "./i18n.js";
import { QuestionRenderer } from "./question_renderer.js";
import { DocumentUploader } from "./doc_uploader.js";

class MediKioskApp {
  constructor() {
    this.appMount = document.getElementById("app-mount");
    this.stepTrackerEl = document.getElementById("step-tracker");
    this.langIndicatorEl = document.getElementById("lang-indicator");
    this.docUploader = null;
    this.questionRenderer = null;

    this.init();
  }

  init() {
    stateManager.subscribe((state) => this.onStateChange(state));
    this.renderCurrentStep();
  }

  onStateChange(state) {
    if (this.langIndicatorEl) {
      const currentLang = LANGUAGES.find(l => l.code === state.language) || LANGUAGES[0];
      this.langIndicatorEl.textContent = `${currentLang.flag} ${currentLang.nativeName}`;
    }
  }

  t(key) {
    return getTranslation(stateManager.get().language, key);
  }

  updateProgressTracker(activeStepNumber) {
    const steps = [
      { num: 1, label: "Language" },
      { num: 2, label: "Register" },
      { num: 3, label: "Consent" },
      { num: 4, label: "History" },
      { num: 5, label: "Documents" },
      { num: 6, label: "QR Code" }
    ];

    this.stepTrackerEl.innerHTML = steps.map((s, idx) => `
      <div class="step-item ${s.num === activeStepNumber ? 'active' : s.num < activeStepNumber ? 'completed' : ''}">
        <span class="step-number">${s.num < activeStepNumber ? '✓' : s.num}</span>
        <span>${s.label}</span>
      </div>
      ${idx < steps.length - 1 ? '<span class="step-separator">›</span>' : ''}
    `).join('');
  }

  renderCurrentStep() {
    const state = stateManager.get();

    // Red flag emergency takeover interceptor
    if (state.redFlag) {
      this.renderRedFlagTakeover();
      return;
    }

    switch (state.currentStep) {
      case "landing":
        this.renderLanding();
        break;
      case "language":
        this.renderLanguageSelection();
        break;
      case "registration":
        this.renderRegistration();
        break;
      case "consent":
        this.renderConsent();
        break;
      case "history":
        this.renderHistory();
        break;
      case "documents":
        this.renderDocuments();
        break;
      case "completion":
        this.renderCompletion();
        break;
      default:
        this.renderLanding();
    }
  }

  // 1. Landing Screen
  renderLanding() {
    this.updateProgressTracker(1);
    this.appMount.innerHTML = `
      <div class="kiosk-card" style="text-align: center; justify-content: center; align-items: center; min-height: 520px;">
        <div class="brand-icon" style="width: 80px; height: 80px; font-size: 40px; margin-bottom: 1.5rem;">+</div>
        <h2>${this.t("welcomeTitle")}</h2>
        <p class="subtitle" style="max-width: 580px;">${this.t("welcomeDesc")}</p>
        
        <button type="button" class="btn btn-primary btn-large" id="btn-start-kiosk" style="margin-top: 1rem;">
          ${this.t("tapToBegin")} →
        </button>

        <div style="margin-top: 3rem; display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center;">
          <span class="badge-pill">🇮🇳 6 Indian Languages</span>
          <span class="badge-pill">🎙️ Voice Enabled</span>
          <span class="badge-pill">🫀 Anatomy Map</span>
          <span class="badge-pill">🛡️ ABDM Ready</span>
        </div>
      </div>
    `;

    document.getElementById("btn-start-kiosk").addEventListener("click", () => {
      stateManager.set({ currentStep: "language" });
      this.renderCurrentStep();
    });
  }

  // 2. Language Selection Screen
  renderLanguageSelection() {
    this.updateProgressTracker(1);
    this.appMount.innerHTML = `
      <div class="kiosk-card">
        <h2>${this.t("selectLangTitle")}</h2>
        <p class="subtitle">${this.t("selectLangSubtitle")}</p>

        <div class="grid-3" style="margin-bottom: 2rem;">
          ${LANGUAGES.map(lang => `
            <div class="touch-card lang-card ${stateManager.get().language === lang.code ? 'selected' : ''}" data-code="${lang.code}">
              <div style="font-size: 2rem;">${lang.flag}</div>
              <div class="card-title" style="font-size: 1.4rem;">${lang.nativeName}</div>
              <div class="card-subtext">${lang.name}</div>
            </div>
          `).join('')}
        </div>

        <div style="display: flex; justify-content: space-between; margin-top: auto;">
          <button type="button" class="btn btn-secondary" id="btn-back-landing">${this.t("back")}</button>
          <button type="button" class="btn btn-primary btn-large" id="btn-confirm-lang">${this.t("confirm")} →</button>
        </div>
      </div>
    `;

    this.appMount.querySelectorAll(".lang-card").forEach(card => {
      card.addEventListener("click", (e) => {
        this.appMount.querySelectorAll(".lang-card").forEach(c => c.classList.remove("selected"));
        e.currentTarget.classList.add("selected");
        const code = e.currentTarget.dataset.code;
        stateManager.set({ language: code });
      });
    });

    document.getElementById("btn-back-landing").addEventListener("click", () => {
      stateManager.set({ currentStep: "landing" });
      this.renderCurrentStep();
    });

    document.getElementById("btn-confirm-lang").addEventListener("click", async () => {
      const { sessionId, language } = stateManager.get();
      if (sessionId) {
        await api.updateLanguage(sessionId, language);
      }
      stateManager.set({ currentStep: "registration" });
      this.renderCurrentStep();
    });
  }

  // 3. Registration & ABHA Verification Screen
  renderRegistration() {
    this.updateProgressTracker(2);
    const p = stateManager.get().patient;
    let mode = p.isNewPatient ? "new" : "abha";

    this.appMount.innerHTML = `
      <div class="kiosk-card">
        <h2>${this.t("patientReg")}</h2>
        <p class="subtitle">${this.t("regSubtitle")}</p>

        <!-- Mode Toggle -->
        <div class="grid-2" style="margin-bottom: 1.5rem;">
          <button type="button" class="btn ${mode === 'new' ? 'btn-primary' : 'btn-secondary'}" id="btn-tab-new">
            👤 ${this.t("newPatient")}
          </button>
          <button type="button" class="btn ${mode === 'abha' ? 'btn-primary' : 'btn-secondary'}" id="btn-tab-abha">
            🆔 ${this.t("haveAbha")}
          </button>
        </div>

        <div id="reg-form-container">
          ${mode === 'abha' ? this.renderAbhaSection() : this.renderNewPatientSection()}
        </div>

        <div id="reg-error-banner" style="display: none;" class="alert-banner alert-danger"></div>

        <div style="display: flex; justify-content: space-between; margin-top: 1.5rem;">
          <button type="button" class="btn btn-secondary" id="btn-back-lang">${this.t("back")}</button>
          <button type="button" class="btn btn-primary btn-large" id="btn-submit-reg">${this.t("confirm")} →</button>
        </div>
      </div>
    `;

    this.attachRegistrationEvents();
  }

  renderAbhaSection() {
    const p = stateManager.get().patient;
    return `
      <div style="background: #f8fafc; padding: 1.5rem; border-radius: 16px; border: 1px solid var(--border-color);">
        <div class="form-group">
          <label class="form-label">${this.t("abhaNumber")}</label>
          <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
            <input 
              type="text" 
              id="input-abha" 
              class="form-input" 
              placeholder="e.g. 91-1234-5678-9012 or user@abdm" 
              value="${p.abhaId || ''}"
              style="flex: 1; min-width: 260px;"
            />
            <button type="button" class="btn btn-secondary" id="btn-verify-abha" style="font-size: 1rem;">
              🔍 ${this.t("verifyAbhaBtn")}
            </button>
          </div>
        </div>

        <div id="abha-result-box" style="display: none; margin-top: 1rem;"></div>

        <!-- Phone fallback -->
        <div class="form-group" style="margin-top: 1rem;">
          <label class="form-label">${this.t("phone")}</label>
          <input 
            type="tel" 
            id="input-phone-abha" 
            class="form-input" 
            placeholder="10-digit mobile number" 
            value="${p.phone || ''}" 
            maxlength="10"
          />
        </div>
      </div>
    `;
  }

  renderNewPatientSection() {
    const p = stateManager.get().patient;
    return `
      <div>
        <div class="form-group">
          <label class="form-label">${this.t("fullName")} *</label>
          <input type="text" id="input-fullname" class="form-input" placeholder="e.g. Ramesh Chandra" value="${p.fullName || ''}" required />
        </div>

        <div class="grid-2">
          <div class="form-group">
            <label class="form-label">${this.t("age")} *</label>
            <input type="number" id="input-age" class="form-input" placeholder="e.g. 45" value="${p.age || ''}" min="1" max="120" required />
          </div>

          <div class="form-group">
            <label class="form-label">${this.t("gender")} *</label>
            <select id="select-gender" class="form-input">
              <option value="male" ${p.gender === 'male' ? 'selected' : ''}>Male</option>
              <option value="female" ${p.gender === 'female' ? 'selected' : ''}>Female</option>
              <option value="other" ${p.gender === 'other' ? 'selected' : ''}>Other</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">${this.t("phone")} *</label>
          <input type="tel" id="input-phone" class="form-input" placeholder="10-digit mobile number" value="${p.phone || ''}" maxlength="10" required />
        </div>
      </div>
    `;
  }

  attachRegistrationEvents() {
    const btnTabNew = document.getElementById("btn-tab-new");
    const btnTabAbha = document.getElementById("btn-tab-abha");
    const btnBack = document.getElementById("btn-back-lang");
    const btnSubmit = document.getElementById("btn-submit-reg");
    const btnVerifyAbha = document.getElementById("btn-verify-abha");

    if (btnTabNew) {
      btnTabNew.addEventListener("click", () => {
        stateManager.set({ patient: { ...stateManager.get().patient, isNewPatient: true } });
        this.renderRegistration();
      });
    }

    if (btnTabAbha) {
      btnTabAbha.addEventListener("click", () => {
        stateManager.set({ patient: { ...stateManager.get().patient, isNewPatient: false } });
        this.renderRegistration();
      });
    }

    if (btnBack) {
      btnBack.addEventListener("click", () => {
        stateManager.set({ currentStep: "language" });
        this.renderCurrentStep();
      });
    }

    if (btnVerifyAbha) {
      btnVerifyAbha.addEventListener("click", async () => {
        const abhaInput = document.getElementById("input-abha");
        const val = abhaInput ? abhaInput.value.trim() : "";
        if (!val) {
          alert("Please enter an ABHA ID or PHR address.");
          return;
        }

        const res = await api.verifyABHA(val);
        const resultBox = document.getElementById("abha-result-box");
        if (resultBox) {
          resultBox.style.display = "block";
          if (res.success && res.data.verified) {
            const prof = res.data.profile;
            resultBox.innerHTML = `
              <div class="alert-banner alert-success">
                ✓ ${res.data.message}<br>
                <strong>Name:</strong> ${prof.full_name} | <strong>Gender:</strong> ${prof.gender} | <strong>State:</strong> ${prof.state || 'N/A'}
              </div>
            `;
            // Auto fill verified info into state
            stateManager.set({
              patient: {
                ...stateManager.get().patient,
                fullName: prof.full_name,
                gender: prof.gender,
                phone: prof.phone_number,
                abhaId: prof.abha_id
              }
            });
            const phoneAbhaInput = document.getElementById("input-phone-abha");
            if (phoneAbhaInput) phoneAbhaInput.value = prof.phone_number;
          } else {
            resultBox.innerHTML = `
              <div class="alert-banner alert-danger">
                ✕ ${res.data?.message || res.error}
              </div>
            `;
          }
        }
      });
    }

    if (btnSubmit) {
      btnSubmit.addEventListener("click", async () => {
        await this.handleRegistrationSubmit();
      });
    }
  }

  async handleRegistrationSubmit() {
    const isNew = stateManager.get().patient.isNewPatient;
    let payload = {};

    if (isNew) {
      const name = document.getElementById("input-fullname")?.value.trim();
      const age = parseInt(document.getElementById("input-age")?.value, 10);
      const gender = document.getElementById("select-gender")?.value;
      const phone = document.getElementById("input-phone")?.value.trim();

      if (!name || isNaN(age) || !phone) {
        this.showRegError("Please fill in all required fields (Name, Age, Phone).");
        return;
      }

      payload = {
        full_name: name,
        age: age,
        gender: gender,
        phone_number: phone,
        preferred_language: stateManager.get().language,
        is_new_patient: true
      };
    } else {
      const abhaId = document.getElementById("input-abha")?.value.trim();
      const phone = document.getElementById("input-phone-abha")?.value.trim() || stateManager.get().patient.phone;
      const name = stateManager.get().patient.fullName || "ABHA Patient";

      if (!abhaId || !phone) {
        this.showRegError("Please enter your ABHA number and a valid 10-digit mobile number.");
        return;
      }

      payload = {
        full_name: name,
        age: stateManager.get().patient.age || 35,
        gender: stateManager.get().patient.gender || "male",
        phone_number: phone,
        abha_id: abhaId,
        preferred_language: stateManager.get().language,
        is_new_patient: false
      };
    }

    const res = await api.registerPatient(payload);
    if (!res.success) {
      this.showRegError(`Registration Error: ${res.error}`);
      return;
    }

    stateManager.set({
      sessionId: res.data.session_id,
      patientId: res.data.patient_id,
      token: res.data.token,
      patient: { ...stateManager.get().patient, ...payload },
      currentStep: "consent"
    });

    this.renderCurrentStep();
  }

  showRegError(msg) {
    const el = document.getElementById("reg-error-banner");
    if (el) {
      el.textContent = msg;
      el.style.display = "block";
    }
  }

  // 4. Clinical Consent Screen
  renderConsent() {
    this.updateProgressTracker(3);
    this.appMount.innerHTML = `
      <div class="kiosk-card">
        <h2>${this.t("consentTitle")}</h2>
        <p class="subtitle">${this.t("consentSubtitle")}</p>

        <div style="background: #f8fafc; border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem;">
          <ul style="list-style-type: none; display: flex; flex-direction: column; gap: 1.1rem;">
            <li style="display: flex; gap: 0.9rem; align-items: start;">
              <span style="font-size: 1.4rem;">📋</span>
              <div>
                <strong>Clinical History Collection:</strong>
                <div style="color: var(--text-muted); font-size: 0.95rem;">${this.t("consentPoint1")}</div>
              </div>
            </li>
            <li style="display: flex; gap: 0.9rem; align-items: start;">
              <span style="font-size: 1.4rem;">🤖</span>
              <div>
                <strong>AI & Speech Tools:</strong>
                <div style="color: var(--text-muted); font-size: 0.95rem;">${this.t("consentPoint2")}</div>
              </div>
            </li>
            <li style="display: flex; gap: 0.9rem; align-items: start;">
              <span style="font-size: 1.4rem;">📄</span>
              <div>
                <strong>Document Scanning & OCR:</strong>
                <div style="color: var(--text-muted); font-size: 0.95rem;">${this.t("consentPoint3")}</div>
              </div>
            </li>
            <li style="display: flex; gap: 0.9rem; align-items: start;">
              <span style="font-size: 1.4rem;">👨‍⚕️</span>
              <div>
                <strong>Physician Access:</strong>
                <div style="color: var(--text-muted); font-size: 0.95rem;">${this.t("consentPoint4")}</div>
              </div>
            </li>
          </ul>
        </div>

        <div style="display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
          <button type="button" class="btn btn-secondary" id="btn-decline-consent" style="color: var(--danger);">
            ${this.t("consentDecline")}
          </button>
          <button type="button" class="btn btn-success btn-large" id="btn-accept-consent">
            ✓ ${this.t("consentAccept")}
          </button>
        </div>
      </div>
    `;

    document.getElementById("btn-accept-consent").addEventListener("click", async () => {
      const sid = stateManager.get().sessionId;
      const res = await api.submitConsent(sid, true);
      if (res.success) {
        stateManager.set({ consentGiven: true, currentStep: "history" });
        this.renderCurrentStep();
      } else {
        alert(`Error recording consent: ${res.error}`);
      }
    });

    document.getElementById("btn-decline-consent").addEventListener("click", async () => {
      const sid = stateManager.get().sessionId;
      await api.submitConsent(sid, false);
      alert("You have declined consent. The session has been terminated safely. Please approach the hospital assistance desk.");
      stateManager.reset();
      this.renderLanding();
    });
  }

  // 5. Clinical History Taking Screen
  async renderHistory() {
    this.updateProgressTracker(4);
    this.appMount.innerHTML = `
      <div class="kiosk-card">
        <div id="history-question-container">
          <div style="text-align: center; padding: 3rem;">
            <div style="font-size: 2rem;">⏳</div>
            <p>Loading your clinical interview...</p>
          </div>
        </div>
      </div>
    `;

    this.questionRenderer = new QuestionRenderer("history-question-container", {
      onSubmitAnswer: async (qId, ans, method) => {
        await this.handleHistoryAnswer(qId, ans, method);
      },
      onVoiceUpload: async (blob) => {
        await this.handleVoiceAnswer(blob);
      }
    });

    // Fetch initial question
    const { sessionId, language } = stateManager.get();
    const res = await api.getNextQuestion(sessionId, null, language);

    if (res.success && res.data.question) {
      this.questionRenderer.render(res.data.question);
    } else {
      // Move to documents if completed
      stateManager.set({ currentStep: "documents" });
      this.renderCurrentStep();
    }
  }

  async handleHistoryAnswer(questionId, answer, inputMethod) {
    const { sessionId } = stateManager.get();
    const res = await api.submitAnswer(sessionId, questionId, answer, inputMethod);

    if (!res.success) {
      alert(`Error submitting answer: ${res.error}`);
      return;
    }

    if (res.data.red_flag) {
      stateManager.set({
        redFlag: true,
        redFlagDetails: res.data
      });
      this.renderRedFlagTakeover();
      return;
    }

    if (res.data.completed || !res.data.next_question) {
      stateManager.set({ currentStep: "documents" });
      this.renderCurrentStep();
    } else {
      this.questionRenderer.render(res.data.next_question);
    }
  }

  async handleVoiceAnswer(audioBlob) {
    const { sessionId, language } = stateManager.get();
    const res = await api.uploadVoice(sessionId, audioBlob, language);

    if (!res.success) {
      alert(`Voice processing error: ${res.error}`);
      return;
    }

    if (res.data.red_flag) {
      stateManager.set({
        redFlag: true,
        redFlagDetails: res.data
      });
      this.renderRedFlagTakeover();
      return;
    }

    // Show transcript confirmation notice briefly
    alert(`Voice transcript recorded: "${res.data.transcript}"`);

    if (res.data.next_question) {
      this.questionRenderer.render(res.data.next_question);
    } else {
      stateManager.set({ currentStep: "documents" });
      this.renderCurrentStep();
    }
  }

  // 6. Medical Document Upload / Scan Screen
  renderDocuments() {
    this.updateProgressTracker(5);
    this.appMount.innerHTML = `
      <div class="kiosk-card">
        <h2>${this.t("docsTitle")}</h2>
        <p class="subtitle">${this.t("docsSubtitle")}</p>

        <div id="doc-uploader-mount"></div>
      </div>
    `;

    this.docUploader = new DocumentUploader("doc-uploader-mount", {
      sessionId: stateManager.get().sessionId,
      onCompleted: (docs) => {
        stateManager.set({
          documents: docs,
          currentStep: "completion"
        });
        this.renderCurrentStep();
      }
    });
  }

  // 7. Completion & QR Code Screen
  async renderCompletion() {
    this.updateProgressTracker(6);
    this.appMount.innerHTML = `
      <div class="kiosk-card" style="text-align: center;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎉</div>
        <h2>${this.t("completeTitle")}</h2>
        <p class="subtitle">${this.t("completeSubtitle")}</p>

        <div id="completion-details-mount" style="padding: 1rem 0;">
          <div style="font-size: 1.5rem;">⏳ Generating Secure Doctor QR Code...</div>
        </div>
      </div>
    `;

    const { sessionId } = stateManager.get();
    const res = await api.completeSession(sessionId);

    if (!res.success) {
      alert(`Error completing session: ${res.error}`);
      return;
    }

    const mount = document.getElementById("completion-details-mount");
    if (mount) {
      mount.innerHTML = `
        <div class="qr-container">
          <div class="qr-image-wrapper">
            <img src="${res.data.qr_data_uri}" alt="Doctor Access QR Code" class="qr-image" />
          </div>

          <div style="margin-bottom: 0.75rem;">
            <span style="font-size: 0.95rem; color: #64748b; font-weight: 600;">Patient Session Token:</span><br>
            <span class="patient-token-badge">${res.data.qr_token}</span>
          </div>

          <p style="font-weight: 700; color: var(--primary); font-size: 1.15rem; max-width: 540px; margin-bottom: 0.5rem;">
            ${this.t("qrInstructions")}
          </p>
          <p style="font-size: 0.9rem; color: #64748b; max-width: 500px;">
            ${this.t("qrOpaqueNotice")}
          </p>
        </div>

        <!-- Demonstration Action: View What the Doctor Sees -->
        <div style="margin-top: 1.5rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 14px; padding: 1.25rem;">
          <div style="font-weight: 700; color: var(--primary); margin-bottom: 0.5rem;">
            🩺 Member 5 Doctor Dashboard Integration Preview
          </div>
          <p style="font-size: 0.95rem; color: var(--text-muted); margin-bottom: 1rem;">
            Click below to test how Member 5's Doctor Dashboard fetches this patient case using endpoint <code>/api/patients/qr/${res.data.qr_token}</code>.
          </p>
          <button type="button" class="btn btn-secondary" id="btn-demo-doctor-view" style="font-size: 1rem;">
            Inspect Doctor View JSON →
          </button>
          <div id="doctor-view-output" style="display: none; text-align: left; margin-top: 1rem; max-height: 250px; overflow-y: auto; background: #0f172a; color: #38bdf8; padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.85rem;"></div>
        </div>

        <div style="margin-top: 2rem;">
          <button type="button" class="btn btn-primary btn-large" id="btn-start-new-session">
            🔄 ${this.t("startNew")}
          </button>
        </div>
      `;

      // Doctor preview demo
      document.getElementById("btn-demo-doctor-view").addEventListener("click", async () => {
        const docRes = await api.getDoctorPatientView(res.data.qr_token);
        const out = document.getElementById("doctor-view-output");
        if (out) {
          out.style.display = "block";
          out.textContent = JSON.stringify(docRes.data, null, 2);
        }
      });

      // Reset
      document.getElementById("btn-start-new-session").addEventListener("click", () => {
        stateManager.reset();
        this.renderLanding();
      });
    }
  }

  // Red Flag Emergency State
  renderRedFlagTakeover() {
    const details = stateManager.get().redFlagDetails || {};
    this.appMount.innerHTML = `
      <div class="red-flag-overlay">
        <div class="red-flag-card">
          <div class="emergency-beacon">🚨</div>
          <h2 style="font-size: 2rem; color: var(--danger); margin-bottom: 1rem;">
            ${this.t("redFlagTitle")}
          </h2>
          <p style="font-size: 1.25rem; font-weight: 600; color: var(--text-main); margin-bottom: 1.5rem; line-height: 1.6;">
            ${details.message || this.t("redFlagMessage")}
          </p>
          <div style="background: #fef2f2; border: 2px solid #fecaca; padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; font-size: 1rem; color: #991b1b;">
            <strong>Hospital Alert Status:</strong> Nursing staff notified • Code priority response dispatched.
          </div>
          <button type="button" class="btn btn-secondary" id="btn-staff-acknowledged" style="font-size: 1rem;">
            Staff Assistance Acknowledged (Restart Kiosk)
          </button>
        </div>
      </div>
    `;

    document.getElementById("btn-staff-acknowledged").addEventListener("click", () => {
      stateManager.reset();
      this.renderLanding();
    });
  }
}

// Boot application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.medikiosk = new MediKioskApp();
});

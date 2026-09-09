/**
 * MediKiosk Patient Session State Manager (Member 1)
 */

class StateManager {
  constructor() {
    this.state = {
      currentStep: "landing", // landing, language, registration, consent, history, anatomy, documents, completion
      sessionId: null,
      patientId: null,
      token: null,
      language: "en",
      patient: {
        fullName: "",
        age: null,
        gender: "male",
        phone: "",
        abhaId: "",
        isNewPatient: true
      },
      consentGiven: false,
      currentQuestion: null,
      answers: {},
      painData: null,
      documents: [],
      redFlag: false,
      redFlagDetails: null,
      isRecording: false,
      audioBlob: null
    };

    this.listeners = new Set();
    this.loadFromStorage();
  }

  loadFromStorage() {
    try {
      const saved = sessionStorage.getItem("medikiosk_state");
      if (saved) {
        const parsed = JSON.parse(saved);
        // Only restore valid session identifiers if not completed
        if (parsed.sessionId && parsed.currentStep !== "completion") {
          this.state = { ...this.state, ...parsed };
        }
      }
    } catch (e) {
      console.warn("Could not load stored session:", e);
    }
  }

  saveToStorage() {
    try {
      sessionStorage.setItem("medikiosk_state", JSON.stringify(this.state));
    } catch (e) {
      console.warn("Could not save session state:", e);
    }
  }

  get() {
    return this.state;
  }

  set(partial) {
    this.state = { ...this.state, ...partial };
    this.saveToStorage();
    this.notify();
  }

  reset() {
    this.state = {
      currentStep: "landing",
      sessionId: null,
      patientId: null,
      token: null,
      language: "en",
      patient: {
        fullName: "",
        age: null,
        gender: "male",
        phone: "",
        abhaId: "",
        isNewPatient: true
      },
      consentGiven: false,
      currentQuestion: null,
      answers: {},
      painData: null,
      documents: [],
      redFlag: false,
      redFlagDetails: null,
      isRecording: false,
      audioBlob: null
    };
    sessionStorage.removeItem("medikiosk_state");
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch (err) {
        console.error("Error in state subscriber:", err);
      }
    }
  }
}

export const stateManager = new StateManager();

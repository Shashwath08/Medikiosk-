/**
 * MediKiosk Dynamic Question Renderer (Member 1)
 *
 * Renders diverse question types dynamically driven by Member 2 AI:
 * - yes_no, single_choice, multiple_choice, slider, text, number, date, pain_location
 * Integrates dual Voice + Touch input on all clinical questions.
 */

import { audioController } from "./audio.js";
import { AnatomyComponent } from "./anatomy.js";

export class QuestionRenderer {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.onSubmitAnswer = options.onSubmitAnswer || null;
    this.onVoiceUpload = options.onVoiceUpload || null;
    this.currentQuestion = null;
    this.selectedMultiChoice = new Set();
    this.sliderValue = 5;
    this.isRecording = false;
  }

  render(question) {
    if (!this.container) return;
    this.currentQuestion = question;
    this.selectedMultiChoice.clear();

    const q = question;
    let inputHtml = "";

    switch (q.question_type) {
      case "yes_no":
        inputHtml = this.renderYesNo(q);
        break;
      case "single_choice":
        inputHtml = this.renderSingleChoice(q);
        break;
      case "multiple_choice":
        inputHtml = this.renderMultipleChoice(q);
        break;
      case "slider":
        inputHtml = this.renderSlider(q);
        break;
      case "text":
        inputHtml = this.renderTextInput(q);
        break;
      case "number":
        inputHtml = this.renderNumberInput(q);
        break;
      case "pain_location":
      case "body_map":
        inputHtml = `<div id="embedded-anatomy-mount"></div>`;
        break;
      default:
        inputHtml = this.renderSingleChoice(q);
    }

    this.container.innerHTML = `
      <div class="dynamic-question-box" style="animation: slide-up 0.25s ease;">
        <!-- Question Header -->
        <div style="margin-bottom: 1.5rem;">
          <h2 style="font-size: 1.85rem; font-weight: 800; color: var(--text-main); margin-bottom: 0.5rem;">
            ${q.question}
          </h2>
          ${q.helper_text ? `<p style="color: var(--text-muted); font-size: 1.1rem;">${q.helper_text}</p>` : ''}
        </div>

        <!-- Voice Controller Card (If voice allowed) -->
        ${q.allow_voice ? this.renderVoiceBanner() : ''}

        <!-- Interactive Touch Input Zone -->
        <div class="touch-input-zone" style="margin-top: 1.25rem;">
          ${inputHtml}
        </div>
      </div>
    `;

    this.attachEvents();

    // If pain location, mount the anatomy component
    if (q.question_type === "pain_location" || q.question_type === "body_map") {
      new AnatomyComponent("embedded-anatomy-mount", {
        onConfirm: (painData) => {
          if (this.onSubmitAnswer) {
            this.onSubmitAnswer(q.question_id, painData, "touch");
          }
        }
      });
    }
  }

  renderVoiceBanner() {
    return `
      <div class="voice-banner" id="voice-banner">
        <div class="voice-status">
          <button type="button" class="mic-btn" id="btn-mic-toggle" title="Click to speak">
            <span id="mic-icon">🎙️</span>
          </button>
          <div>
            <div id="voice-status-text" style="font-size: 1.15rem; font-weight: 700;">
              Tap Mic to Speak in Your Language
            </div>
            <div style="font-size: 0.9rem; color: #15803d; font-weight: 500;">
              AI Speech Recognition (Member 2 ready)
            </div>
          </div>
        </div>
        <div id="wave-container" style="display: none;" class="waveform-indicator">
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
        </div>
      </div>
    `;
  }

  renderYesNo(q) {
    return `
      <div class="grid-2">
        <button type="button" class="btn btn-success btn-large btn-choice" data-value="yes" style="font-size: 1.6rem;">
          ✓ Yes
        </button>
        <button type="button" class="btn btn-secondary btn-large btn-choice" data-value="no" style="font-size: 1.6rem;">
          ✕ No
        </button>
      </div>
    `;
  }

  renderSingleChoice(q) {
    const opts = q.options || [];
    return `
      <div class="grid-2">
        ${opts.map(opt => `
          <div class="touch-card btn-choice" data-value="${opt.id}">
            <div class="card-icon">${this.getIcon(opt.icon || opt.id)}</div>
            <div class="card-title">${opt.label}</div>
            ${opt.subtext ? `<div class="card-subtext">${opt.subtext}</div>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  }

  renderMultipleChoice(q) {
    const opts = q.options || [];
    return `
      <div>
        <div class="grid-2" style="margin-bottom: 1.5rem;">
          ${opts.map(opt => `
            <div class="touch-card multi-card" data-value="${opt.id}">
              <div class="card-icon">${this.getIcon(opt.icon || opt.id)}</div>
              <div class="card-title">${opt.label}</div>
            </div>
          `).join('')}
        </div>
        <button type="button" class="btn btn-primary btn-large btn-full" id="btn-submit-multi">
          Confirm Selected Options →
        </button>
      </div>
    `;
  }

  renderSlider(q) {
    const min = q.min_val ?? 1;
    const max = q.max_val ?? 10;
    this.sliderValue = Math.round((min + max) / 2);

    return `
      <div style="background: #ffffff; padding: 2rem; border-radius: 18px; border: 2px solid var(--border-color);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
          <span style="font-size: 1.25rem; font-weight: 700;">Select Level:</span>
          <span class="pain-score-badge" id="dynamic-slider-badge" style="font-size: 1.8rem; padding: 0.4rem 1.2rem;">
            ${this.sliderValue} ${q.unit || ''}
          </span>
        </div>
        <input 
          type="range" 
          id="dynamic-range-input" 
          class="pain-scale-input" 
          min="${min}" 
          max="${max}" 
          value="${this.sliderValue}"
          style="margin-bottom: 1.5rem;"
        />
        <div style="display: flex; justify-content: space-between; font-size: 0.95rem; color: #64748b; font-weight: 600; margin-bottom: 2rem;">
          <span>${min} (Mild / Low)</span>
          <span>${max} (Severe / Extreme)</span>
        </div>
        <button type="button" class="btn btn-primary btn-large btn-full" id="btn-submit-slider">
          Confirm & Next →
        </button>
      </div>
    `;
  }

  renderTextInput(q) {
    const opts = q.options || [];
    return `
      <div>
        <div class="form-group">
          <input 
            type="text" 
            id="dynamic-text-input" 
            class="form-input" 
            placeholder="Type your answer here or select a quick option..."
            style="font-size: 1.4rem; padding: 1.1rem;"
          />
        </div>
        ${opts.length > 0 ? `
          <div style="display: flex; flex-wrap: wrap; gap: 0.6rem; margin: 1rem 0 1.5rem 0;">
            ${opts.map(opt => `
              <button type="button" class="btn btn-secondary chip-choice" data-value="${opt.label}" style="font-size: 1rem; padding: 0.5rem 1rem; min-height: 44px;">
                + ${opt.label}
              </button>
            `).join('')}
          </div>
        ` : ''}
        <button type="button" class="btn btn-primary btn-large btn-full" id="btn-submit-text">
          Submit Answer →
        </button>
      </div>
    `;
  }

  renderNumberInput(q) {
    return `
      <div>
        <div class="form-group" style="max-width: 320px; margin: 0 auto 1.5rem auto;">
          <input 
            type="number" 
            id="dynamic-number-input" 
            class="form-input" 
            value="${q.min_val || 1}" 
            min="${q.min_val || 0}" 
            max="${q.max_val || 100}"
            style="font-size: 2rem; text-align: center;"
          />
        </div>
        <button type="button" class="btn btn-primary btn-large btn-full" id="btn-submit-number">
          Confirm Number →
        </button>
      </div>
    `;
  }

  attachEvents() {
    // Single choice / Yes-No clicks
    this.container.querySelectorAll(".btn-choice").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const value = e.currentTarget.dataset.value;
        if (this.onSubmitAnswer && this.currentQuestion) {
          this.onSubmitAnswer(this.currentQuestion.question_id, value, "touch");
        }
      });
    });

    // Multiple choice toggles
    this.container.querySelectorAll(".multi-card").forEach(card => {
      card.addEventListener("click", (e) => {
        const val = e.currentTarget.dataset.value;
        if (this.selectedMultiChoice.has(val)) {
          this.selectedMultiChoice.delete(val);
          e.currentTarget.classList.remove("selected");
        } else {
          this.selectedMultiChoice.add(val);
          e.currentTarget.classList.add("selected");
        }
      });
    });

    // Multiple choice submit
    const submitMulti = this.container.querySelector("#btn-submit-multi");
    if (submitMulti) {
      submitMulti.addEventListener("click", () => {
        const answers = Array.from(this.selectedMultiChoice);
        if (this.onSubmitAnswer && this.currentQuestion) {
          this.onSubmitAnswer(this.currentQuestion.question_id, answers, "touch");
        }
      });
    }

    // Slider input & submit
    const rangeInput = this.container.querySelector("#dynamic-range-input");
    if (rangeInput) {
      rangeInput.addEventListener("input", (e) => {
        this.sliderValue = parseInt(e.target.value, 10);
        const badge = this.container.querySelector("#dynamic-slider-badge");
        if (badge) badge.textContent = `${this.sliderValue} ${this.currentQuestion.unit || ''}`;
      });
    }

    const submitSlider = this.container.querySelector("#btn-submit-slider");
    if (submitSlider) {
      submitSlider.addEventListener("click", () => {
        if (this.onSubmitAnswer && this.currentQuestion) {
          this.onSubmitAnswer(this.currentQuestion.question_id, this.sliderValue, "touch");
        }
      });
    }

    // Text chips & text submit
    this.container.querySelectorAll(".chip-choice").forEach(chip => {
      chip.addEventListener("click", (e) => {
        const input = this.container.querySelector("#dynamic-text-input");
        if (input) {
          input.value = e.currentTarget.dataset.value;
        }
      });
    });

    const submitText = this.container.querySelector("#btn-submit-text");
    if (submitText) {
      submitText.addEventListener("click", () => {
        const input = this.container.querySelector("#dynamic-text-input");
        const val = input ? input.value.trim() : "";
        if (this.onSubmitAnswer && this.currentQuestion) {
          this.onSubmitAnswer(this.currentQuestion.question_id, val || "None", "touch");
        }
      });
    }

    // Voice microphone toggle
    const micBtn = this.container.querySelector("#btn-mic-toggle");
    if (micBtn) {
      micBtn.addEventListener("click", async () => {
        await this.handleMicToggle();
      });
    }
  }

  async handleMicToggle() {
    const micBtn = this.container.querySelector("#btn-mic-toggle");
    const statusText = this.container.querySelector("#voice-status-text");
    const wave = this.container.querySelector("#wave-container");

    if (!this.isRecording) {
      // Start recording
      const res = await audioController.startRecording();
      if (!res.success) {
        alert(res.error || "Could not access microphone.");
        return;
      }

      this.isRecording = true;
      micBtn.classList.add("recording");
      if (statusText) statusText.textContent = "Listening... Speak now";
      if (wave) wave.style.display = "flex";
    } else {
      // Stop recording
      this.isRecording = false;
      micBtn.classList.remove("recording");
      if (statusText) statusText.textContent = "Processing speech...";
      if (wave) wave.style.display = "none";

      const audioBlob = await audioController.stopRecording();
      if (this.onVoiceUpload && audioBlob) {
        this.onVoiceUpload(audioBlob);
      }
    }
  }

  getIcon(name) {
    const icons = {
      fever: "🌡️",
      cough: "🫁",
      body_pain: "⚡",
      chest_discomfort: "🫀",
      stomach_pain: "🩺",
      headache: "🤕",
      other: "➕",
      thermometer: "🌡️",
      heart: "❤️",
      activity: "📈",
      user: "👤",
      circle: "⭕",
      "alert-circle": "⚠️",
      plus: "➕"
    };
    return icons[name] || "📋";
  }
}

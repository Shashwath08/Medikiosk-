/**
 * MediKiosk Interactive Human Anatomy Pain-Location Component (Member 1)
 *
 * Provides Front & Back interactive SVG body maps with identifiable region IDs,
 * multi-region selection, pain intensity rating (0-10), pain characteristics,
 * and structured JSON export for Member 2/4.
 */

export class AnatomyComponent {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.currentView = "front"; // 'front' or 'back'
    this.selectedRegions = new Map(); // id -> { id, region, side, label }
    this.painIntensity = 5;
    this.painTypes = new Set();
    this.onSelectionChange = options.onSelectionChange || null;
    this.onConfirm = options.onConfirm || null;
    
    this.init();
  }

  init() {
    if (!this.container) return;
    this.render();
    this.attachEvents();
  }

  // Region metadata dictionary
  static REGION_METADATA = {
    // Front View
    "body-head": { region: "head", side: "center", label: "Head / Cranium" },
    "body-face": { region: "face", side: "center", label: "Face / Sinuses" },
    "body-neck": { region: "neck", side: "center", label: "Neck (Front)" },
    "body-chest": { region: "chest", side: "center", label: "Chest / Sternum" },
    "body-abdomen": { region: "abdomen", side: "center", label: "Abdomen / Stomach" },
    "body-pelvis": { region: "pelvis", side: "center", label: "Pelvis / Groin" },
    
    "body-shoulder-left": { region: "shoulder", side: "left", label: "Left Shoulder" },
    "body-shoulder-right": { region: "shoulder", side: "right", label: "Right Shoulder" },
    "body-arm-left": { region: "arm", side: "left", label: "Left Upper Arm" },
    "body-arm-right": { region: "arm", side: "right", label: "Right Upper Arm" },
    "body-elbow-left": { region: "elbow", side: "left", label: "Left Elbow" },
    "body-elbow-right": { region: "elbow", side: "right", label: "Right Elbow" },
    "body-forearm-left": { region: "forearm", side: "left", label: "Left Forearm" },
    "body-forearm-right": { region: "forearm", side: "right", label: "Right Forearm" },
    "body-wrist-left": { region: "wrist", side: "left", label: "Left Wrist" },
    "body-wrist-right": { region: "wrist", side: "right", label: "Right Wrist" },
    "body-hand-left": { region: "hand", side: "left", label: "Left Hand" },
    "body-hand-right": { region: "hand", side: "right", label: "Right Hand" },

    "body-hip-left": { region: "hip", side: "left", label: "Left Hip" },
    "body-hip-right": { region: "hip", side: "right", label: "Right Hip" },
    "body-thigh-left": { region: "thigh", side: "left", label: "Left Thigh" },
    "body-thigh-right": { region: "thigh", side: "right", label: "Right Thigh" },
    "body-knee-left": { region: "knee", side: "left", label: "Left Knee" },
    "body-knee-right": { region: "knee", side: "right", label: "Right Knee" },
    "body-leg-left": { region: "lower_leg", side: "left", label: "Left Shin / Calf" },
    "body-leg-right": { region: "lower_leg", side: "right", label: "Right Shin / Calf" },
    "body-ankle-left": { region: "ankle", side: "left", label: "Left Ankle" },
    "body-ankle-right": { region: "ankle", side: "right", label: "Right Ankle" },
    "body-foot-left": { region: "foot", side: "left", label: "Left Foot" },
    "body-foot-right": { region: "foot", side: "right", label: "Right Foot" },

    // Back View
    "body-back-head": { region: "head", side: "center", label: "Back of Head" },
    "body-back-neck": { region: "neck", side: "center", label: "Cervical Spine / Neck" },
    "body-back-upper": { region: "upper_back", side: "center", label: "Upper Back / Thoracic" },
    "body-back-lower": { region: "lower_back", side: "center", label: "Lower Back / Lumbar" },
    "body-back-glutes": { region: "pelvis", side: "center", label: "Gluteal / Lower Spine" },

    "body-shoulder-left-back": { region: "shoulder", side: "left", label: "Left Shoulder (Back)" },
    "body-shoulder-right-back": { region: "shoulder", side: "right", label: "Right Shoulder (Back)" },
    "body-arm-left-back": { region: "arm", side: "left", label: "Left Arm (Back)" },
    "body-arm-right-back": { region: "arm", side: "right", label: "Right Arm (Back)" },
    "body-elbow-left-back": { region: "elbow", side: "left", label: "Left Elbow (Back)" },
    "body-elbow-right-back": { region: "elbow", side: "right", label: "Right Elbow (Back)" },
    "body-thigh-left-back": { region: "thigh", side: "left", label: "Left Hamstring" },
    "body-thigh-right-back": { region: "thigh", side: "right", label: "Right Hamstring" },
    "body-knee-left-back": { region: "knee", side: "left", label: "Left Knee (Back)" },
    "body-knee-right-back": { region: "knee", side: "right", label: "Right Knee (Back)" },
    "body-calf-left-back": { region: "lower_leg", side: "left", label: "Left Calf" },
    "body-calf-right-back": { region: "lower_leg", side: "right", label: "Right Calf" },
    "body-heel-left-back": { region: "foot", side: "left", label: "Left Heel" },
    "body-heel-right-back": { region: "foot", side: "right", label: "Right Heel" },
  };

  render() {
    this.container.innerHTML = `
      <div class="anatomy-container">
        <div class="anatomy-header">
          <div>
            <h3 style="font-size: 1.3rem; font-weight: 800;">Interactive Body Pain Map</h3>
            <p style="color: var(--text-muted); font-size: 0.95rem;">
              Tap directly on any region where you feel pain. You can choose multiple areas.
            </p>
          </div>
          <div class="view-toggle-group">
            <button type="button" class="view-toggle-btn ${this.currentView === 'front' ? 'active' : ''}" data-view="front">
              Front View
            </button>
            <button type="button" class="view-toggle-btn ${this.currentView === 'back' ? 'active' : ''}" data-view="back">
              Back View
            </button>
          </div>
        </div>

        <div class="anatomy-main-layout">
          <!-- SVG Container -->
          <div class="anatomy-viewer">
            <div id="svg-stage" style="width: 100%; display: flex; justify-content: center;">
              ${this.currentView === 'front' ? this.getFrontSvg() : this.getBackSvg()}
            </div>
            <div class="anatomy-hint">
              <strong>${this.currentView.toUpperCase()} VIEW</strong> • Tap body parts to select or deselect
            </div>
          </div>

          <!-- Configuration & Pain Rating Panel -->
          <div class="pain-details-panel">
            <!-- Selected Regions List -->
            <div class="selected-regions-box">
              <div class="selected-regions-header">
                <span>Selected Locations (${this.selectedRegions.size})</span>
                ${this.selectedRegions.size > 0 ? '<button type="button" class="clear-btn" id="btn-clear-regions">Clear All</button>' : ''}
              </div>
              <div class="regions-chip-list" id="regions-chip-list">
                ${this.renderChips()}
              </div>
            </div>

            <!-- Pain Severity Slider -->
            <div class="pain-slider-section">
              <div class="slider-labels-row">
                <label class="form-label" style="margin: 0;">Pain Severity (0 to 10)</label>
                <span class="pain-score-badge" id="pain-score-badge">${this.painIntensity}/10</span>
              </div>
              <input 
                type="range" 
                id="pain-severity-slider" 
                class="pain-scale-input" 
                min="0" 
                max="10" 
                step="1" 
                value="${this.painIntensity}"
              />
              <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #64748b; font-weight: 600;">
                <span>0 (No Pain)</span>
                <span>5 (Moderate)</span>
                <span>10 (Severe / Worst)</span>
              </div>
            </div>

            <!-- Pain Character / Types -->
            <div class="pain-types-section">
              <label class="form-label">Type of Pain (Optional)</label>
              <div class="pain-types-grid">
                ${this.renderPainTypePills()}
              </div>
            </div>

            <!-- Confirm / Continue Button -->
            <button type="button" class="btn btn-primary btn-large btn-full" id="btn-confirm-pain" style="margin-top: 0.5rem;">
              Confirm Pain Locations & Continue →
            </button>
          </div>
        </div>
      </div>
    `;

    this.updateSvgSelections();
    this.updateScoreBadgeColor();
  }

  renderChips() {
    if (this.selectedRegions.size === 0) {
      return `<div class="empty-regions-text">No region selected yet. Tap anywhere on the body figure.</div>`;
    }
    return Array.from(this.selectedRegions.values())
      .map(item => `
        <span class="region-chip" data-id="${item.id}">
          ${item.label}
          <span class="remove-x" data-remove="${item.id}">×</span>
        </span>
      `).join('');
  }

  renderPainTypePills() {
    const types = [
      { id: "sharp", label: "Sharp / Stabbing" },
      { id: "dull", label: "Dull / Aching" },
      { id: "throbbing", label: "Throbbing" },
      { id: "burning", label: "Burning" },
      { id: "cramping", label: "Cramping" },
      { id: "shooting", label: "Shooting / Radiating" },
    ];
    return types.map(t => `
      <div class="pain-type-pill ${this.painTypes.has(t.id) ? 'active' : ''}" data-type="${t.id}">
        ${t.label}
      </div>
    `).join('');
  }

  attachEvents() {
    // View toggle buttons
    this.container.querySelectorAll(".view-toggle-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const view = e.currentTarget.dataset.view;
        if (view !== this.currentView) {
          this.currentView = view;
          this.render();
          this.attachEvents();
        }
      });
    });

    // SVG region click/touch handler
    const svgStage = this.container.querySelector("#svg-stage");
    if (svgStage) {
      svgStage.querySelectorAll(".body-region").forEach(el => {
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          this.toggleRegion(e.currentTarget.id);
        });
      });
    }

    // Remove chip handler
    const chipList = this.container.querySelector("#regions-chip-list");
    if (chipList) {
      chipList.addEventListener("click", (e) => {
        const removeId = e.target.dataset.remove;
        if (removeId) {
          this.removeRegion(removeId);
        }
      });
    }

    // Clear all button
    const clearBtn = this.container.querySelector("#btn-clear-regions");
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        this.selectedRegions.clear();
        this.render();
        this.attachEvents();
        if (this.onSelectionChange) this.onSelectionChange(this.getData());
      });
    }

    // Pain slider
    const slider = this.container.querySelector("#pain-severity-slider");
    if (slider) {
      slider.addEventListener("input", (e) => {
        this.painIntensity = parseInt(e.target.value, 10);
        const badge = this.container.querySelector("#pain-score-badge");
        if (badge) {
          badge.textContent = `${this.painIntensity}/10`;
          this.updateScoreBadgeColor();
        }
      });
    }

    // Pain type pills
    this.container.querySelectorAll(".pain-type-pill").forEach(pill => {
      pill.addEventListener("click", (e) => {
        const type = e.currentTarget.dataset.type;
        if (this.painTypes.has(type)) {
          this.painTypes.delete(type);
        } else {
          this.painTypes.add(type);
        }
        e.currentTarget.classList.toggle("active");
      });
    });

    // Confirm button
    const confirmBtn = this.container.querySelector("#btn-confirm-pain");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", () => {
        if (this.onConfirm) {
          this.onConfirm(this.getData());
        }
      });
    }
  }

  toggleRegion(id) {
    if (this.selectedRegions.has(id)) {
      this.selectedRegions.delete(id);
    } else {
      const meta = AnatomyComponent.REGION_METADATA[id] || {
        region: id.replace("body-", "").replace("-back", ""),
        side: "center",
        label: id.replace("body-", "").replace(/-/g, " ")
      };
      this.selectedRegions.set(id, { id, ...meta });
    }
    this.render();
    this.attachEvents();
    if (this.onSelectionChange) {
      this.onSelectionChange(this.getData());
    }
  }

  removeRegion(id) {
    this.selectedRegions.delete(id);
    this.render();
    this.attachEvents();
    if (this.onSelectionChange) {
      this.onSelectionChange(this.getData());
    }
  }

  updateSvgSelections() {
    this.container.querySelectorAll(".body-region").forEach(el => {
      if (this.selectedRegions.has(el.id)) {
        el.classList.add("selected");
      } else {
        el.classList.remove("selected");
      }
    });
  }

  updateScoreBadgeColor() {
    const badge = this.container.querySelector("#pain-score-badge");
    if (!badge) return;
    if (this.painIntensity <= 3) {
      badge.style.backgroundColor = "#16a34a"; // Green
    } else if (this.painIntensity <= 6) {
      badge.style.backgroundColor = "#d97706"; // Amber
    } else {
      badge.style.backgroundColor = "#dc2626"; // Red
    }
  }

  getData() {
    const locations = Array.from(this.selectedRegions.values()).map(r => ({
      region: r.region,
      side: r.side,
      pain: true
    }));

    return {
      view: this.currentView,
      locations: locations,
      pain_intensity: this.painIntensity,
      pain_types: Array.from(this.painTypes)
    };
  }

  /* Anatomical Front View SVG */
  getFrontSvg() {
    return `
      <svg class="body-svg" viewBox="0 0 280 500" xmlns="http://www.w3.org/2000/svg">
        <!-- Head -->
        <circle id="body-head" class="body-region" cx="140" cy="40" r="28" />
        <!-- Face -->
        <ellipse id="body-face" class="body-region" cx="140" cy="44" rx="18" ry="16" />
        <!-- Neck -->
        <rect id="body-neck" class="body-region" x="127" y="70" width="26" height="20" rx="4" />
        
        <!-- Left Shoulder (patient perspective: viewer's right) -->
        <path id="body-shoulder-left" class="body-region" d="M 154 90 L 195 98 L 190 120 L 154 110 Z" />
        <!-- Right Shoulder (patient perspective: viewer's left) -->
        <path id="body-shoulder-right" class="body-region" d="M 126 90 L 85 98 L 90 120 L 126 110 Z" />

        <!-- Chest -->
        <path id="body-chest" class="body-region" d="M 108 92 L 172 92 L 168 145 L 112 145 Z" />
        <!-- Abdomen -->
        <path id="body-abdomen" class="body-region" d="M 112 147 L 168 147 L 164 195 L 116 195 Z" />
        <!-- Pelvis / Groin -->
        <path id="body-pelvis" class="body-region" d="M 116 197 L 164 197 L 152 230 L 128 230 Z" />

        <!-- Left Arm (Upper) -->
        <rect id="body-arm-left" class="body-region" x="188" y="122" width="22" height="48" rx="8" />
        <!-- Right Arm (Upper) -->
        <rect id="body-arm-right" class="body-region" x="70" y="122" width="22" height="48" rx="8" />

        <!-- Left Elbow -->
        <circle id="body-elbow-left" class="body-region" cx="199" cy="176" r="12" />
        <!-- Right Elbow -->
        <circle id="body-elbow-right" class="body-region" cx="81" cy="176" r="12" />

        <!-- Left Forearm -->
        <rect id="body-forearm-left" class="body-region" x="190" y="192" width="18" height="44" rx="6" />
        <!-- Right Forearm -->
        <rect id="body-forearm-right" class="body-region" x="72" y="192" width="18" height="44" rx="6" />

        <!-- Left Wrist -->
        <rect id="body-wrist-left" class="body-region" x="191" y="238" width="16" height="12" rx="3" />
        <!-- Right Wrist -->
        <rect id="body-wrist-right" class="body-region" x="73" y="238" width="16" height="12" rx="3" />

        <!-- Left Hand -->
        <path id="body-hand-left" class="body-region" d="M 189 252 L 209 252 L 206 280 L 189 276 Z" />
        <!-- Right Hand -->
        <path id="body-hand-right" class="body-region" d="M 71 252 L 91 252 L 91 276 L 74 280 Z" />

        <!-- Left Hip -->
        <path id="body-hip-left" class="body-region" d="M 152 205 L 175 228 L 160 252 L 146 230 Z" />
        <!-- Right Hip -->
        <path id="body-hip-right" class="body-region" d="M 128 205 L 105 228 L 120 252 L 134 230 Z" />

        <!-- Left Thigh -->
        <rect id="body-thigh-left" class="body-region" x="146" y="254" width="28" height="72" rx="10" />
        <!-- Right Thigh -->
        <rect id="body-thigh-right" class="body-region" x="106" y="254" width="28" height="72" rx="10" />

        <!-- Left Knee -->
        <circle id="body-knee-left" class="body-region" cx="160" cy="336" r="14" />
        <!-- Right Knee -->
        <circle id="body-knee-right" class="body-region" cx="120" cy="336" r="14" />

        <!-- Left Shin / Leg -->
        <rect id="body-leg-left" class="body-region" x="150" y="354" width="20" height="74" rx="7" />
        <!-- Right Shin / Leg -->
        <rect id="body-leg-right" class="body-region" x="110" y="354" width="20" height="74" rx="7" />

        <!-- Left Ankle -->
        <circle id="body-ankle-left" class="body-region" cx="160" cy="436" r="10" />
        <!-- Right Ankle -->
        <circle id="body-ankle-right" class="body-region" cx="120" cy="436" r="10" />

        <!-- Left Foot -->
        <path id="body-foot-left" class="body-region" d="M 152 448 L 174 448 L 180 478 L 152 476 Z" />
        <!-- Right Foot -->
        <path id="body-foot-right" class="body-region" d="M 106 448 L 128 448 L 128 476 L 100 478 Z" />
      </svg>
    `;
  }

  /* Anatomical Back View SVG */
  getBackSvg() {
    return `
      <svg class="body-svg" viewBox="0 0 280 500" xmlns="http://www.w3.org/2000/svg">
        <!-- Back of Head -->
        <circle id="body-back-head" class="body-region" cx="140" cy="40" r="28" />
        <!-- Back of Neck -->
        <rect id="body-back-neck" class="body-region" x="127" y="70" width="26" height="20" rx="4" />

        <!-- Left Shoulder Back (viewer left) -->
        <path id="body-shoulder-left-back" class="body-region" d="M 126 90 L 85 98 L 90 120 L 126 110 Z" />
        <!-- Right Shoulder Back (viewer right) -->
        <path id="body-shoulder-right-back" class="body-region" d="M 154 90 L 195 98 L 190 120 L 154 110 Z" />

        <!-- Upper Back -->
        <path id="body-back-upper" class="body-region" d="M 108 92 L 172 92 L 168 150 L 112 150 Z" />
        <!-- Lower Back (Lumbar) -->
        <path id="body-back-lower" class="body-region" d="M 112 152 L 168 152 L 164 195 L 116 195 Z" />
        <!-- Glutes -->
        <path id="body-back-glutes" class="body-region" d="M 116 197 L 164 197 L 156 240 L 124 240 Z" />

        <!-- Left Arm Back (Upper) -->
        <rect id="body-arm-left-back" class="body-region" x="70" y="122" width="22" height="48" rx="8" />
        <!-- Right Arm Back (Upper) -->
        <rect id="body-arm-right-back" class="body-region" x="188" y="122" width="22" height="48" rx="8" />

        <!-- Left Elbow Back -->
        <circle id="body-elbow-left-back" class="body-region" cx="81" cy="176" r="12" />
        <!-- Right Elbow Back -->
        <circle id="body-elbow-right-back" class="body-region" cx="199" cy="176" r="12" />

        <!-- Left Forearm Back -->
        <rect id="body-forearm-left-back" class="body-region" x="72" y="192" width="18" height="44" rx="6" />
        <!-- Right Forearm Back -->
        <rect id="body-forearm-right-back" class="body-region" x="190" y="192" width="18" height="44" rx="6" />

        <!-- Left Wrist Back -->
        <rect id="body-wrist-left-back" class="body-region" x="73" y="238" width="16" height="12" rx="3" />
        <!-- Right Wrist Back -->
        <rect id="body-wrist-right-back" class="body-region" x="191" y="238" width="16" height="12" rx="3" />

        <!-- Left Hand Back -->
        <path id="body-hand-left-back" class="body-region" d="M 71 252 L 91 252 L 91 276 L 74 280 Z" />
        <!-- Right Hand Back -->
        <path id="body-hand-right-back" class="body-region" d="M 189 252 L 209 252 L 206 280 L 189 276 Z" />

        <!-- Left Hamstring -->
        <rect id="body-thigh-left-back" class="body-region" x="106" y="254" width="28" height="72" rx="10" />
        <!-- Right Hamstring -->
        <rect id="body-thigh-right-back" class="body-region" x="146" y="254" width="28" height="72" rx="10" />

        <!-- Left Knee Back -->
        <circle id="body-knee-left-back" class="body-region" cx="120" cy="336" r="14" />
        <!-- Right Knee Back -->
        <circle id="body-knee-right-back" class="body-region" cx="160" cy="336" r="14" />

        <!-- Left Calf -->
        <rect id="body-calf-left-back" class="body-region" x="110" y="354" width="20" height="74" rx="7" />
        <!-- Right Calf -->
        <rect id="body-calf-right-back" class="body-region" x="150" y="354" width="20" height="74" rx="7" />

        <!-- Left Heel -->
        <path id="body-heel-left-back" class="body-region" d="M 108 436 L 128 436 L 126 472 L 110 472 Z" />
        <!-- Right Heel -->
        <path id="body-heel-right-back" class="body-region" d="M 152 436 L 172 436 L 170 472 L 154 472 Z" />
      </svg>
    `;
  }
}

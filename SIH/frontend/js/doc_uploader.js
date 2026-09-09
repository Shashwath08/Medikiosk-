/**
 * MediKiosk Document Upload & Scan UI (Member 1)
 *
 * Supports file browsing, camera capture, progress tracking,
 * and periodic status polling from Member 3's OCR service.
 */

import { api } from "./api.js";

export class DocumentUploader {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.sessionId = options.sessionId;
    this.onCompleted = options.onCompleted || null;
    this.uploadedDocs = []; // { document_id, filename, doc_type, status, progress, preview }
    this.selectedFile = null;
    this.selectedDocType = "prescription";
    this.pollingTimers = new Map();

    this.init();
  }

  setSessionId(sessionId) {
    this.sessionId = sessionId;
  }

  init() {
    if (!this.container) return;
    this.render();
    this.attachEvents();
  }

  render() {
    this.container.innerHTML = `
      <div class="doc-upload-container">
        <!-- Upload Options Card -->
        <div style="background: #ffffff; border: 2px dashed #94a3b8; border-radius: 18px; padding: 2rem; text-align: center; margin-bottom: 2rem;">
          <div style="font-size: 3rem; margin-bottom: 0.5rem;">📄</div>
          <h3 style="font-size: 1.4rem; font-weight: 800; margin-bottom: 0.5rem;">Upload or Scan Medical Document</h3>
          <p style="color: var(--text-muted); margin-bottom: 1.5rem; font-size: 1rem;">
            Attach past prescriptions, lab tests, or discharge summaries (PDF, JPEG, PNG). Max 10MB.
          </p>

          <!-- Document Type Selector -->
          <div style="max-width: 440px; margin: 0 auto 1.5rem auto; text-align: left;">
            <label class="form-label">Document Category:</label>
            <select id="doc-type-select" class="form-input" style="width: 100%; cursor: pointer;">
              <option value="prescription">Prescription Slip</option>
              <option value="lab_report">Lab Test / Blood Report</option>
              <option value="discharge_summary">Discharge Summary</option>
              <option value="scan_report">Scan / X-Ray / Ultrasound</option>
              <option value="previous_record">Previous Medical Record</option>
              <option value="other">Other Medical Document</option>
            </select>
          </div>

          <!-- Upload Actions -->
          <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <label class="btn btn-secondary" style="cursor: pointer;">
              📁 Browse Files / PDF
              <input type="file" id="file-input-device" accept="image/*,application/pdf" style="display: none;" />
            </label>
            <label class="btn btn-primary" style="cursor: pointer;">
              📷 Take Photo / Scan
              <input type="file" id="file-input-camera" accept="image/*" capture="environment" style="display: none;" />
            </label>
          </div>

          <!-- Staged File Preview Banner -->
          <div id="staged-file-card" style="display: none; margin-top: 1.5rem; background: #eff6ff; padding: 1.25rem; border-radius: 12px; border: 1px solid #bfdbfe;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <div style="text-align: left;">
                <strong id="staged-filename" style="font-size: 1.1rem; color: var(--primary);">filename.pdf</strong>
                <div id="staged-filesize" style="font-size: 0.9rem; color: var(--text-muted);">1.2 MB</div>
              </div>
              <div style="display: flex; gap: 0.5rem;">
                <button type="button" class="btn btn-danger" id="btn-cancel-staged" style="min-height: 44px; padding: 0.5rem 1rem; font-size: 1rem;">
                  Cancel
                </button>
                <button type="button" class="btn btn-success" id="btn-upload-staged" style="min-height: 44px; padding: 0.5rem 1.25rem; font-size: 1rem;">
                  Upload Now ↑
                </button>
              </div>
            </div>
            <!-- Upload Progress Bar -->
            <div id="upload-progress-bar-container" style="display: none; margin-top: 1rem; width: 100%; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
              <div id="upload-progress-bar" style="width: 0%; height: 100%; background: var(--success); transition: width 0.3s ease;"></div>
            </div>
          </div>
        </div>

        <!-- Uploaded Documents Queue with OCR Status -->
        <div style="margin-bottom: 2rem;">
          <h4 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem;">
            Uploaded Documents (${this.uploadedDocs.length})
          </h4>
          <div id="uploaded-docs-list" style="display: flex; flex-direction: column; gap: 0.9rem;">
            ${this.renderUploadedDocsList()}
          </div>
        </div>

        <!-- Continue Button -->
        <button type="button" class="btn btn-primary btn-large btn-full" id="btn-continue-docs">
          ${this.uploadedDocs.length > 0 ? "Done Uploading — Proceed to Finish →" : "Skip Document Upload & Finish →"}
        </button>
      </div>
    `;
  }

  renderUploadedDocsList() {
    if (this.uploadedDocs.length === 0) {
      return `
        <div style="background: #f8fafc; padding: 1.5rem; text-align: center; border-radius: 12px; color: #64748b; border: 1px solid #e2e8f0;">
          No documents uploaded yet. You can attach records or skip to the next step.
        </div>
      `;
    }

    return this.uploadedDocs.map(doc => {
      let statusBadge = "";
      if (doc.status === "uploaded") {
        statusBadge = `<span class="badge-pill" style="background: #fef3c7; color: #b45309;">⏳ Queued</span>`;
      } else if (doc.status === "processing") {
        statusBadge = `<span class="badge-pill" style="background: #e0f2fe; color: #0369a1;">⚙️ Processing OCR (${doc.progress}%)</span>`;
      } else if (doc.status === "completed") {
        statusBadge = `<span class="badge-pill" style="background: #dcfce7; color: #15803d;">✓ OCR Extracted</span>`;
      } else {
        statusBadge = `<span class="badge-pill" style="background: #fee2e2; color: #b91c1c;">✕ Failed</span>`;
      }

      return `
        <div style="background: #ffffff; border: 1px solid var(--border-color); border-radius: 14px; padding: 1.25rem; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <div style="font-weight: 700; font-size: 1.1rem; color: var(--text-main);">${doc.filename}</div>
              <div style="font-size: 0.9rem; color: var(--text-muted); text-transform: capitalize;">
                Type: ${doc.doc_type.replace('_', ' ')}
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              ${statusBadge}
            </div>
          </div>

          <!-- Preview accordions if OCR completed -->
          ${doc.preview ? `
            <div style="margin-top: 0.9rem; padding: 0.8rem; background: #f8fafc; border-radius: 8px; font-size: 0.9rem; border-left: 3px solid var(--secondary);">
              <strong>Extracted Details (Member 3 OCR):</strong>
              <div style="margin-top: 0.3rem;">
                ${doc.preview.institution ? `<div><strong>Hospital:</strong> ${doc.preview.institution}</div>` : ''}
                ${doc.preview.clinical_impression ? `<div><strong>Impression:</strong> ${doc.preview.clinical_impression}</div>` : ''}
                ${doc.preview.extracted_rx ? `<div><strong>Medications:</strong> ${doc.preview.extracted_rx.join(', ')}</div>` : ''}
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  attachEvents() {
    const docTypeSelect = this.container.querySelector("#doc-type-select");
    if (docTypeSelect) {
      docTypeSelect.addEventListener("change", (e) => {
        this.selectedDocType = e.target.value;
      });
    }

    // Device file input
    const fileDevice = this.container.querySelector("#file-input-device");
    if (fileDevice) {
      fileDevice.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          this.stageFile(e.target.files[0]);
        }
      });
    }

    // Camera capture input
    const fileCamera = this.container.querySelector("#file-input-camera");
    if (fileCamera) {
      fileCamera.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          this.stageFile(e.target.files[0]);
        }
      });
    }

    // Cancel staged
    const cancelBtn = this.container.querySelector("#btn-cancel-staged");
    if (cancelBtn) {
      cancelBtn.addEventListener("click", () => {
        this.selectedFile = null;
        const stagedCard = this.container.querySelector("#staged-file-card");
        if (stagedCard) stagedCard.style.display = "none";
      });
    }

    // Upload staged
    const uploadBtn = this.container.querySelector("#btn-upload-staged");
    if (uploadBtn) {
      uploadBtn.addEventListener("click", async () => {
        await this.performUpload();
      });
    }

    // Continue / Finish
    const continueBtn = this.container.querySelector("#btn-continue-docs");
    if (continueBtn) {
      continueBtn.addEventListener("click", () => {
        if (this.onCompleted) {
          this.onCompleted(this.uploadedDocs);
        }
      });
    }
  }

  stageFile(file) {
    this.selectedFile = file;
    const stagedCard = this.container.querySelector("#staged-file-card");
    const nameEl = this.container.querySelector("#staged-filename");
    const sizeEl = this.container.querySelector("#staged-filesize");

    if (stagedCard && nameEl && sizeEl) {
      nameEl.textContent = file.name;
      sizeEl.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to upload`;
      stagedCard.style.display = "block";
    }
  }

  async performUpload() {
    if (!this.selectedFile || !this.sessionId) {
      alert("Missing file or active session.");
      return;
    }

    const progressContainer = this.container.querySelector("#upload-progress-bar-container");
    const progressBar = this.container.querySelector("#upload-progress-bar");
    if (progressContainer && progressBar) {
      progressContainer.style.display = "block";
      progressBar.style.width = "40%";
    }

    const res = await api.uploadDocument(this.sessionId, this.selectedFile, this.selectedDocType);

    if (progressBar) progressBar.style.width = "100%";

    if (!res.success) {
      alert(`Upload Failed: ${res.error}`);
      if (progressContainer) progressContainer.style.display = "none";
      return;
    }

    const docData = {
      document_id: res.data.document_id,
      filename: res.data.filename,
      doc_type: res.data.document_type,
      status: res.data.status,
      progress: 25,
      preview: null
    };

    this.uploadedDocs.push(docData);
    this.selectedFile = null;

    // Start polling OCR status for this document
    this.pollOcrStatus(docData.document_id);

    // Re-render
    this.render();
    this.attachEvents();
  }

  pollOcrStatus(documentId) {
    const timer = setInterval(async () => {
      const res = await api.getDocumentStatus(documentId);
      if (res.success) {
        const doc = this.uploadedDocs.find(d => d.document_id === documentId);
        if (doc) {
          doc.status = res.data.status;
          doc.progress = res.data.progress_percent;
          if (res.data.parsed_preview) {
            doc.preview = res.data.parsed_preview;
          }

          // Re-render list
          const listEl = this.container.querySelector("#uploaded-docs-list");
          if (listEl) listEl.innerHTML = this.renderUploadedDocsList();

          if (res.data.status === "completed" || res.data.status === "failed") {
            clearInterval(timer);
            this.pollingTimers.delete(documentId);
          }
        }
      }
    }, 2000);

    this.pollingTimers.set(documentId, timer);
  }

  cleanup() {
    for (const timer of this.pollingTimers.values()) {
      clearInterval(timer);
    }
    this.pollingTimers.clear();
  }
}

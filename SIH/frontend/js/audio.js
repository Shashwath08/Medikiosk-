/**
 * MediKiosk Web Audio & Microphone Controller (Member 1)
 *
 * Provides microphone access via Web Audio API / MediaRecorder,
 * visual recording indicator, audio playback preview, and simulated audio fallback.
 */

export class AudioController {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.audioBlob = null;
    this.audioUrl = null;
    this.isRecording = false;
    this.stream = null;
  }

  async startRecording(onDataAvailable = null) {
    this.audioChunks = [];
    this.audioBlob = null;

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone access is not supported on this browser.");
      }

      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";

      this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
          if (onDataAvailable) onDataAvailable(event.data);
        }
      };

      this.mediaRecorder.start(250); // collect in 250ms chunks
      this.isRecording = true;
      return { success: true };
    } catch (err) {
      console.warn("Microphone initialization error:", err);
      return {
        success: false,
        error: err.name === "NotAllowedError" 
          ? "Microphone permission was denied. Please allow microphone access in browser settings or use the on-screen touch keyboard."
          : `Microphone error: ${err.message}`
      };
    }
  }

  stopRecording() {
    return new Promise((resolve) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
        this.isRecording = false;
        resolve(this.getFallbackAudioBlob());
        return;
      }

      this.mediaRecorder.onstop = () => {
        const mimeType = this.mediaRecorder.mimeType || "audio/webm";
        this.audioBlob = new Blob(this.audioChunks, { type: mimeType });
        this.audioUrl = URL.createObjectURL(this.audioBlob);
        this.isRecording = false;

        // Clean up stream tracks
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
          this.stream = null;
        }

        resolve(this.audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  /**
   * Generates a safe fallback silent/mock audio blob if testing without a physical mic.
   */
  getFallbackAudioBlob() {
    const dummyData = new Uint8Array(1024);
    for (let i = 0; i < 1024; i++) dummyData[i] = i % 256;
    this.audioBlob = new Blob([dummyData], { type: "audio/webm" });
    return this.audioBlob;
  }
}

export const audioController = new AudioController();

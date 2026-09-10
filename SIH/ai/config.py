"""
Central configuration for the MediKiosk AI + Voice module (Member 2).

Everything is overridable via environment variables so that Member 4 can
deploy the same code inside FastAPI without touching the source.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------- Ollama / LLM
OLLAMA_HOST: str = os.getenv("MEDIKIOSK_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("MEDIKIOSK_OLLAMA_MODEL", "gemma3:4b")
OLLAMA_TIMEOUT: int = int(os.getenv("MEDIKIOSK_OLLAMA_TIMEOUT", "120"))

# Deterministic output is mandatory for a clinical extraction system.
LLM_TEMPERATURE: float = 0.0
LLM_TOP_P: float = 0.9
LLM_NUM_PREDICT: int = 512

# Second local AI pass that removes unsupported values.
ENABLE_LLM_VALIDATION_PASS: bool = (
    os.getenv("MEDIKIOSK_LLM_VALIDATION", "1").strip() == "1"
)
# LLM-assisted spelling correction for typed input (suggestion only, never silent).
ENABLE_LLM_CORRECTION: bool = (
    os.getenv("MEDIKIOSK_LLM_CORRECTION", "1").strip() == "1"
)

# ------------------------------------------------------------------- Speech
STT_MODEL_SIZE: str = os.getenv("MEDIKIOSK_STT_MODEL", "small")
STT_DEVICE: str = os.getenv("MEDIKIOSK_STT_DEVICE", "cpu")
STT_COMPUTE_TYPE: str = os.getenv("MEDIKIOSK_STT_COMPUTE", "int8")
SAMPLE_RATE: int = 16000
CHANNELS: int = 1
MAX_RECORD_SECONDS: int = int(os.getenv("MEDIKIOSK_MAX_RECORD_SECONDS", "30"))
SILENCE_STOP_SECONDS: float = 2.0

# Language handling stays modular - do not hardcode English anywhere else.
DEFAULT_LANGUAGE: str = os.getenv("MEDIKIOSK_LANGUAGE", "en")
STT_LANGUAGE: str | None = os.getenv("MEDIKIOSK_STT_LANGUAGE", "en") or None

# ------------------------------------------------------------------- TTS
TTS_RATE: int = int(os.getenv("MEDIKIOSK_TTS_RATE", "165"))
TTS_VOLUME: float = float(os.getenv("MEDIKIOSK_TTS_VOLUME", "1.0"))
TTS_ENABLED: bool = os.getenv("MEDIKIOSK_TTS_ENABLED", "1").strip() == "1"
# "auto"       -> in-process engine (fresh instance per utterance on Windows)
# "subprocess" -> one Python process per sentence; slower, but always works
TTS_MODE: str = os.getenv("MEDIKIOSK_TTS_MODE", "auto").strip().lower()

# ------------------------------------------------------------------- Safety
# Minimum fuzzy similarity for an extracted token to count as "supported"
# by the patient's own words. Below this the value is dropped (anti-hallucination).
SUPPORT_MATCH_THRESHOLD: float = 0.78
# Drop unsupported values instead of keeping them.
STRICT_SUPPORT_CHECK: bool = (
    os.getenv("MEDIKIOSK_STRICT_SUPPORT", "1").strip() == "1"
)

# ------------------------------------------------------------------- Privacy
# Never log full patient histories by default.
LOG_PATIENT_TEXT: bool = os.getenv("MEDIKIOSK_LOG_PATIENT_TEXT", "0").strip() == "1"
KEEP_AUDIO_FILES: bool = os.getenv("MEDIKIOSK_KEEP_AUDIO", "0").strip() == "1"
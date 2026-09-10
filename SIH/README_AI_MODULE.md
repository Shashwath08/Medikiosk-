# MediKiosk — AI + Voice Engine (Member 2)

Local-only clinical history engine: speech in → clean, validated, structured JSON out.
No OpenAI, no paid APIs, no patient data leaving the machine.

**Boundary:** this module does NOT diagnose, prescribe, or triage. Red-flag/triage logic is Member 5's.

---

## 1. Setup

```bash
# 1. Ollama + model
curl -fsSL https://ollama.com/install.sh | sh     # or download from ollama.com
ollama serve
ollama pull gemma3:4b

# 2. System audio deps (Linux)
sudo apt install portaudio19-dev espeak ffmpeg

# 3. Python
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Check everything is alive:

```bash
python -m ai.history.main --health
```

## 2. Run

```bash
python -m ai.history.main                 # full kiosk (speak / type)
python -m ai.history.main --text          # text only, no mic
python -m ai.history.main --no-tts        # no voice output
python -m ai.history.main --extract "my head is paining a lof from yeaterday"
```

Tests:

```bash
pytest tests/test_offline.py -v            # no Ollama needed (25 tests)
pytest tests/test_extraction_live.py -v -s # needs Ollama + gemma3:4b
```

## 3. Structure

```
ai/
├── config.py                  # all settings, env-overridable
├── history/
│   ├── main.py                # InterviewSession + CLI kiosk
│   ├── question_engine.py     # adaptive questioning, section registry (AYUSH-ready)
│   ├── history_extractor.py   # Ollama client, extraction, validation, support guard
│   ├── clinical_schema.py     # Pydantic schema, merge logic, JSON contract
│   ├── text_normalizer.py     # cleanup, correction suggestions, support matching
│   └── prompts.py             # all Gemma prompts
└── speech/
    ├── speech_to_text.py      # Faster-Whisper (small / cpu / int8 / 16 kHz)
    └── text_to_speech.py      # pyttsx3, language-parameterised
```

## 4. Anti-hallucination: three independent layers

| Layer | What it does |
|---|---|
| Prompt | JSON mode, temperature 0, explicit "never invent, unclear → null" rules + few-shot |
| Schema | Unknown keys stripped, null-tokens ("N/A", "not mentioned") → `null`, lists deduped, Pydantic rejects malformed output |
| Support guard | Deterministic: every extracted value must trace back to the patient's own words (fuzzy token match). `"a lof"` → dropped. Invented `severity` → dropped. Values copied from previous history → dropped. |

Optional 4th layer: second local Gemma pass that can only *remove* values (`ENABLE_LLM_VALIDATION_PASS`).

Everything dropped is returned in `dropped` and stored in the turn record — auditable, never silent.

## 5. Backend contract (Member 4)

```python
from ai.history.main import InterviewSession, extract_history_from_text
from ai.speech.speech_to_text import speech_to_text, listen_and_transcribe
from ai.speech.text_to_speech import generate_speech, speak
from ai.history.text_normalizer import normalise_text, suggest_correction
from ai.history.history_extractor import extract_field, health_check
```

FastAPI sketch (Member 4 writes this, not this module):

```python
SESSIONS: dict[str, InterviewSession] = {}

@app.post("/interview/start")
def start():
    s = InterviewSession(); SESSIONS[s.session_id] = s
    return {"session_id": s.session_id, "question": s.start()}

@app.post("/interview/answer")
def answer(session_id: str, text: str, mode: str = "text"):
    return SESSIONS[session_id].submit_answer(text, input_mode=mode)

@app.post("/interview/correction-preview")
def preview(session_id: str, text: str):
    return SESSIONS[session_id].preview_correction(text)   # → Did you mean ...

@app.get("/interview/final")
def final(session_id: str):
    return SESSIONS[session_id].final_response()           # → {"success","data","error"}
```

Response shapes:

```jsonc
// submit_answer
{"success": true, "extracted": {...}, "dropped": {...}, "denial": false,
 "history": {...}, "next_question": {...}, "state": {...}}

// final_response
{"success": true, "data": { ...17 schema fields... }, "error": null}
{"success": false, "data": {}, "error": "descriptive error message"}
```

`session.audit_dump()` gives the full turn trail (raw text, normalised text, extracted, dropped) if the backend wants to persist it.

## 6. Speech confirmation flow

```python
result  = listen_and_transcribe()
payload = build_confirmation_payload(result)
# → {"prompt": "You said:", "transcription": "...", "actions": ["confirm","speak_again","type_correction"]}
```

Nothing enters the history until the patient confirms.

## 7. Adding AYUSH sections later

```python
from ai.history.question_engine import Question, Section, register_section

register_section(Section("trividha", "Trividha Pariksha", [
    Question("tv_nadi", "review_of_systems", "Nadi pariksha related question..."),
]), after="hpi")
```

Core flow, extraction and validation stay untouched. Add new schema fields to
`clinical_schema.py` only if AYUSH needs fields outside the current 17.

## 8. Privacy

- Model runs locally via Ollama; no external calls anywhere in the code path.
- Audio → temp file → transcribe → deleted (`KEEP_AUDIO_FILES=0` by default).
- Patient text is not logged (`LOG_PATIENT_TEXT=0`).
- No API keys exist in this module.

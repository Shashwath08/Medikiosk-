"""
Gemma 3 4B (Ollama) extraction engine for MediKiosk - Member 2.

Pipeline for one patient answer:
    normalised text
        -> Gemma extraction (JSON mode, temperature 0)
        -> lenient JSON parse
        -> unknown-field strip + Pydantic validation
        -> optional second local AI validation pass
        -> deterministic support guard (drops anything the patient never said)
        -> PartialHistory
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from ..config import (
    ENABLE_LLM_VALIDATION_PASS,
    LLM_NUM_PREDICT,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    STRICT_SUPPORT_CHECK,
)
from .clinical_schema import (
    ALL_FIELDS,
    LIST_FIELDS,
    STRING_FIELDS,
    PartialHistory,
)
from .prompts import (
    CORRECTION_SYSTEM_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
    build_correction_prompt,
    build_extraction_prompt,
    build_validation_prompt,
)
from .text_normalizer import is_supported_by_text, normalise_text


class OllamaUnavailable(RuntimeError):
    """Raised when the local model cannot be reached. Never falls back to a cloud API."""


class ExtractionResult(BaseModel):
    partial: PartialHistory = Field(default_factory=PartialHistory)
    dropped: Dict[str, Any] = Field(default_factory=dict)
    raw_model_output: str = ""
    used_llm_validation: bool = False
    warnings: List[str] = Field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return self.partial.non_empty()


# --------------------------------------------------------------------------
# Ollama client
# --------------------------------------------------------------------------


class OllamaClient:
    def __init__(
        self,
        host: str = OLLAMA_HOST,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def installed_models(self) -> List[str]:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system: str = "",
        json_mode: bool = True,
        num_predict: int = LLM_NUM_PREDICT,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
                "top_p": LLM_TOP_P,
                "num_predict": num_predict,
            },
        }
        if json_mode:
            payload["format"] = "json"

        try:
            r = requests.post(
                f"{self.host}/api/generate", json=payload, timeout=self.timeout
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaUnavailable(
                f"Local model '{self.model}' not reachable at {self.host}: {exc}"
            ) from exc

        return (r.json().get("response") or "").strip()


_client: Optional[OllamaClient] = None


def get_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


# --------------------------------------------------------------------------
# JSON parsing + hard cleanup
# --------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?|```", re.IGNORECASE)


def parse_json_lenient(text: str) -> Optional[Dict[str, Any]]:
    """Small models still leak fences/prose sometimes. Recover the first JSON object."""
    if not text:
        return None
    cleaned = _FENCE.sub("", text).strip()
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(cleaned[start:i + 1])
                    return obj if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def strip_unknown_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove any key Gemma invented; also normalise obvious type mismatches."""
    out: Dict[str, Any] = {}
    for key, value in (data or {}).items():
        field = str(key).strip().lower().replace(" ", "_")
        if field not in ALL_FIELDS:
            continue
        if field in LIST_FIELDS and isinstance(value, str):
            value = [v.strip() for v in re.split(r"[,;]| and ", value) if v.strip()]
        if field in STRING_FIELDS and isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        out[field] = value
    return out


# --------------------------------------------------------------------------
# Deterministic anti-hallucination guard
# --------------------------------------------------------------------------


def apply_support_guard(
    partial: PartialHistory,
    *sources: str,
) -> tuple[PartialHistory, Dict[str, Any]]:
    """
    Drop every value that is not traceable to the patient's own words.
    This is the layer that stops "a lof" -> duration, and stops the model from
    copying previous history into the current turn.
    """
    if not STRICT_SUPPORT_CHECK:
        return partial, {}

    data = partial.model_dump()
    dropped: Dict[str, Any] = {}

    for field in STRING_FIELDS:
        value = data.get(field)
        if value and not is_supported_by_text(value, *sources):
            dropped[field] = value
            data[field] = None

    for field in LIST_FIELDS:
        kept, removed = [], []
        for item in data.get(field) or []:
            (kept if is_supported_by_text(item, *sources) else removed).append(item)
        if removed:
            dropped[field] = removed
        data[field] = kept

    return PartialHistory(**data), dropped


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def extract_field(
    patient_answer: str,
    current_field: Optional[str] = None,
    current_history: Optional[Dict[str, Any]] = None,
    current_question: Optional[str] = None,
    run_validation: Optional[bool] = None,
    client: Optional[OllamaClient] = None,
) -> ExtractionResult:
    """
    Main entry point used by the question engine and (later) by FastAPI.

    Raises OllamaUnavailable if the local model is down - the caller decides
    what to show. Nothing is ever sent to an external service.
    """
    result = ExtractionResult()
    raw_answer = (patient_answer or "").strip()
    if not raw_answer:
        return result

    normalised = normalise_text(raw_answer)
    llm = client or get_client()

    output = llm.generate(
        prompt=build_extraction_prompt(
            patient_answer=normalised,
            current_field=current_field,
            current_question=current_question,
            current_history=current_history,
        ),
        system=EXTRACTION_SYSTEM_PROMPT,
        json_mode=True,
    )
    result.raw_model_output = output

    parsed = parse_json_lenient(output)
    if parsed is None:
        result.warnings.append("model returned malformed JSON; turn discarded")
        return result

    cleaned = strip_unknown_fields(parsed)
    if not cleaned:
        return result

    # ---- second local AI validation pass (never diagnoses, only removes) ----
    if run_validation is None:
        run_validation = ENABLE_LLM_VALIDATION_PASS
    if run_validation and cleaned:
        try:
            checked = llm.generate(
                prompt=build_validation_prompt(normalised, cleaned),
                system=VALIDATION_SYSTEM_PROMPT,
                json_mode=True,
                num_predict=384,
            )
            reparsed = parse_json_lenient(checked)
            if reparsed is not None:
                validated = strip_unknown_fields(reparsed)
                # Validation may only remove/shrink, never introduce new keys.
                cleaned = {k: v for k, v in validated.items() if k in cleaned}
                result.used_llm_validation = True
        except OllamaUnavailable:
            result.warnings.append("validation pass skipped (model unreachable)")

    try:
        partial = PartialHistory(**cleaned)
    except Exception as exc:  # malformed output -> reject the turn, never guess
        result.warnings.append(f"schema validation failed: {exc}")
        return result

    partial, dropped = apply_support_guard(partial, normalised, raw_answer)
    result.partial = partial
    result.dropped = dropped
    if dropped:
        result.warnings.append("unsupported values removed by support guard")
    return result


def llm_correct_spelling(text: str, client: Optional[OllamaClient] = None) -> str:
    """Spelling/STT correction suggestion. Returns '' if the model is unavailable."""
    if not text.strip():
        return ""
    llm = client or get_client()
    try:
        out = llm.generate(
            prompt=build_correction_prompt(text),
            system=CORRECTION_SYSTEM_PROMPT,
            json_mode=False,
            num_predict=128,
        )
    except OllamaUnavailable:
        return ""
    out = out.strip().strip('"').split("\n")[0]
    return out.replace("OUTPUT:", "").strip()


def health_check() -> Dict[str, Any]:
    """Useful for the kiosk startup screen and for Member 4's /health endpoint."""
    llm = get_client()
    available = llm.is_available()
    models = llm.installed_models() if available else []
    return {
        "ollama_reachable": available,
        "model": OLLAMA_MODEL,
        "model_installed": any(m.startswith(OLLAMA_MODEL.split(":")[0]) for m in models),
        "installed_models": models,
    }

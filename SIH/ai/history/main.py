"""
MediKiosk AI + Voice module - orchestration layer (Member 2).

Two ways to use this file:

1) As a library (this is what Member 4 will import into FastAPI):

       from ai.history.main import InterviewSession

       session = InterviewSession()
       q = session.start()                          # -> question dict
       out = session.submit_answer("my head is paining since yesterday")
       ...
       final = session.final_response()             # -> {"success": ..., "data": ..., "error": ...}

2) As a standalone kiosk CLI (Phase 1-8 testing, no FastAPI needed):

       python -m ai.history.main            # text + speech
       python -m ai.history.main --text     # text only
       python -m ai.history.main --no-tts
"""

from __future__ import annotations

import argparse
import json
import uuid
from typing import Any, Dict, List, Optional

from ..config import ENABLE_LLM_CORRECTION, TTS_ENABLED
from .clinical_schema import ClinicalHistory, ModuleResponse, PartialHistory, TurnRecord
from .history_extractor import (
    ExtractionResult,
    OllamaUnavailable,
    extract_field,
    health_check,
)
from .question_engine import (
    Question,
    QuestionEngine,
    is_bare_affirmation,
    is_explicit_denial,
)
from .text_normalizer import CorrectionSuggestion, normalise_text, suggest_correction


class InterviewSession:
    """One patient interview. Framework-agnostic: no FastAPI, no globals."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        history: Optional[ClinicalHistory] = None,
        language: str = "en",
    ) -> None:
        self.session_id = session_id or uuid.uuid4().hex
        self.engine = QuestionEngine(history=history)
        self.language = language
        self.turns: List[TurnRecord] = []
        self.errors: List[str] = []
        self.clarify_counts: Dict[str, int] = {}

    # ------------------------------------------------------------- questions
    def start(self) -> Optional[Dict[str, Any]]:
        return self.next_question()

    def next_question(self) -> Optional[Dict[str, Any]]:
        q = self.engine.next_question()
        if q is None:
            return None
        return self._question_dict(q)

    @staticmethod
    def _clarify_text(q: Question) -> str:
        """Follow-up used when the patient answers 'yes' without any detail."""
        if q.is_list_field:
            return "Please tell me which ones."
        return "Please tell me a little more about it."

    def _question_dict(self, q: Question) -> Dict[str, Any]:
        return {
            "question_id": q.id,
            "field": q.field,
            "text": q.text,
            "hint": q.hint,
            "section_id": q.section_id,
            "section_title": q.section_title,
            "is_list_field": q.is_list_field,
            "progress": self.engine.progress(),
        }

    # ---------------------------------------------------------------- answers
    def preview_correction(self, text: str) -> Dict[str, Any]:
        """
        Step for the UI: 'Did you mean ...?' with [Use correction] / [Keep original].
        Nothing is stored here.
        """
        suggestion: CorrectionSuggestion = suggest_correction(
            text, use_llm=ENABLE_LLM_CORRECTION
        )
        return suggestion.model_dump()

    def submit_answer(
        self,
        answer_text: str,
        input_mode: str = "text",
        question_id: Optional[str] = None,
        original_text: Optional[str] = None,
        correction_applied: bool = False,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Feed one patient answer into the history.

        answer_text     : the text the patient CONFIRMED (corrected or original)
        original_text   : what they actually said/typed, kept for audit
        overwrite       : True when the patient is correcting an earlier field
        """
        question = self.engine.current_question
        if question_id:
            question = next(
                (q for q in self.engine.all_questions() if q.id == question_id),
                question,
            )
        raw = (original_text or answer_text or "").strip()
        confirmed = (answer_text or "").strip()
        normalised = normalise_text(confirmed)

        record = TurnRecord(
            question_id=question.id if question else None,
            question_text=question.text if question else None,
            target_field=question.field if question else None,
            input_mode=input_mode,
            raw_text=raw,
            normalised_text=normalised,
            correction_applied=correction_applied,
        )

        # "yes" confirms that something exists but never says WHAT it is.
        # Ask again for the detail; store nothing, and do not mark the
        # question as asked so the engine re-serves it.
        if question is not None and is_bare_affirmation(normalised):
            self.turns.append(record)
            asked_before = self.clarify_counts.get(question.id, 0)
            self.clarify_counts[question.id] = asked_before + 1
            if asked_before >= 1:
                # Already asked once for detail - move on rather than loop.
                self.engine.mark_asked(question)
                return {
                    "success": True, "extracted": {}, "dropped": {},
                    "denial": False, "needs_detail": False,
                    "history": self.engine.history.to_json_dict(),
                    "next_question": self.next_question(),
                    "state": self.engine.state(),
                }
            return {
                "success": True, "extracted": {}, "dropped": {},
                "denial": False, "needs_detail": True,
                "clarify": self._clarify_text(question),
                "history": self.engine.history.to_json_dict(),
                "next_question": self._question_dict(question),
                "state": self.engine.state(),
            }

        if question is not None:
            self.engine.mark_asked(question)

        # Explicit "no" -> keep field empty, do not re-ask, do not invent.
        if question is not None and is_explicit_denial(normalised):
            self.engine.mark_denied(question)
            self.turns.append(record)
            return {
                "success": True,
                "extracted": {},
                "dropped": {},
                "denial": True,
                "history": self.engine.history.to_json_dict(),
                "next_question": self.next_question(),
                "state": self.engine.state(),
            }

        try:
            result: ExtractionResult = extract_field(
                patient_answer=normalised,
                current_field=question.field if question else None,
                current_history=self.engine.history.to_json_dict(),
                current_question=question.text if question else None,
            )
        except OllamaUnavailable as exc:
            self.errors.append(str(exc))
            self.turns.append(record)
            return {
                "success": False,
                "error": str(exc),
                "extracted": {},
                "history": self.engine.history.to_json_dict(),
                "next_question": self._question_dict(question) if question else None,
                "state": self.engine.state(),
            }

        partial: PartialHistory = result.partial
        self.engine.apply_partial(partial, overwrite_strings=overwrite)

        record.extracted = partial.non_empty()
        record.dropped_values = result.dropped
        self.turns.append(record)

        return {
            "success": True,
            "extracted": record.extracted,
            "dropped": result.dropped,
            "warnings": result.warnings,
            "denial": False,
            "history": self.engine.history.to_json_dict(),
            "next_question": self.next_question(),
            "state": self.engine.state(),
        }

    # ----------------------------------------------------------------- output
    def is_complete(self) -> bool:
        return self.engine.is_complete()

    def final_response(self) -> Dict[str, Any]:
        try:
            data = self.engine.history.to_json_dict()
        except Exception as exc:
            return ModuleResponse.fail(f"history serialisation failed: {exc}").model_dump()
        return ModuleResponse.ok(data).model_dump()

    def audit_dump(self) -> Dict[str, Any]:
        """Full turn-by-turn trail. Backend decides whether to persist this."""
        return {
            "session_id": self.session_id,
            "language": self.language,
            "turns": [t.model_dump() for t in self.turns],
            "state": self.engine.state(),
            "history": self.engine.history.to_json_dict(),
            "errors": self.errors,
        }


# --------------------------------------------------------------------------
# Backend-friendly one-shot helpers
# --------------------------------------------------------------------------


def extract_history_from_text(text: str) -> Dict[str, Any]:
    """Single-shot extraction (useful for tests and for Member 4's /extract endpoint)."""
    try:
        result = extract_field(patient_answer=normalise_text(text))
    except OllamaUnavailable as exc:
        return ModuleResponse.fail(str(exc)).model_dump()
    history = ClinicalHistory(**result.partial.non_empty())
    return ModuleResponse.ok(history.to_json_dict()).model_dump()


# --------------------------------------------------------------------------
# CLI kiosk
# --------------------------------------------------------------------------


def _speaker(enabled: bool):
    if not enabled:
        return lambda text: None
    try:
        from ..speech.text_to_speech import speak
        return lambda text: speak(text)
    except Exception:
        return lambda text: None


def _capture_speech() -> Optional[str]:
    try:
        from ..speech.speech_to_text import listen_and_transcribe
    except Exception as exc:
        print(f"[speech unavailable: {exc}]")
        return None
    result = listen_and_transcribe()
    if result.get("success"):
        return result.get("text")
    print(f"[speech error] {result.get('error')}")
    return None


def run_cli(text_only: bool = False, tts: bool = TTS_ENABLED) -> Dict[str, Any]:
    print("=" * 60)
    print("  MediKiosk - Clinical History Assistant")
    print("  (This kiosk only records your history. It does not diagnose.)")
    print("=" * 60)

    status = health_check()
    if not status["ollama_reachable"]:
        print("\n[!] Ollama is not running. Start it with:  ollama serve")
        print("[!] And pull the model:                  ollama pull gemma3:4b\n")
        return ModuleResponse.fail("ollama not reachable").model_dump()
    if not status["model_installed"]:
        print(f"\n[!] Model {status['model']} not installed. Run: ollama pull {status['model']}\n")

    say = _speaker(tts)
    session = InterviewSession()
    question = session.start()

    while question:
        print(f"\n[{question['section_title']}]  "
              f"{question['progress']['answered']}/{question['progress']['total']}")
        print(f"MediKiosk: {question['text']}")
        if question["hint"]:
            print(f"           ({question['hint']})")
        say(question["text"])

        answer = None
        while answer is None:
            if text_only:
                answer = input("You (type): ").strip()
                break

            mode = input("Choose - [s]peak / [t]ype / [skip] : ").strip().lower()
            if mode in ("skip", "k"):
                session.engine.mark_asked(session.engine.current_question)
                answer = ""
                break
            if mode.startswith("s"):
                spoken = _capture_speech()
                if not spoken:
                    print("Could not hear that. Please try again.")
                    continue
                print(f'\nYou said: "{spoken}"')
                choice = input("[c]onfirm / [r]etry / [e]dit : ").strip().lower()
                if choice.startswith("r"):
                    continue
                if choice.startswith("e"):
                    spoken = input("Correct it: ").strip()
                answer = spoken
            else:
                answer = input("You (type): ").strip()

        if not answer:
            if session.engine.current_question:
                session.engine.mark_asked(session.engine.current_question)
            question = session.next_question()
            continue

        suggestion = session.preview_correction(answer)
        final_text, corrected = answer, False
        if suggestion["changed"]:
            print(f'\nDid you mean: "{suggestion["corrected"]}"')
            if input("[u]se correction / [k]eep original : ").strip().lower().startswith("u"):
                final_text, corrected = suggestion["corrected"], True

        print("...processing")
        out = session.submit_answer(
            final_text,
            input_mode="text" if text_only else "mixed",
            original_text=answer,
            correction_applied=corrected,
        )
        if not out["success"]:
            print(f"[error] {out.get('error')}")
            break
        if out.get("needs_detail"):
            print(f"MediKiosk: {out['clarify']}")
            say(out["clarify"])
            question = out["next_question"]
            continue
        if out.get("extracted"):
            print(f"  recorded: {json.dumps(out['extracted'], ensure_ascii=False)}")
        if out.get("dropped"):
            print(f"  ignored (unclear/unsupported): {out['dropped']}")

        question = out["next_question"]

    final = session.final_response()
    print("\n" + "=" * 60)
    print("FINAL STRUCTURED HISTORY (for backend)")
    print("=" * 60)
    print(json.dumps(final, indent=4, ensure_ascii=False))
    say("Thank you. Your details have been recorded. Please wait for the doctor.")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="MediKiosk AI + Voice module")
    parser.add_argument("--text", action="store_true", help="text-only mode (no mic)")
    parser.add_argument("--no-tts", action="store_true", help="disable speech output")
    parser.add_argument("--health", action="store_true", help="check local model status")
    parser.add_argument("--extract", type=str, help="one-shot extraction from a sentence")
    args = parser.parse_args()

    if args.health:
        print(json.dumps(health_check(), indent=4))
        return
    if args.extract:
        print(json.dumps(extract_history_from_text(args.extract), indent=4, ensure_ascii=False))
        return

    run_cli(text_only=args.text, tts=not args.no_tts)


if __name__ == "__main__":
    main()
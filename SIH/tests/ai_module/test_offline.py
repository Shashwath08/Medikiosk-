"""
Deterministic tests - no Ollama, no microphone needed.
Run:  pytest tests/test_offline.py -v
"""

from __future__ import annotations

import pytest

from ai.history.clinical_schema import (
    ClinicalHistory,
    ModuleResponse,
    PartialHistory,
    merge_history,
)
from ai.history.history_extractor import (
    apply_support_guard,
    parse_json_lenient,
    strip_unknown_fields,
)
from ai.history.question_engine import QuestionEngine, is_explicit_denial
from ai.history.text_normalizer import (
    is_supported_by_text,
    normalise_text,
    suggest_correction,
)


# ------------------------------------------------------------------ normaliser
@pytest.mark.parametrize("raw,expected", [
    ("my head is paining paining", "My head is paining"),
    ("my head is paining my head is paining", "My head is paining"),
    ("   i   have  fever   ", "I have fever"),
    ("i have fever ,, and cough .", "I have fever, and cough."),
    ("uh um i have chest pain", "I have chest pain"),
])
def test_normalise(raw, expected):
    assert normalise_text(raw) == expected


def test_normalise_empty():
    assert normalise_text("") == ""
    assert normalise_text("   ") == ""


def test_correction_suggests_without_mutating(monkeypatch):
    s = suggest_correction("my head is paining a lof from yeaterday", use_llm=False)
    assert s.original == "my head is paining a lof from yeaterday"
    assert "yesterday" in s.corrected.lower()
    assert s.changed is True


def test_correction_leaves_unknown_words_alone():
    # a drug/local word must not be fuzzy-mapped into something else
    s = suggest_correction("i take dolo and shankhpushpi", use_llm=False)
    assert "shankhpushpi" in s.corrected.lower()


# --------------------------------------------------------------- support guard
def test_support_true_cases():
    assert is_supported_by_text("head pain", "my head is paining a lot from yesterday")
    assert is_supported_by_text("unable to sleep", "i am not able to sleep")
    assert is_supported_by_text("yesterday", "my head is paining from yeaterday")


def test_support_false_cases():
    assert not is_supported_by_text("severe", "my head is paining from yesterday")
    assert not is_supported_by_text("diabetes mellitus type 2", "i have sugar")
    assert not is_supported_by_text("a lof", "")


def test_guard_drops_garbled_duration():
    partial = PartialHistory(
        chief_complaint="head pain",
        onset="yesterday",
        duration="a lof",
        severity="severe",
    )
    cleaned, dropped = apply_support_guard(
        partial, "My head is paining a lot from yesterday"
    )
    assert cleaned.chief_complaint == "head pain"
    assert cleaned.onset == "yesterday"
    assert cleaned.duration is None
    assert cleaned.severity is None
    assert "severity" in dropped


def test_guard_drops_list_items_not_said():
    partial = PartialHistory(associated_symptoms=["unable to sleep", "chest pain"])
    cleaned, dropped = apply_support_guard(partial, "I am not able to sleep")
    assert cleaned.associated_symptoms == ["unable to sleep"]
    assert dropped["associated_symptoms"] == ["chest pain"]


# ---------------------------------------------------------------------- schema
def test_null_tokens_become_none():
    h = ClinicalHistory(severity="not mentioned", duration="N/A", onset="  ")
    assert h.severity is None and h.duration is None and h.onset is None


def test_list_cleanup_and_dedupe():
    h = ClinicalHistory(medications=["Dolo", "dolo ", "none", ""])
    assert h.medications == ["Dolo"]


def test_string_field_given_list():
    h = ClinicalHistory(onset=["yesterday", "night"])
    assert h.onset == "yesterday, night"


def test_unknown_fields_stripped():
    data = strip_unknown_fields({"chief_complaint": "fever", "diagnosis": "malaria",
                                 "triage_level": "red"})
    assert data == {"chief_complaint": "fever"}


def test_lenient_json_parse():
    assert parse_json_lenient('```json\n{"onset": "yesterday"}\n```') == {"onset": "yesterday"}
    assert parse_json_lenient('sure! {"onset": "today"} hope this helps') == {"onset": "today"}
    assert parse_json_lenient("no json here") is None


def test_merge_does_not_overwrite_existing_string():
    base = ClinicalHistory(chief_complaint="head pain")
    merged = merge_history(base, PartialHistory(chief_complaint="fever"))
    assert merged.chief_complaint == "head pain"
    forced = merge_history(base, PartialHistory(chief_complaint="fever"),
                           overwrite_strings=True)
    assert forced.chief_complaint == "fever"


def test_merge_unions_lists():
    base = ClinicalHistory(medications=["Dolo"])
    merged = merge_history(base, PartialHistory(medications=["dolo", "BP tablet"]))
    assert merged.medications == ["Dolo", "BP tablet"]


def test_module_response_contract():
    ok = ModuleResponse.ok(ClinicalHistory().model_dump()).model_dump()
    assert ok["success"] is True and ok["error"] is None
    assert set(ok["data"]) == set(ClinicalHistory().model_dump())
    bad = ModuleResponse.fail("model down").model_dump()
    assert bad == {"success": False, "data": {}, "error": "model down"}


# ------------------------------------------------------------- question engine
def test_engine_skips_already_answered_fields():
    engine = QuestionEngine(history=ClinicalHistory(
        chief_complaint="head pain", onset="yesterday", severity="severe"))
    asked_fields = []
    for _ in range(30):
        q = engine.next_question()
        if q is None:
            break
        asked_fields.append(q.field)
        engine.mark_asked(q)
    assert "chief_complaint" not in asked_fields
    assert "onset" not in asked_fields
    assert "severity" not in asked_fields
    assert "medications" in asked_fields


def test_engine_skips_hpi_without_complaint():
    engine = QuestionEngine()
    first = engine.next_question()
    assert first.field == "chief_complaint"
    engine.mark_asked(first)
    nxt = engine.next_question()
    assert nxt.field != "onset"  # no complaint yet -> HPI details skipped


def test_engine_finishes():
    engine = QuestionEngine()
    for _ in range(60):
        q = engine.next_question()
        if q is None:
            break
        engine.mark_asked(q)
    assert engine.is_complete()


def test_denial_detection():
    assert is_explicit_denial("no")
    assert is_explicit_denial("Nothing.")
    assert is_explicit_denial("nahi hai")
    assert not is_explicit_denial("no fever but headache is there")


def test_denied_field_not_reasked():
    engine = QuestionEngine(history=ClinicalHistory(chief_complaint="fever"))
    q = next(q for q in engine.all_questions() if q.field == "allergies")
    engine.mark_asked(q)
    engine.mark_denied(q)
    remaining = []
    for _ in range(40):
        nq = engine.next_question()
        if nq is None:
            break
        remaining.append(nq.field)
        engine.mark_asked(nq)
    assert "allergies" not in remaining


def test_duration_not_reasked_when_onset_has_timespan():
    engine = QuestionEngine(history=ClinicalHistory(
        chief_complaint="burning stomach pain", onset="2 days ago"))
    fields = []
    for _ in range(40):
        q = engine.next_question()
        if q is None:
            break
        fields.append(q.field)
        engine.mark_asked(q)
    assert "duration" not in fields


def test_duration_still_asked_for_non_time_onset():
    engine = QuestionEngine(history=ClinicalHistory(
        chief_complaint="chest pain", onset="after eating food"))
    fields = []
    for _ in range(40):
        q = engine.next_question()
        if q is None:
            break
        fields.append(q.field)
        engine.mark_asked(q)
    assert "duration" in fields


def test_bare_affirmation_detected():
    from ai.history.question_engine import is_bare_affirmation
    for text in ["yes", "Yes.", "haan", "yes i have", "ok", "yup"]:
        assert is_bare_affirmation(text), text
    for text in ["yes i have fever", "yes since 2 days", "yes doctor gave BP tablet"]:
        assert not is_bare_affirmation(text), text


def test_yes_never_stored_as_clinical_value():
    h = ClinicalHistory(associated_symptoms=["yes", "haan", "fever"],
                        severity="yes", medications=["ok"])
    assert h.associated_symptoms == ["fever"]
    assert h.severity is None
    assert h.medications == []


def test_affirmation_triggers_followup_not_extraction():
    import ai.history.main as m
    session = m.InterviewSession()
    q = session.start()
    out = session.submit_answer("yes", question_id=q["question_id"])
    assert out["needs_detail"] is True
    assert out["extracted"] == {}
    # same question is served again, not marked as answered
    assert out["next_question"]["question_id"] == q["question_id"]


def test_affirmation_does_not_loop_forever():
    import ai.history.main as m
    session = m.InterviewSession()
    q = session.start()
    session.submit_answer("yes", question_id=q["question_id"])
    out = session.submit_answer("yes", question_id=q["question_id"])
    assert out["needs_detail"] is False
    assert out["next_question"]["question_id"] != q["question_id"]


def test_progress_does_not_count_conditional_skips():
    engine = QuestionEngine()
    p = engine.progress()
    assert p["answered"] == 0
    assert p["total"] == 8      # chief complaint + 7 standalone sections
    engine.history = ClinicalHistory(chief_complaint="head pain")
    p2 = engine.progress()
    assert p2["answered"] == 1
    assert p2["total"] > p["total"]   # HPI questions now in play
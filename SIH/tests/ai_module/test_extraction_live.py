"""
Live tests against the local Gemma 3 4B model (Ollama must be running).

    ollama serve
    ollama pull gemma3:4b
    pytest tests/test_extraction_live.py -v -s

Assertions are INVARIANTS (what must never happen), not exact string matches -
an LLM will phrase things differently every day, but it must never invent.
"""

from __future__ import annotations

import pytest

from ai.history.history_extractor import extract_field, health_check
from ai.history.text_normalizer import is_supported_by_text

pytestmark = pytest.mark.skipif(
    not health_check()["ollama_reachable"],
    reason="Ollama not running - live model tests skipped",
)

STRING_FIELDS_TO_CHECK = ["chief_complaint", "onset", "duration", "severity",
                          "character", "location", "radiation",
                          "aggravating_factors", "relieving_factors"]


def _extract(answer: str, field=None, question=None, history=None):
    result = extract_field(answer, current_field=field, current_question=question,
                           current_history=history)
    print(f"\nIN : {answer}\nOUT: {result.partial.non_empty()}\nDROPPED: {result.dropped}")
    return result.partial


def _assert_no_hallucination(partial, answer: str):
    data = partial.model_dump()
    for f in STRING_FIELDS_TO_CHECK:
        if data.get(f):
            assert is_supported_by_text(data[f], answer), f"{f}={data[f]!r} not in answer"


# 1. Normal English
def test_normal_english():
    p = _extract("I have headache since yesterday")
    assert p.chief_complaint and "head" in p.chief_complaint.lower()
    assert p.onset and "yesterday" in p.onset.lower()
    assert p.severity is None


# 2 + 4 + 5. Broken English + spelling mistakes + STT errors
def test_broken_english_with_typos():
    answer = "my head is paining a lof from yeaterday"
    p = _extract(answer)
    assert p.chief_complaint is not None
    assert p.duration is None, "garbled 'a lof' must never become duration"
    assert (p.duration or "") .lower() not in ("a lof", "a lot", "lofing")
    assert p.severity is None


# 3. Indian English
def test_indian_english():
    p = _extract("since 3 days I am getting loose motion only")
    assert p.chief_complaint is not None
    assert p.onset or p.duration


# 6 + 7. Repeated words and phrases
def test_repeated_words_and_phrases():
    p = _extract("my head is paining paining my head is paining")
    assert p.chief_complaint is not None
    _assert_no_hallucination(p, "my head is paining")


# 8. Missing information
def test_missing_information_stays_null():
    answer = "I am having stomach pain"
    p = _extract(answer)
    assert p.onset is None and p.duration is None and p.severity is None
    assert p.medications == [] and p.allergies == []


# 9. Unfamiliar / non-medical description
def test_unfamiliar_symptom_not_rejected():
    answer = "I am feeling something pulling inside my stomach"
    p = _extract(answer)
    assert p.chief_complaint is not None
    _assert_no_hallucination(p, answer)


# 10. Existing disease, patient wording preserved, no diagnosis upgrade
def test_existing_disease_patient_wording():
    answer = "I have sugar since 5 years"
    p = _extract(answer, field="past_medical_history",
                 question="Do you have any old or ongoing illness?")
    joined = " ".join(p.past_medical_history).lower()
    assert "sugar" in joined or "diabet" in joined
    assert "type 2" not in joined and "mellitus" not in joined


# 11. Medication without a name
def test_medication_without_name():
    answer = "I take some tablet for BP but I don't remember the name"
    p = _extract(answer, field="medications",
                 question="Are you taking any medicines regularly?")
    joined = " ".join(p.medications).lower()
    assert joined, "the fact that patient takes a BP tablet must be preserved"
    for invented in ("amlodipine", "telmisartan", "atenolol", "losartan"):
        assert invented not in joined, "drug name must never be invented"


# 12. Allergies
def test_allergies():
    p = _extract("I am allergic to penicillin injection", field="allergies",
                 question="Are you allergic to any medicine or food?")
    assert any("penicillin" in a.lower() for a in p.allergies)


# 13. Family history
def test_family_history():
    p = _extract("my father has BP and my mother has sugar",
                 field="family_history",
                 question="Does anyone in your family have any illness?")
    joined = " ".join(p.family_history).lower()
    assert "father" in joined or "mother" in joined


# 14. Personal history
def test_personal_history():
    answer = "I smoke 5 cigarettes daily and I sleep late"
    p = _extract(answer, field="personal_history",
                 question="Tell me about your food, sleep, smoking and alcohol.")
    assert p.personal_history is not None
    _assert_no_hallucination(p, answer)


# 15. Multiple symptoms in one answer
def test_multiple_symptoms_one_answer():
    answer = "since two days I have fever cough and body pain and I cannot eat"
    p = _extract(answer)
    assert p.chief_complaint is not None
    assert len(p.associated_symptoms) >= 1


# 16. Ambiguous information
def test_ambiguous_answer():
    p = _extract("maybe something is wrong I don't know")
    data = p.model_dump()
    filled = [k for k, v in data.items() if v not in (None, [])]
    assert len(filled) <= 1, f"ambiguous answer should extract almost nothing: {filled}"


# 17. Very short answer
def test_very_short_answer():
    p = _extract("fever", field="chief_complaint",
                 question="What health problem brought you to the hospital today?")
    assert p.chief_complaint and "fever" in p.chief_complaint.lower()
    assert p.onset is None and p.duration is None


# 18. Long answer
def test_long_answer():
    answer = ("since last week I am getting pain in my chest mostly when I climb stairs "
              "it becomes better when I sit down and it also goes to my left hand "
              "I also feel breathless sometimes")
    p = _extract(answer)
    assert p.chief_complaint is not None
    _assert_no_hallucination(p, answer)


# Previous history must not be copied into the current turn
def test_previous_history_not_copied():
    history = {"chief_complaint": "head pain", "onset": "yesterday",
               "severity": "severe", "medications": ["Dolo"]}
    p = _extract("no", field="allergies", question="Any allergies?", history=history)
    assert p.chief_complaint is None
    assert p.medications == []


# Full spec example
def test_spec_example():
    answer = "my head is paining a lot from yesterday and I am not able to sleep"
    p = _extract(answer)
    assert p.chief_complaint is not None
    assert p.onset and "yesterday" in p.onset.lower()
    assert p.duration is None
    assert p.severity is None
    assert len(p.associated_symptoms) >= 1

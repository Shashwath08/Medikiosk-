"""
Adaptive question engine for MediKiosk - Member 2.

Keeps track of:
  * current section
  * current question
  * answered fields
  * questions already asked (so a genuine "no" is never re-asked)

Never asks for information the patient has already given.
Sections are registered, not hardcoded into the flow, so AYUSH modules
(Trividha / Ashtavidha / Dashavidha Pariksha, Prakriti, Agni, Nidana ...)
can be plugged in later without touching this file's logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Callable, Dict, List, Optional

from .clinical_schema import LIST_FIELDS, ClinicalHistory

SkipRule = Callable[[ClinicalHistory], bool]


@dataclass
class Question:
    id: str
    field: str
    text: str
    section_id: str = ""
    section_title: str = ""
    skip_if: Optional[SkipRule] = None
    # Optional per-question hint shown on the kiosk screen.
    hint: str = ""

    @property
    def is_list_field(self) -> bool:
        return self.field in LIST_FIELDS


@dataclass
class Section:
    id: str
    title: str
    questions: List[Question] = dc_field(default_factory=list)
    # e.g. AYUSH sections can be enabled only for AYUSH OPDs
    enabled: bool = True


def _has_complaint(h: ClinicalHistory) -> bool:
    return h.chief_complaint is not None


def _no_complaint(h: ClinicalHistory) -> bool:
    """HPI detail questions make no sense before a chief complaint exists."""
    return not _has_complaint(h)


# An onset like "2 days ago" / "yesterday" already tells us how long it has
# lasted. Asking duration again just annoys the patient. We skip the QUESTION;
# we do NOT copy the value into `duration` - that would be inventing data.
_RELATIVE_TIME = re.compile(
    r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|few|couple|several)\b"
    r"[^.]{0,15}\b(second|minute|hour|day|week|month|year)s?\b"
    r"|\b(yesterday|today|last night|this morning|since morning|since evening|"
    r"last week|last month)\b",
    re.IGNORECASE,
)


def _skip_duration(h: ClinicalHistory) -> bool:
    if _no_complaint(h):
        return True
    return bool(h.onset and _RELATIVE_TIME.search(h.onset))


# --------------------------------------------------------------------------
# Default (allopathic / general OPD) sections
# --------------------------------------------------------------------------

def build_default_sections() -> List[Section]:
    return [
        Section("chief_complaint", "Chief Complaint", [
            Question(
                "cc_main", "chief_complaint",
                "What health problem brought you to the hospital today?",
                hint="Aap apni problem simple words me bata sakte hain.",
            ),
        ]),
        Section("hpi", "History of Present Illness", [
            Question("hpi_onset", "onset",
                     "When did this problem start?", skip_if=_no_complaint),
            Question("hpi_duration", "duration",
                     "For how long have you been having this problem?",
                     skip_if=_skip_duration),
            Question("hpi_location", "location",
                     "Where exactly do you feel it?", skip_if=_no_complaint),
            Question("hpi_character", "character",
                     "How does it feel? For example pain, burning, heaviness or pulling.",
                     skip_if=_no_complaint),
            Question("hpi_severity", "severity",
                     "How bad is it? Mild, moderate or severe?", skip_if=_no_complaint),
            Question("hpi_radiation", "radiation",
                     "Does it spread to any other part of your body?",
                     skip_if=_no_complaint),
            Question("hpi_aggravating", "aggravating_factors",
                     "Is there anything that makes it worse?", skip_if=_no_complaint),
            Question("hpi_relieving", "relieving_factors",
                     "Is there anything that gives you relief?", skip_if=_no_complaint),
            Question("hpi_associated", "associated_symptoms",
                     "Are you having any other problem along with this?",
                     skip_if=_no_complaint),
        ]),
        Section("pmh", "Past Medical History", [
            Question("pmh_main", "past_medical_history",
                     "Do you have any old or ongoing illness, like sugar, BP, asthma or anything else?"),
        ]),
        Section("psh", "Past Surgical History", [
            Question("psh_main", "past_surgical_history",
                     "Have you had any operation or surgery before?"),
        ]),
        Section("meds", "Medications", [
            Question("meds_main", "medications",
                     "Are you taking any medicines regularly?",
                     hint="Agar naam yaad nahi hai to bas itna bataiye kis cheez ki dawa hai."),
        ]),
        Section("allergy", "Allergies", [
            Question("allergy_main", "allergies",
                     "Are you allergic to any medicine or food?"),
        ]),
        Section("family", "Family History", [
            Question("family_main", "family_history",
                     "Does anyone in your family have any illness?"),
        ]),
        Section("personal", "Personal History", [
            Question("personal_main", "personal_history",
                     "Please tell me about your food habits, sleep, and whether you smoke or drink alcohol."),
        ]),
        Section("ros", "Review of Systems", [
            Question("ros_main", "review_of_systems",
                     "Are you facing any other problem such as fever, cough, vomiting, or trouble in passing urine or stool?"),
        ]),
    ]


# --------------------------------------------------------------------------
# Registry (AYUSH-ready)
# --------------------------------------------------------------------------

_EXTRA_SECTIONS: List[Section] = []


def register_section(section: Section, after: Optional[str] = None) -> None:
    """
    Plug in an additional section at runtime.

    Example (Member later, AYUSH):
        register_section(Section("trividha", "Trividha Pariksha", [...]), after="hpi")
    """
    section.__dict__["_after"] = after
    _EXTRA_SECTIONS.append(section)


def clear_registered_sections() -> None:
    _EXTRA_SECTIONS.clear()


def build_sections() -> List[Section]:
    sections = build_default_sections()
    for extra in _EXTRA_SECTIONS:
        after = extra.__dict__.get("_after")
        if after:
            idx = next((i for i, s in enumerate(sections) if s.id == after), None)
            if idx is not None:
                sections.insert(idx + 1, extra)
                continue
        sections.append(extra)
    return [s for s in sections if s.enabled]


# --------------------------------------------------------------------------
# Negation detection (structural only - no disease list)
# --------------------------------------------------------------------------

_NEGATIVE = re.compile(
    r"^\s*(no|nope|nahi|nothing|none|nil|not any|no problem|no sir|no madam|"
    r"i don'?t have any|dont have|no i don'?t|nahi hai|kuch nahi)\b[\s.,!]*$",
    re.IGNORECASE,
)


def is_explicit_denial(text: str) -> bool:
    """True for short, clearly negative answers like 'no', 'nothing', 'nahi'."""
    return bool(_NEGATIVE.match((text or "").strip()))


_AFFIRMATIVE = re.compile(
    r"^\s*(yes|yeah|yep|yup|ya|haan|ha|hmm|ok|okay|sure|correct|true|"
    r"yes sir|yes madam|theek hai|i have|yes i have|i do|yes i do|"
    r"there is|it is there)\b[\s.,!]*$",
    re.IGNORECASE,
)


def is_bare_affirmation(text: str) -> bool:
    """
    True for answers like "yes" / "haan" / "yes I have" that confirm something
    without saying WHAT. These must trigger a follow-up, never an extraction -
    "yes" is not a symptom, a medicine or an allergy.
    """
    return bool(_AFFIRMATIVE.match((text or "").strip()))


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------


class QuestionEngine:
    def __init__(
        self,
        history: Optional[ClinicalHistory] = None,
        sections: Optional[List[Section]] = None,
    ) -> None:
        self.history: ClinicalHistory = history or ClinicalHistory()
        self.sections: List[Section] = sections or build_sections()
        self.asked: List[str] = []
        self.denied_fields: List[str] = []
        self.current_question: Optional[Question] = None
        self.current_section_id: Optional[str] = None

    # ------------------------------------------------------------------ state
    def all_questions(self) -> List[Question]:
        out: List[Question] = []
        for section in self.sections:
            for q in section.questions:
                q.section_id = section.id
                q.section_title = section.title
                out.append(q)
        return out

    def _should_skip(self, q: Question) -> bool:
        if q.id in self.asked:
            return True
        if self.history.is_field_answered(q.field):
            return True          # patient already gave this - never re-ask
        if q.field in self.denied_fields:
            return True
        if q.skip_if and q.skip_if(self.history):
            return True
        return False

    def next_question(self) -> Optional[Question]:
        for q in self.all_questions():
            if not self._should_skip(q):
                self.current_question = q
                self.current_section_id = q.section_id
                return q
        self.current_question = None
        return None

    def is_complete(self) -> bool:
        return self.next_question() is None

    def mark_asked(self, question: Question) -> None:
        if question.id not in self.asked:
            self.asked.append(question.id)

    def mark_denied(self, question: Question) -> None:
        """Patient explicitly said 'no' - keep the field empty but do not re-ask."""
        if question.field not in self.denied_fields:
            self.denied_fields.append(question.field)

    def apply_partial(self, partial, overwrite_strings: bool = False) -> None:
        from .clinical_schema import merge_history

        self.history = merge_history(self.history, partial, overwrite_strings)

    def progress(self) -> Dict[str, int]:
        """
        Progress over questions that are actually in play.

        A question skipped by a condition (HPI details before a chief complaint
        exists) is neither done nor pending - it is not counted at all, so the
        total grows as the interview opens up. Counting those as "answered" made
        the very first question read 9/17.
        """
        done = pending = 0
        for q in self.all_questions():
            answered = (
                q.id in self.asked
                or self.history.is_field_answered(q.field)
                or q.field in self.denied_fields
            )
            if answered:
                done += 1
            elif q.skip_if and q.skip_if(self.history):
                continue          # not applicable right now
            else:
                pending += 1
        total = done + pending
        return {"answered": done, "total": total,
                "percent": int(done * 100 / total) if total else 0}

    def state(self) -> Dict[str, object]:
        return {
            "current_section": self.current_section_id,
            "current_question": self.current_question.id if self.current_question else None,
            "answered_fields": self.history.answered_fields(),
            "denied_fields": list(self.denied_fields),
            "asked": list(self.asked),
            "progress": self.progress(),
        }
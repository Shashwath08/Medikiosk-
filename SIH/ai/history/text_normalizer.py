"""
Text normalisation + auto-correction for MediKiosk (Member 2).

Design rules:
  * The ORIGINAL patient text is never destroyed - callers keep both.
  * No disease dictionary. The lexicon below only contains generic English /
    speech-artifact words, never a mapping of symptoms to diagnoses.
  * Corrections are SUGGESTIONS. Nothing medical is silently rewritten.
"""

from __future__ import annotations

import difflib
import re
from typing import Iterable, List, Optional

from pydantic import BaseModel

from ..config import SUPPORT_MATCH_THRESHOLD

# --------------------------------------------------------------------------
# Small, deliberately generic lexicon (NOT a disease list).
# Used only for fuzzy correction of everyday words that STT/typing mangle.
# --------------------------------------------------------------------------

COMMON_LEXICON: set[str] = {
    # time
    "yesterday", "today", "tomorrow", "morning", "afternoon", "evening",
    "night", "day", "days", "week", "weeks", "month", "months", "year",
    "years", "hour", "hours", "minute", "minutes", "since", "from", "ago",
    "last", "past", "before", "after", "sometimes", "always", "often",
    # body / generic descriptors patients use constantly (generic, not diagnostic)
    "head", "chest", "stomach", "abdomen", "back", "leg", "legs", "hand",
    "hands", "arm", "arms", "throat", "eye", "eyes", "ear", "ears", "neck",
    "knee", "shoulder", "body", "skin", "nose", "mouth", "tooth", "teeth",
    "pain", "paining", "pains", "painful", "ache", "aching", "burning",
    "heavy", "heaviness", "swelling", "swollen", "tight", "pulling",
    "severe", "mild", "moderate", "slight", "little", "lot", "very", "much",
    "left", "right", "upper", "lower", "side", "front", "middle",
    "fever", "cough", "cold", "vomiting", "loose", "motion", "weakness",
    "tired", "sleep", "sleeping", "appetite", "breath", "breathing",
    # interview vocabulary
    "medicine", "medicines", "tablet", "tablets", "tablets", "capsule",
    "injection", "syrup", "doctor", "hospital", "surgery", "operation",
    "allergy", "allergic", "mother", "father", "brother", "sister",
    "family", "smoking", "smoke", "alcohol", "drinking", "tobacco",
    "remember", "name", "problem", "started", "start", "feeling", "feel",
    "taking", "take", "having", "have", "getting", "not", "able", "unable",
    "increases", "increase", "decreases", "decrease", "better", "worse",
}

# Speech-to-text / keyboard artifacts that carry zero clinical meaning.
FILLER_TOKENS: set[str] = {
    "uh", "uhh", "um", "umm", "hmm", "hmmm", "ah", "aa", "aah", "err",
    "erm", "mmm", "like", "you know", "actually",
}

_WS = re.compile(r"\s+")
_PUNCT_SPACE = re.compile(r"\s+([,.;:!?])")
_MULTI_PUNCT = re.compile(r"([,.;:!?])\1+")
_NON_TEXT = re.compile(r"[^\w\s,.;:!?'\-/%]")
_TOKEN = re.compile(r"[a-zA-Z]+")

STOPWORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "been", "i",
    "my", "me", "mine", "of", "in", "on", "at", "to", "for", "and", "or",
    "it", "its", "this", "that", "there", "here", "he", "she", "they",
    "we", "you", "your", "so", "do", "does", "did", "has", "have", "had",
    "will", "would", "can", "could", "some", "any", "as", "with", "but",
}


# Grammar glue that the model legitimately rephrases ("dont remember" ->
# "not remembered"). Ignored during support checking; they carry no clinical fact
# on their own, so they can never smuggle in invented information.
IGNORED_IN_SUPPORT = {
    "not", "non", "dont", "doesnt", "didnt", "cannot", "cant", "isnt", "wasnt",
    "never", "also", "then", "than", "and", "but", "per", "about", "around",
    "patient", "reported", "stated", "says", "said", "remembered", "known",
}


class CorrectionSuggestion(BaseModel):
    """UI contract for the 'Did you mean ...' step."""

    original: str
    corrected: str
    changed: bool
    changes: List[str] = []
    source: str = "rules"  # "rules" | "llm" | "rules+llm"


# --------------------------------------------------------------------------
# Core normalisation
# --------------------------------------------------------------------------


def _collapse_repeated_words(text: str) -> str:
    """'paining paining paining' -> 'paining'"""
    out: List[str] = []
    for word in text.split():
        if out and word.lower().strip(".,;:!?") == out[-1].lower().strip(".,;:!?"):
            continue
        out.append(word)
    return " ".join(out)


def _collapse_repeated_phrases(text: str, max_len: int = 5) -> str:
    """'my head is paining my head is paining' -> 'my head is paining'"""
    words = text.split()
    n = len(words)
    for size in range(max_len, 1, -1):
        i = 0
        cleaned: List[str] = []
        while i < n:
            window = [w.lower() for w in words[i:i + size]]
            nxt = [w.lower() for w in words[i + size:i + 2 * size]]
            if len(window) == size and window == nxt:
                cleaned.extend(words[i:i + size])
                i += 2 * size
                while [w.lower() for w in words[i:i + size]] == window:
                    i += size
            else:
                cleaned.append(words[i])
                i += 1
        words = cleaned
        n = len(words)
    return " ".join(words)


def _strip_fillers(text: str) -> str:
    kept = [w for w in text.split() if w.lower().strip(".,;:!?") not in FILLER_TOKENS]
    return " ".join(kept) if kept else text


def _fix_punctuation(text: str) -> str:
    text = _NON_TEXT.sub(" ", text)
    text = _MULTI_PUNCT.sub(r"\1", text)
    text = _PUNCT_SPACE.sub(r"\1", text)
    text = _WS.sub(" ", text).strip()
    return text


def _sentence_case(text: str) -> str:
    if not text:
        return text
    text = text[0].upper() + text[1:]
    return re.sub(r"\bi\b", "I", text)


def normalise_text(text: str) -> str:
    """
    Deterministic cleanup only. Never changes clinical meaning.
    (US spelling alias `normalize_text` is provided below.)
    """
    if not text or not text.strip():
        return ""
    cleaned = _fix_punctuation(text.strip())
    cleaned = _strip_fillers(cleaned)
    cleaned = _collapse_repeated_words(cleaned)
    cleaned = _collapse_repeated_phrases(cleaned)
    cleaned = _WS.sub(" ", cleaned).strip()
    return _sentence_case(cleaned)


# US-spelling alias so either import works.
normalize_text = normalise_text


# --------------------------------------------------------------------------
# Auto-correction (suggestion only)
# --------------------------------------------------------------------------


def _rule_correct(text: str) -> tuple[str, List[str]]:
    """
    Fuzzy-correct only tokens that are clearly close to a generic lexicon word.
    Unknown words (possible drug names, local terms, rare diseases) are LEFT ALONE.
    """
    changes: List[str] = []
    out_tokens: List[str] = []

    for raw in text.split():
        prefix = ""
        suffix = ""
        core = raw
        while core and not core[0].isalnum():
            prefix += core[0]
            core = core[1:]
        while core and not core[-1].isalnum():
            suffix = core[-1] + suffix
            core = core[:-1]

        low = core.lower()
        if (
            len(low) >= 4
            and low.isalpha()
            and low not in COMMON_LEXICON
            and low not in STOPWORDS
        ):
            match = difflib.get_close_matches(low, COMMON_LEXICON, n=1, cutoff=0.82)
            if match and match[0] != low:
                changes.append(f"{core} -> {match[0]}")
                core = match[0] if core.islower() else match[0].capitalize()

        out_tokens.append(prefix + core + suffix)

    return " ".join(out_tokens), changes


def suggest_correction(
    text: str,
    use_llm: Optional[bool] = None,
) -> CorrectionSuggestion:
    """
    Produce a 'Did you mean ...' suggestion for typed or transcribed input.

    The caller MUST show this to the patient with [Use correction] / [Keep original].
    Nothing here mutates the stored history.
    """
    original = text.strip()
    normalised = normalise_text(original)
    corrected, changes = _rule_correct(normalised)
    source = "rules"

    from ..config import ENABLE_LLM_CORRECTION

    if use_llm is None:
        use_llm = ENABLE_LLM_CORRECTION

    if use_llm:
        try:
            from .history_extractor import llm_correct_spelling  # lazy: avoids cycles

            llm_out = llm_correct_spelling(corrected)
            if llm_out and llm_out.strip() and llm_out.strip().lower() != corrected.lower():
                if _safe_correction(corrected, llm_out):
                    changes.append("llm spelling pass")
                    corrected = llm_out.strip()
                    source = "rules+llm"
        except Exception:
            # Ollama unavailable -> silently fall back to rules. Never block the kiosk.
            pass

    corrected = _sentence_case(_WS.sub(" ", corrected).strip())
    return CorrectionSuggestion(
        original=original,
        corrected=corrected,
        changed=corrected.strip().lower() != original.strip().lower(),
        changes=changes,
        source=source,
    )


def _safe_correction(before: str, after: str) -> bool:
    """Reject LLM 'corrections' that rewrite/expand the answer instead of fixing spelling."""
    b, a = before.split(), after.split()
    if not a:
        return False
    if abs(len(a) - len(b)) > max(2, len(b) * 0.3):
        return False
    ratio = difflib.SequenceMatcher(None, before.lower(), after.lower()).ratio()
    return ratio >= 0.6


# --------------------------------------------------------------------------
# Support matching (anti-hallucination guard used by the extractor)
# --------------------------------------------------------------------------


def tokenise(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


def _token_supported(token: str, haystack: Iterable[str]) -> bool:
    if token in STOPWORDS or len(token) <= 2:
        return True
    for word in haystack:
        if token == word:
            return True
        if len(token) >= 4 and (token.startswith(word[:4]) or word.startswith(token[:4])):
            if difflib.SequenceMatcher(None, token, word).ratio() >= 0.66:
                return True
        if difflib.SequenceMatcher(None, token, word).ratio() >= SUPPORT_MATCH_THRESHOLD:
            return True
    return False


def is_supported_by_text(value: str, *sources: str) -> bool:
    """
    True if the meaningful words of `value` trace back to something the patient
    actually said (allowing for spelling and inflection differences).

    "head pain"                      vs "my head is paining"        -> True
    "unable to sleep"                vs "i am not able to sleep"    -> True
    "a tablet for BP, name not remembered"
                                     vs "i take some tablet for BP
                                         but i dont remember the name" -> True
    "severe"                         vs "my head is paining"        -> False
    "a lof"                          vs "head paining a lot"        -> False
    """
    if not value:
        return False
    haystack: List[str] = []
    for src in sources:
        haystack.extend(tokenise(src))
    if not haystack:
        return False

    content = [
        t for t in tokenise(value)
        if t not in STOPWORDS and t not in IGNORED_IN_SUPPORT and len(t) > 2
    ]
    if not content:
        # Value carries no content word of its own - nothing to verify, reject.
        return False

    supported = sum(1 for t in content if _token_supported(t, haystack))
    if supported == len(content):
        return True
    # Longer descriptive phrases may contain one connecting word that the
    # patient phrased differently; still require the clear majority to match.
    return len(content) >= 3 and (supported / len(content)) >= 0.7

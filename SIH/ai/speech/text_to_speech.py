"""
Local Text-to-Speech for MediKiosk (Member 2).

Primary engine : pyttsx3 (fully offline, uses OS voices - SAPI5 / NSSpeech / espeak)
Optional engine: any future offline multilingual engine can be plugged in by
                 implementing the same three methods. Language is a parameter
                 everywhere, never hardcoded into the app flow.
"""

from __future__ import annotations

import gc
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

from ..config import DEFAULT_LANGUAGE, TTS_ENABLED, TTS_MODE, TTS_RATE, TTS_VOLUME


class TTSEngine:
    """Thin wrapper so the rest of the app never touches pyttsx3 directly."""

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        rate: int = TTS_RATE,
        volume: float = TTS_VOLUME,
        fresh_per_call: Optional[bool] = None,
    ) -> None:
        self.language = language
        self.rate = rate
        self.volume = volume
        # pyttsx3 + SAPI5 (Windows) stops responding after the first
        # runAndWait() on a reused engine, so build a fresh one per utterance.
        self.fresh_per_call = (
            sys.platform == "win32" if fresh_per_call is None else fresh_per_call
        )
        self.mode = TTS_MODE
        self._engine = None
        self._voice_id: Optional[str] = None
        self.available = False
        self._init_engine()
        if self.mode == "subprocess":
            self.available = True

    def _release_engine(self) -> None:
        """
        pyttsx3.init() returns a CACHED engine while any reference to the old one
        is still alive, so a "new" engine is often the same dead object. Drop the
        reference and force collection before asking for another.
        """
        engine, self._engine = self._engine, None
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass
        del engine
        gc.collect()

    def _build_engine(self):
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)
        if self._voice_id:
            try:
                engine.setProperty("voice", self._voice_id)
            except Exception:
                pass
        return engine

    def _init_engine(self) -> None:
        try:
            self._engine = self._build_engine()
            self.select_voice(self.language)
            self.available = True
            if self.fresh_per_call:
                # Keep the chosen voice id, but hold no live engine reference.
                self._release_engine()
        except Exception:
            self._engine = None
            self.available = False

    # ------------------------------------------------------------- voices
    def list_voices(self) -> List[Dict[str, Any]]:
        if not self._engine:
            return []
        out = []
        for v in self._engine.getProperty("voices"):
            out.append({
                "id": v.id,
                "name": getattr(v, "name", ""),
                "languages": [
                    l.decode(errors="ignore") if isinstance(l, bytes) else str(l)
                    for l in getattr(v, "languages", []) or []
                ],
            })
        return out

    def select_voice(self, language: str) -> bool:
        """
        Pick the best installed voice for a language code ('en', 'hi', 'kn', ...).
        Returns False if no matching voice exists - caller can still speak in default.
        """
        if not self._engine:
            return False
        self.language = language
        lang = language.lower()
        for voice in self.list_voices():
            blob = f"{voice['name']} {' '.join(voice['languages'])} {voice['id']}".lower()
            if lang in blob or (lang == "hi" and "hindi" in blob) or (
                lang == "en" and ("english" in blob or "en_" in blob or "en-" in blob)
            ):
                try:
                    self._engine.setProperty("voice", voice["id"])
                    self._voice_id = voice["id"]
                    return True
                except Exception:
                    return False
        return False

    def set_rate(self, rate: int) -> None:
        self.rate = rate
        if self._engine:
            self._engine.setProperty("rate", rate)

    def _speak_subprocess(self, text: str) -> bool:
        """
        Bulletproof fallback: one short-lived Python process per sentence.
        Slower (~1s startup) but immune to every pyttsx3 engine-reuse problem.
        """
        voice = self._voice_id or ""
        code = (
            "import sys,pyttsx3;"
            "e=pyttsx3.init();"
            f"e.setProperty('rate',{self.rate});"
            f"e.setProperty('volume',{self.volume});"
            f"v={voice!r};"
            "e.setProperty('voice',v) if v else None;"
            "e.say(sys.argv[1]);e.runAndWait()"
        )
        try:
            done = subprocess.run(
                [sys.executable, "-c", code, text],
                timeout=60,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return done.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------- speaking
    def speak(self, text: str) -> bool:
        """
        Blocking speak. Returns False if TTS is unavailable (kiosk still works).

        A fresh engine is used per call on Windows; elsewhere the shared engine
        is reused and rebuilt automatically if its run loop has already ended.
        """
        if not text or not text.strip():
            return False
        if not self.available:
            return False

        if self.mode == "subprocess":
            return self._speak_subprocess(text)

        if self.fresh_per_call:
            try:
                self._release_engine()          # ensure init() cannot hand back a stale engine
                engine = self._build_engine()
                engine.say(text)
                engine.runAndWait()
                try:
                    engine.stop()
                except Exception:
                    pass
                del engine
                gc.collect()
                return True
            except Exception:
                return False

        for attempt in (1, 2):
            try:
                if self._engine is None:
                    self._engine = self._build_engine()
                self._engine.say(text)
                self._engine.runAndWait()
                return True
            except RuntimeError:
                # "run loop already started" - drop the engine and retry once
                try:
                    self._engine.endLoop()
                except Exception:
                    pass
                self._engine = None
                if attempt == 2:
                    return False
            except Exception:
                return False
        return False

    def to_file(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """Render speech to a WAV file (useful when the frontend plays the audio)."""
        if not self.available or not text.strip():
            return None
        if output_path is None:
            fd, output_path = tempfile.mkstemp(prefix="medikiosk_tts_", suffix=".wav")
            os.close(fd)
        try:
            engine = self._build_engine() if self.fresh_per_call else self._engine
            if engine is None:
                engine = self._build_engine()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return output_path if os.path.exists(output_path) else None
        except Exception:
            return None


_engine: Optional[TTSEngine] = None


def get_engine(language: str = DEFAULT_LANGUAGE) -> TTSEngine:
    global _engine
    if _engine is None:
        _engine = TTSEngine(language=language)
    elif language != _engine.language:
        _engine.select_voice(language)
    return _engine


# --------------------------------------------------------------------------
# Public functions (backend contract)
# --------------------------------------------------------------------------


def speak(text: str, language: str = DEFAULT_LANGUAGE) -> bool:
    if not TTS_ENABLED:
        return False
    return get_engine(language).speak(text)


def generate_speech(
    text: str,
    output_path: Optional[str] = None,
    language: str = DEFAULT_LANGUAGE,
) -> Optional[str]:
    """Return a path to a rendered WAV file, or None if TTS is unavailable."""
    return get_engine(language).to_file(text, output_path)


def tts_status() -> Dict[str, Any]:
    engine = get_engine()
    return {
        "available": engine.available,
        "language": engine.language,
        "voices": [v["name"] for v in engine.list_voices()],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(tts_status(), indent=4))
    # Three separate calls - all three must be audible. If only the first is
    # heard, the engine is being reused when it should be rebuilt.
    print(f"mode: {get_engine().mode}, "
          f"fresh_per_call: {get_engine().fresh_per_call}")
    for line in (
        "What health problem brought you to the hospital today?",
        "When did this problem start?",
        "Are you taking any medicines regularly?",
    ):
        print(f"speaking: {line}  ->  {speak(line)}")
    print("\nAll three should have been audible. If only the first was, run:")
    print('  $env:MEDIKIOSK_TTS_MODE="subprocess"   then try this again')
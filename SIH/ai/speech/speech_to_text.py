"""
Local Speech-to-Text for MediKiosk (Member 2) - Faster-Whisper, CPU, int8.

Nothing leaves the machine. Audio is written to a temp file and deleted
immediately after transcription unless KEEP_AUDIO_FILES is enabled.
"""

from __future__ import annotations

import os
import tempfile
import time
import wave
from typing import Any, Dict, Optional

from ..config import (
    CHANNELS,
    KEEP_AUDIO_FILES,
    MAX_RECORD_SECONDS,
    SAMPLE_RATE,
    STT_COMPUTE_TYPE,
    STT_DEVICE,
    STT_LANGUAGE,
    STT_MODEL_SIZE,
)

class RecordingTooShort(RuntimeError):
    """Raised when the mic produced (almost) no audio - a real, reportable error."""


MIN_RECORD_SECONDS = 0.4


def _drain_stdin() -> None:
    """Discard buffered keypresses so a stray Enter does not end the recording."""
    try:
        import msvcrt  # Windows
        while msvcrt.kbhit():
            msvcrt.getch()
        return
    except ImportError:
        pass
    try:
        import sys
        import termios  # POSIX
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def list_input_devices():
    """Diagnostic helper: which microphones does the OS expose?"""
    try:
        import sounddevice as sd
    except Exception as exc:
        return {"available": False, "error": str(exc), "devices": []}
    try:
        devices = [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0
        ]
        default = sd.default.device[0] if sd.default.device else None
        return {"available": bool(devices), "default_input": default,
                "devices": devices, "error": None}
    except Exception as exc:
        return {"available": False, "error": str(exc), "devices": []}


_model = None


def get_model():
    """Lazy singleton - loading Whisper takes a few seconds, do it once."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # imported lazily on purpose

        _model = WhisperModel(
            STT_MODEL_SIZE,
            device=STT_DEVICE,
            compute_type=STT_COMPUTE_TYPE,
        )
    return _model


def preload() -> bool:
    """Call at kiosk startup so the first patient does not wait."""
    try:
        get_model()
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Recording
# --------------------------------------------------------------------------


def record_audio(
    max_seconds: int = MAX_RECORD_SECONDS,
    output_path: Optional[str] = None,
    countdown: bool = True,
) -> str:
    """
    Record from the default microphone until Enter is pressed or max_seconds.
    Returns the path of a 16 kHz mono WAV file.
    """
    import queue
    import threading

    import sounddevice as sd

    if output_path is None:
        fd, output_path = tempfile.mkstemp(prefix="medikiosk_", suffix=".wav")
        os.close(fd)

    _drain_stdin()          # stray Enter must not stop the recording instantly

    frames: "queue.Queue[bytes]" = queue.Queue()
    stop = threading.Event()

    def _callback(indata, _frames, _time, status):  # noqa: ANN001
        if status:
            pass  # dropped frames - not fatal for speech
        frames.put(bytes(indata))

    def _wait_for_enter():
        try:
            input()
        except EOFError:
            pass
        stop.set()

    if countdown:
        print("Recording... speak now, then press Enter to stop.")
    threading.Thread(target=_wait_for_enter, daemon=True).start()

    started = time.time()
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=1024,
        dtype="int16",
        channels=CHANNELS,
        callback=_callback,
    ):
        while not stop.is_set() and (time.time() - started) < max_seconds:
            time.sleep(0.05)

    written = 0
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        while not frames.empty():
            chunk = frames.get()
            written += len(chunk)
            wf.writeframes(chunk)

    seconds = written / (SAMPLE_RATE * 2 * CHANNELS)
    if seconds < MIN_RECORD_SECONDS:
        raise RecordingTooShort(
            f"only {seconds:.2f}s of audio captured - the recording stopped before "
            "you finished speaking, or the microphone returned no data"
        )

    return output_path


# --------------------------------------------------------------------------
# Transcription
# --------------------------------------------------------------------------


def speech_to_text(
    audio_file: str,
    language: Optional[str] = STT_LANGUAGE,
) -> Dict[str, Any]:
    """
    Transcribe an existing audio file.

    Returns: {"success": bool, "text": str, "language": str,
              "confidence": float|None, "error": str|None}
    """
    if not audio_file or not os.path.exists(audio_file):
        return {"success": False, "text": "", "language": language,
                "confidence": None, "error": "audio file not found"}

    try:
        model = get_model()
        segments, info = model.transcribe(
            audio_file,
            language=language,
            beam_size=5,
            vad_filter=True,                       # handles pauses
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,      # stops Whisper inventing continuations
            temperature=0.0,
        )
        parts, logprobs = [], []
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                parts.append(text)
                logprobs.append(getattr(seg, "avg_logprob", None))

        text = " ".join(parts).strip()
        valid = [lp for lp in logprobs if lp is not None]
        confidence = round(float(sum(valid) / len(valid)), 3) if valid else None

        return {
            "success": bool(text),
            "text": text,
            "language": getattr(info, "language", language),
            "confidence": confidence,
            "error": None if text else "no speech detected",
        }
    except Exception as exc:
        return {"success": False, "text": "", "language": language,
                "confidence": None, "error": f"transcription failed: {exc}"}


def listen_and_transcribe(
    max_seconds: int = MAX_RECORD_SECONDS,
    language: Optional[str] = STT_LANGUAGE,
) -> Dict[str, Any]:
    """Record from the mic, transcribe, then delete the temp audio."""
    path = None
    try:
        path = record_audio(max_seconds=max_seconds)
        result = speech_to_text(path, language=language)
        result["audio_path"] = path if KEEP_AUDIO_FILES else None
        return result
    except RecordingTooShort as exc:
        return {"success": False, "text": "", "language": language,
                "confidence": None, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "text": "", "language": language,
                "confidence": None,
                "error": f"recording failed ({type(exc).__name__}): {exc}"}
    finally:
        if path and not KEEP_AUDIO_FILES and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def build_confirmation_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Contract for the kiosk screen (Section 15 of the spec):
        "You said: <text>"   [Confirm] [Speak again] [Type correction]
    """
    return {
        "prompt": "You said:",
        "transcription": result.get("text", ""),
        "confidence": result.get("confidence"),
        "low_confidence": (result.get("confidence") is not None
                           and result["confidence"] < -1.0),
        "actions": ["confirm", "speak_again", "type_correction"],
        "success": result.get("success", False),
        "error": result.get("error"),
    }


if __name__ == "__main__":
    import json

    print("--- microphones ---")
    print(json.dumps(list_input_devices(), indent=4))
    print("\n--- whisper model ---")
    print("loading (first run downloads ~460 MB)...")
    print("loaded" if preload() else "FAILED to load - is faster-whisper installed?")
    print("\n--- recording test ---")
    print(json.dumps(build_confirmation_payload(listen_and_transcribe()), indent=4))
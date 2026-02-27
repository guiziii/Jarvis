#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS - Wake word voice assistant for OpenClaw (macOS)
Says "Jarvis" → records → transcribes → routes → OpenClaw (tools) → speaks.

Run:
  python3 jarvis.py

Optional run as script:
  chmod +x jarvis.py
  ./jarvis.py
"""

from __future__ import annotations

import re
import os
import sys
import json
import time
import math
import wave
import queue as queue_module
import shutil
import signal
import struct
import asyncio
import random
import string
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any, Dict, Tuple

import pvporcupine

try:
    import pyaudio  # type: ignore
except Exception:
    pyaudio = None

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    import sounddevice as sd  # type: ignore
except Exception:
    sd = None

try:
    import torch  # type: ignore
except Exception:
    torch = None

try:
    import whisper  # type: ignore
except Exception:
    whisper = None

# ──────────────────────────────────────────────────────────────────────────────
# Config (ENV)
# ──────────────────────────────────────────────────────────────────────────────

WAKE_WORD = os.environ.get("WAKE_WORD", "jarvis").strip().lower()
WAKE_SENSITIVITY = float(os.environ.get("WAKE_SENSITIVITY", "0.6"))
PICOVOICE_KEY = os.environ.get("PICOVOICE_KEY", "").strip()

SAMPLE_RATE = int(os.environ.get("SAMPLE_RATE", "16000"))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "512"))
INITIAL_WAIT = float(os.environ.get("INITIAL_WAIT", "0.15"))

MAX_RECORD_SECONDS = int(os.environ.get("MAX_RECORD_SECONDS", "20"))
MIN_VOICE_CHUNKS = int(os.environ.get("MIN_VOICE_CHUNKS", "5"))

SILENCE_RMS = float(os.environ.get("SILENCE_RMS", "0.012"))
SILENCE_DURATION = float(os.environ.get("SILENCE_DURATION", "1.0"))

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "auto")  # auto|cpu|cuda
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))

TTS_VOICE = os.environ.get("TTS_VOICE", "").strip()
TTS_RATE = int(os.environ.get("TTS_RATE", "200"))

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "").strip()

OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", "openclaw").strip()

# Logging
JARVIS_LOG_TO_FILE = os.environ.get("JARVIS_LOG_TO_FILE", "0").strip() in ("1", "true", "yes", "on")
JARVIS_LOG_FILE = os.environ.get("JARVIS_LOG_FILE", os.path.expanduser("~/.openclaw/jarvis.log"))
JARVIS_LOG_LEVEL = os.environ.get("JARVIS_LOG_LEVEL", "INFO").strip().upper()
JARVIS_LOG_MAX_BYTES = int(os.environ.get("JARVIS_LOG_MAX_BYTES", "1048576"))
JARVIS_LOG_BACKUPS = int(os.environ.get("JARVIS_LOG_BACKUPS", "3"))

# Session
JARVIS_SESSION_ID = os.environ.get("JARVIS_SESSION_ID", "").strip()

# Cloud lock
CLOUD_LOCK_FILE = os.path.expanduser("~/.openclaw/jarvis_cloud_lock.json")
CLOUD_LOCK_HOURS = int(os.environ.get("CLOUD_LOCK_HOURS", "24"))

# Gemini fallback keys (DO NOT hardcode secrets in the repository)
# Provide keys via environment variable:
#   export GEMINI_FALLBACK_KEYS="key1,key2,key3"
# Or via a file path:
#   export GEMINI_FALLBACK_KEYS_FILE="/path/to/keys.txt"   # one key per line (comments allowed with #)
#
# If no keys are provided, Gemini fallback is disabled.
def _load_gemini_fallback_keys() -> list[str]:
    keys: list[str] = []

    # 1) From a file (preferred for local dev)
    keys_file = os.environ.get("GEMINI_FALLBACK_KEYS_FILE", "").strip()
    if keys_file:
        try:
            with open(os.path.expanduser(keys_file), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    keys.append(line)
        except Exception as e:
            print(f"[WARN] Failed to read GEMINI_FALLBACK_KEYS_FILE: {e}", file=sys.stderr)

    # 2) From env var (comma-separated)
    keys_env = os.environ.get("GEMINI_FALLBACK_KEYS", "").strip()
    if keys_env:
        keys.extend([k.strip() for k in keys_env.split(",") if k.strip()])

    # De-duplicate while preserving order
    seen = set()
    deduped: list[str] = []
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        deduped.append(k)

    return deduped

GEMINI_FALLBACK_KEYS = _load_gemini_fallback_keys()
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")

# Runtime state
_pa_global = None
_whisper_global = None
_model_override = None
_tools_models_cache = []
_current_proc = None
_current_proc_lock = threading.Lock()
_cloud_locked_until: float = 0.0

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _log(level: str, msg: str) -> None:
    # minimal logger (kept as in original behavior)
    ts = _now_utc().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)

    if not JARVIS_LOG_TO_FILE:
        return

    try:
        os.makedirs(os.path.dirname(JARVIS_LOG_FILE), exist_ok=True)
        # naive rotation
        if os.path.exists(JARVIS_LOG_FILE) and os.path.getsize(JARVIS_LOG_FILE) > JARVIS_LOG_MAX_BYTES:
            for i in range(JARVIS_LOG_BACKUPS - 1, 0, -1):
                src = f"{JARVIS_LOG_FILE}.{i}"
                dst = f"{JARVIS_LOG_FILE}.{i+1}"
                if os.path.exists(src):
                    os.replace(src, dst)
            os.replace(JARVIS_LOG_FILE, f"{JARVIS_LOG_FILE}.1")

        with open(JARVIS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # don't crash on logging issues
        pass

def _require(dep: Any, name: str, install_hint: str) -> None:
    if dep is None:
        raise RuntimeError(f"Missing dependency: {name}. Install: {install_hint}")

def _has_picovoice_key() -> bool:
    return bool(PICOVOICE_KEY)

def _cloud_lock_load() -> float:
    try:
        if not os.path.exists(CLOUD_LOCK_FILE):
            return 0.0
        with open(CLOUD_LOCK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return float(data.get("locked_until", 0.0))
    except Exception:
        return 0.0

def _cloud_lock_save(locked_until: float) -> None:
    try:
        os.makedirs(os.path.dirname(CLOUD_LOCK_FILE), exist_ok=True)
        with open(CLOUD_LOCK_FILE, "w", encoding="utf-8") as f:
            json.dump({"locked_until": locked_until}, f)
    except Exception:
        pass

def _cloud_lock_is_active() -> bool:
    global _cloud_locked_until
    if _cloud_locked_until <= 0:
        _cloud_locked_until = _cloud_lock_load()
    return time.time() < _cloud_locked_until

def _cloud_lock_activate(hours: int = CLOUD_LOCK_HOURS) -> None:
    global _cloud_locked_until
    _cloud_locked_until = time.time() + (hours * 3600)
    _cloud_lock_save(_cloud_locked_until)

def _select_whisper_device() -> str:
    if WHISPER_COMPUTE == "cpu":
        return "cpu"
    if WHISPER_COMPUTE == "cuda":
        return "cuda"
    # auto
    if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
        return "cuda"
    return "cpu"

def _load_whisper_model() -> Any:
    global _whisper_global
    if _whisper_global is not None:
        return _whisper_global

    _require(whisper, "openai-whisper", "pip install -U openai-whisper")
    device = _select_whisper_device()
    _log("INFO", f"Loading Whisper model '{WHISPER_MODEL}' on device={device} ...")
    _whisper_global = whisper.load_model(WHISPER_MODEL, device=device)
    return _whisper_global

def _transcribe_wav(path: str) -> str:
    model = _load_whisper_model()
    result = model.transcribe(path, fp16=False)
    text = (result.get("text") or "").strip()
    return text

def _speak(text: str) -> None:
    # macOS default: `say`
    if not text.strip():
        return

    cmd = ["say"]
    if TTS_VOICE:
        cmd += ["-v", TTS_VOICE]
    if TTS_RATE:
        cmd += ["-r", str(TTS_RATE)]
    cmd += [text]

    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        _log("WARN", f"TTS failed: {e}")

def _openclaw_call(prompt: str) -> Tuple[int, str]:
    # Calls OpenClaw CLI tool
    # OpenClaw must be installed and accessible via OPENCLAW_BIN.
    cmd = [OPENCLAW_BIN, prompt]

    env = os.environ.copy()
    if OLLAMA_HOST:
        env["OLLAMA_HOST"] = OLLAMA_HOST

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out.strip()
    except FileNotFoundError:
        return 127, f"OpenClaw binary not found: {OPENCLAW_BIN}"
    except Exception as e:
        return 1, f"OpenClaw call failed: {e}"

# ──────────────────────────────────────────────────────────────────────────────
# Audio
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AudioChunk:
    data: bytes

def _record_until_silence() -> str:
    """
    Records audio from mic until silence or max seconds.
    Writes a temporary WAV file and returns its path.
    """
    _require(pyaudio, "pyaudio", "pip install pyaudio (or use brew/portaudio build)")
    pa = pyaudio.PyAudio()

    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    frames: list[bytes] = []
    voice_chunks = 0
    silence_seconds = 0.0
    start_t = time.time()

    try:
        while True:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)

            # RMS
            rms = _rms_16bit(data)
            if rms >= SILENCE_RMS:
                voice_chunks += 1
                silence_seconds = 0.0
            else:
                silence_seconds += (CHUNK_SIZE / SAMPLE_RATE)

            if time.time() - start_t >= MAX_RECORD_SECONDS:
                break

            # Don't stop too early if user started speaking
            if voice_chunks >= MIN_VOICE_CHUNKS and silence_seconds >= SILENCE_DURATION:
                break

    finally:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        try:
            pa.terminate()
        except Exception:
            pass

    # Write WAV
    fd, wav_path = tempfile.mkstemp(prefix="jarvis_", suffix=".wav")
    os.close(fd)

    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    return wav_path

def _rms_16bit(data: bytes) -> float:
    # data is int16 PCM mono
    if not data:
        return 0.0
    count = len(data) // 2
    if count <= 0:
        return 0.0
    fmt = f"<{count}h"
    samples = struct.unpack(fmt, data)
    ssum = 0.0
    for x in samples:
        ssum += (x * x)
    mean = ssum / count
    return math.sqrt(mean) / 32768.0

# ──────────────────────────────────────────────────────────────────────────────
# Wake word loop
# ──────────────────────────────────────────────────────────────────────────────

def _wake_loop() -> None:
    if not _has_picovoice_key():
        raise RuntimeError(
            "PICOVOICE_KEY is required for wake-word detection.\n"
            "Set it via environment variable: export PICOVOICE_KEY='...'\n"
            "Tip: put it in a local .env and load it in your shell."
        )

    _require(pyaudio, "pyaudio", "pip install pyaudio")
    porcupine = pvporcupine.create(
        access_key=PICOVOICE_KEY,
        keywords=[WAKE_WORD],
        sensitivities=[WAKE_SENSITIVITY],
    )

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length,
    )

    _log("INFO", f"Listening for wake word: '{WAKE_WORD}' ...")

    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm_unpacked)
            if keyword_index >= 0:
                _log("INFO", "Wake word detected!")
                time.sleep(INITIAL_WAIT)
                _handle_interaction()

    finally:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        try:
            pa.terminate()
        except Exception:
            pass
        try:
            porcupine.delete()
        except Exception:
            pass

def _handle_interaction() -> None:
    wav_path = ""
    try:
        wav_path = _record_until_silence()
        _log("INFO", f"Recorded audio: {wav_path}")

        text = _transcribe_wav(wav_path)
        _log("INFO", f"Transcribed: {text}")

        if not text:
            _speak("I didn't catch that.")
            return

        # route to OpenClaw
        rc, out = _openclaw_call(text)
        if rc != 0:
            _log("WARN", f"OpenClaw returned rc={rc}: {out}")
            _speak("Sorry, I had trouble running that.")
            return

        if out:
            _speak(out)
        else:
            _speak("Done.")

    except KeyboardInterrupt:
        raise
    except Exception as e:
        _log("ERROR", f"Interaction failed: {e}")
        _speak("Something went wrong.")
    finally:
        if wav_path:
            try:
                os.remove(wav_path)
            except Exception:
                pass

def main() -> None:
    try:
        _wake_loop()
    except KeyboardInterrupt:
        _log("INFO", "Exiting.")
        return
    except Exception as e:
        _log("ERROR", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()

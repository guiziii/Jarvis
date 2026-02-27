# Jarvis Wake-Word Assistant (OpenClaw)

A wake-word voice assistant for macOS:  
**“Jarvis” → record → transcribe → route to OpenClaw → speak the response**.

---

## ✨ Features

- Wake-word detection via Picovoice Porcupine
- Local microphone recording
- Speech-to-text transcription using Whisper
- Command routing via OpenClaw CLI
- Text-to-speech using macOS `say`
- Environment-based secure configuration
- Optional Gemini fallback (via external keys)

---

## 📦 Requirements

- macOS (for built-in `say`)
- Python 3.10+
- A working microphone
- Picovoice Porcupine access key (required)

---

## 🛠 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install pvporcupine pyaudio openai-whisper
```

### PyAudio on macOS

If installation fails:

```bash
brew install portaudio
pip install pyaudio
```

---

## 🔐 Configuration (Secrets via Environment Variables)

### Required

```bash
export PICOVOICE_KEY="your_picovoice_key_here"
```

---

### Optional Configuration

```bash
export WAKE_WORD="jarvis"
export WAKE_SENSITIVITY="0.6"
export WHISPER_MODEL="base"
export WHISPER_COMPUTE="auto"        # auto | cpu | cuda
export OPENCLAW_BIN="openclaw"
export TTS_VOICE=""                  # macOS voice name
export TTS_RATE="200"
export OLLAMA_HOST=""
```

---

## 🤖 Gemini Fallback (Optional)

Keys must NOT be committed.

### Option 1 — Environment variable

```bash
export GEMINI_FALLBACK_KEYS="key1,key2,key3"
```

### Option 2 — File (recommended)

```bash
export GEMINI_FALLBACK_KEYS_FILE="$HOME/.secrets/gemini_keys.txt"
```

One key per line:

```
# comment allowed
your_key_here
another_key_here
```

Optional:

```bash
export GEMINI_FALLBACK_MODEL="gemini-2.0-flash"
```

---

## 🚀 Running

```bash
python3 jarvis.py
```

Or:

```bash
chmod +x jarvis.py
./jarvis.py
```

---

## 🔒 Security Notes

Never commit:

- `.env`
- `*.local`
- `*keys*.txt`
- Any secret/token file
- `~/.openclaw/`

Suggested `.gitignore` additions:

```gitignore
.env
*.local
*.secrets
*keys*.txt
**/.openclaw/*
```

All credentials must be injected at runtime via environment variables.

---

## 🧠 How It Works

1. Listens continuously for the configured wake word.
2. When detected, records audio until silence.
3. Transcribes audio using Whisper.
4. Sends the transcription to OpenClaw CLI.
5. Speaks the response using macOS TTS.

---

## 🧪 Troubleshooting

### PICOVOICE_KEY is required

Make sure it is set:

```bash
echo $PICOVOICE_KEY
```

If empty, export it again.

---

### PyAudio build errors

```bash
brew install portaudio
pip install --force-reinstall pyaudio
```


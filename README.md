# Voice Typer

Local speech-to-text that works everywhere on your Mac. Hold a hotkey, speak, release — text is instantly pasted into any app. Powered by OpenAI Whisper running 100% on your machine. No internet. No API. Free forever.

## Features

- Works in any app — browser, Notion, VS Code, Slack, anywhere
- Auto-detects language (100+ languages supported)
- macOS menu bar app with last 5 transcriptions history
- VAD filter — ignores silence automatically
- Adjustable model size: tiny (fast) → large-v3 (most accurate)
- CLI mode for terminal use

## Hotkey

| Action | Keys |
|---|---|
| Start recording | Hold `Cmd + Shift + Space` |
| Stop + transcribe | Release `Space` |

## Setup

```bash
cd voice-to-text
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Grant permissions when macOS asks:
- **Microphone** — for recording
- **Accessibility** — for global hotkey (System Settings → Privacy → Accessibility)

## Usage

```bash
# Menu bar app (recommended)
python app.py

# More accurate, slower
python app.py --model medium

# Force English only
python app.py --lang en

# CLI mode (no menu bar)
python cli.py
```

## Models

| Model | Size | Speed | Best for |
|---|---|---|---|
| tiny | 75 MB | instant | quick notes |
| base | 145 MB | very fast | general use |
| small | 465 MB | fast | **recommended** |
| medium | 1.5 GB | moderate | accuracy |
| large-v3 | 3 GB | slow | best quality |

Models download automatically on first use and are cached permanently.

## Requirements

- macOS 12+
- Python 3.10+
- Apple Silicon or Intel Mac

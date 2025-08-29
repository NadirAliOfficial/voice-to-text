# 🎙️ Voice Typer — Free, Local, AI Voice-to-Text for Mac

> Hold **⌃ Ctrl** anywhere on your Mac → speak → release → text is instantly typed into any app. No internet. No subscription. No limits.

[![macOS](https://img.shields.io/badge/macOS-12%2B-black?logo=apple)](https://www.apple.com/macos/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?logo=openai)](https://github.com/openai/whisper)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Stars](https://img.shields.io/github/stars/NadirAliOfficial/voice-to-text?style=social)](https://github.com/NadirAliOfficial/voice-to-text/stargazers)

---

## ✨ What it does

Voice Typer runs **100% locally** on your Mac using OpenAI Whisper. Hold Ctrl, speak naturally, release — your words appear wherever your cursor is. Works in every app: browser, VS Code, Notion, WhatsApp, Slack, Terminal, anything.

No API key. No cloud. No monthly fee. Your voice never leaves your machine.

---

## 🎬 Demo

```
Hold ⌃ Ctrl  →  [🎙 waveform animation appears]  →  release  →  text pastes instantly
```

**Works in:**
- 🌐 Chrome, Safari, Firefox
- 💬 WhatsApp, Telegram, Slack
- 📝 Notion, Obsidian, Notes
- 💻 VS Code, Terminal, Xcode
- 📧 Gmail, Outlook — anywhere

---

## 🚀 Features

| Feature | Detail |
|---|---|
| **Hold-to-record** | Hold ⌃ Ctrl anywhere, release to paste |
| **Real-time waveform** | Voice Memos-style animation reacts to your voice |
| **100+ languages** | Auto-detects English, Urdu, Arabic, French and more |
| **Smart accuracy** | Optimised Whisper params — no more mishearing |
| **Single instance** | Lock file prevents duplicate processes |
| **History** | All transcriptions saved, searchable, exportable |
| **Privacy** | Zero network calls — completely offline after setup |
| **Free forever** | No limits, no subscriptions, no API keys |

---

## ⚡ Quick Start

```bash
git clone https://github.com/NadirAliOfficial/voice-to-text.git
cd voice-to-text
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Grant permissions when macOS asks:**
- **Microphone** — System Settings → Privacy → Microphone
- **Accessibility** — System Settings → Privacy → Accessibility *(for global hotkey)*

That's it. The Whisper model downloads automatically on first run (~500 MB).

---

## 🎛️ Options

```bash
# Default (auto language, small model)
python main.py

# Force English for faster transcription
python main.py --lang en

# Higher accuracy (slower, downloads 1.5 GB)
python main.py --model medium

# Best accuracy (downloads 3 GB)
python main.py --model large-v3
```

| Model | Size | Speed | Best for |
|---|---|---|---|
| `tiny` | 75 MB | ⚡ instant | Quick notes |
| `base` | 145 MB | ⚡ very fast | General use |
| `small` | 465 MB | ✅ fast | **Default** |
| `medium` | 1.5 GB | 🐢 moderate | High accuracy |
| `large-v3` | 3 GB | 🐢 slow | Best quality |

---

## 🏗️ How it works

```
Hold Ctrl
    └─► AudioRecorder (sounddevice, 16kHz)
             └─► faster-whisper (CTranslate2, int8)
                      └─► pynput Cmd+V → paste into active app
```

- **[faster-whisper](https://github.com/guillaumekynast/faster-whisper)** — 4× faster than original Whisper, same accuracy
- **[pynput](https://github.com/moses-palmer/pynput)** — global hotkey listener + keyboard controller
- **[sounddevice](https://python-sounddevice.readthedocs.io/)** — low-latency microphone capture
- **[pyperclip](https://github.com/asweigart/pyperclip)** — cross-app clipboard

---

## 📋 Requirements

- macOS 12 Monterey or later
- Python 3.10+
- Apple Silicon or Intel Mac
- ~1 GB disk space (model cache)

---

## 🤝 Contributing

PRs welcome. Ideas for contributions:

- [ ] Windows / Linux support
- [ ] Custom hotkey picker in UI
- [ ] Speaker diarization (multi-speaker)
- [ ] Export to Markdown / Notion
- [ ] Menu bar mode

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<p align="center">
  Built with ❤️ · Powered by <a href="https://github.com/openai/whisper">OpenAI Whisper</a> · Runs on your Mac
</p>

<p align="center">
  If this saved you time, consider giving it a ⭐
</p>

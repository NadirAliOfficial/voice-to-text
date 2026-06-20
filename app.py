"""
Voice Typer — local speech-to-text, works everywhere, free forever.

Hold  Cmd + Shift + Space  to record.
Release to transcribe and auto-paste into the active app.

Run:
    python app.py
    python app.py --model base     # faster
    python app.py --model medium   # more accurate
    python app.py --lang en        # force language (skips auto-detect)
"""

import argparse
import subprocess
import threading
import time

import pyperclip
import rumps
from pynput import keyboard

from recorder import AudioRecorder
from transcriber import Transcriber

ICON_READY       = "🎙"
ICON_RECORDING   = "🔴"
ICON_PROCESSING  = "⏳"
HOTKEY           = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.space}


def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.08)
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "v" using command down'],
        capture_output=True,
    )


class VoiceTyperApp(rumps.App):
    def __init__(self, model_size="small", language=None):
        super().__init__(ICON_READY, quit_button="Quit")

        self._recorder    = AudioRecorder()
        self._transcriber = None          # loaded in background so app opens fast
        self._model_size  = model_size
        self._language    = language
        self._recording   = False
        self._pressed     = set()
        self._history     = []            # last 5 transcriptions

        # Menu
        self._status   = rumps.MenuItem("Status: loading model...")
        self._model_lbl = rumps.MenuItem(f"Model: {model_size}")
        self._hist_sep  = rumps.separator
        self._hist_items = [rumps.MenuItem("—") for _ in range(5)]
        self.menu = [
            self._status,
            self._model_lbl,
            None,
            rumps.MenuItem("Hotkey: Cmd+Shift+Space"),
            None,
            "Last 5 transcriptions",
            *self._hist_items,
        ]

        threading.Thread(target=self._load_model, daemon=True).start()

    # ── model loading ────────────────────────────────────────────────────────

    def _load_model(self):
        self._transcriber = Transcriber(self._model_size, self._language)
        self._status.title = "Status: Ready"
        self.title          = ICON_READY
        self._start_hotkey_listener()

    # ── hotkey listener ──────────────────────────────────────────────────────

    def _start_hotkey_listener(self):
        def on_press(key):
            self._pressed.add(key)
            if HOTKEY.issubset(self._pressed) and not self._recording:
                self._start_recording()

        def on_release(key):
            if key in self._pressed:
                self._pressed.discard(key)
            if self._recording and keyboard.Key.space not in self._pressed:
                self._stop_and_transcribe()

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    # ── record / transcribe ──────────────────────────────────────────────────

    def _start_recording(self):
        self._recording    = True
        self.title         = ICON_RECORDING
        self._status.title = "Status: Recording... (release Space to stop)"
        self._recorder.start()

    def _stop_and_transcribe(self):
        audio = self._recorder.stop()
        self._recording = False

        if audio is None:
            self.title         = ICON_READY
            self._status.title = "Status: Ready (too short, try again)"
            return

        self.title         = ICON_PROCESSING
        self._status.title = "Status: Transcribing..."
        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    def _transcribe(self, audio):
        try:
            text, lang = self._transcriber.transcribe(audio)
            if text:
                paste_text(text)
                self._add_history(text)
                rumps.notification(
                    "Voice Typer",
                    f"Language: {lang.upper()}",
                    text[:120] + ("..." if len(text) > 120 else ""),
                )
            else:
                self._status.title = "Status: Ready (no speech detected)"
        except Exception as e:
            self._status.title = f"Status: Error — {e}"

        self.title         = ICON_READY
        self._status.title = "Status: Ready"

    # ── history ──────────────────────────────────────────────────────────────

    def _add_history(self, text):
        short = text[:60] + ("..." if len(text) > 60 else "")
        self._history.insert(0, short)
        self._history = self._history[:5]
        for i, item in enumerate(self._hist_items):
            item.title = self._history[i] if i < len(self._history) else "—"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: small)")
    parser.add_argument("--lang",  default=None,
                        help="Force language code e.g. en, ur, ar (default: auto-detect)")
    args = parser.parse_args()

    VoiceTyperApp(model_size=args.model, language=args.lang).run()

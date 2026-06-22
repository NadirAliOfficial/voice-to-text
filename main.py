"""
Voice Typer — hold ⌃ Ctrl anywhere to record, release to paste.
No window opens. Only the recording overlay appears.
"""

import argparse
import fcntl
import json
import os
import random
import sys
import threading
import time
import tkinter as tk
from datetime import datetime

import customtkinter as ctk
from PIL import Image, ImageTk

from recorder import AudioRecorder
from transcriber import Transcriber
from pynput import keyboard
import pyperclip

ctk.set_appearance_mode("dark")

# ── single-instance lock ───────────────────────────────────────────────────────
_LOCK_PATH = "/tmp/voicetyper.lock"
_lock_fd   = None

def _acquire_lock():
    global _lock_fd
    _lock_fd = open(_LOCK_PATH, "w")
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except IOError:
        return False

BG      = "#0a0a0a"
BG2     = "#111111"
BG3     = "#1a1a1a"
ACCENT  = "#e74c3c"
ACCENTD = "#b03030"
GREEN   = "#1db954"
YELLOW  = "#f0a500"
TEXT    = "#ededed"
TEXT2   = "#888888"
TEXT3   = "#444444"
BORDER  = "#222222"

HISTORY_FILE = os.path.expanduser("~/.voicetyper_history.json")
CMD_KEYS     = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
_kbd         = keyboard.Controller()
ICON_PATH    = os.path.join(os.path.dirname(__file__), "icon.png")


def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(h):
    with open(HISTORY_FILE, "w") as f:
        json.dump(h[-500:], f, indent=2)


def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.4)
    # release any stuck modifier keys before pasting
    for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
              keyboard.Key.shift, keyboard.Key.alt):
        try:
            _kbd.release(k)
        except Exception:
            pass
    time.sleep(0.15)
    _kbd.press(keyboard.Key.cmd)
    _kbd.tap("v")
    _kbd.release(keyboard.Key.cmd)


def _set_dock_badge(text):
    try:
        from AppKit import NSApplication
        NSApplication.sharedApplication().dockTile().setBadgeLabel_(text)
    except Exception:
        pass


# ── transparent waveform overlay ──────────────────────────────────────────────

class Overlay:
    BARS  = 36
    BAR_W = 3
    GAP   = 2
    H_BARS = 42
    H_INFO = 18
    H      = 42 + 18

    def __init__(self, root):
        self._root     = root
        self._win      = None
        self._canvas   = None
        self._active   = False
        self._elapsed  = 0
        self._vals     = [0.08] * self.BARS
        self._tgt      = [0.08] * self.BARS
        self._dot_on   = True
        self._recorder = None

    def show(self, recorder=None):
        if self._win and self._win.winfo_exists():
            return
        self._active   = True
        self._elapsed  = 0
        self._vals     = [0.08] * self.BARS
        self._tgt      = [0.08] * self.BARS
        self._recorder = recorder

        W = self.BARS * (self.BAR_W + self.GAP) + 4

        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.wm_attributes("-topmost", True)
        win.wm_attributes("-transparent", True)
        win.configure(bg="systemTransparent")

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{W}x{self.H}+{(sw - W) // 2}+{sh - self.H - 110}")

        c = tk.Canvas(win, bg="systemTransparent", highlightthickness=0,
                      width=W, height=self.H)
        c.pack()

        self._canvas = c
        self._W      = W
        self._win    = win

        self._animate()
        self._count()

    def _animate(self):
        if not (self._win and self._win.winfo_exists()):
            return
        if self._active:
            # use real mic level as base amplitude, add natural per-bar variation
            base = min(1.0, (self._recorder.level * 18) if self._recorder else 0.4)
            base = max(0.08, base)
            for i in range(self.BARS):
                variation = random.uniform(0.4, 1.0)
                raw  = base * variation
                left = self._vals[i - 1] if i > 0 else raw
                right = self._vals[i + 1] if i < self.BARS - 1 else raw
                self._tgt[i] = raw * 0.55 + left * 0.25 + right * 0.20
        else:
            for i in range(self.BARS):
                self._tgt[i] = 0.05
        for i in range(self.BARS):
            self._vals[i] += (self._tgt[i] - self._vals[i]) * 0.18
        self._draw()
        self._win.after(35, self._animate)

    def _draw(self):
        c = self._canvas
        c.delete("all")
        W = self._W

        bar_cy   = self.H_BARS // 2          # vertical center of bar zone
        max_half = bar_cy - 3

        # ── bars (white pills, centered horizontally) ──
        total_bar_w = self.BARS * (self.BAR_W + self.GAP) - self.GAP
        x0 = (W - total_bar_w) // 2
        for i, val in enumerate(self._vals):
            x    = x0 + i * (self.BAR_W + self.GAP)
            half = max(2, int(val * max_half))
            r    = max(1, self.BAR_W // 2)
            c.create_rectangle(x, bar_cy - half + r,
                               x + self.BAR_W, bar_cy + half - r,
                               fill="white", outline="")
            c.create_oval(x, bar_cy - half,
                          x + self.BAR_W, bar_cy - half + r * 2,
                          fill="white", outline="")
            c.create_oval(x, bar_cy + half - r * 2,
                          x + self.BAR_W, bar_cy + half,
                          fill="white", outline="")

        # ── dot + timer centered below bars ──
        info_y = self.H_BARS + self.H_INFO // 2  # vertical center of info row
        self._dot_on = not self._dot_on
        dot_r = 5
        dot_x = W // 2 - 22
        c.create_oval(dot_x - dot_r, info_y - dot_r,
                      dot_x + dot_r, info_y + dot_r,
                      fill=ACCENT if self._dot_on else "#6b1010", outline="")
        m, s = divmod(self._elapsed, 60)
        c.create_text(W // 2 + 2, info_y, text=f"{m}:{s:02d}",
                      fill="white", font=("Menlo", 11, "bold"), anchor="center")

    def _count(self):
        if not (self._win and self._win.winfo_exists()):
            return
        if self._active:
            self._elapsed += 1
        self._win.after(1000, self._count)

    def transcribing(self):
        self._active = False
        if self._win and self._win.winfo_exists():
            self._win.after(1400, self._destroy)

    def hide(self):
        self._active = False
        self._destroy()

    def _destroy(self):
        try:
            if self._win and self._win.winfo_exists():
                self._win.destroy()
        except Exception:
            pass
        self._win = None


# ── app ───────────────────────────────────────────────────────────────────────

class VoiceTyperApp:
    def __init__(self, model_size="small", language=None):
        self._model_size  = model_size
        self._language    = language
        self._recorder    = AudioRecorder()
        self._transcriber = None
        self._recording   = False
        self._pressed     = set()
        self._history     = load_history()
        self._prev_app    = None

        # plain Tk root — withdrawn immediately, never visible
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        # accessory policy: macOS won't auto-quit a withdrawn window
        def _bg_policy():
            try:
                from AppKit import NSApplication
                NSApplication.sharedApplication().setActivationPolicy_(1)
            except Exception:
                pass
        self.root.after(200, _bg_policy)

        self._main_win = None
        self._set_dock_icon()
        self._overlay = Overlay(self.root)

        threading.Thread(target=self._load_model, daemon=True).start()
        threading.Thread(target=self._hotkey_listener, daemon=True).start()

        # wire dock icon click → open main window
        self.root.after(300, self._install_dock_handler)

    def _set_dock_icon(self):
        if not os.path.exists(ICON_PATH):
            return
        try:
            from AppKit import NSApplication, NSImage
            ns = NSApplication.sharedApplication()
            ns.setApplicationIconImage_(
                NSImage.alloc().initWithContentsOfFile_(ICON_PATH))
        except Exception:
            pass

    def _install_dock_handler(self):
        try:
            from AppKit import NSApplication
            from Foundation import NSObject
            import objc

            app_ref = self

            class Delegate(NSObject):
                def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
                    app_ref.root.after(0, app_ref.open_main_window)
                    return True

            self._delegate = Delegate.alloc().init()
            NSApplication.sharedApplication().setDelegate_(self._delegate)
        except Exception:
            pass

    # ── main window ───────────────────────────────────────────────────────────

    def open_main_window(self):
        if self._main_win and self._main_win.winfo_exists():
            self._main_win.lift()
            self._main_win.focus_force()
            return
        self._build_main_window()

    def _build_main_window(self):
        win = tk.Toplevel(self.root)
        win.title("Voice Typer")
        win.geometry("820x620")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.protocol("WM_DELETE_WINDOW", win.withdraw)

        try:
            if os.path.exists(ICON_PATH):
                img   = Image.open(ICON_PATH, encoding="utf-8").resize((64, 64), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                win.iconphoto(True, photo)
                win._icon_ref = photo
        except Exception:
            pass

        # sidebar
        sb = tk.Frame(win, bg=BG2, width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        tk.Frame(win, bg=BORDER, width=1).pack(side="left", fill="y")

        # logo
        logo = tk.Frame(sb, bg=BG2)
        logo.pack(fill="x", padx=18, pady=(24, 0))
        if os.path.exists(ICON_PATH):
            try:
                pil  = Image.open(ICON_PATH, encoding="utf-8").resize((36, 36), Image.LANCZOS)
                ctki = ctk.CTkImage(pil, size=(36, 36))
                ctk.CTkLabel(logo, image=ctki, text="", fg_color=BG2).pack(side="left", padx=(0, 10))
            except Exception:
                pass
        col = tk.Frame(logo, bg=BG2)
        col.pack(side="left")
        tk.Label(col, text="Voice Typer", font=("SF Pro Display", 13, "bold"),
                 fg=TEXT, bg=BG2).pack(anchor="w")
        tk.Label(col, text="AI · Local · Private", font=("SF Pro Display", 9),
                 fg=TEXT3, bg=BG2).pack(anchor="w")

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=16, pady=18)

        # nav
        nav_btns = {}
        view_frames = {}
        content = tk.Frame(win, bg=BG)
        content.pack(side="right", fill="both", expand=True)

        def switch(key):
            for k, parts in nav_btns.items():
                active = k == key
                for w in parts:
                    w.configure(bg=BG3 if active else BG2)
                parts[0].configure(fg=ACCENT if active else TEXT3)
            for k, f in view_frames.items():
                if k == key:
                    f.pack(fill="both", expand=True)
                else:
                    f.pack_forget()

        def nav(key, icon, label):
            f = tk.Frame(sb, bg=BG2, cursor="hand2")
            f.pack(fill="x", padx=8, pady=1)
            inner = tk.Frame(f, bg=BG2, padx=10, pady=9)
            inner.pack(fill="x")
            ic = tk.Label(inner, text=icon, fg=TEXT3, bg=BG2, font=("SF Pro Display", 12))
            ic.pack(side="left")
            lb = tk.Label(inner, text=f"  {label}", fg=TEXT3, bg=BG2, font=("SF Pro Display", 12))
            lb.pack(side="left")
            nav_btns[key] = [ic, inner, f, lb]
            for w in (f, inner, ic, lb):
                w.bind("<Button-1>", lambda _, k=key: switch(k))

        nav("history",  "📋", "History")
        nav("stats",    "📊", "Stats")
        nav("settings", "⚙", "Settings")

        # status bottom
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=16, side="bottom", pady=(0, 6))
        btm = tk.Frame(sb, bg=BG2)
        btm.pack(side="bottom", fill="x", padx=18, pady=(0, 18))
        self._mw_status = tk.Label(btm, text="● ready", fg=GREEN, bg=BG2,
                                   font=("SF Pro Display", 10))
        self._mw_status.pack(side="left")

        # ── history view ──
        hv = tk.Frame(content, bg=BG)
        view_frames["history"] = hv

        hdr = tk.Frame(hv, bg=BG)
        hdr.pack(fill="x", padx=28, pady=(28, 14))
        tk.Label(hdr, text="History", font=("SF Pro Display", 19, "bold"),
                 fg=TEXT, bg=BG).pack(side="left")
        tk.Button(hdr, text="Export", font=("SF Pro Display", 10),
                  bg=BG3, fg=TEXT2, relief="flat", cursor="hand2", padx=10, pady=4,
                  command=self._export).pack(side="right", padx=4)
        tk.Button(hdr, text="Clear", font=("SF Pro Display", 10),
                  bg=BG3, fg=ACCENT, relief="flat", cursor="hand2", padx=10, pady=4,
                  command=lambda: (self._history.clear(), save_history(self._history),
                                   self._refresh_hist(hs))).pack(side="right")

        search_var = tk.StringVar()
        sf = tk.Frame(hv, bg=BG3)
        sf.pack(fill="x", padx=28, pady=(0, 14))
        tk.Frame(sf, bg=BORDER, height=1).pack(fill="x")
        si = tk.Frame(sf, bg=BG3)
        si.pack(fill="x", padx=12, pady=7)
        tk.Label(si, text="⌕", fg=TEXT3, bg=BG3, font=("SF Pro Display", 13)).pack(side="left", padx=(0, 6))
        tk.Entry(si, textvariable=search_var, bg=BG3, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("SF Pro Display", 12),
                 highlightthickness=0).pack(side="left", fill="x", expand=True, ipady=2)

        hs = ctk.CTkScrollableFrame(hv, fg_color=BG, corner_radius=0)
        hs.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self._refresh_hist(hs)
        search_var.trace("w", lambda *_: self._refresh_hist(hs, search_var.get()))

        # ── stats view ──
        sv = tk.Frame(content, bg=BG)
        view_frames["stats"] = sv
        tk.Label(sv, text="Stats", font=("SF Pro Display", 19, "bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=28, pady=(28, 20))
        sc = tk.Frame(sv, bg=BG)
        sc.pack(fill="x", padx=28)
        self._stats_frame = sc
        self._refresh_stats_frame()

        # ── settings view ──
        stv = tk.Frame(content, bg=BG)
        view_frames["settings"] = stv
        tk.Label(stv, text="Settings", font=("SF Pro Display", 19, "bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=28, pady=(28, 20))

        def scard(label, sub):
            c = tk.Frame(stv, bg=BG3)
            c.pack(fill="x", padx=28, pady=4)
            tk.Frame(c, bg=BORDER, height=1).pack(fill="x")
            row = tk.Frame(c, bg=BG3)
            row.pack(fill="x", padx=18, pady=14)
            L = tk.Frame(row, bg=BG3)
            L.pack(side="left")
            tk.Label(L, text=label, fg=TEXT, bg=BG3,
                     font=("SF Pro Display", 13, "bold")).pack(anchor="w")
            tk.Label(L, text=sub, fg=TEXT3, bg=BG3,
                     font=("SF Pro Display", 9)).pack(anchor="w", pady=(2, 0))
            return row

        r1 = scard("Model", "tiny=fastest  ·  large-v3=best")
        self._model_var = ctk.StringVar(value=self._model_size)
        ctk.CTkOptionMenu(r1, variable=self._model_var, width=130,
                          values=["tiny","base","small","medium","large-v3"],
                          command=lambda _: self._apply_model(),
                          fg_color=BG4, button_color=BG4,
                          dropdown_fg_color=BG3).pack(side="right")

        r2 = scard("Language", "en  ur  ar  fr  auto=detect")
        self._lang_var = ctk.StringVar(value=self._language or "en")
        lr = tk.Frame(r2, bg=BG3)
        lr.pack(side="right")
        ctk.CTkButton(lr, text="Apply", width=66, height=30,
                      fg_color=ACCENT, hover_color=ACCENTD,
                      font=ctk.CTkFont("SF Pro Display", 11),
                      command=self._apply_lang).pack(side="right", padx=(8, 0))
        ctk.CTkEntry(lr, textvariable=self._lang_var, width=76, height=30,
                     fg_color=BG4, border_color=BG4, text_color=TEXT).pack(side="right")

        r3 = scard("Hotkey", "Hold to record, release to paste")
        tk.Label(r3, text="Hold  ⌃ Ctrl", fg=TEXT2, bg=BG3,
                 font=("Menlo", 12)).pack(side="right")

        switch("history")
        self._main_win = win
        win.lift()
        win.focus_force()

    def _refresh_hist(self, scroll, q=""):
        for w in scroll.winfo_children():
            w.destroy()
        items = ([h for h in self._history if q.lower() in h["text"].lower()]
                 if q else self._history)
        if not items:
            tk.Label(scroll, text="No transcriptions yet.\nHold ⌃ Ctrl and speak.",
                     font=("SF Pro Display", 12), fg=TEXT3, bg=BG,
                     justify="center").pack(pady=50)
            return
        for e in items:
            card = tk.Frame(scroll, bg=BG3)
            card.pack(fill="x", pady=3, padx=2)
            tk.Frame(card, bg=BORDER, height=1).pack(fill="x")
            meta = tk.Frame(card, bg=BG3)
            meta.pack(fill="x", padx=12, pady=(9, 0))
            tk.Label(meta, text=e["time"], fg=TEXT3, bg=BG3,
                     font=("Menlo", 9)).pack(side="left")
            tk.Label(meta, text=f"{e['lang']}  ·  {e['words']}w", fg=TEXT3, bg=BG3,
                     font=("Menlo", 9)).pack(side="right")
            tk.Label(card, text=e["text"], fg=TEXT, bg=BG3,
                     font=("SF Pro Display", 12), wraplength=520,
                     justify="left", anchor="w").pack(fill="x", padx=12, pady=(5, 10))
            tk.Button(card, text="Copy", font=("SF Pro Display", 10),
                      bg=BG4, fg=TEXT2, relief="flat", cursor="hand2", padx=8, pady=2,
                      command=lambda t=e["text"]: (
                          self.root.clipboard_clear(),
                          self.root.clipboard_append(t))).pack(anchor="e", padx=10, pady=(0, 8))

    def _refresh_stats_frame(self):
        for w in self._stats_frame.winfo_children():
            w.destroy()
        today = datetime.now().strftime("%Y-%m-%d")
        langs = {}
        for h in self._history:
            langs[h["lang"]] = langs.get(h["lang"], 0) + 1
        for label, val, color in [
            ("Sessions",    str(len(self._history)),                    ACCENT),
            ("Words",       f"{sum(h['words'] for h in self._history):,}", "#5dade2"),
            ("Today",       str(sum(1 for h in self._history if h["time"].startswith(today))), GREEN),
            ("Top lang",    max(langs, key=langs.get) if langs else "—", YELLOW),
        ]:
            c = tk.Frame(self._stats_frame, bg=BG3)
            c.pack(fill="x", pady=4)
            tk.Frame(c, bg=BORDER, height=1).pack(fill="x")
            r = tk.Frame(c, bg=BG3)
            r.pack(fill="x", padx=18, pady=14)
            tk.Label(r, text=label, fg=TEXT2, bg=BG3,
                     font=("SF Pro Display", 12)).pack(side="left")
            tk.Label(r, text=val, fg=color, bg=BG3,
                     font=("SF Pro Display", 20, "bold")).pack(side="right")

    def _export(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text", "*.txt")],
            initialfile="voice_typer_history.txt")
        if path:
            with open(path, "w") as f:
                for h in self._history:
                    f.write(f"[{h['time']}] [{h['lang']}]\n{h['text']}\n\n")

    def _apply_model(self):
        self._model_size = self._model_var.get()
        threading.Thread(target=self._load_model, daemon=True).start()

    def _apply_lang(self):
        v = self._lang_var.get().strip()
        self._language = None if v == "auto" else v
        if self._transcriber:
            self._transcriber.language = self._language

    # ── model ─────────────────────────────────────────────────────────────────

    def _load_model(self):
        self._transcriber = Transcriber(self._model_size, self._language)
        print(f"[voice typer] model ready ({self._model_size})")

    # ── hotkey ────────────────────────────────────────────────────────────────

    def _hotkey_listener(self):
        def on_press(key):
            self._pressed.add(key)
            # only trigger when Ctrl is held ALONE — no other keys
            ctrl_only = bool(self._pressed & CMD_KEYS) and self._pressed.issubset(CMD_KEYS)
            if ctrl_only and not self._recording:
                self.root.after(0, self._start)
            elif self._recording and key not in CMD_KEYS:
                self.root.after(0, self._cancel)

        def on_release(key):
            if key in self._pressed:
                self._pressed.discard(key)
            if self._recording and not (self._pressed & CMD_KEYS):
                self.root.after(0, self._stop)

        with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
            l.join()

    # ── record ────────────────────────────────────────────────────────────────

    def _start(self):
        if not self._transcriber:
            return
        # capture the frontmost app NOW so we can restore it before pasting
        self._prev_app = None
        try:
            from AppKit import NSWorkspace
            self._prev_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        except Exception:
            pass
        self._recording = True
        self._recorder.start()
        self._overlay.show(recorder=self._recorder)
        _set_dock_badge("⏺")

    def _cancel(self):
        self._recording = False
        self._recorder.stop()
        self._overlay.hide()
        _set_dock_badge("")

    def _stop(self):
        self._recording = False
        audio = self._recorder.stop()
        _set_dock_badge("")

        if audio is None:
            self._overlay.hide()
            return

        self._overlay.transcribing()
        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    def _transcribe(self, audio):
        try:
            text, lang = self._transcriber.transcribe(audio)
            if text:
                self.root.after(0, self._overlay.hide)
                # reactivate the app that was focused before recording
                try:
                    from AppKit import NSApplicationActivateIgnoringOtherApps
                    if self._prev_app:
                        self._prev_app.activateWithOptions_(
                            NSApplicationActivateIgnoringOtherApps)
                except Exception:
                    pass
                time.sleep(0.35)
                print(f"[paste] {text[:60]}")
                paste_text(text)
                entry = {
                    "text":  text,
                    "lang":  lang.upper(),
                    "time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "words": len(text.split()),
                }
                self._history.insert(0, entry)
                save_history(self._history)
        except Exception as e:
            print(f"[error] {e}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not _acquire_lock():
        print("[voice typer] already running — exiting")
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="small",
                        choices=["tiny","base","small","medium","large-v3"])
    parser.add_argument("--lang", default=None)
    args = parser.parse_args()
    VoiceTyperApp(model_size=args.model, language=args.lang).run()

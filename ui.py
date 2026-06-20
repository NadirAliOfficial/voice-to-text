"""
Voice Typer — History & Settings window.
Launched from the menu bar. Runs in its own thread.
"""

import json
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk

HISTORY_FILE = os.path.expanduser("~/.voicetyper_history.json")
BG       = "#1a1a1a"
BG2      = "#242424"
BG3      = "#2e2e2e"
ACCENT   = "#e74c3c"
GREEN    = "#2ecc71"
TEXT     = "#f0f0f0"
SUBTEXT  = "#888888"
FONT     = ("SF Pro Display", 13)
FONT_SM  = ("SF Pro Display", 11)
FONT_LG  = ("SF Pro Display", 16, "bold")


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-500:], f, indent=2)


class VoiceTyperUI:
    def __init__(self, get_status_fn=None, set_model_fn=None, set_lang_fn=None,
                 toggle_continuous_fn=None):
        self._get_status      = get_status_fn
        self._set_model       = set_model_fn
        self._set_lang        = set_lang_fn
        self._toggle_cont     = toggle_continuous_fn
        self._root            = None
        self._history         = load_history()
        self._lock            = threading.Lock()

    # ── public API ────────────────────────────────────────────────────────────

    def add_entry(self, text, lang):
        entry = {
            "text": text,
            "lang": lang.upper(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "words": len(text.split()),
        }
        with self._lock:
            self._history.insert(0, entry)
            save_history(self._history)
        if self._root and self._root.winfo_exists():
            self._root.after(0, self._refresh_history)

    def show(self):
        if self._root and self._root.winfo_exists():
            self._root.lift()
            self._root.focus_force()
            return
        t = threading.Thread(target=self._build, daemon=True)
        t.start()

    # ── window ────────────────────────────────────────────────────────────────

    def _build(self):
        self._root = tk.Tk()
        self._root.title("Voice Typer")
        self._root.geometry("700x560")
        self._root.configure(bg=BG)
        self._root.resizable(True, True)
        self._root.minsize(560, 400)

        self._build_header()
        self._build_tabs()
        self._root.mainloop()

    def _build_header(self):
        hdr = tk.Frame(self._root, bg=BG, pady=16)
        hdr.pack(fill="x", padx=24)

        tk.Label(hdr, text="🎙  Voice Typer", font=FONT_LG,
                 bg=BG, fg=TEXT).pack(side="left")

        self._status_lbl = tk.Label(hdr, text="● Ready", font=FONT_SM,
                                    bg=BG, fg=GREEN)
        self._status_lbl.pack(side="right", padx=4)

        self._update_status_loop()

    def _build_tabs(self):
        nb = ttk.Notebook(self._root)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",      background=BG,  borderwidth=0)
        style.configure("TNotebook.Tab",  background=BG2, foreground=TEXT,
                        padding=[14, 6], font=FONT_SM)
        style.map("TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", TEXT)])

        self._tab_history  = tk.Frame(nb, bg=BG)
        self._tab_stats    = tk.Frame(nb, bg=BG)
        self._tab_settings = tk.Frame(nb, bg=BG)

        nb.add(self._tab_history,  text="  History  ")
        nb.add(self._tab_stats,    text="  Stats  ")
        nb.add(self._tab_settings, text="  Settings  ")

        self._build_history_tab()
        self._build_stats_tab()
        self._build_settings_tab()

    # ── history tab ──────────────────────────────────────────────────────────

    def _build_history_tab(self):
        toolbar = tk.Frame(self._tab_history, bg=BG, pady=8)
        toolbar.pack(fill="x", padx=12)

        self._search_var = tk.StringVar()
        self._search_var.trace("w", lambda *_: self._refresh_history())
        tk.Entry(toolbar, textvariable=self._search_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=FONT_SM,
                 width=28).pack(side="left", ipady=4, padx=(0, 8))
        tk.Label(toolbar, text="🔍 search", bg=BG, fg=SUBTEXT,
                 font=FONT_SM).pack(side="left")

        tk.Button(toolbar, text="Export .txt", font=FONT_SM, bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=10,
                  command=self._export).pack(side="right", padx=4)
        tk.Button(toolbar, text="Clear all", font=FONT_SM, bg=BG3, fg=ACCENT,
                  relief="flat", cursor="hand2", padx=10,
                  command=self._clear_history).pack(side="right", padx=4)

        frame = tk.Frame(self._tab_history, bg=BG)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._canvas  = tk.Canvas(frame, bg=BG, highlightthickness=0)
        scrollbar     = tk.Scrollbar(frame, orient="vertical",
                                     command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._hist_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._hist_frame, anchor="nw")

        self._hist_frame.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._canvas_win, width=e.width))
        self._canvas.bind_all("<MouseWheel>", lambda e: self._canvas.yview_scroll(
            -1 * (e.delta // 120), "units"))

        self._refresh_history()

    def _refresh_history(self):
        for w in self._hist_frame.winfo_children():
            w.destroy()

        q = self._search_var.get().lower() if hasattr(self, "_search_var") else ""
        with self._lock:
            items = [h for h in self._history if q in h["text"].lower()] if q else self._history[:]

        if not items:
            tk.Label(self._hist_frame, text="No transcriptions yet.\nHold Cmd and speak!",
                     bg=BG, fg=SUBTEXT, font=FONT, justify="center").pack(pady=40)
            return

        for entry in items:
            self._history_card(entry)

    def _history_card(self, entry):
        card = tk.Frame(self._hist_frame, bg=BG2, pady=10, padx=12)
        card.pack(fill="x", pady=3)

        top = tk.Frame(card, bg=BG2)
        top.pack(fill="x")
        tk.Label(top, text=entry["time"], bg=BG2, fg=SUBTEXT,
                 font=FONT_SM).pack(side="left")
        tk.Label(top, text=f"[{entry['lang']}]  {entry['words']} words",
                 bg=BG2, fg=SUBTEXT, font=FONT_SM).pack(side="right")

        tk.Label(card, text=entry["text"], bg=BG2, fg=TEXT, font=FONT,
                 wraplength=580, justify="left", anchor="w").pack(
                     fill="x", pady=(6, 8))

        tk.Button(card, text="Copy", font=FONT_SM, bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=8,
                  command=lambda t=entry["text"]: self._copy(t)).pack(
                      side="right")

    def _copy(self, text):
        self._root.clipboard_clear()
        self._root.clipboard_append(text)

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="voice_typer_history.txt",
        )
        if path:
            with open(path, "w") as f:
                for h in self._history:
                    f.write(f"[{h['time']}] [{h['lang']}]\n{h['text']}\n\n")

    def _clear_history(self):
        with self._lock:
            self._history.clear()
            save_history(self._history)
        self._refresh_history()
        self._refresh_stats()

    # ── stats tab ────────────────────────────────────────────────────────────

    def _build_stats_tab(self):
        self._stats_frame = tk.Frame(self._tab_stats, bg=BG)
        self._stats_frame.pack(fill="both", expand=True, padx=24, pady=24)
        self._refresh_stats()

    def _refresh_stats(self):
        for w in self._stats_frame.winfo_children():
            w.destroy()

        with self._lock:
            total      = len(self._history)
            words      = sum(h["words"] for h in self._history)
            today_str  = datetime.now().strftime("%Y-%m-%d")
            today      = sum(1 for h in self._history if h["time"].startswith(today_str))
            langs      = {}
            for h in self._history:
                langs[h["lang"]] = langs.get(h["lang"], 0) + 1

        stats = [
            ("🎙  Total transcriptions", str(total)),
            ("📝  Total words",          f"{words:,}"),
            ("📅  Today's sessions",     str(today)),
            ("🌍  Top language",         max(langs, key=langs.get) if langs else "—"),
        ]

        for label, value in stats:
            row = tk.Frame(self._stats_frame, bg=BG2, pady=14, padx=20)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, bg=BG2, fg=SUBTEXT,
                     font=FONT).pack(side="left")
            tk.Label(row, text=value, bg=BG2, fg=TEXT,
                     font=("SF Pro Display", 15, "bold")).pack(side="right")

        if langs:
            tk.Label(self._stats_frame, text="Languages used",
                     bg=BG, fg=SUBTEXT, font=FONT_SM).pack(anchor="w", pady=(20, 6))
            for lang, count in sorted(langs.items(), key=lambda x: -x[1]):
                row = tk.Frame(self._stats_frame, bg=BG2, pady=8, padx=20)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=lang, bg=BG2, fg=TEXT, font=FONT).pack(side="left")
                tk.Label(row, text=str(count), bg=BG2, fg=SUBTEXT,
                         font=FONT).pack(side="right")

    # ── settings tab ─────────────────────────────────────────────────────────

    def _build_settings_tab(self):
        f = tk.Frame(self._tab_settings, bg=BG)
        f.pack(fill="both", expand=True, padx=24, pady=24)

        def row(label, widget_fn):
            r = tk.Frame(f, bg=BG2, pady=12, padx=20)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=label, bg=BG2, fg=TEXT, font=FONT).pack(side="left")
            widget_fn(r)

        # Model
        self._model_var = tk.StringVar(value="small")
        def model_widget(parent):
            opts = ["tiny", "base", "small", "medium", "large-v3"]
            m = ttk.Combobox(parent, textvariable=self._model_var,
                             values=opts, width=12, state="readonly")
            m.pack(side="right")
            m.bind("<<ComboboxSelected>>", lambda _: self._apply_model())
        row("Model", model_widget)

        # Language
        self._lang_var = tk.StringVar(value="en")
        def lang_widget(parent):
            e = tk.Entry(parent, textvariable=self._lang_var, width=8,
                         bg=BG3, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=FONT)
            e.pack(side="right", ipady=3)
            tk.Button(parent, text="Apply", font=FONT_SM, bg=ACCENT, fg="white",
                      relief="flat", cursor="hand2", padx=8,
                      command=self._apply_lang).pack(side="right", padx=6)
        row("Language (e.g. en, ur, auto)", lang_widget)

        # Hotkey info
        def hotkey_info(parent):
            tk.Label(parent, text="Hold Cmd to record", bg=BG2,
                     fg=SUBTEXT, font=FONT_SM).pack(side="right")
        row("Hotkey", hotkey_info)

        # Info box
        info = tk.Frame(f, bg=BG3, pady=12, padx=16)
        info.pack(fill="x", pady=(20, 0))
        tk.Label(info, text="ℹ️  How it works",
                 bg=BG3, fg=TEXT, font=("SF Pro Display", 12, "bold")).pack(anchor="w")
        lines = [
            "• Hold Cmd → speak → release to transcribe",
            "• Text auto-pastes into any focused app",
            "• AI model: OpenAI Whisper (runs 100% local)",
            "• No internet needed after first model download",
            "• History saved to ~/.voicetyper_history.json",
        ]
        for line in lines:
            tk.Label(info, text=line, bg=BG3, fg=SUBTEXT,
                     font=FONT_SM, anchor="w").pack(fill="x", pady=1)

    def _apply_model(self):
        if self._set_model:
            self._set_model(self._model_var.get())

    def _apply_lang(self):
        lang = self._lang_var.get().strip()
        if self._set_lang:
            self._set_lang(None if lang == "auto" else lang)

    # ── status pulse ─────────────────────────────────────────────────────────

    def _update_status_loop(self):
        if self._get_status and self._root:
            status = self._get_status()
            color  = ACCENT if "Recording" in status else \
                     "#f39c12" if "Transcrib" in status else GREEN
            self._status_lbl.config(text=f"● {status}", fg=color)
            self._root.after(500, self._update_status_loop)

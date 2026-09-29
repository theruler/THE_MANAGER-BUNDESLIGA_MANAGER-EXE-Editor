import tkinter as tk
from tkinter import ttk
import i18n
from translator import TRANSLATION_ENGINES, translate_string

SOURCE_LANGS = ["auto", "de", "en", "fr", "es", "it"]
TARGET_LANGS = ["it", "en", "de", "fr", "es"]

COLOR_IDLE = "#7F8C8D"
COLOR_BUSY = "#1565C0"
COLOR_OK = "#27AE60"
COLOR_ERR = "#C0392B"


class TranslationBar(ttk.Frame):

    def __init__(self, parent, on_translate, reg=None, share_with=None,
                 pady=(8, 0), max_error_len=80):
        super().__init__(parent)
        self._on_translate = on_translate
        self._max_error_len = max_error_len
        self._reg = reg or self._default_reg
        if share_with is not None:
            self.engine_var = share_with.engine_var
            self.source_lang_var = share_with.source_lang_var
            self.target_lang_var = share_with.target_lang_var
        else:
            self.engine_var = tk.StringVar(value="Google Translate")
            self.source_lang_var = tk.StringVar(value="auto")
            self.target_lang_var = tk.StringVar(value="it")
        self.controls = []

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=pady)
        for key, var, values, width in (
                ("tr.engine", self.engine_var, list(TRANSLATION_ENGINES.keys()), 18),
                ("tr.from", self.source_lang_var, SOURCE_LANGS, 6),
                ("tr.to", self.target_lang_var, TARGET_LANGS, 6)):
            self._reg(ttk.Label(row), key).pack(side=tk.LEFT, padx=(0 if key == "tr.engine" else 8, 3))
            combo = ttk.Combobox(row, textvariable=var, state="readonly", width=width, values=values)
            combo.pack(side=tk.LEFT, padx=(0, 8))
            self.controls.append(combo)
        self.button = self._reg(ttk.Button(row, command=self.run_translation), "tr.translate_play")
        self.button.pack(side=tk.LEFT, padx=(0, 6))
        self.controls.append(self.button)
        self.status_label = ttk.Label(row, text="", font=("Segoe UI", 9, "italic"),foreground=COLOR_IDLE)
        self.status_label.pack(side=tk.LEFT, padx=(4, 0))

    @staticmethod
    def _default_reg(widget, key):
        widget.config(text=i18n.tr(key))
        return widget

    def make_translate_fn(self):
        engine = self.engine_var.get()
        src = self.source_lang_var.get()
        tgt = self.target_lang_var.get()
        return lambda text: translate_string(
            text, target_lang=tgt, source_lang=src, engine=engine)

    def set_status(self, text="", color=COLOR_IDLE):
        self.status_label.config(text=text, foreground=color)

    def run_translation(self):
        self.set_status("…", COLOR_BUSY)
        self.button.config(state=tk.DISABLED)
        self.update_idletasks()
        try:
            self._on_translate(self.make_translate_fn())
        except Exception as exc:
            self.set_status(
                i18n.tr("tr.error", error=str(exc)[:self._max_error_len]),
                COLOR_ERR)
            return False
        finally:
            self.button.config(state=tk.NORMAL)
        self.set_status(i18n.tr("tr.translated_check"), COLOR_OK)
        self.after(2000, self.set_status)
        return True

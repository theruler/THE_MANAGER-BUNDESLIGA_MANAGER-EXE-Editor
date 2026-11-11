"""Bundesliga Manager Hattrick (BMH) - string editor support.

Games handled (the text file next to the EXE; BMHExeStringsPanel below edits the strings
stored INSIDE a supported BMH.EXE, see bmh_exe_strings.py):
    FLTD.EXE (ENG)  ->  TEXTE.BLK
    BMH.EXE  (GER)  ->  TEXTD.BLK

TEXT*.BLK layout:
    0  u8   edition identifier        \
    1  u16  declared buffer size       } 7-byte header, kept verbatim and never
    3  u32  unused header field       /  interpreted (the size may differ from the real payload)
    7  ...  string buffer: consecutive NUL-terminated ISO 646-DE strings
The first TEXT_COUNT (1382) strings are indexed; a shorter file is rejected.
Offsets are relative to the start of the string buffer (file offset 7).
Anything after the 1382nd string is preserved untouched.
"""
import os
import re
import struct
import tkinter as tk
from tkinter import ttk, messagebox
from translator import TranslationIntegrityError
try:                                        # control-token shield already used by string_codec_mixin
    from translator import CONTROL_TOKEN_PATTERN as _SHARED_TOKENS
except ImportError:                         # pragma: no cover
    _SHARED_TOKENS = None
from preview_dialog import make_preview_tree
import newspaper_grammar as NG
import newspaper_editor as _ne
from charmap import CharmapEncodeError
from bmh_exe_strings import BMHExeStrings, BMHExeError, BMHExeSpaceError  # noqa: F401  (re-exported)

TEXT_COUNT = 0x566  # pointer table TextPointerTable[1382]

GAMES = {
    "fltd.exe": {"label": "Bundesliga Manager Hattrick (ENG)", "blk": "TEXTE.BLK", "lang": "ENG"},
    "bmh.exe":  {"label": "Bundesliga Manager Hattrick (GER)", "blk": "TEXTD.BLK", "lang": "GER"},
}


def detect_game(path):
    return GAMES.get(os.path.basename(path).lower())


def find_file_ci(directory, name):
    try:
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if entry.lower() == name.lower() and os.path.isfile(full):
                return full
    except OSError:
        pass
    return None


def find_dir_ci(directory, name):
    try:
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if entry.lower() == name.lower() and os.path.isdir(full):
                return full
    except OSError:
        pass
    return None


# ---------------------------------------------------------------- codec ----
# DIN 66003 / ISO 646-DE: the 7-bit German national variant.
_BASE_DE_DECODE = {0x40: "§", 0x5B: "Ä", 0x5C: "Ö", 0x5D: "Ü",
                   0x7B: "ä", 0x7C: "ö", 0x7D: "ü", 0x7E: "ß"}
# Effective tables (base + user char map).  They are mutated in place by set_charmap(),
# so every module holding a reference sees the current mapping.
_DE_DECODE = dict(_BASE_DE_DECODE)
_DE_ENCODE = {ch: code for code, ch in _DE_DECODE.items()}


def set_charmap(mapping):
    """Overlay a user char map ({"7e": "à", ...}: byte -> character) on ISO 646-DE.

    A mapped byte decodes to its character and a mapped character encodes to its byte.
    The byte's plain ASCII character is then no longer encodable (it would be ambiguous);
    raw bytes stay reachable through \\xNN."""
    overrides = {}
    for key, value in (mapping or {}).items():
        try:
            code = int(str(key), 16)
        except ValueError:
            continue
        if 0 < code <= 0xFF and isinstance(value, str) and len(value) == 1:
            overrides[code] = value
    _DE_DECODE.clear()
    _DE_DECODE.update(_BASE_DE_DECODE)
    _DE_DECODE.update(overrides)
    _DE_ENCODE.clear()
    for code, ch in _DE_DECODE.items():          # overrides come last and win
        _DE_ENCODE[ch] = code
    for code, ch in overrides.items():
        _DE_ENCODE[ch] = code
_ESCAPE_RE = re.compile(r"\\x([0-9A-Fa-f]{2})")
# Control codes inside the strings of the EXE (never to be sent to a translation engine):
#   %x02 %x10 ... colour/attribute codes, %c %z %V %0 ... placeholders, %% literal, # alternatives
#   separator, #x end of an alternatives group (only when no letter follows).
# Look of the template editor for the commentary strings: same editor as the newspaper strings of the
# MZ games (newspaper_editor.NewspaperEditorPanel) with the BMH grammar dialect.  Random selectors
# %x02..%x05 have as many branches as the code says; the context selectors found in the EXEs (10 11 20
# 21 40 50 60 70 80 90) have the branch counts below.  What each context code means is not known, so
# they are shown by code only.
_BMH_RANDOM = {code: (f"RANDOM{code[1]}", colour) for code, colour in
               (("02", "#4A235A"), ("03", "#6C3483"), ("04", "#8E44AD"), ("05", "#A569BD"))}
_BMH_CONTEXT = {code: (f"CTX {code}", colour) for code, colour in
                (("10", "#3A1F14"), ("11", "#4A2818"), ("20", "#512A18"), ("21", "#5E3019"),
                 ("40", "#874415"), ("50", "#A65D20"), ("60", "#B8742A"), ("70", "#7B5B3A"),
                 ("80", "#8D6E63"), ("90", "#6D4C41"))}
BMH_STYLE = _ne.EditorStyle(
    dialect=NG.BMH_COMMENTARY,
    marker_ui={meta[0]: (meta[1], meta[2]) for meta in NG.BMH_MARKER_META.values()},
    selector_names={**_BMH_RANDOM, **_BMH_CONTEXT},
    context_branch_count={"10": 2, "11": 2, "20": 2, "21": 3, "40": 4, "50": 2,
                          "60": 2, "70": 2, "80": 2, "90": 2},
    title="💬  Commentary Template Editor",
)
_EXE_TOKEN_RE = re.compile(r"%x[0-9A-Fa-f]{2}|%%|%[A-Za-z0-9]|#x(?![A-Za-z0-9])|#")


class BMHEncodeError(ValueError):
    pass


def decode_text(raw: bytes) -> str:
    """bytes -> editable text. Control/unknown bytes become \\xNN so the mapping is lossless."""
    out = []
    for b in raw:
        if b in _DE_DECODE:
            out.append(_DE_DECODE[b])
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
        else:
            out.append(f"\\x{b:02X}")
    return "".join(out)


def encode_text(text: str) -> bytes:
    out = bytearray()
    i = 0
    while i < len(text):
        m = _ESCAPE_RE.match(text, i)
        if m:
            value = int(m.group(1), 16)
            if value == 0:
                raise BMHEncodeError("\\x00 is the string terminator and cannot be used inside a text")
            out.append(value)
            i = m.end()
            continue
        ch = text[i]
        if ch in _DE_ENCODE:
            out.append(_DE_ENCODE[ch])
        elif 0x20 <= ord(ch) < 0x7F and ord(ch) not in _DE_DECODE:
            out.append(ord(ch))
        else:
            raise BMHEncodeError(f"Character {ch!r} is not available in ISO 646-DE (use \\xNN for raw bytes)")
        i += 1
    return bytes(out)


# ------------------------------------------------------------- database ----
class BMHFormatError(ValueError):
    pass


class TextDb:
    """Python counterpart of bmh::TextDb (strings / blob / offsets / raw)."""

    HEADER_SIZE = 7

    def __init__(self, strings, header=b"\0" * HEADER_SIZE, tail=b""):
        self.strings = list(strings)
        self.header = bytes(header)
        self.tail = bytes(tail)

    @property
    def blob(self) -> bytes:
        return b"".join(s + b"\0" for s in self.strings)

    @property
    def offsets(self):
        result, pos = [], 0
        for s in self.strings:
            result.append(pos)
            pos += len(s) + 1
        return result

    def raw(self, text_id: int, n: int) -> bytes:
        start = self.offsets[text_id]
        chunk = self.blob[start:start + n]
        return chunk + b"\0" * (n - len(chunk))

    def __getitem__(self, text_id):
        return self.strings[text_id]

    def to_bytes(self) -> bytes:
        return self.header + self.blob + self.tail

    @classmethod
    def from_bytes(cls, data: bytes) -> "TextDb":
        data = bytes(data)
        if len(data) < cls.HEADER_SIZE:
            raise BMHFormatError("File shorter than the 7-byte header")
        parts = data[cls.HEADER_SIZE:].split(b"\0")
        if len(parts) - 1 < TEXT_COUNT:
            raise BMHFormatError(f"Text database too short: {len(parts) - 1} strings, expected at least {TEXT_COUNT}")
        strings = parts[:TEXT_COUNT]
        consumed = cls.HEADER_SIZE + sum(len(x) + 1 for x in strings)
        return cls(strings, data[:cls.HEADER_SIZE], data[consumed:])


def load_textd(path) -> TextDb:
    with open(path, "rb") as handle:
        return TextDb.from_bytes(handle.read())


# ---------------------------------------------------------------- panel ----
class BMHStringsPanel(ttk.Frame):
    """String editor tab for the BMH text database, with the shared translation bar."""

    def __init__(self, parent, *, reg, translate_var, on_translate_toggle, on_change):
        super().__init__(parent)
        from translation_bar import TranslationBar  # project module, imported lazily

        self._reg = reg
        self._on_change = on_change
        self._translate_var = translate_var
        self.db = None
        self.path = None
        self.disk_bytes = b""
        self._strings = []
        self._original = []
        self._baseline = []
        self.current_id = None
        self._visible = []
        self._suspend = False

        search = ttk.Frame(self, padding=(15, 10, 15, 4))
        search.pack(fill=tk.X)
        self._search_frame = search
        ttk.Label(search, text="Search:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.search_var, font=("Segoe UI", 10))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        entry.bind("<Escape>", lambda _e: (self.search_var.set(""), "break")[1])
        self.modified_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(search, text="Modified only", variable=self.modified_only_var,
                        command=self._refresh_tree).pack(side=tk.LEFT, padx=(0, 12))
        self.counter = ttk.Label(search, text="0 / 0", font=("Segoe UI", 9, "bold"), foreground="#2980B9")
        self.counter.pack(side=tk.LEFT)
        self.search_var.trace_add("write", lambda *_: self._refresh_tree())

        box = ttk.Frame(self, padding=(15, 0, 15, 8))
        box.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(box, columns=("id", "offset", "text"), show="headings", selectmode="browse")
        for name, title, width, stretch in (("id", "ID", 55, False), ("offset", "Offset", 75, False), ("text", "Text", 400, True)):
            self.tree.heading(name, text=title)
            self.tree.column(name, anchor=tk.W if name == "text" else tk.CENTER, width=width, stretch=stretch)
        self.tree.tag_configure("modified", background="#FFF3CD")
        scroll = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        edit = ttk.LabelFrame(self, text="Edit string", padding=12)
        edit.pack(fill=tk.X, padx=15, pady=(5, 12))
        self._edit_frame = edit
        self.edit_text = tk.Text(edit, height=3, wrap="word", font=("Consolas", 12, "bold"), relief="solid",
                                 borderwidth=1, padx=5, pady=4, state=tk.DISABLED)
        self.edit_text.pack(fill=tk.X, pady=(0, 6))
        # same look as the main editor: every 0x20 is highlighted in blue
        self.edit_text.tag_configure("space_bg", background="#B3E5FC", foreground="#0288D1")
        self.edit_text.bind("<KeyRelease>", self._on_text_modified)
        self.edit_text.bind("<Return>", lambda _e: (self.apply_edit(), "break")[1])
        info = ttk.Frame(edit)
        info.pack(fill=tk.X)
        self._info_row = info
        self.info_label = ttk.Label(info, text="", font=("Segoe UI", 9, "bold"), foreground="#27AE60")
        self.info_label.pack(side=tk.LEFT)
        self.size_label = ttk.Label(info, text="", font=("Segoe UI", 9, "italic"), foreground="#2980B9")
        self.size_label.pack(side=tk.RIGHT)
        row = ttk.Frame(edit)
        row.pack(fill=tk.X, pady=(8, 0))
        self._btn_row = row
        self.apply_button = ttk.Button(row, text="Apply", command=self.apply_edit, state=tk.DISABLED)
        self.apply_button.pack(side=tk.RIGHT)
        self.discard_button = ttk.Button(row, text="Discard", command=self.discard_edit, state=tk.DISABLED)
        self.discard_button.pack(side=tk.RIGHT, padx=(0, 6))
        self.translate_check = ttk.Checkbutton(row, variable=translate_var, command=on_translate_toggle)
        reg(self.translate_check, "action.translation")
        self.translate_check.pack(side=tk.LEFT)

        self.bar = TranslationBar(edit, on_translate=self._translate_current_entry, reg=reg)

    # ---------------------------------------------------------------- state
    @property
    def loaded(self) -> bool:
        return self.db is not None

    def load(self, path, data: bytes):
        db = TextDb.from_bytes(data)  # raises BMHFormatError
        self.db, self.path, self.disk_bytes = db, path, bytes(data)
        self._strings = list(db.strings)
        self._original = list(db.strings)
        self._baseline = list(db.strings)
        self.current_id = None
        self.search_var.set("")
        self.modified_only_var.set(False)
        self._refresh_tree()
        self._set_edit_enabled(False)
        self._on_change()

    def clear(self):
        self.db = None
        self.path = None
        self.disk_bytes = b""
        self._strings, self._original, self._baseline = [], [], []
        self.current_id = None
        self.tree.delete(*self.tree.get_children())
        self._set_edit_text("")
        self._set_edit_enabled(False)
        self.counter.config(text="0 / 0")
        self.info_label.config(text="")
        self.size_label.config(text="")
        self.set_translate_enabled(False)

    def is_dirty(self) -> bool:
        return self.loaded and self._strings != self._baseline

    def has_pending_edit(self) -> bool:
        if not self.loaded or self.current_id is None:
            return False
        try:
            return encode_text(self._edit_value()) != self._strings[self.current_id]
        except BMHEncodeError:
            return True

    def payload(self) -> bytes:
        self.db.strings = list(self._strings)
        return self.db.to_bytes()

    def mark_saved(self, path, payload: bytes):
        self.path, self.disk_bytes = path, bytes(payload)
        self._baseline = list(self._strings)
        self._original = list(self._strings)
        self._refresh_tree()
        self._on_change()

    # ------------------------------------------------------------- tree/UI
    def _edit_value(self) -> str:
        return self.edit_text.get("1.0", "end-1c").replace("\n", "")

    def _set_edit_text(self, value):
        self.edit_text.config(state=tk.NORMAL)
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.insert("1.0", value)
        self._highlight_spaces()

    def _set_edit_enabled(self, enabled):
        self.edit_text.config(state=tk.NORMAL if enabled else tk.DISABLED)
        if not enabled:
            self.apply_button.config(state=tk.DISABLED)
            self.discard_button.config(state=tk.DISABLED)

    # hooks overridden by BMHExeStringsPanel
    def _offsets(self):
        return TextDb(self._strings).offsets

    def _check_raw(self, raw):
        """Extra validation of an encoded text; returns an error message or None."""
        return None

    def _size_text(self, raw):
        return f"{len(raw)} bytes (original {len(self._original[self.current_id])})"

    def _row_values(self, text_id, offsets):
        return (text_id, f"0x{offsets[text_id]:05X}", decode_text(self._strings[text_id]))

    def _refresh_tree(self):
        if not self.loaded:
            return
        needle = self.search_var.get().strip().lower()
        only_mod = self.modified_only_var.get()
        offsets = self._offsets()
        self.tree.delete(*self.tree.get_children())
        self._visible = []
        for i in range(len(self._strings)):
            if only_mod and self._strings[i] == self._original[i]:
                continue
            values = self._row_values(i, offsets)
            if needle and needle not in values[2].lower() and needle != str(i):
                continue
            tag = ("modified",) if self._strings[i] != self._original[i] else ()
            self.tree.insert("", tk.END, iid=str(i), values=values, tags=tag)
            self._visible.append(i)
        self.counter.config(text=f"{len(self._visible)} / {len(self._strings)}")
        if self.current_id is not None and self.tree.exists(str(self.current_id)):
            self.tree.selection_set(str(self.current_id))

    def refresh_texts(self):
        """Redisplay all strings (e.g. after the char map changed); raw bytes are untouched."""
        if not self.loaded:
            return
        self._refresh_tree()
        if self.current_id is not None:
            self._show(self.current_id)

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        new_id = int(sel[0])
        if new_id == self.current_id:
            return
        if self.has_pending_edit():
            if not messagebox.askyesno("BMH Strings", "The current text has pending changes. Discard them?"):
                if self.tree.exists(str(self.current_id)):
                    self.tree.selection_set(str(self.current_id))
                return
        self._show(new_id)

    def _show(self, text_id):
        self.current_id = text_id
        self._set_edit_text(decode_text(self._strings[text_id]))
        self._on_text_modified()

    def _highlight_spaces(self):
        """Blue background on every space (0x20) of the edit box."""
        widget = self.edit_text
        widget.tag_remove("space_bg", "1.0", tk.END)
        index = "1.0"
        while True:
            index = widget.search(" ", index, stopindex=tk.END)
            if not index:
                break
            widget.tag_add("space_bg", index, f"{index} + 1 chars")
            index = f"{index} + 1 chars"

    def _on_text_modified(self, _event=None):
        self._highlight_spaces()
        if self.current_id is None:
            return
        try:
            raw = encode_text(self._edit_value())
            err = None
        except BMHEncodeError as exc:
            raw, err = None, str(exc)
        if err is None:
            err = self._check_raw(raw)
        if err:
            self.info_label.config(text=err, foreground="#C0392B")
            self.size_label.config(text="")
        else:
            offset = self._offsets()[self.current_id]
            self.info_label.config(text=f"ID {self.current_id}  -  offset 0x{offset:05X}", foreground="#27AE60")
            self.size_label.config(text=self._size_text(raw))
        pending = err is not None or raw != self._strings[self.current_id]
        self.apply_button.config(state=tk.NORMAL if (pending and err is None) else tk.DISABLED)
        self.discard_button.config(state=tk.NORMAL if pending else tk.DISABLED)
        self._on_change()

    def apply_edit(self):
        if self.current_id is None:
            return False
        try:
            raw = encode_text(self._edit_value())
        except BMHEncodeError as exc:
            messagebox.showerror("BMH Strings", str(exc))
            return False
        problem = self._check_raw(raw)
        if problem:
            messagebox.showerror("BMH Strings", problem)
            return False
        self._strings[self.current_id] = raw
        self._refresh_tree()  # offsets of the following strings may shift
        self._on_text_modified()
        return True

    def discard_edit(self):
        if self.current_id is not None:
            self._show(self.current_id)

    # ----------------------------------------------------------- translator
    def set_translate_enabled(self, enabled: bool):
        if enabled and not self.bar.winfo_manager():
            self.bar.pack(fill=tk.X, pady=(8, 0))
        elif not enabled and self.bar.winfo_manager():
            self.bar.pack_forget()

    def apply_defaults(self, *, source_label=None, target_language=None):
        # TranslationBar owns the language lists; failures here must never block loading.
        try:
            if source_label:
                self.bar.set_default_source_from_profile(source_label)
            if target_language:
                self.bar.set_default_target_from_language(target_language)
        except Exception:
            pass

    @classmethod
    def _protected_patterns(cls):
        """Regexes whose matches are never sent to the translation engine (\\xNN always)."""
        return (_ESCAPE_RE,)

    @classmethod
    def _translate_text(cls, translate_fn, text):
        """Translate text chunk by chunk so control codes are never sent to the engine."""
        return cls._translate_chunks(translate_fn, text, cls._protected_patterns())

    @staticmethod
    def _translate_chunks(translate_fn, text, patterns):
        spans = sorted((m.start(), m.end()) for rx in patterns for m in rx.finditer(text))
        merged = []
        for start, end in spans:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        out, cursor = [], 0
        for start, end in merged + [(len(text), len(text))]:
            part = text[cursor:start]
            if re.search(r"\w", part):
                lead = part[:len(part) - len(part.lstrip())]
                trail = part[len(part.rstrip()):]
                out.append(lead + translate_fn(part.strip()) + trail)
            else:
                out.append(part)
            out.append(text[start:end])
            cursor = end
        return "".join(out)

    def _translate_current_entry(self, translate_fn):
        if self.current_id is None:
            return
        translated = self._translate_text(translate_fn, self._edit_value()).replace("\n", " ")
        self._set_edit_text(translated)
        self._on_text_modified()

    def translate_all(self, root):
        if not self.loaded:
            messagebox.showinfo("Translate all", "No text file loaded.")
            return
        if self.has_pending_edit() and not self.apply_edit():
            return
        ids = [i for i, s in enumerate(self._strings) if re.search(r"[A-Za-z\xC4\xD6\xDC\xE4\xF6\xFC]", decode_text(s))]
        ids = self._ask_translate_range(root, ids)
        if not ids:
            return
        translate_fn = self.bar.make_translate_fn()
        win = tk.Toplevel(root)
        win.title("Translate all")
        win.resizable(False, False)
        win.grab_set()
        ttk.Label(win, text="Translating...", font=("Segoe UI", 10, "bold"), padding=10).pack()
        var = tk.IntVar(value=0)
        ttk.Progressbar(win, maximum=len(ids), variable=var, length=360).pack(padx=20, pady=(0, 6))
        status = ttk.Label(win, text="", font=("Segoe UI", 9, "italic"), padding=(10, 0, 10, 10))
        status.pack()
        win.update()
        results, skipped, error = {}, 0, None
        try:
            for n, text_id in enumerate(ids, 1):
                source = decode_text(self._strings[text_id])
                status.config(text=f"{n}/{len(ids)}  {source[:50]}")
                var.set(n)
                win.update()
                try:
                    translated = self._translate_text(translate_fn, source)
                except TranslationIntegrityError:
                    skipped += 1
                    continue
                except Exception as exc:
                    error = exc          # engine failure: stop, keep what is done
                    break
                try:
                    results[text_id] = encode_text(translated)
                except BMHEncodeError:
                    skipped += 1  # translated text has characters the game charset cannot hold
        finally:
            win.destroy()
        if error is not None and not results:
            messagebox.showerror("Translate all", f"Translation aborted, nothing was changed.\n\n{error}")
            return
        changed = 0
        for text_id, raw in results.items():
            if raw != self._strings[text_id]:
                self._strings[text_id] = raw
                changed += 1
        self._refresh_tree()
        if self.current_id is not None:
            self._show(self.current_id)
        self._on_change()
        summary = (f"Translated: {changed}\nUnchanged: {len(results) - changed}\n"
                   f"Skipped (characters not in ISO 646-DE / altered tokens): {skipped}")
        if error is not None:
            messagebox.showwarning("Translate all", summary + "\n\nTranslation interrupted by an error; "
                                   f"strings translated before it were applied:\n{str(error)[:300]}")
        else:
            messagebox.showinfo("Translate all", summary)

    def _ask_translate_range(self, root, ids):
        """Ask for an inclusive ID range (IDs as shown in the table); returns the ids inside it."""
        if not ids:
            messagebox.showinfo("Translate all", "No translatable strings found.")
            return None
        lo_all, hi_all = min(ids), max(ids)
        win = tk.Toplevel(root)
        win.title("Translate all")
        win.resizable(False, False)
        win.transient(root)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text=f"Translatable strings: {len(ids)} (IDs {lo_all}-{hi_all})").grid(
            row=0, column=0, columnspan=4, sticky="w")
        from_var, to_var = tk.StringVar(value=str(lo_all)), tk.StringVar(value=str(hi_all))
        ttk.Label(frm, text="From ID").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=from_var, width=8).grid(row=1, column=1, padx=(4, 12))
        ttk.Label(frm, text="To ID").grid(row=1, column=2, sticky="w")
        ttk.Entry(frm, textvariable=to_var, width=8).grid(row=1, column=3, padx=(4, 0))
        info = ttk.Label(frm, text="", font=("Segoe UI", 9, "bold"))
        info.grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 8))
        row = ttk.Frame(frm)
        row.grid(row=3, column=0, columnspan=4, sticky="e")
        ok = ttk.Button(row, text="Start")
        ok.pack(side=tk.LEFT, padx=(0, 6))
        result = {"ids": None}

        def compute():
            try:
                lo = int(from_var.get().strip().lstrip("#") or lo_all)
                hi = int(to_var.get().strip().lstrip("#") or hi_all)
            except ValueError:
                return None
            return None if hi < lo else [i for i in ids if lo <= i <= hi]

        def update(*_):
            sel = compute()
            if sel is None:
                info.config(text="Invalid range", foreground="#C0392B")
                ok.config(state=tk.DISABLED)
            else:
                info.config(text=f"{len(sel)} strings selected", foreground="#1565C0")
                ok.config(state=tk.NORMAL if sel else tk.DISABLED)

        def accept(*_):
            sel = compute()
            if sel:
                result["ids"] = sel
                win.destroy()

        ok.config(command=accept)
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side=tk.LEFT)
        for var in (from_var, to_var):
            var.trace_add("write", update)
        win.bind("<Return>", accept)
        win.bind("<Escape>", lambda _e: win.destroy())
        update()
        win.grab_set()
        win.wait_window()
        return result["ids"]


# ------------------------------------------------------------ EXE strings ----
class BMHExeStringsPanel(BMHStringsPanel):
    """Strings stored inside a supported BMH.EXE (LE executable).

    Same UI as the TEXT*.BLK tab.  The model is BMHExeStrings: a string that outgrows its slot is
    moved into free space and only the pointer to it is patched.  The "EXE space" bar in the edit
    box shows how much of the room available for these strings is used.
    """

    def __init__(self, parent, space_bar_factory=None, **kwargs):
        """space_bar_factory(parent) -> the free-space bar widget (FreeSpaceBar of main_editor.py:
        it is defined there once and handed in, to avoid a circular import)."""
        super().__init__(parent, **kwargs)
        self._template_active = False
        self._translate_on = False
        self.template_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self._btn_row, text="Template editor", variable=self.template_var,
                        command=self._sync_template_panel).pack(side=tk.LEFT, padx=(12, 0))
        # the same editor as the newspaper strings: replaces the plain text box for templates
        self.template_panel = _ne.NewspaperEditorPanel(
            self._edit_frame, self, on_show=self._template_shown, on_hide=self._template_hidden,
            style=BMH_STYLE, codec=(self._template_decode, self._template_encode),
            commit=self._commit_template,
            pack_kwargs={"fill": tk.X, "pady": (0, 6), "before": self._info_row})
        self.space_bar = space_bar_factory(self._edit_frame) if space_bar_factory else None
        if self.space_bar is not None:
            self.space_bar.pack(fill=tk.X, pady=(8, 0), before=self._btn_row)

    # --------------------------------------------------------------- state
    def load(self, path, data: bytes):
        model = BMHExeStrings(data)            # raises BMHExeError
        self.db, self.path, self.disk_bytes = model, path, bytes(data)
        self._strings = list(model.strings)
        self._original = list(model.strings)
        self._baseline = list(model.strings)
        self._hide_template()
        self.current_id = None
        self.search_var.set("")
        self.modified_only_var.set(False)
        self._refresh_tree()
        self._set_edit_enabled(False)
        self._on_change()

    def clear(self):
        self._hide_template()
        super().clear()
        if self.space_bar is not None:
            self.space_bar.clear()

    def mark_saved(self, path, payload: bytes):
        # re-read the written image: moved strings now live elsewhere and are the new baseline
        model = BMHExeStrings(payload)
        keep = self.current_id if self.current_id is not None and self.current_id < len(model.strings) else None
        self.db, self.path, self.disk_bytes = model, path, bytes(payload)
        self._strings = list(model.strings)
        self._baseline = list(model.strings)
        self._original = list(model.strings)
        self.current_id = keep
        self._refresh_tree()
        self._on_change()

    # ------------------------------------------------------------ grammar
    # Commentary strings are templates (selectors %xNN ... #x with "#"-separated branches and %c/%z/%0
    # markers).  Same language as the newspaper strings of the MZ games: newspaper_grammar.py with the
    # BMH_COMMENTARY dialect (terminator "#x").
    @staticmethod
    def _is_template(text):
        return "%x" in text

    @classmethod
    def _template_rows(cls, text, string_id="?"):
        return NG.components(text, string_id, NG.BMH_COMMENTARY)

    @classmethod
    def _translate_text(cls, translate_fn, text):
        """Templates are translated component by component (one branch at a time) and rebuilt, so the
        structure can never be damaged; any other text is protected token by token."""
        if cls._is_template(text):
            try:
                rows = cls._template_rows(text)
            except NG.NewspaperGrammarError:
                rows = None
            if rows is not None:
                patterns = (_ESCAPE_RE, NG.MARKER_PATTERN)
                for row in rows:
                    row["translated_text"] = cls._translate_chunks(translate_fn, row["source_text"], patterns)
                try:
                    return NG.rebuild(rows, "?", NG.BMH_COMMENTARY)
                except NG.NewspaperGrammarError as exc:
                    raise TranslationIntegrityError(str(exc))
        return cls._translate_chunks(translate_fn, text, cls._protected_patterns())

    def _grammar_problem(self, index, raw):
        """Error text when a string that is (or was) a template no longer parses, else None."""
        text, original = raw.decode("latin-1"), self._original[index].decode("latin-1")
        if not (self._is_template(text) or self._is_template(original)):
            return None
        try:
            NG.parse(text, str(index), NG.BMH_COMMENTARY)
        except NG.NewspaperGrammarError as exc:
            return "Template grammar error: " + str(exc)
        return None

    def _structure(self, raw):
        try:
            return NG.selector_codes(raw.decode("latin-1"), "?", NG.BMH_COMMENTARY)
        except NG.NewspaperGrammarError:
            return None

    # ---------------------------------------------------- template editor
    @property
    def translation_bar(self):
        return self.bar                       # shared with the template editor's own bar

    @staticmethod
    def _template_decode(_entry, text):
        return decode_text(text.encode("latin-1", errors="replace"))

    @staticmethod
    def _template_encode(_entry, text):
        try:
            return encode_text(text).decode("latin-1")
        except BMHEncodeError as exc:
            raise CharmapEncodeError(str(exc)) from exc

    def _parses(self, text):
        try:
            NG.parse(text, "?", NG.BMH_COMMENTARY)
            return True
        except NG.NewspaperGrammarError:
            return False

    def _hide_template(self):
        if self.template_panel.winfo_manager():
            self.template_panel.hide()

    def _sync_template_panel(self):
        """Template strings are edited with the newspaper editor, every other string in the text box."""
        if not self.loaded or self.current_id is None:
            self._hide_template()
            return
        text = self._strings[self.current_id].decode("latin-1")
        if self.template_var.get() and self._is_template(text) and self._parses(text):
            entry = {"string_id": f"#{self.current_id}", "text": text}
            self.template_panel.show(entry, decode_fn=lambda e: e["text"],
                                     translate_enabled=self._translate_on)
        else:
            self._hide_template()

    def _template_shown(self):
        self._template_active = True
        self.edit_text.pack_forget()
        if self.bar.winfo_manager():          # the template editor has its own translation bar
            self.bar.pack_forget()
        self.info_label.config(text=f"ID {self.current_id}  -  offset 0x{self._offsets()[self.current_id]:05X}",
                               foreground="#27AE60")
        self._update_save_state()

    def _template_hidden(self):
        self._template_active = False
        if not self.edit_text.winfo_manager():
            self.edit_text.pack(fill=tk.X, pady=(0, 6), before=self._info_row)
        if self._translate_on and not self.bar.winfo_manager():
            self.bar.pack(fill=tk.X, pady=(8, 0))
        if self.loaded and self.current_id is not None:
            self._set_edit_text(decode_text(self._strings[self.current_id]))
            self._on_text_modified()

    def _commit_template(self, _entry, rebuilt):
        raw = rebuilt.encode("latin-1")
        problem = self._check_raw(raw)
        if problem:
            return problem
        self._strings[self.current_id] = raw
        self._refresh_tree()
        self._set_edit_text(decode_text(raw))
        self._update_save_state()
        return None

    def _update_save_state(self):
        """Called by the template editor on every change (and by us): buttons, size and space."""
        if self._template_active and self.current_id is not None:
            dirty = self.template_panel.is_dirty()
            rebuilt = self.template_panel._get_rebuilt_template()
            problem = None
            if rebuilt is not None:
                raw = rebuilt.encode("latin-1")
                problem = self._check_raw(raw)
                if problem is None:
                    self.size_label.config(text=self._size_text(raw))
                else:
                    self.size_label.config(text="")
            self.apply_button.config(state=tk.NORMAL if (dirty and rebuilt is not None and problem is None)
                                     else tk.DISABLED)
            self.discard_button.config(state=tk.NORMAL if dirty else tk.DISABLED)
            if problem:
                self.info_label.config(text=problem, foreground="#C0392B")
        self._on_change()

    def has_pending_edit(self):
        if self._template_active:
            return self.template_panel.is_dirty()
        return super().has_pending_edit()

    def apply_edit(self):
        if self._template_active:
            self.template_panel.apply()
            return not self.template_panel.is_dirty()
        return super().apply_edit()

    def discard_edit(self):
        if self._template_active:
            self.template_panel.discard()
            self._update_save_state()
            return
        super().discard_edit()

    def _show(self, text_id):
        super()._show(text_id)
        self._sync_template_panel()

    def set_translate_enabled(self, enabled):
        self._translate_on = bool(enabled)
        if self._template_active:
            if self.bar.winfo_manager():
                self.bar.pack_forget()
            self.template_panel.refresh_translation(self._translate_on)
        else:
            super().set_translate_enabled(enabled)

    def payload(self) -> bytes:
        for index, (raw, old) in enumerate(zip(self._strings, self._baseline)):
            if raw != old:
                problem = self._grammar_problem(index, raw)
                if problem:
                    raise BMHExeError(f"String #{index}: {problem}")
        return super().payload()

    # --------------------------------------------------------------- hooks
    @classmethod
    def _protected_patterns(cls):
        extra = (_EXE_TOKEN_RE,) + ((_SHARED_TOKENS,) if _SHARED_TOKENS is not None else ())
        return (_ESCAPE_RE,) + extra

    def _offsets(self):
        return self.db.offsets

    def _check_raw(self, raw):
        if not raw:
            return "Empty text is not supported in the EXE (use a single space)."
        return self._grammar_problem(self.current_id, raw) if self.current_id is not None else None

    def _planned(self, pending=None):
        strings = list(self._strings)
        if pending is not None and self.current_id is not None:
            strings[self.current_id] = pending
        return strings

    def _size_text(self, raw):
        item = self.db.items[self.current_id]
        status = self.db.status(self.current_id, raw)
        if status == "moved":
            note = "will be relocated"
        elif status == "in place":
            note = "fits its slot"
        else:
            note = "unchanged"
        self._update_space(self._planned(raw))
        text = f"{len(raw)} / {item.slot - 1} bytes in place - {note}"
        if self._is_template(raw.decode("latin-1")):
            same = self._structure(raw) == self._structure(self._original[self.current_id])
            text += " - template OK" if same else " - template structure changed"
        return text

    def _update_space(self, strings=None):
        """Bytes needed by the current texts / room available for these strings."""
        if self.space_bar is None:
            return
        if not self.loaded:
            self.space_bar.clear()
            return
        info = self.db.space_info(self._strings if strings is None else strings)
        capacity = max(1, info["capacity"])
        percent = 100.0 * info["used"] / capacity
        if not info["ok"]:
            text = f"{info['used']:,} / {info['capacity']:,} bytes - NOT ENOUGH SPACE"
        else:
            text = f"{info['used']:,} / {info['capacity']:,} bytes ({percent:.0f}%) - {info['free']:,} free"
            if info["cave"]:
                text += f" (incl. {info['cave']:,} added free bytes, {info['cave_used']:,} used)"
            if info["moved"]:
                text += f" - {info['moved']} moved"
        self.space_bar.set(info["used"], capacity, text, error=not info["ok"])

    def _refresh_tree(self):
        super()._refresh_tree()
        self._update_space()


def show_exe_preview(root, panel):
    """Changes preview for the EXE strings (BMH counterpart of preview_dialog.show_preview_dialog,
    which needs MZ-profile data): what is going to be written, where it goes and which pointers move."""
    model = panel.db
    strings = list(panel._strings)
    changed = [i for i, (old, new) in enumerate(zip(panel._baseline, strings)) if old != new]
    plan, problem = None, ""
    try:
        plan = model.plan(strings)
    except BMHExeError as exc:
        problem = str(exc)
    info = model.space_info(strings)
    dialog = tk.Toplevel(root)
    dialog.title("BMH EXE Strings - changes preview")
    dialog.geometry("1100x640")
    dialog.minsize(800, 420)
    dialog.transient(root)
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
    tabs = {name: ttk.Frame(notebook) for name in ("Summary", "Strings", "Pointers")}
    for name, frame in tabs.items():
        notebook.add(frame, text="  %s  " % name)

    relocated = len(plan.moved) if plan else 0
    lines = [
        "Profile: %s" % model.profile_name,
        "File: %s" % (panel.path or ""),
        "",
        "Strings changed: %d" % len(changed),
        "Strings written elsewhere (pointer patched): %d%s" % (
            relocated, "  (every string laid out again)" if plan and plan.repacked else ""),
        "Space used by the texts: %s / %s bytes (%s free)" % (
            format(info["used"], ","), format(info["capacity"], ","), format(info["free"], ",")),
    ]
    if info["cave"]:
        lines.append("Added free space (not part of the original strings): %s / %s bytes used" % (
            format(info["cave_used"], ","), format(info["cave"], ",")))
    lines.append("Save possible: %s" % ("yes" if info["ok"] and not panel.has_pending_edit() else "NO"))
    if problem:
        lines += ["", "Reason:", "- " + problem]
    summary = tk.Text(tabs["Summary"], wrap="word", font=("Consolas", 10), padx=12, pady=12)
    summary.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    summary.insert("1.0", "\n".join(lines))
    summary.config(state=tk.DISABLED)

    tree = make_preview_tree(tabs["Strings"], [
        ("status", "Status", 90, tk.CENTER), ("id", "ID", 50, tk.E),
        ("offset", "Offset", 90, tk.CENTER), ("newoffset", "New offset", 90, tk.CENTER),
        ("oldlen", "Old bytes", 70, tk.E), ("newlen", "New bytes", 70, tk.E),
        ("slot", "Slot", 55, tk.E), ("ptrs", "Pointers", 65, tk.E),
        ("old", "Old text", 260, tk.W), ("new", "New text", 260, tk.W),
    ])
    pointers = make_preview_tree(tabs["Pointers"], [
        ("source", "Pointer at", 110, tk.CENTER), ("id", "String ID", 80, tk.E),
        ("old", "Old target", 130, tk.CENTER), ("new", "New target", 130, tk.CENTER),
    ])
    for i in changed:
        item = model.items[i]
        old_off = model._file_offset(item.obj, item.off)
        if plan and i in plan.moved:
            new_off = model._file_offset(*plan.moved[i])
            status = "PENDING" if not problem else "FAIL"
            state = "relocated"
        else:
            new_off, state = old_off, ("in place" if not problem else "no space")
            status = "PENDING" if not problem else "FAIL"
        tree.insert("", tk.END, values=(
            state, i, f"0x{old_off:X}", f"0x{new_off:X}", len(panel._baseline[i]), len(strings[i]),
            item.slot - 1, len(item.sources), decode_text(panel._baseline[i]), decode_text(strings[i]),
        ), tags=(status,))
        if plan and i in plan.moved and new_off != old_off:
            for f in item.sources:
                pointers.insert("", tk.END, values=(
                    f"0x{f.src_lin:X}", i, f"0x{old_off:X}", f"0x{new_off:X}"))
    ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=(2, 10))
    return dialog

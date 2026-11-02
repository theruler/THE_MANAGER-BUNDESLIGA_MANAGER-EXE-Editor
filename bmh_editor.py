"""Bundesliga Manager Hattrick (BMH) - string editor support.

Games handled (the EXE itself is NOT parsed yet, only the text file next to it):
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


# ---------------------------------------------------------------- codec ----
# DIN 66003 / ISO 646-DE: the 7-bit German national variant.
_DE_DECODE = {0x40: "§", 0x5B: "Ä", 0x5C: "Ö", 0x5D: "Ü",
              0x7B: "ä", 0x7C: "ö", 0x7D: "ü", 0x7E: "ß"}
_DE_ENCODE = {ch: code for code, ch in _DE_DECODE.items()}
_ESCAPE_RE = re.compile(r"\\x([0-9A-Fa-f]{2})")


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
        elif 0x20 <= ord(ch) < 0x7F and ch not in "@[\\]{|}~":
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
        self.edit_text = tk.Text(edit, height=3, wrap="word", font=("Consolas", 12, "bold"), relief="solid",
                                 borderwidth=1, padx=5, pady=4, state=tk.DISABLED)
        self.edit_text.pack(fill=tk.X, pady=(0, 6))
        self.edit_text.bind("<KeyRelease>", self._on_text_modified)
        self.edit_text.bind("<Return>", lambda _e: (self.apply_edit(), "break")[1])
        info = ttk.Frame(edit)
        info.pack(fill=tk.X)
        self.info_label = ttk.Label(info, text="", font=("Segoe UI", 9, "bold"), foreground="#27AE60")
        self.info_label.pack(side=tk.LEFT)
        self.size_label = ttk.Label(info, text="", font=("Segoe UI", 9, "italic"), foreground="#2980B9")
        self.size_label.pack(side=tk.RIGHT)
        row = ttk.Frame(edit)
        row.pack(fill=tk.X, pady=(8, 0))
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

    def _set_edit_enabled(self, enabled):
        self.edit_text.config(state=tk.NORMAL if enabled else tk.DISABLED)
        if not enabled:
            self.apply_button.config(state=tk.DISABLED)
            self.discard_button.config(state=tk.DISABLED)

    def _row_values(self, text_id, offsets):
        return (text_id, f"0x{offsets[text_id]:05X}", decode_text(self._strings[text_id]))

    def _refresh_tree(self):
        if not self.loaded:
            return
        needle = self.search_var.get().strip().lower()
        only_mod = self.modified_only_var.get()
        offsets = TextDb(self._strings).offsets
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

    def _on_text_modified(self, _event=None):
        if self.current_id is None:
            return
        try:
            raw = encode_text(self._edit_value())
            err = None
        except BMHEncodeError as exc:
            raw, err = None, str(exc)
        original_len = len(self._original[self.current_id])
        if err:
            self.info_label.config(text=err, foreground="#C0392B")
            self.size_label.config(text="")
        else:
            offset = TextDb(self._strings).offsets[self.current_id]
            self.info_label.config(text=f"ID {self.current_id}  -  offset 0x{offset:05X}", foreground="#27AE60")
            self.size_label.config(text=f"{len(raw)} bytes (original {original_len})")
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

    @staticmethod
    def _translate_text(translate_fn, text):
        """Translate text chunk by chunk so \\xNN control codes are never sent to the engine."""
        parts = _ESCAPE_RE.split(text)  # even index = text, odd index = captured hex digits
        out = []
        for index, part in enumerate(parts):
            if index % 2:
                out.append("\\x" + part)
            elif re.search(r"\w", part):
                lead = part[:len(part) - len(part.lstrip())]
                trail = part[len(part.rstrip()):]
                out.append(lead + translate_fn(part.strip()) + trail)
            else:
                out.append(part)
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
        if not ids or not messagebox.askyesno("Translate all", f"Translate {len(ids)} strings with the selected engine?"):
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
        results, skipped = {}, 0
        try:
            for n, text_id in enumerate(ids, 1):
                source = decode_text(self._strings[text_id])
                status.config(text=f"{n}/{len(ids)}  {source[:50]}")
                var.set(n)
                win.update()
                translated = self._translate_text(translate_fn, source)
                try:
                    results[text_id] = encode_text(translated)
                except BMHEncodeError:
                    skipped += 1  # translated text has characters the game charset cannot hold
        except Exception as exc:
            win.destroy()
            messagebox.showerror("Translate all", f"Translation aborted, nothing was changed.\n\n{exc}")
            return
        win.destroy()
        changed = 0
        for text_id, raw in results.items():
            if raw != self._strings[text_id]:
                self._strings[text_id] = raw
                changed += 1
        self._refresh_tree()
        if self.current_id is not None:
            self._show(self.current_id)
        self._on_change()
        messagebox.showinfo("Translate all", f"Translated: {changed}\nUnchanged: {len(results) - changed}\n"
                                             f"Skipped (characters not in ISO 646-DE): {skipped}")

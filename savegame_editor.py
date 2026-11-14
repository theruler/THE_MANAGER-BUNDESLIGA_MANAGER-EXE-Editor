"""BMP / THE MANAGER savegame (.MAN) editor.

Works in two ways:
  * standalone:   python savegame_editor.py [cartella | file.MAN]
  * as a tab:     SavegamePanel(parent, standalone=False) inside the main editor.
                  The host calls panel.set_dir(<cartella dell'EXE>) and the panel lists every
                  .MAN found there; picking one opens it.

Layout (nested notebooks):
  Manager     Profilo (con ritratto 0.VGA e logo club da .\\PIC) | Storico | Statistiche
  Squadra     Rosa | Giocatori | Mercato
  Economia    Stadio | Prestiti | Sponsor
  Campionato  Classifica | Risultati | Calendario
  Coppe       Stato | Accoppiamenti
  Club        Dati club | Classifica estesa | Serie in corso | Record | Scontri diretti
  Messaggi
  Avanzate    Blocchi grezzi (dati non ancora decifrati, offset reali del file)
"""
from __future__ import annotations
import os
import re
import shutil
import struct
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw

import i18n

APP_TITLE = "BMP / THE MANAGER Savegame Editor"
ICON_FILE = "THE_MANAGER_String_Editor.ico"

# --------------------------------------------------------------------------- PALETTE & VGA DECODE (Native Integration)
def _hex_palette(s: str, scale: int = 1) -> list[tuple[int, int, int]]:
    return [
        (min(255, int(s[i:i+2], 16) * scale),
         min(255, int(s[i+2:i+4], 16) * scale),
         min(255, int(s[i+4:i+6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]

_PAL_NORMAL20 = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040C10303C3C002C281C24201420181018100C140C083C3C3C300C300000003F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4)

def _palette_to_flat_rgb(pal: list[tuple[int, int, int]], size: int = 256) -> list[int]:
    flat: list[int] = []
    for r, g, b in pal:
        flat.extend((r, g, b))
    while len(flat) < size * 3:
        flat.extend((0, 0, 0))
    return flat[:size * 3]

def _decode_vga(data: bytes, fmt: str = "BMP"):
    header_len = 8 if fmt == "BMH" else 6
    if len(data) < header_len + 1:
        return None
    width = data[0] | (data[1] << 8)
    height = data[2] | (data[3] << 8)
    payload_len = int.from_bytes(data[4:header_len], "little")
    if width <= 0 or height <= 0 or width > 1280 or height > 960 or payload_len < 1:
        return None
    payload_end = header_len + payload_len - 1
    if payload_end >= len(data):
        return None
    offset = data[payload_end] - 1
    if offset < 1:
        return None
    pixels = bytearray()
    i = header_len
    target = width * height
    while i < payload_end and len(pixels) < target:
        b = data[i]
        if b > offset + 1:
            if i + 1 >= payload_end:
                return None
            count = b - offset
            pixels.extend((data[i + 1],) * count)
            i += 2
        elif b == offset + 1:
            i += 1
        else:
            count = b + 1
            if i + count >= payload_end:
                return None
            pixels.extend(data[i + 1:i + 1 + count])
            i += count + 1
    if len(pixels) != target:
        return None
    return width, height, bytes(pixels), bytes(data[payload_end + 1:])

def load_vga_image_safe(path: str) -> Image.Image | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
        res = _decode_vga(data, "BMH") or _decode_vga(data, "BMP")
        if not res:
            return None
        w, h, pix, trailer = res
        img = Image.frombytes("P", (w, h), pix)
        pal = _PAL_NORMAL20
        if len(trailer) >= 768:
            pal = [(trailer[i]*4, trailer[i+1]*4, trailer[i+2]*4) for i in range(0, 768, 3)]
        img.putpalette(_palette_to_flat_rgb(pal))
        return img
    except Exception:
        return None

# --------------------------------------------------------------------------- PIC (manager portraits)
FACE_W, FACE_STEP, FACE_ZOOM = 40, 41, 3     # 0.VGA: 4 volti 40x40 a passo 41 px, poi 0a.VGA, 0b.VGA ...


def find_pic_dir(*bases):
    """Cartella PIC (case-insensitive) in una delle basi o nella loro cartella superiore."""
    seen = set()
    for base in bases:
        if not base:
            continue
        for d in (base, os.path.dirname(os.path.abspath(base))):
            d = os.path.abspath(d)
            if d in seen:
                continue
            seen.add(d)
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for n in names:
                p = os.path.join(d, n)
                if n.lower() == "pic" and os.path.isdir(p):
                    return p
    return None


def load_faces(pic_dir):
    """[(stem, indice, PIL.Image 40x40)] di tutti i volti: 0.VGA, poi 0a.VGA, 0b.VGA... se esistono."""
    out = []
    if not pic_dir:
        return out
    try:
        names = {n.lower(): n for n in os.listdir(pic_dir)}
    except OSError:
        return out
    for stem in ["0"] + ["0" + ch for ch in "abcdefghijklmnopqrstuvwxyz"]:
        real = names.get(stem + ".vga")
        img = load_vga_image_safe(os.path.join(pic_dir, real)) if real else None
        if img is None:
            if stem == "0":
                continue
            break
        img = img.convert("RGB")
        for i in range((img.width + 1) // FACE_STEP):
            if i * FACE_STEP + FACE_W <= img.width and img.height >= FACE_W:
                out.append((stem, i, img.crop((i * FACE_STEP, 0, i * FACE_STEP + FACE_W, FACE_W))))
    return out


# --------------------------------------------------------------------------- STYLE
BG, FG, MUTED = "#F4F6F9", "#2C3E50", "#7F8C8D"
ACCENT, ERR, OK = "#2980B9", "#C0392B", "#27AE60"

# own translator: data/lang/savegame_<code>.py  (same loader as the main editor, different prefix)
_TR = i18n.Translator("savegame_")


def T(key, **fmt):
    return _TR.tr(key, **fmt)


# =========================================================================== FORMAT / CORE (no Tk)
SIG = b"WeRnEr_krahe~&~JeNs_onnen>V2\x00"
MB, CB, PB, LB = 2345, 5557, 15813, 21400      # managers, clubs, players, squad tables
CHK1, FIX = 28006, 34368                         # first checksum byte, start of the message block
H = 28435                                        # base of the records / series tables
N_MANAGERS_OFF = 2339
SEASONS_COUNT_OFF = 34224

_FMT = {"u8": "<B", "i16": "<h", "u16": "<H", "i32": "<i"}
_LIMITS = {"u8": (0, 255), "i16": (-32768, 32767), "u16": (0, 65535), "i32": (-2 ** 31, 2 ** 31 - 1)}


class SaveError(Exception):
    """args[0] is an i18n key (data/lang/savegame_*.py)."""

    def __str__(self):
        return T(self.args[0])


def _crypt(src, dst, a, b, st, enc):
    """Stream cipher c = k + (k ^ p) (mod 256), k += 0xD7.  st = [key, checksum]; the checksum is
    the running sum of the PLAIN bytes."""
    k, c = st
    if enc:
        for i in range(a, b):
            p = src[i]
            dst[i] = (k + (k ^ p)) & 255
            c = (c + p) & 255
            k = (k + 0xD7) & 255
    else:
        for i in range(a, b):
            p = ((src[i] - k) & 255) ^ k
            dst[i] = p
            c = (c + p) & 255
            k = (k + 0xD7) & 255
    st[0], st[1] = k, c


def pos4(v):
    return T("pos.gk" if v < 25 else "pos.df" if v < 50 else "pos.mf" if v < 75 else "pos.fw")


class SaveFile:
    """Decrypted savegame held in memory (self.buf is the plaintext)."""

    def __init__(self, path, data):
        self.path = path
        self.original = bytes(data)
        self.buf, self.mend = self._decode(self.original)
        self.roundtrip_ok = self.encode() == self.original
        self.dirty = False

    # ----- crypto -----
    @staticmethod
    def _decode(data):
        if len(data) < FIX + 1:
            raise SaveError("err.too_short")
        if data[:len(SIG)] != SIG:
            raise SaveError("err.bad_sig")
        try:
            p = bytearray(data)
            st = [data[34], data[34]]
            _crypt(data, p, 35, CHK1, st, False)
            if st[1] != data[CHK1]:
                raise SaveError("err.chk1")
            _crypt(data, p, CHK1 + 1, FIX, st, False)
            pos = FIX
            for m in range(p[N_MANAGERS_OFF]):
                for _ in range(p[41 + m]):
                    _crypt(data, p, pos, pos + 5, st, False)
                    n = p[pos + 4]
                    _crypt(data, p, pos + 5, pos + 5 + n, st, False)
                    pos += 5 + n
            if st[1] != data[pos]:
                raise SaveError("err.chk2")
        except IndexError:
            raise SaveError("err.truncated")
        return p, pos

    def encode(self):
        o = bytearray(self.buf)
        st = [self.buf[34], self.buf[34]]
        _crypt(self.buf, o, 35, CHK1, st, True)
        o[CHK1] = st[1]
        _crypt(self.buf, o, CHK1 + 1, self.mend, st, True)
        o[self.mend] = st[1]
        return bytes(o)

    # ----- field access -----
    def rd(self, off, t="u8"):
        return struct.unpack_from(_FMT[t], self.buf, off)[0]

    def wr(self, off, t, value):
        lo, hi = _LIMITS[t]
        try:
            v = int(round(float(value)))
        except (TypeError, ValueError):
            v = 0
        struct.pack_into(_FMT[t], self.buf, off, max(lo, min(hi, v)))
        self.dirty = True

    def get_str(self, off, n):
        raw = bytes(self.buf[off:off + n])
        z = raw.find(0)
        return (raw if z < 0 else raw[:z]).decode("latin-1")

    def set_str(self, off, n, s):
        raw = s.encode("latin-1", "replace")[:n - 1]
        self.buf[off:off + n] = raw + bytes(n - len(raw))
        self.dirty = True

    # ----- lookups -----
    @property
    def n_managers(self):
        return self.buf[N_MANAGERS_OFF]

    def manager_name(self, m):
        return self.get_str(MB + 778 * m, 29)

    def club_name(self, i):
        return self.get_str(CB + 34 * i, 23) if 0 <= i < 200 else ""

    def club_ids(self, limit=200):
        return [i for i in range(limit) if self.club_name(i)]

    # ----- messages (variable-length block: 4 ptr bytes + len + text) -----
    def read_messages(self):
        out, p = [], FIX
        for m in range(self.n_managers):
            for _ in range(self.buf[41 + m]):
                n = self.buf[p + 4]
                out.append([m, bytes(self.buf[p:p + 4]), self.get_str(p + 5, n)])
                p += 5 + n
        return out

    def write_messages(self, msgs):
        tail = bytes(self.buf[self.mend:])
        head = bytes(self.buf[:FIX])
        body = b""
        for _m, ptr, text in msgs:
            if not text.endswith("^"):
                text += "^"
            raw = text.encode("latin-1", "replace")[:254]
            body += ptr + bytes([len(raw) + 1]) + raw + b"\x00"
        self.buf = bytearray(head + body + tail)
        self.mend = FIX + len(body)
        self.dirty = True


def list_man_files(directory):
    """Every *.MAN (case-insensitive) in a directory, sorted by name."""
    try:
        names = [n for n in os.listdir(directory)
                 if n.lower().endswith(".man") and os.path.isfile(os.path.join(directory, n))]
    except OSError:
        return []
    return sorted(names, key=str.lower)


# =========================================================================== STYLE
def apply_editor_style(root):
    """Same look as DOSTranslationEditor._apply_modern_style (used when running standalone)."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, font=("Segoe UI", 10), foreground=FG)
    style.configure("TLabelframe", background=BG, font=("Segoe UI", 10, "bold"), foreground=FG)
    style.configure("TLabelframe.Label", background=BG, foreground=FG)
    style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6, background="#3498DB",
                    foreground="white", borderwidth=0)
    style.map("TButton", background=[("active", "#2980B9"), ("disabled", "#BDC3C7")])
    style.configure("Treeview", font=("Consolas", 10), rowheight=28, background="white",
                    fieldbackground="white", foreground=FG, borderwidth=0)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#EAECEE",
                    foreground=FG, padding=6)
    style.map("Treeview", background=[("selected", "#2980B9")], foreground=[("selected", "white")])
    style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=(10, 3))
    style.map("TNotebook.Tab", font=[("selected", ("Segoe UI", 9, "bold"))],
              padding=[("selected", (10, 4))])


# =========================================================================== WIDGETS
class ScrollFrame(ttk.Frame):
    """Vertically scrollable container (scrollbar only when needed); put children in .inner."""
    _wheel_installed = False

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=BG, yscrollincrement=20)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self._vsb_shown = False
        self.canvas.configure(yscrollcommand=self._vsb_set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self._install_wheel(self)

    def _vsb_set(self, first, last):
        self.vsb.set(first, last)
        full = float(first) <= 0.0 and float(last) >= 1.0
        if full and self._vsb_shown:
            self.vsb.pack_forget()
            self._vsb_shown = False
        elif not full and not self._vsb_shown:
            self.vsb.pack(side="right", fill="y", before=self.canvas)
            self._vsb_shown = True

    @classmethod
    def _install_wheel(cls, widget):
        if cls._wheel_installed:
            return
        cls._wheel_installed = True
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind_all(seq, cls._on_wheel, add="+")

    @staticmethod
    def _on_wheel(event):
        try:
            w = event.widget.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, KeyError, AttributeError):
            return
        if isinstance(w, tk.Text):
            return
        while w is not None:
            if isinstance(w, ScrollFrame):
                if not w._vsb_shown:
                    return
                step = -1 if (getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0) else 1
                w.canvas.yview_scroll(step * 3, "units")
                return
            w = getattr(w, "master", None)


class E:
    """Editable cell: get() -> text, set_(text) -> bool (False = rejected)."""
    __slots__ = ("get", "set")

    def __init__(self, get, set_):
        self.get, self.set = get, set_

    def text(self):
        return self.get()

    def commit(self, text):
        return self.set(text)


class Ch(E):
    """Editable cell edited through a drop-down list; options() -> list of display strings."""
    __slots__ = ("options",)

    def __init__(self, get, set_, options):
        super().__init__(get, set_)
        self.options = options


class D:
    """Read-only cell computed on every row refresh."""
    __slots__ = ("fn",)

    def __init__(self, fn):
        self.fn = fn

    def text(self):
        return self.fn()


def _autohide(bar, show):
    """yscroll/xscrollcommand that shows the scrollbar only when the content does not fit."""
    state = {"on": False}

    def setter(first, last):
        bar.set(first, last)
        full = float(first) <= 0.0 and float(last) >= 1.0
        if full and state["on"]:
            bar.grid_remove()
            state["on"] = False
        elif not full and not state["on"]:
            show()
            state["on"] = True
    return setter


class EditableGrid(ttk.Frame):
    """Treeview with in-place editing (scrollbars only when needed).  columns = [(title, width[, anchor])];
    rows = lists of str/int (static), E / Ch (editable) or D (dynamic read-only)."""

    def __init__(self, parent, columns, rows=(), height=12):
        super().__init__(parent)
        ids = [f"c{i}" for i in range(len(columns))]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", height=height,
                                 selectmode="browse")
        for cid, spec in zip(ids, columns):
            self.tree.heading(cid, text=spec[0])
            self.tree.column(cid, width=spec[1], minwidth=30,
                             anchor=spec[2] if len(spec) > 2 else "center", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=_autohide(vsb, lambda: vsb.grid(row=0, column=1, sticky="ns")),
                            xscrollcommand=_autohide(hsb, lambda: hsb.grid(row=1, column=0, sticky="ew")))
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._edit = None
        self.rows = []
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Return>", self._on_return)
        self.tree.bind("<F2>", self._on_return)
        self.set_rows(rows)

    @staticmethod
    def _display(cell):
        if isinstance(cell, (E, D)):
            return cell.text()
        return "" if cell is None else str(cell)

    def set_rows(self, rows):
        self._finish(False)
        self.rows = [list(r) for r in rows]
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            self.tree.insert("", "end", iid=str(i), values=[self._display(c) for c in row])

    def refresh_all(self):
        for i in range(len(self.rows)):
            self._refresh_row(i)

    def _refresh_row(self, i):
        self.tree.item(str(i), values=[self._display(c) for c in self.rows[i]])

    # ----- editing -----
    def _on_double(self, ev):
        if self.tree.identify_region(ev.x, ev.y) != "cell":
            return
        iid = self.tree.identify_row(ev.y)
        col = int(self.tree.identify_column(ev.x)[1:]) - 1
        if iid:
            self.begin_edit(int(iid), col)

    def _on_return(self, _ev):
        sel = self.tree.selection()
        if sel:
            row = int(sel[0])
            for c, cell in enumerate(self.rows[row]):
                if isinstance(cell, E):
                    self.begin_edit(row, c)
                    break
        return "break"

    def begin_edit(self, row, col):
        self._finish(True)
        if row >= len(self.rows) or col >= len(self.rows[row]):
            return
        cell = self.rows[row][col]
        if not isinstance(cell, E):
            return
        iid = str(row)
        self.tree.selection_set(iid)
        self.tree.see(iid)
        self.tree.update_idletasks()
        bbox = self.tree.bbox(iid, f"#{col + 1}")
        if not bbox:
            return
        x, y, w, h = bbox
        var = tk.StringVar(value=cell.text())
        if isinstance(cell, Ch):
            ent = ttk.Combobox(self.tree, textvariable=var, values=cell.options(), state="readonly")
            ent.place(x=x, y=y, width=max(w, 200), height=h)
            ent.focus_set()
            ent.bind("<<ComboboxSelected>>", lambda e: self._finish(True, refocus=True))
            ent.bind("<Escape>", lambda e: self._finish(False, refocus=True))
            ent.bind("<FocusOut>", lambda e, ent=ent: self.after(150, lambda: self._combo_lost(ent)))
            ent.after(30, lambda: self._post(ent))
        else:
            ent = ttk.Entry(self.tree, textvariable=var)
            ent.place(x=x, y=y, width=w, height=h)
            ent.focus_set()
            ent.select_range(0, "end")
            ent.bind("<Return>", lambda e: self._finish(True, refocus=True))
            ent.bind("<Escape>", lambda e: self._finish(False, refocus=True))
            ent.bind("<Tab>", lambda e: self._finish(True, move=1) or "break")
            ent.bind("<Shift-Tab>", lambda e: self._finish(True, move=-1) or "break")
            ent.bind("<ISO_Left_Tab>", lambda e: self._finish(True, move=-1) or "break")
            ent.bind("<FocusOut>",
                     lambda e, ent=ent: self._edit and self._edit[2] is ent and self._finish(True))
        self._edit = (row, col, ent, var, cell.text())

    @staticmethod
    def _post(combo):
        try:
            combo.tk.call("ttk::combobox::Post", str(combo))
        except tk.TclError:
            pass

    def _combo_lost(self, combo):
        """The drop-down list steals the focus from the combobox: only give up when it is really gone."""
        if not (self._edit and self._edit[2] is combo):
            return
        try:
            focus = str(self.focus_get() or "")
        except KeyError:                               # the popdown list
            return
        if focus.startswith(str(combo)) or "popdown" in focus:
            return
        self._finish(False)

    def _finish(self, commit, move=0, refocus=False):
        ed = self._edit
        if not ed:
            return
        self._edit = None
        row, col, ent, var, before = ed
        text = var.get()
        ent.destroy()
        if commit and text != before:
            if not self.rows[row][col].commit(text):
                self.bell()
            self._refresh_row(row)
        if move:
            self._edit_next(row, col, move)
        elif refocus:
            self.tree.focus_set()

    def _edit_next(self, row, col, step):
        r, c = row, col
        while True:
            c += step
            if c >= len(self.rows[r]) or c < 0:
                r += step
                if r < 0 or r >= len(self.rows):
                    return
                c = -1 if step > 0 else len(self.rows[r])
                continue
            if isinstance(self.rows[r][c], E):
                self.begin_edit(r, c)
                return


class ValueEntry(ttk.Entry):
    """Entry bound to an E cell; commits while typing, resyncs (clamped) on focus-out/Return."""

    def __init__(self, parent, cell, width=9, maxlen=None, upper=False, on_write=None,
                 justify="right"):
        self.var = tk.StringVar()
        kw = {}
        if maxlen:
            kw = dict(validate="key",
                      validatecommand=(parent.register(lambda p, n=maxlen: len(p) <= n), "%P"))
        super().__init__(parent, textvariable=self.var, width=width, justify=justify, **kw)
        self.cell, self.upper, self.on_write = cell, upper, on_write
        self.refresh()
        self.bind("<KeyRelease>", self._typed)
        self.bind("<FocusOut>", lambda e: self.refresh())
        self.bind("<Return>", lambda e: self.refresh())

    def _typed(self, _e=None):
        text = self.var.get()
        if self.upper and text != text.upper():
            pos = self.index("insert")
            text = text.upper()
            self.var.set(text)
            self.icursor(pos)
        if text == self._last:
            return
        if self.cell.commit(text):
            self._last = text
            if self.on_write:
                self.on_write()

    def refresh(self):
        self._last = self.cell.text()
        self.var.set(self._last)


# =========================================================================== PANEL
NOTE_FONT = ("Segoe UI", 9, "italic")
H1_FONT = ("Segoe UI", 9, "bold")


def _tl(key):
    """Translated pipe-separated list."""
    return T(key).split("|")


class SavegamePanel(ttk.Frame):
    """Savegame editor panel.  API for the host:
         set_dir(path)   list the .MAN files of a folder (does not open anything)
         load_file(path) open a savegame (asks before discarding unsaved edits)
         is_dirty() / confirm_discard() / save() / clear() / set_language(code)"""

    def __init__(self, parent, standalone=False, on_change=None):
        super().__init__(parent)
        self.standalone = standalone
        self.on_change = on_change
        self.sf = None
        self.dir = ""
        self._files = {}
        self._status = ("status.none", {}, MUTED)
        self.mi = self.lg = self.md = self.cup = 0
        self.rec_club = None
        self._pages, self._page_by_path, self._group_inner = [], {}, {}
        self._live = []                       # callbacks that refresh derived labels after every edit
        self._photos = {}
        if not standalone:
            _TR.set_language(i18n.current_language())
        self._configure_styles()
        self._build_toolbar()
        self.body = ttk.Frame(self)
        self.body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.placeholder = ttk.Label(self.body, font=NOTE_FONT, foreground=MUTED,
                                     anchor="center", justify="center")
        self.placeholder.pack(expand=True)
        self._build_notebook()
        self.clear()

    # ------------------------------------------------------------------ setup
    def _configure_styles(self):
        st = ttk.Style(self)
        st.configure("Sub.TNotebook", background=BG)
        st.configure("Sub.TNotebook.Tab", font=("Segoe UI", 9), padding=(12, 3), background="#E3E8EE")
        st.map("Sub.TNotebook.Tab", background=[("selected", "#FFFFFF")],
               font=[("selected", ("Segoe UI", 9, "bold"))])

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(10, 8, 10, 6))
        bar.pack(fill=tk.X)

        self.btn_dir = ttk.Button(bar, command=self._choose_dir)
        self.btn_dir.pack(side=tk.LEFT, padx=(0, 6))

        self.saveas_btn = ttk.Button(bar, command=lambda: self.save(True))
        self.saveas_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.file_combo = ttk.Combobox(bar, state="readonly", width=22)
        self.file_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.file_combo.bind("<<ComboboxSelected>>", self._on_pick)

        self.mgr_combo = ttk.Combobox(bar, state="readonly", width=26)
        self.mgr_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.mgr_combo.bind("<<ComboboxSelected>>", self._on_manager)

        if self.standalone:
            self.lang_combo = ttk.Combobox(bar, state="readonly", width=11)
            langs = _TR.discover_languages()
            self._lang_codes = [c for c, _ in langs]
            self.lang_combo.config(values=[n for _, n in langs])
            if _TR.current_language() in self._lang_codes:
                self.lang_combo.current(self._lang_codes.index(_TR.current_language()))
            self.lang_combo.pack(side=tk.RIGHT, padx=(8, 0))
            self.lang_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self.set_language(self._lang_codes[self.lang_combo.current()]))

        self.info_label = ttk.Label(bar, font=("Segoe UI", 9, "italic"), foreground=MUTED)
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._apply_toolbar_texts()

    def _apply_toolbar_texts(self):
        self.btn_dir.config(text=T("tb.folder"))
        self.saveas_btn.config(text=T("tb.save_as"))

    def _build_notebook(self):
        G = lambda k: T("grp." + k)
        P = lambda k: T("pg." + k)
        layout = [
            (G("manager"), [(P("profile"), self._pg_profile, "mgr"), (P("history"), self._pg_history, "mgr"),
                            (P("stats"), self._pg_stats, "mgr")]),
            (G("squad"), [(P("roster"), self._pg_squad, "mgr"), (P("players"), self._pg_players, None),
                           (P("market"), self._pg_market, None)]),
            (G("economy"), [(P("stadium"), self._pg_stadium, "mgr"), (P("loans"), self._pg_loans, "mgr"),
                            (P("sponsors"), self._pg_sponsors, "mgr")]),
            (G("league"), [(P("standings"), self._pg_standings, "league"),
                           (P("results"), self._pg_results, "league"),
                           (P("calendar"), self._pg_calendar, "league")]),
            (G("cups"), [(P("cup_state"), self._pg_cup_state, None), (P("cup_ties"), self._pg_cup_ties, None)]),
            (G("clubs"), [(P("clubs"), self._pg_clubs, None), (P("ext_standings"), self._pg_ext_standings, None),
                          (P("series"), self._pg_series, None),
                          (P("records"), self._pg_records, None), (P("versus"), self._pg_versus, "mgr")]),
            (G("messages"), [(P("messages"), self._pg_messages, None)]),
            (G("advanced"), [(P("raw"), self._pg_raw, None)]),
        ]
        self.nb = ttk.Notebook(self.body)
        for gname, pages in layout:
            gframe = ttk.Frame(self.nb)
            self.nb.add(gframe, text=gname)
            if len(pages) == 1:
                self._add_page(gframe, pages[0][1], pages[0][2])
                continue
            inner = ttk.Notebook(gframe, style="Sub.TNotebook")
            inner.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._group_inner[str(gframe)] = inner
            for title, builder, dep in pages:
                holder = ttk.Frame(inner)
                inner.add(holder, text=title)
                self._add_page(holder, builder, dep)
            inner.bind("<<NotebookTabChanged>>", self._ensure_visible)
        self.nb.bind("<<NotebookTabChanged>>", self._ensure_visible)

    def _add_page(self, host, builder, dep):
        page = {"host": host, "build": builder, "dep": dep, "stale": True}
        self._pages.append(page)
        self._page_by_path[str(host)] = page

    # ------------------------------------------------------------------ language
    def set_language(self, code):
        if code == _TR.current_language() or not _TR.set_language(code):
            return False
        self.retranslate()
        return True

    def retranslate(self):
        self._apply_toolbar_texts()
        shown = self.sf is not None
        self.nb.destroy()
        self._pages, self._page_by_path, self._group_inner = [], {}, {}
        self._build_notebook()
        if shown:
            self.nb.pack(fill=tk.BOTH, expand=True)
            self._fill_managers()
            self._invalidate()
        self.refresh_list()
        self._render_status()
        if self.standalone and _TR.current_language() in self._lang_codes:
            self.lang_combo.current(self._lang_codes.index(_TR.current_language()))

    # ------------------------------------------------------------------ lazy pages
    def _current_page(self):
        try:
            top = self.nb.select()
        except tk.TclError:
            return None
        if not top:
            return None
        inner = self._group_inner.get(top)
        return self._page_by_path.get(inner.select() if inner else top)

    def _ensure_visible(self, _e=None):
        page = self._current_page()
        if self.sf and page and page["stale"]:
            self._build(page)

    def _build(self, page):
        host = page["host"]
        for child in host.winfo_children():
            child.destroy()
        page["stale"] = False
        try:
            page["build"](host)
        except Exception as exc:
            traceback.print_exc()
            ttk.Label(host, text=T("err.page", error=exc), foreground=ERR).pack(padx=10, pady=10)

    def _invalidate(self, dep=None):
        for p in self._pages:
            if dep is None or p["dep"] == dep:
                for child in p["host"].winfo_children():
                    child.destroy()
                p["stale"] = True
        self._ensure_visible()

    def _reload(self, host):
        page = self._page_by_path[str(host)]
        self.after_idle(lambda: self._build(page))

    # ------------------------------------------------------------------ files
    def set_dir(self, directory):
        self.dir = os.path.abspath(directory) if directory else ""
        self.refresh_list()
        if self.dir and not self.sf:
            names = list_man_files(self.dir)
            if names:
                self.load_file(os.path.join(self.dir, names[0]))

    def refresh_list(self, select=None):
        names = list_man_files(self.dir) if self.dir else []
        self._files = {n: os.path.join(self.dir, n) for n in names}
        self.file_combo.config(values=names)
        cur = select or (os.path.basename(self.sf.path) if self.sf else None)
        self.file_combo.set(cur if cur in self._files else "")
        if not self.sf:
            if not self.dir:
                msg = T("ph.no_dir")
            elif not names:
                msg = T("ph.none", dir=self.dir)
            else:
                msg = T("ph.pick", n=len(names))
            self.placeholder.config(text=msg)
        self._render_status()

    def _on_pick(self, _e=None):
        path = self._files.get(self.file_combo.get())
        if path and not self.load_file(path):
            self.file_combo.set(os.path.basename(self.sf.path) if self.sf else "")

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir or None, title=T("dlg.folder"))
        if d and self.confirm_discard():
            self._unload()
            self.set_dir(d)

    def _filetypes(self):
        return [(T("dlg.type_man"), "*.MAN *.man"), (T("dlg.type_all"), "*.*")]

    def is_dirty(self):
        return bool(self.sf and self.sf.dirty)

    def confirm_discard(self):
        if not self.is_dirty():
            return True
        return messagebox.askyesno(T("dlg.title"),
                                   T("dlg.discard", name=os.path.basename(self.sf.path)),
                                   parent=self.winfo_toplevel())

    def load_file(self, path):
        if not self.confirm_discard():
            return False
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            sf = SaveFile(os.path.abspath(path), data)
        except (OSError, SaveError) as exc:
            messagebox.showerror(T("dlg.title"), f"{os.path.basename(path)}:\n{exc}",
                                 parent=self.winfo_toplevel())
            self._set_status_raw(str(exc), ERR)
            return False
        self.sf = sf
        self.mi = min(sf.buf[49], max(0, sf.n_managers - 1))
        self.lg = self.md = self.cup = 0
        self.rec_club = None
        folder = os.path.dirname(sf.path)
        if os.path.normcase(folder) != os.path.normcase(self.dir):
            self.dir = folder
        self.refresh_list(select=os.path.basename(sf.path))
        self._fill_managers()
        self.placeholder.pack_forget()
        self.nb.pack(fill=tk.BOTH, expand=True)
        self.nb.select(0)
        self._invalidate()
        self._set_status_key("status.loaded_ok" if sf.roundtrip_ok else "status.loaded_warn",
                             MUTED if sf.roundtrip_ok else ERR, name=os.path.basename(sf.path))
        self._update_ui(keep_status=True)

        return True

    def _unload(self):
        self.sf = None
        self.nb.pack_forget()
        self.placeholder.pack(expand=True)
        self._invalidate()
        self.mgr_combo.config(values=[], state="disabled")
        self.mgr_combo.set("")

    def clear(self):
        self._unload()
        self.dir = ""
        self.refresh_list()
        self._set_status_key("status.none", MUTED)
        self._update_ui(keep_status=True)

    # ------------------------------------------------------------------ saving
    def save(self, save_as=False):
        sf = self.sf
        if not sf:
            return False
        parent = self.winfo_toplevel()
        path = sf.path
        if save_as:
            path = filedialog.asksaveasfilename(
                initialdir=os.path.dirname(sf.path), initialfile=os.path.basename(sf.path),
                defaultextension=".MAN", title=T("dlg.save_as"), filetypes=self._filetypes())
            if not path:
                return False
        if not sf.roundtrip_ok and not messagebox.askyesno(T("dlg.title"), T("dlg.roundtrip"), parent=parent):
            return False
        made_backup = False
        try:
            data = sf.encode()
            check, _ = SaveFile._decode(data)
            if (bytes(check[:CHK1]) != bytes(sf.buf[:CHK1])
                    or bytes(check[CHK1 + 1:sf.mend]) != bytes(sf.buf[CHK1 + 1:sf.mend])):
                raise SaveError("err.verify")
            backup = path + ".bak"
            if os.path.isfile(path) and not os.path.exists(backup):
                shutil.copy2(path, backup)
                made_backup = True
            tmp = path + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
        except (OSError, SaveError) as exc:
            messagebox.showerror(T("dlg.title"), T("dlg.save_failed", error=exc), parent=parent)
            return False
        sf.path, sf.original, sf.dirty = os.path.abspath(path), data, False
        if os.path.normcase(os.path.dirname(sf.path)) == os.path.normcase(self.dir):
            self.refresh_list(select=os.path.basename(sf.path))
        self._set_status_key("status.saved", OK, name=os.path.basename(path),
                             backup=T("status.backup") if made_backup else "")
        self._update_ui(keep_status=True)
        if self.on_change:
            self.on_change()
        return True

    def _set_status_key(self, key, color=MUTED, **args):
        self._status = (key, args, color)
        self._render_status()

    def _set_status_raw(self, text, color=MUTED):
        self._status = (None, text, color)
        self._render_status()

    def _render_status(self):
        key, args, color = self._status
        st_text = args if key is None else T(key, **args)
        parts = []
        if self.dir:
            parts.append(f"({self.dir})")
        if st_text:
            parts.append(st_text)
        self.info_label.config(text=" – ".join(parts), foreground=color)

    def _update_ui(self, keep_status=False):
        loaded = bool(self.sf)
        self.saveas_btn.config(state=tk.NORMAL if loaded else tk.DISABLED)
        if loaded and self.sf.dirty and not keep_status:
            self._set_status_key("status.dirty", ERR)

    def _changed(self):
        for fn in list(self._live):
            try:
                fn()
            except tk.TclError:                # widget destroyed with its page
                self._live.remove(fn)
        self._update_ui()
        if self.on_change:
            self.on_change()

    def _fill_managers(self):
        sf = self.sf
        vals = [T("mgr.item", n=m + 1, name=sf.manager_name(m)) for m in range(sf.n_managers)]
        self.mgr_combo.config(values=vals, state="readonly")
        if vals:
            self.mgr_combo.current(self.mi)

    def _on_manager(self, _e=None):
        i = self.mgr_combo.current()
        if i >= 0 and i != self.mi:
            self.mi = i
            self._invalidate("mgr")

    def _mo(self):
        return MB + 778 * self.mi

    def _num(self, off, t="u8"):
        def get():
            return str(self.sf.rd(off, t))

        def set_(text):
            try:
                v = int(text.strip())
            except ValueError:
                return False
            self.sf.wr(off, t, v)
            self._changed()
            return True
        return E(get, set_)

    def _txt(self, off, n):
        def set_(text):
            self.sf.set_str(off, n, text.upper())
            self._changed()
            return True
        return E(lambda: self.sf.get_str(off, n), set_)

    def _pair(self, off, empty_255):
        def get():
            v = self.sf.buf[off]
            return "" if (empty_255 and v == 255) else f"{v >> 4}:{v & 15}"

        def set_(text):
            t = text.strip()
            if not t:
                self.sf.wr(off, "u8", 255 if empty_255 else 0)
            else:
                parts = [p for p in re.split(r"[:\s/,;\-]+", t) if p]
                try:
                    a = int(parts[0])
                    b = int(parts[1]) if len(parts) > 1 else 0
                except (ValueError, IndexError):
                    return False
                self.sf.wr(off, "u8", (max(0, min(15, a)) << 4) | max(0, min(15, b)))
            self._changed()
            return True
        return E(get, set_)

    def _club_label(self, v):
        n = self.sf.club_name(v)
        return f"{v} – {n}" if n else f"{v} – ?"

    def _club_options(self):
        return [self._club_label(i) for i in self.sf.club_ids()]

    def _club_cell(self, off):
        def set_(text):
            m = re.match(r"\s*(\d+)", text)
            if not m:
                return False
            self.sf.wr(off, "u8", int(m.group(1)))
            self._changed()
            return True
        return Ch(lambda: self._club_label(self.sf.buf[off]), set_, self._club_options())

    def _club_combo(self, parent, off, width=30):
        cb = ttk.Combobox(parent, state="readonly", width=width, values=self._club_options())
        cb.set(self._club_label(self.sf.buf[off]))

        def picked(_e):
            self.sf.wr(off, "u8", self.sf.club_ids()[cb.current()])
            self._changed()
        cb.bind("<<ComboboxSelected>>", picked)
        return cb

    def _live_label(self, parent, fn, **kw):
        """Read-only label whose text is fn(), refreshed after every edit."""
        lab = ttk.Label(parent, **kw)
        lab.config(text=fn())
        self._live.append(lambda: lab.config(text=fn()))
        return lab

    def _hexrun(self, off, n):
        """Editable cell for n raw bytes shown as hex (e.g. '73 94 81')."""
        def get():
            return " ".join(f"{x:02X}" for x in self.sf.buf[off:off + n])

        def set_(text):
            try:
                vals = [int(t, 16) for t in re.split(r"[\s,;:]+", text.strip()) if t]
            except ValueError:
                return False
            if len(vals) != n or any(not 0 <= v <= 255 for v in vals):
                return False
            self.sf.buf[off:off + n] = bytes(vals)
            self.sf.dirty = True
            self._changed()
            return True
        return E(get, set_)

    def _note(self, parent, text, wrap=900):
        return ttk.Label(parent, text=text, foreground=MUTED, font=NOTE_FONT,
                         wraplength=wrap, justify="left")

    def _field(self, parent, row, label, widget, col=0):
        ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="w", padx=(4, 8), pady=3)
        widget.grid(row=row, column=col * 2 + 1, sticky="w", padx=(0, 4), pady=3)

    def _num_field(self, parent, off, t="u8", width=8, **kw):
        return ValueEntry(parent, self._num(off, t), width=width, **kw)

    def _combo_field(self, parent, options, off, base, width=20):
        cb = ttk.Combobox(parent, values=options, state="readonly", width=width)
        idx = self.sf.buf[off] - base
        if 0 <= idx < len(options):
            cb.current(idx)
        else:
            cb.set(f"? ({self.sf.buf[off]})")

        def picked(_e):
            self.sf.wr(off, "u8", cb.current() + base)
            self._changed()
        cb.bind("<<ComboboxSelected>>", picked)
        return cb

    def _value_grid(self, parent, off, n, cols, w=44, first_w=44):
        columns = [("#", first_w)] + [(str(i + 1), w) for i in range(cols)]
        rows = [[i + 1] + [self._num(off + k) for k in range(i, min(n, i + cols))]
                for i in range(0, n, cols)]
        return EditableGrid(parent, columns, rows, height=len(rows))

    def _labeled(self, parent, text, **grid):
        lf = ttk.LabelFrame(parent, text=text, padding=8)
        lf.grid(**grid)
        return lf

    def _scroll_page(self, host):
        sc = ScrollFrame(host)
        sc.pack(fill=tk.BOTH, expand=True)
        return sc.inner

    def _league_bar(self, host):
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("lbl.league")).pack(side="left")
        cb = ttk.Combobox(bar, values=_tl("lists.leagues"), state="readonly", width=14)
        cb.current(self.lg)
        cb.pack(side="left", padx=6)

        def picked(_e):
            self.lg, self.md = cb.current(), 0
            self.after_idle(lambda: self._invalidate("league"))
        cb.bind("<<ComboboxSelected>>", picked)
        return bar

    # =================================================================== PAGES: Manager
    def _pg_profile(self, host):
        sf, o = self.sf, self._mo()
        body = self._scroll_page(host)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        ident = self._labeled(body, T("prof.identity"), row=0, column=0, sticky="nsew", padx=(10, 5), pady=(10, 5))
        self._field(ident, 0, T("prof.name"),
                    ValueEntry(ident, self._txt(o, 29), width=30, maxlen=28, upper=True,
                               justify="left", on_write=self._refresh_manager_combo))
        league_holder = []
        ids = sf.club_ids()
        cb = ttk.Combobox(ident, values=self._club_options(), state="readonly", width=30)
        cb.set(self._club_label(sf.buf[o + 30]))

        def club_picked(_e):
            v = ids[cb.current()]
            sf.wr(o + 30, "u8", v)
            sf.wr(o + 312, "u8", 0 if v < 18 else 1 if v < 38 else 2)
            self._changed()
            for w in league_holder:
                w.refresh()
        cb.bind("<<ComboboxSelected>>", club_picked)
        self._field(ident, 1, T("c.club"), cb)

        self._field(ident, 2, T("prof.cash"), self._num_field(ident, o + 496, "i32", width=14))

        def month_cell():
            def set_(t):
                try:
                    sf.wr(27964, "i32", int(t) - 1)
                except ValueError:
                    return False
                self._changed()
                return True
            return E(lambda: str(sf.rd(27964, "i32") + 1), set_)

        def year_cell():
            def set_(t):
                try:
                    v = int(t)
                except ValueError:
                    return False
                sf.wr(27968, "i32", v)
                sf.wr(27976, "u16", v)
                self._changed()
                return True
            return E(lambda: str(sf.rd(27968, "i32")), set_)
        date = ttk.Frame(ident)
        ValueEntry(date, self._num(27960, "i32"), width=4).pack(side="left")
        ttk.Label(date, text=" / ").pack(side="left")
        ValueEntry(date, month_cell(), width=4).pack(side="left")
        ttk.Label(date, text=" / ").pack(side="left")
        ValueEntry(date, year_cell(), width=6).pack(side="left")
        self._field(ident, 3, T("prof.date"), date)

        def level_cell():
            def set_(t):
                try:
                    v = int(t)
                except ValueError:
                    return False
                sf.wr(34062, "u8", max(0, min(4, 5 - v)))
                self._changed()
                return True
            return E(lambda: str(5 - sf.buf[34062]), set_)
        self._field(ident, 4, T("prof.level"), ValueEntry(ident, level_cell(), width=4))

        face_lab = ttk.Label(ident, anchor="center", relief="solid")
        face_lab.grid(row=0, column=2, rowspan=5, padx=(16, 4), pady=3, sticky="ne")

        def show_face(*_):
            faces = self._faces()
            idx = sf.buf[o + 29] - 1
            if 0 <= idx < len(faces):
                im = faces[idx][2].resize((FACE_W * FACE_ZOOM, FACE_W * FACE_ZOOM), Image.NEAREST)
                self._photos["face"] = ImageTk.PhotoImage(im)
                face_lab.config(image=self._photos["face"], text="")
            else:
                self._photos["face"] = None
                face_lab.config(image="", text="—", width=8)
        self._field(ident, 5, T("prof.portrait_id"),
                    ValueEntry(ident, self._num(o + 29), width=4, on_write=show_face))
        show_face()

        mgmt = self._labeled(body, T("prof.mgmt"), row=0, column=1, sticky="nsew", padx=(5, 10), pady=(10, 5))
        items = list(zip(_tl("prof.mgmt_items"), (305, 319, 321, 322, 323, 324, 317, 314,
                                                  325, 326, 327, 328, 329)))
        # posizione (1-13) -> (riga, colonna): sx 3,4,5,6,9 | dx 10,11,12,13 | piu' in basso 1,2 / 7,8
        place = {3: (0, 0), 4: (1, 0), 5: (2, 0), 6: (3, 0), 9: (4, 0),
                 10: (0, 1), 11: (1, 1), 12: (2, 1), 13: (3, 1),
                 1: (6, 0), 2: (6, 1), 7: (7, 0), 8: (7, 1)}
        ttk.Frame(mgmt, height=14).grid(row=5, column=0)
        for pos, (r, col) in place.items():
            label, d = items[pos - 1]
            self._field(mgmt, r, label, self._num_field(mgmt, o + d, width=6), col=col)

        adv = self._labeled(body, T("prof.internal"), row=1, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=5)
        lg = self._num_field(adv, o + 312, width=6)
        league_holder.append(lg)
        a_lab = _tl("prof.internal_items")
        self._field(adv, 0, a_lab[0], lg, col=0)
        self._field(adv, 0, a_lab[1], self._num_field(adv, o + 265, width=6), col=1)
        self._field(adv, 0, a_lab[2], self._num_field(adv, o + 320, width=6), col=2)
        self._note(body, T("prof.note")).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 5))

        ext = self._labeled(body, T("prof.extra"), row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        extra = [(480, "u16"), (482, "u16"), (432, "u16"), (436, "u16"), (310, "u16"), (376, "u16"), (384, "u16"),
                 (392, "u16"), (400, "u16"), (502, "u16"), (506, "u16"), (313, "u8"), (315, "u8"), (318, "u8")]
        extra += [(x, "u8") for x in (32, 35, 36, 40, 43, 44, 45, 46, 47, 48, 49, 53, 56)]
        for k, (x, t) in enumerate(extra):
            self._field(ext, k // 6, T("prof.extra_item", off=x), self._num_field(ext, o + x, t, width=8), col=k % 6)
        self._note(body, T("prof.extra_note")).grid(row=4, column=0, columnspan=2, sticky="w", padx=10,
                                                    pady=(2, 10))

    def _pic_dir(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return find_pic_dir(self.dir, os.getcwd(), here) or None

    def _faces(self):
        pic = self._pic_dir()
        if "faces" not in self._photos or self._photos.get("faces_dir") != pic:
            self._photos["faces_dir"], self._photos["faces"] = pic, load_faces(pic)
        return self._photos["faces"]

    def _refresh_manager_combo(self):
        if self.sf:
            self._fill_managers()

    def _pg_history(self, host):
        sf, o = self.sf, self._mo()
        count = min(50, sf.rd(SEASONS_COUNT_OFF, "u16"))
        left = ttk.Frame(host)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        pal = ttk.LabelFrame(left, text=T("hist.palmares"), padding=8)
        pal.pack(fill="x")
        self._field(pal, 0, T("hist.seasons_played"), self._num_field(pal, SEASONS_COUNT_OFF, "u16", width=6))
        titles = _tl("lists.titles")
        for i, t in enumerate(titles):
            self._field(pal, 1 + i, T("hist.titles", name=t), self._num_field(pal, o + 57 + i, width=6))
        for i, t in enumerate(titles[1:]):
            self._field(pal, 6 + i, T("hist.round", name=t), self._num_field(pal, o + 306 + i, width=6))

        bil = ttk.LabelFrame(left, text=T("hist.balance"), padding=8)
        bil.pack(fill="x", pady=(10, 0))
        rows = [[lab, self._num(o + x, "u16"), self._num(o + x + 2, "u16")]
                for lab, x in zip(_tl("hist.balance_items"), (420, 424, 428, 440, 444, 448))]
        EditableGrid(bil, [("", 110, "w"), (T("c.home"), 80), (T("c.away_full"), 80)], rows,
                     height=len(rows)).pack()

        sea = ttk.LabelFrame(host, text=T("hist.seasons"), padding=8)
        sea.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        btns = ttk.Frame(sea)
        btns.pack(fill="x", pady=(0, 6))

        def add():
            c = sf.rd(SEASONS_COUNT_OFF, "u16")
            if c >= 50:
                return
            b = o + 62 + 4 * c
            for k in range(4):
                sf.buf[b + k] = sf.buf[b - 4 + k] if c else (1, 0, 0, 0)[k]
            sf.wr(SEASONS_COUNT_OFF, "u16", c + 1)
            self._changed()
            self._reload(host)

        def remove():
            c = sf.rd(SEASONS_COUNT_OFF, "u16")
            if not c:
                return
            for k in range(4):
                sf.buf[o + 62 + 4 * (c - 1) + k] = 0
            sf.wr(SEASONS_COUNT_OFF, "u16", c - 1)
            self._changed()
            self._reload(host)
        ttk.Button(btns, text=T("hist.add"), command=add).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text=T("hist.remove"), command=remove).pack(side="left")
        rows = [[i + 1] + [self._num(o + 62 + 4 * i + k) for k in range(4)] for i in range(count)]
        cols = _tl("hist.season_cols")
        EditableGrid(sea, [("#", 50), (cols[0], 90), (cols[1], 70), (cols[2], 95), (cols[3], 80)],
                     rows, height=12).pack(fill="both", expand=True)
        self._note(sea, T("hist.note"), wrap=520).pack(anchor="w", pady=(6, 0))

    def _pg_stats(self, host):
        o = self._mo()
        body = self._scroll_page(host)
        for title, off, n, cols, w in ((T("stats.positions"), o + 267, 38, 10, 44),
                                       (T("stats.attendance"), o + 330, 17, 10, 44),
                                       (T("stats.series"), H + 3904 + 21 * self.mi, 21, 21, 40)):
            lf = ttk.LabelFrame(body, text=title, padding=8)
            lf.pack(fill="x", padx=10, pady=(10, 5))
            self._value_grid(lf, off, n, cols, w=w).pack(anchor="w")
        ch = ttk.LabelFrame(body, text=T("stats.chart"), padding=8)
        ch.pack(fill="x", padx=10, pady=5)
        self._field(ch, 0, T("std.home_games") + " (+476)", self._num_field(ch, o + 476, "u16", width=6))
        self._field(ch, 0, "+478", self._num_field(ch, o + 478, "u16", width=6), col=1)
        self._note(body, T("stats.note")).pack(anchor="w", padx=10, pady=(2, 10))

    # =================================================================== PAGES: Squadra
    def _pg_squad(self, host):
        sf = self.sf
        rows, slots = [], []
        for i in range(25):
            b = LB + 52 * (self.mi * 25 + i)
            pi = sf.buf[b + 15]
            if not pi:
                continue
            pb = PB + 37 * pi
            slots.append(b)
            rows.append([sf.get_str(pb, 26), D(lambda pb=pb: pos4(self.sf.buf[pb + 31])),
                         self._num(b + 10), self._num(b + 16), self._num(b + 17), self._num(b + 18),
                         self._num(b + 19), self._num(b + 40, "i32"), self._num(b + 11),
                         self._num(b + 13), self._num(b + 1), self._num(b), self._num(b + 3),
                         self._num(b + 6),
                         self._num(b + 14), self._num(b + 20, "i16"), self._num(b + 25),
                         self._num(b + 26), self._num(b + 28), self._num(b + 30), self._num(b + 34)]
                        + [self._num(b + x, "u8") for x in (2, 4, 5, 9, 12, 23, 24)] + [self._num(b + 48, "u16"), self._num(b + 50, "u16")])
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        c = _tl("squad.cols")
        widths = (200, 55, 50, 55, 55, 60, 65, 90, 60, 60, 55, 55, 55, 55)
        xc = _tl("squad.extra_cols")
        grid = EditableGrid(host, [(c[0], widths[0], "w")] + [(t, w) for t, w in zip(c[1:], widths[1:])]
                            + [(t, 58) for t in xc], rows, height=14)

        def all99():
            for b in slots:
                for k in (16, 17, 18):
                    sf.wr(b + k, "u8", 99)
            self._changed()
            grid.refresh_all()
        ttk.Button(bar, text=T("squad.all99"), command=all99).pack(side="left")
        ttk.Label(bar, text=T("squad.count", n=len(rows)), foreground=MUTED).pack(side="right")

        def avg_text():
            if not slots:
                return ""
            n = len(slots)
            av = [sum(sf.buf[b + k] for b in slots) / n for k in (16, 17, 18)]
            return T("squad.avg", c=f"{av[0]:.1f}", t=f"{av[1]:.1f}", f=f"{av[2]:.1f}")
        self._live_label(bar, avg_text, foreground=MUTED).pack(side="left", padx=12)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._note(host, T("squad.note") + " " + T("squad.extra_note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_players(self, host):
        sf = self.sf
        club_ids = sorted({sf.buf[PB + 37 * i + 36] for i in range(151) if sf.buf[PB + 37 * i]})
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("pl.search")).pack(side="left")
        q = tk.StringVar()
        ttk.Entry(bar, textvariable=q, width=22).pack(side="left", padx=(6, 14))
        ttk.Label(bar, text=T("pl.club")).pack(side="left")
        cb = ttk.Combobox(bar, state="readonly", width=28,
                          values=[T("pl.all")] + [self._club_label(c) for c in club_ids])
        cb.current(0)
        cb.pack(side="left", padx=6)
        count = ttk.Label(bar, foreground=MUTED)
        count.pack(side="right")
        c = _tl("pl.cols")
        grid = EditableGrid(host, [("#", 45), (c[0], 190, "w")] + [(t, w) for t, w in zip(
            c[1:9], (50, 55, 55, 60, 95, 50, 55, 55))] + [(c[9], 230, "w")] + [(t, 50) for t in _tl("pl.extra_cols")], height=16)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        def draw(*_):
            f = q.get().upper()
            sel = cb.current()
            club = club_ids[sel - 1] if sel > 0 else None
            rows = []
            for i in range(151):
                o = PB + 37 * i
                if not sf.buf[o] or (club is not None and sf.buf[o + 36] != club):
                    continue
                if f and f not in sf.get_str(o, 26):
                    continue
                rows.append([i, self._txt(o, 26), self._num(o + 26), self._num(o + 28), self._num(o + 29),
                             self._num(o + 30), self._num(o + 31),
                             D(lambda o=o: pos4(self.sf.buf[o + 31])), self._num(o + 34),
                             self._num(o + 35), self._club_cell(o + 36), self._num(o + 27), self._num(o + 32), self._num(o + 33)])
            grid.set_rows(rows)
            count.config(text=T("pl.count", n=len(rows)))
        q.trace_add("write", draw)
        cb.bind("<<ComboboxSelected>>", draw)
        draw()

    def _pg_market(self, host):
        sf = self.sf
        rows = []
        for i in range(100, 125):
            b = LB + 52 * i
            pi = sf.buf[b + 15]
            if not pi:
                continue
            pb = PB + 37 * pi
            rows.append([i, sf.get_str(pb, 26), D(lambda pb=pb: pos4(self.sf.buf[pb + 31])),
                         self._num(b + 16), self._num(b + 17), self._num(b + 18), self._num(b + 19),
                         self._num(b + 14), self._num(b + 20), self._num(b + 40, "i32")])
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("mk.count", n=len(rows)), foreground=MUTED).pack(side="right")
        c = _tl("mk.cols")
        widths = (200, 55, 55, 55, 60, 65, 55, 55, 100)
        EditableGrid(host, [("#", 45), (c[0], widths[0], "w")] + [(t, w) for t, w in zip(c[1:], widths[1:])],
                     rows, height=12).pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._note(host, T("mk.note")).pack(anchor="w", padx=10, pady=(0, 8))

    # =================================================================== PAGES: Economia
    def _pg_stadium(self, host):
        o = self._mo()
        body = self._scroll_page(host)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        sizes = _tl("lists.sizes")
        grades = [T("lists.grade_1"), "2", "3", "4", "5", T("lists.grade_6")]
        amp = self._labeled(body, T("std.expansions"), row=0, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=(10, 5))
        top = ttk.Frame(amp)
        top.pack(anchor="w", pady=(0, 6))
        self._field(top, 0, T("std.ticket"), self._num_field(top, o + 266, width=6))
        self._field(top, 0, T("std.capacity"),
                    self._live_label(top, lambda: f"{self.sf.rd(o + 350, 'i32') + self.sf.rd(o + 358, 'i32'):,}"),
                    col=1)
        names = _tl("std.exp_items")
        choice = {4: (o + 374, sizes, 0), 5: (o + 382, sizes, 0), 6: (o + 390, grades, 1), 7: (o + 398, grades, 1)}
        rows = []
        for k in range(1, 8):
            cur = self._num(o + 350 + 8 * (k - 1), "i32") if k < 4 else self._choice_cell(*choice[k])
            rows.append([names[k - 1], cur, self._num(o + 354 + 8 * (k - 1), "i32"),
                         self._num(o + 404 + 2 * k, "u16")])
        c = _tl("std.exp_cols")
        EditableGrid(amp, [(c[0], 150, "w"), (c[1], 110), (c[2], 120), (c[3], 130)], rows,
                     height=7).pack(anchor="w")

        aff = self._labeled(body, T("std.attendance"), row=1, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=5)
        self._field(aff, 0, T("std.season_att"), self._num_field(aff, o + 484, "i32", width=12))
        self._field(aff, 1, T("std.record_att"), self._num_field(aff, o + 488, "i32", width=12))
        self._field(aff, 2, T("std.record_opp"), self._club_combo(aff, o + 500))
        self._field(aff, 3, T("std.min_att"), self._num_field(aff, o + 492, "i32", width=12))
        self._field(aff, 4, T("std.min_opp"), self._club_combo(aff, o + 504))
        self._field(aff, 0, T("std.home_games"), self._num_field(aff, o + 476, "u16", width=12), col=1)

        def avg_att():
            n = self.sf.rd(o + 476, 'u16')
            return f"{self.sf.rd(o + 484, 'i32') / n:,.0f}" if n else "–"
        self._field(aff, 1, T("std.avg_att"), self._live_label(aff, avg_att), col=1)

    def _choice_cell(self, off, labels, base):
        """Cella di tabella che mostra l'etichetta di un valore a un byte (accetta etichetta o numero)."""
        buf = self.sf.buf

        def get():
            i = buf[off] - base
            return labels[i] if 0 <= i < len(labels) else f"? ({buf[off]})"

        def set_(text):
            t = text.strip().lower()
            for i, lab in enumerate(labels):
                if t == lab.lower() or t == str(i + base):
                    buf[off] = i + base
                    self.sf.dirty = True
                    self._changed()
                    return True
            return False
        return E(get, set_)

    def _loan_date(self, b_day, b_year):
        """Cella data gg/mm/aaaa di un prestito: giorno a b_day, mese (0-11) a b_day+2, anno u16 a b_year."""
        buf = self.sf.buf

        def get():
            d, mth, y = buf[b_day], buf[b_day + 2], buf[b_year] | (buf[b_year + 1] << 8)
            return "–" if not (d or y) else f"{d:02d}/{mth + 1:02d}/{y}"

        def set_(text):
            text = text.strip()
            if text in ("", "–", "-", "0"):
                d, mth, y = 0, 0, 0
            else:
                try:
                    d, mth, y = (int(t) for t in re.split(r"[/.\-\s]+", text))
                except ValueError:
                    return False
                if not (1 <= d <= 31 and 1 <= mth <= 12 and 0 <= y <= 65535):
                    return False
                mth -= 1
            buf[b_day], buf[b_day + 2] = d, mth
            buf[b_year], buf[b_year + 1] = y & 255, y >> 8
            self.sf.dirty = True
            self._changed()
            return True
        return E(get, set_)

    def _pg_loans(self, host):
        o = self._mo()
        rows = []
        mi = self.mi
        others = [k for k in range(self.sf.n_managers) if k != mi]     # prestatori: gli altri manager, in ordine

        def lender(g):
            if g == 0:
                return T("loan.bank")
            if g - 1 < len(others):
                k = others[g - 1]
                return T("mgr.item", n=k + 1, name=self.sf.manager_name(k))
            return T("loan.lender", n=g)
        for g in range(5):
            for i in range(3):
                b = o + 508 + (g * 3 + i) * 18
                rows.append([lender(g), i + 1, self._num(b, "i32"), self._num(b + 4, "i32"),
                             self._num(b + 12, "u16"), self._loan_date(b + 8, b + 14), self._loan_date(b + 9, b + 16)])
        c = _tl("loan.cols")
        sf = self.sf
        tot = ttk.Frame(host)
        tot.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(tot, text=T("loan.total") + ":").pack(side="left")
        self._live_label(tot, lambda: f"{sum(sf.rd(o + 508 + 18 * k, 'i32') for k in range(15)):,}",
                         font=H1_FONT).pack(side="left", padx=(6, 24))
        ttk.Label(tot, text=T("loan.interest_total") + ":").pack(side="left")
        self._live_label(tot, lambda: f"{sum(sf.rd(o + 512 + 18 * k, 'i32') for k in range(15)):,}",
                         font=H1_FONT).pack(side="left", padx=6)
        EditableGrid(host, [(c[0], 190, "w"), ("#", 45), (c[1], 110), (c[2], 120), (c[3], 70),
                            (c[4], 110), (c[5], 110)], rows, height=15).pack(fill="both", expand=True, padx=10, pady=10)
        self._note(host, T("loan.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_sponsors(self, host):
        mi = self.mi
        a = 33918 + 36 * mi
        body = self._scroll_page(host)
        top = ttk.Frame(body)
        top.pack(fill="x", padx=10, pady=(10, 5))
        shirt, board, tv, adcost = T("sp.shirt"), T("sp.board"), T("sp.tv"), T("sp.adcost")
        ent = ttk.LabelFrame(top, text=T("sp.income"), padding=8)
        ent.pack(side="left", fill="y", padx=(0, 10))
        rows = [[shirt, self._num(a, "i32")]]
        rows += [[f"{board} {k + 1}", self._num(a + 4 + 4 * k, "i32")] for k in range(6)]
        rows += [[tv, self._num(a + 28, "i32")], [adcost, self._num(a + 32, "i32")]]
        EditableGrid(ent, [(T("sp.item"), 150, "w"), (T("sp.amount"), 120)], rows, height=len(rows)).pack()
        con = ttk.LabelFrame(top, text=T("sp.contracts"), padding=8)
        con.pack(side="left", fill="y")
        spaces = [(shirt, 33462 + 2 * mi)] + [(f"{board} {k + 1}", 33470 + (mi * 6 + k) * 2) for k in range(6)]
        rows = [[lab, self._num(x), self._num(x + 1)] for lab, x in spaces]
        c = _tl("sp.contract_cols")
        EditableGrid(con, [(c[0], 140, "w"), (c[1], 110), (c[2], 100)], rows, height=len(rows)).pack()
        off = ttk.LabelFrame(body, text=T("sp.offers"), padding=8)
        off.pack(fill="x", padx=10, pady=5)
        rows = []
        for j in range(10):
            t, b = (mi * 2) * 10 + j, (mi * 2 + 1) * 10 + j
            rows.append([j + 1, self._num(33518 + t), self._num(33598 + 4 * t, "i32"),
                         self._num(33518 + b), self._num(33598 + 4 * b, "i32")])
        c = _tl("sp.offer_cols")
        EditableGrid(off, [(c[0], 80), (c[1], 110), (c[2], 140), (c[3], 130), (c[4], 150)], rows,
                     height=10).pack(anchor="w")
        self._note(body, T("sp.note")).pack(anchor="w", padx=10, pady=(2, 10))

    # =================================================================== PAGES: Campionato
    def _pg_standings(self, host):
        sf = self.sf
        a, b = ((0, 18), (18, 38), (38, 58))[self.lg]
        recs = []
        for i in range(a, b):
            o = 12357 + 54 * i
            pt = sf.buf[o] + sf.buf[o + 1]
            gd = sf.buf[o + 22] + sf.buf[o + 23] - sf.buf[o + 26] - sf.buf[o + 27]
            recs.append((i, o, pt, gd))
        recs.sort(key=lambda r: (-r[2], -r[3]))
        bar = self._league_bar(host)
        ttk.Button(bar, text=T("st.resort"), command=lambda: self._reload(host)).pack(side="left", padx=6)
        rows = []
        for k, (i, o, _pt, _gd) in enumerate(recs):
            rows.append([k + 1, sf.club_name(i),
                         D(lambda o=o: str(self.sf.buf[o] + self.sf.buf[o + 1])),
                         D(lambda o=o: f"{self.sf.buf[o + 22] + self.sf.buf[o + 23] - self.sf.buf[o + 26] - self.sf.buf[o + 27]:+d}")]
                        + [self._num(o + x) for x in (0, 1, 22, 23, 26, 27, 30, 31, 38, 39, 42, 43)]
                        + [self._num(o + 50, "i32")])
        c = _tl("st.cols")
        cols = [("#", 40), (c[0], 190, "w")] + [(t, 85 if k == len(c) - 2 else 55) for k, t in enumerate(c[1:])]
        EditableGrid(host, cols, rows, height=20).pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._note(host, T("st.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_results(self, host):
        lg = self.lg
        n, per = (38, 10) if lg else (34, 9)
        self.md = min(self.md, n - 1)
        bar = self._league_bar(host)
        ms = ttk.Combobox(bar, values=[T("res.round", n=d + 1) for d in range(n)], state="readonly", width=14)
        ms.current(self.md)
        ms.pack(side="left", padx=(10, 6))

        def goto(d):
            self.md = max(0, min(n - 1, d))
            self._reload(host)
        ms.bind("<<ComboboxSelected>>", lambda e: goto(ms.current()))
        ttk.Button(bar, text="◀", width=3, command=lambda: goto(self.md - 1)).pack(side="left", padx=2)
        ttk.Button(bar, text="▶", width=3, command=lambda: goto(self.md + 1)).pack(side="left", padx=2)
        b = 59 + (lg * 38 + self.md) * 20
        rows = [[k + 1, self._num(b + 2 * k), "–", self._num(b + 2 * k + 1)] for k in range(per)]
        EditableGrid(host, [(T("res.match"), 80), (T("c.home"), 80), ("", 30), (T("c.away"), 80)], rows,
                     height=per).pack(anchor="w", padx=10, pady=(0, 6))
        self._note(host, T("res.note")).pack(anchor="w", padx=10)

    def _pg_calendar(self, host):
        body = self._scroll_page(host)
        lf = ttk.LabelFrame(body, text=T("cal.season"), padding=8)
        lf.pack(fill="x", padx=10, pady=(10, 5))
        self._field(lf, 0, T("cal.day"), self._num_field(lf, 27972, "i32", width=8))
        for i in range(3):
            self._field(lf, 1 + i, T("cal.next", n=i + 1), self._num_field(lf, 28432 + i, width=6))
        bar = self._league_bar(body)
        ttk.Label(bar, text=T("cal.matches"), foreground=MUTED).pack(side="left", padx=6)
        f, n = ((0, 9), (20, 10), (40, 10))[self.lg]
        rows = [[k + 1, self._club_cell(27900 + f + 2 * k), self._club_cell(27901 + f + 2 * k)]
                for k in range(n)]
        EditableGrid(body, [("#", 40), (T("c.home_team"), 250, "w"), (T("c.away_team"), 250, "w")],
                     rows, height=n).pack(anchor="w", padx=10, pady=(0, 6))
        self._note(body, T("cal.note")).pack(anchor="w", padx=10, pady=(0, 6))
        pf = ttk.LabelFrame(body, text=T("cal.perm"), padding=8)
        pf.pack(fill="x", padx=10, pady=5)
        self._value_grid(pf, 28244 + 20 * self.lg, 20, 10).pack(anchor="w")
        self._note(body, T("cal.perm_note")).pack(anchor="w", padx=10, pady=(2, 10))

    # =================================================================== PAGES: Coppe
    def _pg_cup_state(self, host):
        body = self._scroll_page(host)
        cups = _tl("lists.cups")
        top = ttk.Frame(body)
        top.pack(fill="x", padx=10, pady=(10, 5))
        rel = ttk.LabelFrame(top, text=T("cup.relegation"), padding=8)
        rel.pack(side="left", fill="y", padx=(0, 10))
        self._field(rel, 0, T("cup.first_leg"), self._num_field(rel, 28007, width=6))
        self._field(rel, 1, T("cup.outcome"), self._num_field(rel, 34367, width=6))
        rnd = ttk.LabelFrame(top, text=T("cup.round"), padding=8)
        rnd.pack(side="left", fill="y", padx=(0, 10))
        for c, name in enumerate(cups):
            self._field(rnd, c, name, self._num_field(rnd, 28233 + c, width=6))
        leg = ttk.LabelFrame(top, text=T("cup.legs_played"), padding=8)
        leg.pack(side="left", fill="y")
        for c in range(3):
            self._field(leg, c, cups[c + 1], self._num_field(leg, 28241 + c, width=6))
        lf = ttk.LabelFrame(body, text=T("cup.qualified"), padding=8)
        lf.pack(fill="x", padx=10, pady=5)
        self._value_grid(lf, 27978, 10, 10).pack(anchor="w")
        lf = ttk.LabelFrame(body, text=T("cup.slots"), padding=8)
        lf.pack(fill="x", padx=10, pady=5)
        self._value_grid(lf, 27988, 18, 6).pack(anchor="w")

    def _pg_cup_ties(self, host):
        body = self._scroll_page(host)
        bar = ttk.Frame(body)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("cup.label")).pack(side="left")
        cb = ttk.Combobox(bar, values=_tl("lists.cups"), state="readonly", width=22)
        cb.current(self.cup)
        cb.pack(side="left", padx=6)

        def picked(_e):
            self.cup = cb.current()
            self._reload(host)
        cb.bind("<<ComboboxSelected>>", picked)
        c = self.cup
        rows = [[k + 1, self._club_cell(28009 + 32 * c + 2 * k), self._club_cell(28010 + 32 * c + 2 * k),
                 self._num(28304 + 32 * c + 2 * k), self._num(28305 + 32 * c + 2 * k)] for k in range(16)]
        EditableGrid(body, [("#", 40), (T("c.home_team"), 240, "w"), (T("c.away_team"), 240, "w"),
                            (T("cup.goals_h"), 60), (T("cup.goals_a"), 60)], rows,
                     height=16).pack(anchor="w", padx=10, pady=(0, 6))
        lf = ttk.LabelFrame(body, text=T("cup.first_leg_goals"), padding=8)
        lf.pack(fill="x", padx=10, pady=5)
        self._value_grid(lf, 28137, 96, 16).pack(anchor="w")
        self._note(body, T("cup.note")).pack(anchor="w", padx=10, pady=(2, 10))

    # =================================================================== PAGES: Club
    def _pg_clubs(self, host):
        sf = self.sf
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("cl.search")).pack(side="left")
        q = tk.StringVar()
        ttk.Entry(bar, textvariable=q, width=24).pack(side="left", padx=6)
        count = ttk.Label(bar, foreground=MUTED)
        count.pack(side="right")
        cols = [("#", 45), (T("c.name"), 200, "w")] + [(t, 52) for t in _tl("cl.cols")]
        grid = EditableGrid(host, cols, height=16)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        def draw(*_):
            f = q.get().upper()
            rows = []
            for i in range(200):
                n = sf.club_name(i)
                if not n or (f and f not in n):
                    continue
                o = CB + 34 * i
                rows.append([i, self._txt(o, 23)] + [self._num(o + k) for k in range(23, 34)])
            grid.set_rows(rows)
            count.config(text=T("cl.count", n=len(rows)))
        q.trace_add("write", draw)
        draw()
        self._note(host, T("cl.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_ext_standings(self, host):
        sf = self.sf
        rows = []
        for i in sf.club_ids(64):
            o = 12357 + 54 * i
            rows.append([i, sf.club_name(i), self._hexrun(o + 4, 8), self._hexrun(o + 13, 8)]
                        + [self._num(o + x) for x in (2, 3, 24, 25, 28, 29, 40, 41, 44, 45, 46)]
                        + [self._hexrun(o + 32, 6)])
        c = _tl("xs.cols")
        cols = [("#", 40), (T("c.club"), 190, "w"), (c[0], 235), (c[1], 235)] + [(t, 48) for t in c[2:13]] \
            + [(c[13], 160)]
        EditableGrid(host, cols, rows, height=20).pack(fill="both", expand=True, padx=10, pady=(10, 6))
        self._note(host, T("xs.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_raw(self, host):
        body = self._scroll_page(host)
        lf = ttk.LabelFrame(body, text=T("raw.block5"), padding=8)
        lf.pack(fill="x", padx=10, pady=(10, 5))
        rows = [[k + 1] + [self._num(5457 + 5 * k + j) for j in range(5)] for k in range(20)]
        c = _tl("raw.cols5")
        EditableGrid(lf, [("#", 40)] + [(t, 70) for t in c], rows, height=10).pack(anchor="w")
        for title, off, n in ((T("raw.tail1"), 34063, 161), (T("raw.tail2"), 34226, 141)):
            lf = ttk.LabelFrame(body, text=title, padding=8)
            lf.pack(fill="x", padx=10, pady=5)
            self._value_grid(lf, off, n, 20, w=38).pack(anchor="w")
        self._note(body, T("raw.note")).pack(anchor="w", padx=10, pady=(2, 10))

    def _pg_series(self, host):
        sf = self.sf
        rows = [[i, sf.club_name(i)] + [self._num(H + 2560 + 21 * i + k) for k in range(21)]
                for i in sf.club_ids(64)]
        EditableGrid(host, [("#", 40), (T("c.club"), 190, "w")] + [(str(k + 1), 42) for k in range(21)],
                     rows, height=18).pack(fill="both", expand=True, padx=10, pady=10)
        self._note(host, T("ser.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_records(self, host):
        sf = self.sf
        ids = sf.club_ids(64)
        if not ids:
            ttk.Label(host, text=T("rec.none"), foreground=MUTED).pack(padx=10, pady=10)
            return
        if self.rec_club not in ids:
            self.rec_club = ids[0]
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("pl.club")).pack(side="left")
        cb = ttk.Combobox(bar, values=[self._club_label(i) for i in ids], state="readonly", width=30)
        cb.current(ids.index(self.rec_club))
        cb.pack(side="left", padx=6)

        def picked(_e):
            self.rec_club = ids[cb.current()]
            self._reload(host)
        cb.bind("<<ComboboxSelected>>", picked)
        i = self.rec_club
        rows = [[lab, self._pair(H + 3988 + 8 * i + k, False), self._club_cell(H + 4500 + 8 * i + k)]
                for k, lab in enumerate(_tl("lists.records"))]
        c = _tl("rec.cols")
        EditableGrid(host, [(c[0], 160, "w"), (c[1], 110), (c[2], 250, "w")], rows,
                     height=8).pack(anchor="w", padx=10, pady=(0, 6))
        self._note(host, T("rec.note")).pack(anchor="w", padx=10)

    def _pg_versus(self, host):
        sf = self.sf
        rows = []
        for i in sf.club_ids(64):
            b = H + (self.mi * 64 + i) * 10
            rows.append([i, sf.club_name(i)] + [self._pair(b + j, True) for j in range(10)])
        home, away = T("c.home"), T("c.away")
        cols = [("#", 40), (T("c.club"), 190, "w")] + [(f"{k} {s}", 62) for k in range(1, 6) for s in (home, away)]
        EditableGrid(host, cols, rows, height=18).pack(fill="both", expand=True, padx=10, pady=10)
        self._note(host, T("vs.note")).pack(anchor="w", padx=10, pady=(0, 8))

    # =================================================================== PAGES: Messaggi
    def _pg_messages(self, host):
        sf = self.sf
        msgs = sf.read_messages()
        body = self._scroll_page(host)
        for idx, (m, _ptr, text) in enumerate(msgs):
            ttk.Label(body, text=T("msg.manager", n=m + 1, name=sf.manager_name(m)),
                      font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
            box = tk.Text(body, height=4, width=80, wrap="word", font=("Segoe UI", 10),
                          relief="solid", bd=1, undo=True)
            box.insert("1.0", text)
            box.pack(anchor="w", padx=10)

            def typed(_e, idx=idx, box=box):
                t = box.get("1.0", "end-1c")
                if len(t) > 240:
                    box.delete("1.0+240c", "end-1c")
                    t = t[:240]
                t = t.replace("\n", "^")
                if t != msgs[idx][2]:
                    msgs[idx][2] = t
                    sf.write_messages(msgs)
                    self._changed()
            box.bind("<KeyRelease>", typed)
        if not msgs:
            self._note(body, T("msg.none")).pack(anchor="w", padx=10, pady=10)
        self._note(body, T("msg.note")).pack(anchor="w", padx=10, pady=(10, 10))


# =================================================================== STANDALONE
def _resource_path(rel):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


def _guess_language():
    import locale
    try:
        name = (locale.getlocale()[0] or "").lower()
    except Exception:
        name = ""
    name = name or os.environ.get("LANG", "").lower()
    if name.startswith(("it", "ital")):
        return "it"
    if name.startswith(("de", "germ", "deut")):
        return "de"
    return "en"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = tk.Tk()
    _TR.set_language(_guess_language())
    root.title(APP_TITLE)
    root.geometry("1180x780")
    root.minsize(780, 560)
    root.configure(bg=BG)
    try:
        root.iconbitmap(default=_resource_path(os.path.join("assets", ICON_FILE)))
    except Exception:
        pass
    apply_editor_style(root)

    def retitle():
        sf = panel.sf
        name = f" – {os.path.basename(sf.path)}" if sf else ""
        root.title(f"{APP_TITLE}{name}{' *' if panel.is_dirty() else ''}")
    panel = SavegamePanel(root, standalone=True, on_change=retitle)
    panel.pack(fill=tk.BOTH, expand=True)

    def on_close():
        if panel.confirm_discard():
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    target = argv[0] if argv else os.getcwd()
    if os.path.isfile(target):
        panel.set_dir(os.path.dirname(os.path.abspath(target)))
        if panel.load_file(target):
            retitle()
    else:
        panel.set_dir(target)
    root.mainloop()


if __name__ == "__main__":
    main()
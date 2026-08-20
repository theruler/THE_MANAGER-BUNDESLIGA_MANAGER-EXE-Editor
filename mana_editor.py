"""
HEADER (984 bytes, 0x0000-0x03D7)
  0x0000  LOGO ID LEAGUE   64 x 1 byte   (img index .\\PIC\\NN.VGA, decimal)
  0x0040  CTF LEAGUE       64 x 3 bytes  (Condition / Technique / Form)
  0x0100  CTF EUROPE      136 x 3 bytes
  0x0298  POINTS LEAGUE    64 x 2 bytes  (byte0=max, byte1=min, range 0-254)
  0x0318  GOALS LEAGUE     64 x 2 bytes
  0x0398  RANK LEAGUE      64 x 1 byte   (initial ranking position)

LEAGUE SECTION (0x03D8, 64 teams x 543 bytes)
  23 bytes  team name  (ASCII, zero-padded)
  20 x 26 bytes  player names

EUROPE SECTION (0x8B98, 136 teams x 23 bytes)
  23 bytes  team name  (ASCII uppercase, zero-padded)
"""

import os
import json
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

HDR_LOGO_OFF  = 0x0000
HDR_CTF_L_OFF = 0x0040
HDR_CTF_E_OFF = 0x0100
HDR_PTS_OFF   = 0x0298
HDR_GLS_OFF   = 0x0318
HDR_RNK_OFF   = 0x0398
LEAGUE_START  = 0x03D8
TEAM_RECORD   = 23 + 20 * 26
EUROPE_START  = LEAGUE_START + 64 * TEAM_RECORD
EUROPE_RECORD = 23

N_LEAGUE = 64
N_EUROPE = 136

LEAGUE_BOUNDS = [
    ( 0, 18, 18),
    (18, 20, 20),
    (38, 20, 20),
    (58,  6,  6),
]

PLAYER_ROLES = ["P"]*2 + ["D"]*5 + ["C"]*8 + ["A"]*5
ROLE_COLOR = {"P": "#2980b9", "D": "#27ae60", "C": "#e67e22", "A": "#c0392b"}

BG     = "#F4F6F9"
FG     = "#2C3E50"
ACCENT = "#3498DB"
MUTED  = "#7F8C8D"
RED    = "#C0392B"

LEAGUE_BTN_COLORS = ["#1a6b3c", "#8B0000", "#1a3a6b", "#5a2d82"]
LEAGUE_BTN_ACTIVE = ["#27ae60", "#c0392b", "#2980b9", "#8e44ad"]

def load_vga_image(vga_path: str, palette_path: str = None, game_mode: str = "EM") -> Image.Image | None:

    if not os.path.isfile(vga_path):
        return None

    try:
        with open(vga_path, "rb") as f:
            data = f.read()

        file_size = len(data)
        header_len = 8 if game_mode == "BMH" else 6

        if file_size < header_len + 1:
            return None

        width = data[0] + (data[1] << 8)
        height = data[2] + (data[3] << 8)

        if width <= 0 or height <= 0 or width > 640 or height > 480:
            return None

        if game_mode == "BMH":
            payload_len = data[4] | (data[5] << 8) | (data[6] << 16) | (data[7] << 24)
        else:
            payload_len = data[4] | (data[5] << 8)

        payload_plus_header = payload_len + header_len
        payload_end = payload_plus_header - 1

        if payload_end >= file_size or payload_end < header_len:
            return None

        palette = []
        if file_size > payload_plus_header:
            pal_bytes = data[payload_plus_header:]
            for b in pal_bytes[:768]:
                palette.append(b * 4 if max(pal_bytes[:768]) <= 63 else b)
        elif palette_path and os.path.isfile(palette_path):
            with open(palette_path, "rb") as pf:
                pal_bytes = pf.read()
            for b in pal_bytes[:768]:
                palette.append(b * 4 if max(pal_bytes[:768]) <= 63 else b)
        else:
            for i in range(256):
                palette.extend([i, i, i])

        while len(palette) < 768:
            palette.extend([0, 0, 0])
        palette = palette[:768]

        offset = data[payload_end] - 1
        if offset < 1:
            return None

        pixels = bytearray()
        i = header_len
        target_pixels = width * height

        while i < payload_end and len(pixels) < target_pixels:
            b = data[i]

            if b > (offset + 1):
                if i + 1 >= payload_end:
                    break
                count = b - offset
                val = data[i + 1]
                pixels.extend([val] * count)
                i += 2
            elif b == 0:
                if i + 1 >= payload_end:
                    break
                val = data[i + 1]
                pixels.append(val)
                i += 2
            elif b == (offset + 1):
                i += 1
            else: 
                count = b + 1
                if i + count >= payload_end:
                    break
                pixels.extend(data[i + 1 : i + 1 + count])
                i += count + 1

        if len(pixels) < target_pixels:
            pixels.extend([0] * (target_pixels - len(pixels)))
        else:
            pixels = pixels[:target_pixels]

        img = Image.frombytes("P", (width, height), bytes(pixels))
        img.putpalette(palette)
        return img.convert("RGBA")

    except Exception as e:
        print(f"Errore durante il caricamento del file VGA {vga_path}: {e}")
        return None


def _dec(raw: bytes) -> str:
    end = raw.find(b"\x00")
    return raw[:end if end != -1 else len(raw)].decode("latin-1")


def _enc(name: str, length: int) -> bytes:
    return (name.upper().encode("latin-1", errors="replace")[:length - 1]
            ).ljust(length, b"\x00")


def parse_mana(data: bytes) -> dict:
    need = EUROPE_START + N_EUROPE * EUROPE_RECORD
    if len(data) < need:
        raise ValueError(f"File too short: {len(data)} bytes (expected at least {need})")

    logo = [data[HDR_LOGO_OFF + i] for i in range(N_LEAGUE)]
    ctfl = [(data[HDR_CTF_L_OFF+i*3], data[HDR_CTF_L_OFF+i*3+1], data[HDR_CTF_L_OFF+i*3+2])
            for i in range(N_LEAGUE)]
    ctfe = [(data[HDR_CTF_E_OFF+i*3], data[HDR_CTF_E_OFF+i*3+1], data[HDR_CTF_E_OFF+i*3+2])
            for i in range(N_EUROPE)]
    pts  = [(data[HDR_PTS_OFF+i*2], data[HDR_PTS_OFF+i*2+1]) for i in range(N_LEAGUE)]
    gls  = [(data[HDR_GLS_OFF+i*2], data[HDR_GLS_OFF+i*2+1]) for i in range(N_LEAGUE)]
    rnk  = [data[HDR_RNK_OFF+i] for i in range(N_LEAGUE)]

    teams = []
    for i in range(N_LEAGUE):
        base = LEAGUE_START + i * TEAM_RECORD
        players = [_dec(data[base+23+p*26: base+23+(p+1)*26]) for p in range(20)]
        teams.append({
            "name":    _dec(data[base: base+23]),
            "players": players,
            "logo":    logo[i],
            "ctf":     list(ctfl[i]),
            "pts":     list(pts[i]),
            "gls":     list(gls[i]),
            "rank":    rnk[i],
        })

    europe = []
    for i in range(N_EUROPE):
        base = EUROPE_START + i * EUROPE_RECORD
        europe.append({"name": _dec(data[base: base+23]), "ctf": list(ctfe[i])})

    return {"teams": teams, "europe": europe}


def serialize_mana(original: bytes, parsed: dict) -> bytes:
    data = bytearray(original)
    for i, t in enumerate(parsed["teams"]):
        data[HDR_LOGO_OFF + i]     = t["logo"] & 0xFF
        data[HDR_CTF_L_OFF+i*3]   = t["ctf"][0] & 0xFF
        data[HDR_CTF_L_OFF+i*3+1] = t["ctf"][1] & 0xFF
        data[HDR_CTF_L_OFF+i*3+2] = t["ctf"][2] & 0xFF
        data[HDR_PTS_OFF+i*2]     = t["pts"][0] & 0xFF
        data[HDR_PTS_OFF+i*2+1]   = t["pts"][1] & 0xFF
        data[HDR_GLS_OFF+i*2]     = t["gls"][0] & 0xFF
        data[HDR_GLS_OFF+i*2+1]   = t["gls"][1] & 0xFF
        data[HDR_RNK_OFF+i]       = t["rank"] & 0xFF
        base = LEAGUE_START + i * TEAM_RECORD
        data[base: base+23] = _enc(t["name"], 23)
        for p, pn in enumerate(t["players"]):
            off = base + 23 + p * 26
            data[off: off+26] = _enc(pn, 26)
    for i, e in enumerate(parsed["europe"]):
        base = EUROPE_START + i * EUROPE_RECORD
        data[base: base+23]        = _enc(e["name"], 23)
        data[HDR_CTF_E_OFF+i*3]   = e["ctf"][0] & 0xFF
        data[HDR_CTF_E_OFF+i*3+1] = e["ctf"][1] & 0xFF
        data[HDR_CTF_E_OFF+i*3+2] = e["ctf"][2] & 0xFF
    return bytes(data)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class _FixedEntry(tk.Entry):

    def __init__(self, parent, lo: int, hi: int, on_change=None, width=3, **kw):
        self._lo  = lo
        self._hi  = hi
        self._var = tk.StringVar()
        vcmd = (parent.winfo_toplevel().register(self._validate), "%P")
        super().__init__(parent, textvariable=self._var,
                         width=width, justify="center",
                         font=("Consolas", 9),
                         validate="key", validatecommand=vcmd, **kw)
        if on_change:
            self._var.trace_add("write", lambda *_: on_change())

    def _validate(self, val):
        return val == "" or val.lstrip("-").isdigit()

    def get_int(self) -> int:
        try:
            return _clamp(int(self._var.get()), self._lo, self._hi)
        except ValueError:
            return self._lo

    def set_int(self, v: int):
        self._var.set(str(_clamp(v, self._lo, self._hi)))


class _LeagueTab(ttk.Frame):

    def __init__(self, parent, parsed: dict, filepath: str = "", on_dirty=None):
        super().__init__(parent)
        self._parsed    = parsed
        self._filepath  = filepath
        self._on_dirty  = on_dirty
        self._building  = True
        self._team_btns: dict[int, tk.Button] = {}
        self._drag_src: int | None = None
        self._drag_moved = False
        self._widgets:  dict[int, dict]   = {}
        self._logo_cvs: dict[int, tk.Canvas] = {}
        self._cur_team: int | None = None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        grid_wrap = ttk.Frame(self, padding=(6, 6))
        grid_wrap.grid(row=0, column=0, sticky="ns")
        ttk.Separator(self, orient="vertical").grid(row=0, column=0,sticky="ns", padx=(0, 0))
        self._detail_outer = ttk.Frame(self, padding=(10, 6))
        self._detail_outer.grid(row=0, column=1, sticky="nsew")
        self._grid_frame = grid_wrap
        self._build_grid()
        self._building = False

    def _build_grid(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()
        self._team_btns.clear()

        col_offset = 0
        for li, (first, count, _) in enumerate(LEAGUE_BOUNDS):
            color  = LEAGUE_BTN_COLORS[li]
            active = LEAGUE_BTN_ACTIVE[li]
            tk.Label(self._grid_frame,
                     text=f" L{li+1} ", bg=color, fg="white",
                     font=("Segoe UI", 8, "bold"), relief="flat", padx=4
                     ).grid(row=0, column=col_offset, padx=(0, 1),
                            pady=(0, 4), sticky="ew")
            for row_i in range(count):
                ti  = first + row_i
                t   = self._parsed["teams"][ti]
                btn = tk.Button(
                    self._grid_frame,
                    text=t["name"][:20] or f"Team {ti}",
                    width=20, anchor="w",
                    bg=color, fg="white",
                    activebackground=active, activeforeground="white",
                    font=("Consolas", 9),
                    relief="flat", bd=0, padx=4, pady=2,
                    cursor="hand2",
                )
                btn.grid(row=row_i + 1, column=col_offset,
                         padx=(0, 1), pady=1, sticky="ew")
                btn.bind("<Button-1>",        lambda e, idx=ti: self._btn_press(idx, e))
                btn.bind("<B1-Motion>",       lambda e, idx=ti: self._btn_motion(idx, e))
                btn.bind("<ButtonRelease-1>", lambda e, idx=ti: self._btn_release(idx, e))
                self._team_btns[ti] = btn
            col_offset += 1

        self._ghost = tk.Label(self._grid_frame.winfo_toplevel(),
                               bg="#c8dff7", fg="#1a3a6b",
                               font=("Consolas", 9), relief="groove",
                               padx=6, pady=2)

        self._show_placeholder()

    def _btn_press(self, ti: int, event):
        self._drag_src   = ti
        self._drag_moved = False

    def _btn_motion(self, ti: int, event):
        self._drag_moved = True
        btn = self._team_btns.get(ti)
        if btn:
            btn.config(relief="groove", bg="#b0c8e8", fg="#1a3a6b")
        x = event.widget.winfo_rootx() + event.x
        y = event.widget.winfo_rooty() + event.y
        name = self._parsed["teams"][ti]["name"][:14] or f"Team {ti}"
        self._ghost.config(text=f"  {name}  ")
        self._ghost.place(x=x - self._ghost.winfo_toplevel().winfo_rootx() + 10,
                          y=y - self._ghost.winfo_toplevel().winfo_rooty() + 10)
        self._ghost.lift()

    def _btn_release(self, ti: int, event):
        src = self._drag_src
        self._drag_src = None

        self._ghost.place_forget()

        if src is not None:
            b = self._team_btns.get(src)
            if b:
                li  = self._league_of(src)
                sel = (src == self._cur_team)
                b.config(relief="sunken" if sel else "flat",
                         bg=LEAGUE_BTN_ACTIVE[li] if sel else LEAGUE_BTN_COLORS[li],
                         fg="white")

        if not self._drag_moved:
            self._show_team(ti)
            return

        x = event.widget.winfo_rootx() + event.x
        y = event.widget.winfo_rooty() + event.y
        target = None
        for idx, btn in self._team_btns.items():
            bx, by = btn.winfo_rootx(), btn.winfo_rooty()
            if bx <= x <= bx + btn.winfo_width() and by <= y <= by + btn.winfo_height():
                target = idx
                break

        if target is not None and target != src and src is not None:
            self._swap_teams(src, target)

        self._drag_moved = False

    def _league_of(self, ti: int) -> int:
        for li, (f, c, _) in enumerate(LEAGUE_BOUNDS):
            if f <= ti < f + c:
                return li
        return 0

    def _swap_teams(self, a: int, b: int):
        t = self._parsed["teams"]
        t[a], t[b] = t[b], t[a]
        self._refresh_btn_label(a)
        self._refresh_btn_label(b)
        if self._cur_team in (a, b):
            self._show_team(self._cur_team)
        if self._on_dirty:
            self._on_dirty()

    def _refresh_btn_label(self, ti: int):
        btn = self._team_btns.get(ti)
        if btn:
            name = self._parsed["teams"][ti]["name"]
            btn.config(text=name[:20] or f"Team {ti}")

    def _show_placeholder(self):
        for w in self._detail_outer.winfo_children():
            w.destroy()
        self._widgets.clear()
        self._logo_cvs.clear()
        ttk.Label(self._detail_outer,
                  text="← Click on a team to edit it",
                  foreground=MUTED, font=("Segoe UI", 12, "italic")
                  ).pack(expand=True)

    def _show_team(self, ti: int):
        self._building = True
        self._cur_team = ti

        for idx, btn in self._team_btns.items():
            li  = self._league_of(idx)
            sel = (idx == ti)
            btn.config(relief="sunken" if sel else "flat",
                       bg=LEAGUE_BTN_ACTIVE[li] if sel else LEAGUE_BTN_COLORS[li])

        for w in self._detail_outer.winfo_children():
            w.destroy()
        self._widgets.clear()
        self._logo_cvs.clear()

        t  = self._parsed["teams"][ti]
        w  = {}
        self._widgets[ti] = w
        c  = self._detail_outer

        rank_max = 20
        for (first, count, rm) in LEAGUE_BOUNDS:
            if first <= ti < first + count:
                rank_max = rm
                break

        left = ttk.Frame(c)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        name_lf  = ttk.LabelFrame(left, text="Team name (max 20)", padding=(4, 2))
        name_lf.pack(fill="x", pady=(0, 4))
        name_var = tk.StringVar(value=t["name"])

        def _limit_name(*_, nv=name_var):
            val = nv.get()
            if len(val) > 20:
                nv.set(val[:20])

        name_ent = ttk.Entry(name_lf, textvariable=name_var,
                             width=20, font=("Consolas", 10))
        name_ent.pack(fill="x")
        name_var.trace_add("write", _limit_name)
        name_var.trace_add("write", lambda *_, idx=ti: self._writeback(idx))
        w["name"] = name_var

        pl_lf = ttk.LabelFrame(left, text="Players (max 13)", padding=(3, 1))
        pl_lf.pack(fill="both", expand=False)
        w["players"] = []
        for p in range(20):
            role  = PLAYER_ROLES[p]
            rclr  = ROLE_COLOR.get(role, FG)
            row_f = ttk.Frame(pl_lf)
            row_f.pack(fill="x", pady=1)
            tk.Label(row_f, text=role, width=2, anchor="center",
                     bg=rclr, fg="white",
                     font=("Segoe UI", 7, "bold"), relief="flat"
                     ).pack(side="left", padx=(0, 2))
            pvar = tk.StringVar(value=t["players"][p])

            def _limit_player(*_, pv=pvar):
                val = pv.get()
                if len(val) > 13:
                    pv.set(val[:13])

            ttk.Entry(row_f, textvariable=pvar,
                      width=18, font=("Consolas", 9)
                      ).pack(side="left", fill="x", expand=True)
            pvar.trace_add("write", _limit_player)
            pvar.trace_add("write", lambda *_, idx=ti: self._writeback(idx))
            w["players"].append(pvar)

        right = ttk.Frame(c)
        right.grid(row=0, column=1, sticky="n", padx=(0, 0))

        stat = ttk.LabelFrame(right, text="Statistics", padding=(12, 8))
        stat.pack(fill="x", pady=(0, 8))

        for j, lbl in enumerate(("CONDITION", "TECHNIQUE", "FORM")):
            ttk.Label(stat, text=lbl, anchor="center",
                      font=("Segoe UI", 8, "bold"),
                      foreground=ACCENT, width=12
                      ).grid(row=0, column=j, padx=6, pady=(0, 2))

        w["ctf"] = []
        for j in range(3):
            fe = _FixedEntry(stat, 0, 99, width=5,
                             on_change=lambda: self._writeback(ti))
            fe.set_int(t["ctf"][j])
            fe.grid(row=1, column=j, padx=6, pady=(0, 10))
            w["ctf"].append(fe)

        ttk.Separator(stat, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        rank_row = ttk.Frame(stat)
        rank_row.grid(row=3, column=0, columnspan=3, pady=3)
        ttk.Label(rank_row, text="RANK", width=6, anchor="e",
                  foreground=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        rank_fe = _FixedEntry(rank_row, 0, rank_max, width=4,
                              on_change=lambda: self._writeback(ti))
        rank_fe.set_int(t["rank"])
        rank_fe.pack(side="left", padx=(4, 4))
        ttk.Label(rank_row, text=f"(0-{rank_max})", foreground=MUTED,
                  font=("Segoe UI", 8)).pack(side="left")
        w["rank"] = rank_fe

        pts_row = ttk.Frame(stat)
        pts_row.grid(row=4, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Label(pts_row, text="POINTS", width=8, anchor="e",
                  foreground=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        w["pts"] = []
        for lbl in ("max", "min"):
            ttk.Label(pts_row, text=lbl, foreground=MUTED,
                      font=("Segoe UI", 8)).pack(side="left", padx=(6, 1))
            fe = _FixedEntry(pts_row, 0, 254, width=4,
                             on_change=lambda: self._writeback(ti))
            fe.set_int(t["pts"][len(w["pts"])])
            fe.pack(side="left", padx=(0, 2))
            w["pts"].append(fe)

        gls_row = ttk.Frame(stat)
        gls_row.grid(row=5, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Label(gls_row, text="GOALS", width=8, anchor="e", foreground=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        w["gls"] = []
        for lbl in ("max", "min"):
            ttk.Label(gls_row, text=lbl, foreground=MUTED,font=("Segoe UI", 8)).pack(side="left", padx=(6, 1))
            fe = _FixedEntry(gls_row, 0, 254, width=4, on_change=lambda: self._writeback(ti))
            fe.set_int(t["gls"][len(w["gls"])])
            fe.pack(side="left", padx=(0, 2))
            w["gls"].append(fe)

        logo_lf = ttk.LabelFrame(right, text="Team Logo", padding=(10, 8))
        logo_lf.pack(fill="x")
        cvs = tk.Canvas(logo_lf, width=200, height=200,bg="#1a1a2e", highlightthickness=2,highlightbackground=ACCENT)
        cvs.pack(pady=(0, 6))
        self._logo_cvs[ti] = cvs
        self._draw_logo_display(cvs, t["logo"])
        ttk.Label(logo_lf, text="Logo ID", font=("Segoe UI", 8), foreground=MUTED).pack()
        
        logo_var = tk.StringVar()
        logo_sb = ttk.Spinbox(
            logo_lf, 
            from_=0, 
            to=255, 
            width=6, 
            textvariable=logo_var, 
            justify="center",
            command=lambda _ti=ti: self._on_logo_id_change(_ti)
        )
        logo_sb._var = logo_var
        
        def _get_int():
            val = logo_var.get()
            if val.isdigit():
                return max(0, min(255, int(val)))
            return 0

        logo_sb.get_int = _get_int
        logo_sb.set_int = lambda v: logo_var.set(str(v))
        
        logo_sb.set_int(t["logo"])
        logo_sb.pack(pady=(2, 8))
        w["logo"] = logo_sb
        logo_var.trace_add("write", lambda *_, _ti=ti: self._on_logo_id_change(_ti))
        c.columnconfigure(0, weight=0)
        c.columnconfigure(1, weight=1)
        c.rowconfigure(0, weight=1)
        self._building = False

    def _writeback(self, ti: int):
        if self._building:
            return
        w = self._widgets.get(ti)
        if not w:
            return
        t = self._parsed["teams"][ti]
        t["name"]    = w["name"].get()[:20].upper()
        t["rank"]    = w["rank"].get_int()
        t["ctf"]     = [fe.get_int() for fe in w["ctf"]]
        p0, p1       = w["pts"][0].get_int(), w["pts"][1].get_int()
        t["pts"]     = [max(p0, p1), min(p0, p1)]
        g0, g1       = w["gls"][0].get_int(), w["gls"][1].get_int()
        t["gls"]     = [max(g0, g1), min(g0, g1)]
        t["logo"]    = w["logo"].get_int()
        t["players"] = [v.get()[:13] for v in w["players"]]
        self._refresh_btn_label(ti)
        if self._on_dirty:
            self._on_dirty()

    def _draw_logo_display(self, cvs: tk.Canvas, logo_id: int):
        W, H = 200, 200
        cvs.delete("all")
        cvs.create_rectangle(0, 0, W, H, fill="#1a1a2e", outline="")

        if self._filepath:
            base_dir = os.path.dirname(os.path.abspath(self._filepath))
        else:
            base_dir = "."

        pic_dir = os.path.join(base_dir, "PIC")

        possible_paths = [
            os.path.join(pic_dir, f"{logo_id:02d}.VGA"),
            os.path.join(pic_dir, f"{logo_id}.VGA"),
            os.path.join(pic_dir, f"{logo_id:02d}.vga"),
            os.path.join(pic_dir, f"{logo_id}.vga"),
        ]

        vga_path = None
        for p in possible_paths:
            if os.path.isfile(p):
                vga_path = p
                break

        pal_path = os.path.join(base_dir, "1.PAL")
        if not os.path.isfile(pal_path):
            pal_path = os.path.join(pic_dir, "1.PAL")

        pil_img = None
        if vga_path:
            pil_img = load_vga_image(vga_path, palette_path=pal_path, game_mode="EM")

        if pil_img:
            pil_resized = pil_img.resize((W, H), Image.NEAREST)
            cvs._photo_ref = ImageTk.PhotoImage(pil_resized)
            cvs.create_image(W // 2, H // 2, image=cvs._photo_ref)
        else:
            cvs.create_oval(16, 16, W - 16, H - 16, outline="#3d5a80", width=3)
            cvs.create_text(W // 2, H // 2 - 14, text=f"VGA #{logo_id}",fill="#e0e0e0", font=("Segoe UI", 16, "bold"))
            cvs.create_text(W // 2, H // 2 + 18, text=f"PIC/{logo_id:02d}.VGA not found",fill="#e74c3c", font=("Consolas", 8))

    def _on_logo_id_change(self, ti: int):
        if self._building:
            return
        self._writeback(ti)
        w   = self._widgets.get(ti)
        cvs = self._logo_cvs.get(ti)
        if w and cvs and "logo" in w:
            self._draw_logo_display(cvs, w["logo"].get_int())

class _UefaTab(ttk.Frame):
    COLS = 5

    def __init__(self, parent, parsed: dict, on_dirty=None):
        super().__init__(parent)
        self._parsed   = parsed
        self._on_dirty = on_dirty
        self._entries: list[tuple] = []
        self._building = True

        self._db, self._years = self._load_db()
        self._selected_year = tk.StringVar()

        self._build()
        self._building = False

    def _load_db(self):
        search_paths = []
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            search_paths.append(os.path.join(base, "data", "uefa_clubs.json"))
        except Exception:
            pass
        search_paths += [os.path.join("data", "uefa_clubs.json"), "uefa_clubs.json"]

        for p in search_paths:
            if not os.path.isfile(p):
                continue
            try:
                with open(p, encoding="utf-8") as fh:
                    raw = json.load(fh)
                db = {}
                if isinstance(raw, dict):
                    for year, clubs in raw.items():
                        db[str(year)] = self._normalise_list(clubs)
                elif isinstance(raw, list):
                    db["default"] = self._normalise_list(raw)
                years = sorted(db.keys(), reverse=True)
                return db, years
            except Exception:
                pass
        return {}, []

    @staticmethod
    def _normalise_list(lst) -> list:
        if lst and isinstance(lst[0], dict):
            return [d.get("name", "") for d in lst]
        return [str(s) for s in lst]

    def _load_year(self, year: str):
        clubs = self._db.get(year, [])
        if not clubs:
            messagebox.showinfo("UEFA", f"No clubs found for year {year}.", parent=self)
            return
        self._building = True
        for i, (name_var, _) in enumerate(self._entries):
            if i < len(clubs):
                name_var.set(clubs[i][:20].upper())
        self._building = False
        for idx in range(N_EUROPE):
            self._wb(idx)

    def _randomize_all(self):
        lo = self._rnd_min.get_int()
        hi = self._rnd_max.get_int()
        if lo > hi:
            lo, hi = hi, lo
        self._building = True
        for _, ctf_fes in self._entries:
            for fe in ctf_fes:
                fe.set_int(random.randint(lo, hi))
        self._building = False
        for idx in range(N_EUROPE):
            self._wb(idx)

    def _wb(self, idx: int):
        if self._building:
            return
        name_var, ctf_fes = self._entries[idx]
        e = self._parsed["europe"][idx]
        e["name"] = name_var.get()[:20].upper()
        e["ctf"]  = [fe.get_int() for fe in ctf_fes]
        if self._on_dirty:
            self._on_dirty()

    def _build(self):
        tb = ttk.Frame(self, padding=(6, 4))
        tb.pack(fill="x", side="top")

        if self._years:
            ttk.Label(tb, text="Year:", foreground=MUTED,
                      font=("Segoe UI", 9)).pack(side="left")
            cmb = ttk.Combobox(tb, textvariable=self._selected_year,
                               values=self._years, width=8, state="readonly",
                               font=("Segoe UI", 9))
            cmb.pack(side="left", padx=(4, 8))
            if self._years:
                cmb.current(0)
                self._selected_year.set(self._years[0])
            ttk.Button(tb, text="Load year",
                       command=lambda: self._load_year(self._selected_year.get())
                       ).pack(side="left", padx=(0, 12))
        else:
            ttk.Label(tb,
                      text="⚠  data/uefa_clubs.json not found — year menu unavailable",
                      foreground=RED, font=("Segoe UI", 8)).pack(side="left", padx=(0, 12))

        ttk.Label(tb, text="Range:", foreground=MUTED,
                  font=("Segoe UI", 9)).pack(side="left", padx=(12, 2))
        self._rnd_max = _FixedEntry(tb, 0, 99, width=4)
        self._rnd_max.set_int(99)
        self._rnd_max.pack(side="left")
        ttk.Label(tb, text="–", foreground=MUTED).pack(side="left", padx=2)
        self._rnd_min = _FixedEntry(tb, 0, 99, width=4)
        self._rnd_min.set_int(40)
        self._rnd_min.pack(side="left", padx=(0, 6))
        ttk.Button(tb, text="🎲  RANDOMIZE CTF",
                   command=self._randomize_all).pack(side="left")

        sep_canvas = tk.Canvas(self, height=3, bg="#aab4be",
                               highlightthickness=0)
        sep_canvas.pack(fill="x")

        outer = ttk.Frame(self, padding=(4, 4))
        outer.pack(fill="both", expand=True)

        NCOLS = self.COLS
        rows_per_col = (N_EUROPE + NCOLS - 1) // NCOLS

        for col in range(NCOLS):
            bc = col * 6
            ttk.Label(outer, text="#", width=3, anchor="e",
                      foreground=MUTED,
                      font=("Segoe UI", 7, "bold")).grid(row=0, column=bc, padx=(2, 1))
            ttk.Label(outer, text="TEAM NAME", width=20, anchor="w",
                      font=("Segoe UI", 8, "bold")).grid(row=0, column=bc+1, padx=(0, 2))
            for j, lbl in enumerate(("C", "T", "F")):
                ttk.Label(outer, text=lbl, width=3, anchor="center",
                          font=("Segoe UI", 8, "bold"),
                          foreground=ACCENT).grid(row=0, column=bc+2+j, padx=1)
            if col < NCOLS - 1:
                sep_c = tk.Canvas(outer, width=3, bg="#aab4be",
                                  highlightthickness=0)
                sep_c.grid(row=0, column=bc+5, rowspan=rows_per_col + 2,
                           sticky="ns", padx=(3, 3))

        sep_hdr = tk.Canvas(outer, height=3, bg="#aab4be",
                            highlightthickness=0)
        sep_hdr.grid(row=1, column=0, columnspan=NCOLS * 6,
                     sticky="ew", pady=(1, 2))

        europe = self._parsed["europe"]
        for i in range(N_EUROPE):
            col     = i // rows_per_col
            row_off = i %  rows_per_col
            row     = row_off + 2
            bc      = col * 6
            e       = europe[i]

            ttk.Label(outer, text=f"{i+1}", width=3, anchor="e",
                      foreground=MUTED,
                      font=("Consolas", 8)).grid(row=row, column=bc,
                                                 padx=(2, 1), pady=0)

            name_var = tk.StringVar(value=e["name"])

            def _limit_uefa_name(*_, nv=name_var):
                v = nv.get()
                if len(v) > 20:
                    nv.set(v[:20])

            ent = ttk.Entry(outer, textvariable=name_var,
                            width=20, font=("Consolas", 8))
            ent.grid(row=row, column=bc+1, padx=(0, 2), pady=0, sticky="w")
            name_var.trace_add("write", _limit_uefa_name)
            name_var.trace_add("write", lambda *_, idx=i: self._wb(idx))

            ctf_fes = []
            for j in range(3):
                fe = _FixedEntry(outer, 0, 99, width=3,
                                 on_change=lambda idx=i: self._wb(idx))
                fe.set_int(e["ctf"][j])
                fe.grid(row=row, column=bc+2+j, padx=1, pady=0)
                ctf_fes.append(fe)

            self._entries.append((name_var, ctf_fes))


class ManaEditorWindow(tk.Toplevel):

    def __init__(self, parent=None, filepath: str = ""):
        super().__init__(parent)
        self.title("MANA.DAT Editor")
        self.geometry("1240x720")
        self.minsize(1000, 600)
        self.configure(bg=BG)
        self._filepath = filepath
        self._original: bytes = b""
        self._parsed:   dict  = {}
        self._dirty     = False
        self._league_tab: _LeagueTab | None = None
        self._uefa_tab:   _UefaTab   | None = None
        self._apply_style()
        self._build_menu()
        self._build_ui()
        if filepath:
            self._load(filepath)

    def _apply_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TFrame",background=BG)
        s.configure("TLabel",background=BG, foreground=FG,font=("Segoe UI", 10))
        s.configure("TLabelframe",background=BG, foreground=FG,font=("Segoe UI", 10, "bold"))
        s.configure("TLabelframe.Label", background=BG, foreground=FG)
        s.configure("TButton",font=("Segoe UI", 9, "bold"),padding=5, background=ACCENT, foreground="white",borderwidth=0)
        s.map("TButton",background=[("active", "#2980B9"), ("disabled", "#BDC3C7")])
        s.configure("TNotebook.Tab",font=("Segoe UI", 10, "bold"), padding=(16, 6))
        s.configure("TEntry",fieldbackground="white")
        s.configure("TCombobox",fieldbackground="white")

    def _build_menu(self):
        mb = tk.Menu(self, tearoff=False)
        self.config(menu=mb)
        fm = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="File", menu=fm)
        fm.add_command(label="Open MANA.DAT…",accelerator="Ctrl+O",command=self.cmd_open)
        fm.add_command(label="Save",accelerator="Ctrl+S",command=self.cmd_save)
        fm.add_command(label="Save as…",accelerator="Ctrl+Shift+S", command=self.cmd_save_as)
        fm.add_separator()
        fm.add_command(label="Close",            command=self.destroy)
        self.bind_all("<Control-o>", lambda e: self.cmd_open())
        self.bind_all("<Control-s>", lambda e: self.cmd_save())
        self.bind_all("<Control-S>", lambda e: self.cmd_save_as())
        hm = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="?", menu=hm)
        hm.add_command(label="MANA.DAT structure…", command=self._show_help)

    def _build_ui(self):
        top = ttk.Frame(self, padding=(12, 8, 12, 4))
        top.pack(fill="x")
        ttk.Button(top, text="Open…",    command=self.cmd_open   ).pack(side="left", padx=(0, 4))
        ttk.Button(top, text="Save",     command=self.cmd_save   ).pack(side="left", padx=(0, 4))
        ttk.Button(top, text="Save as…", command=self.cmd_save_as).pack(side="left")
        self._file_lbl = ttk.Label(top, text="No file",foreground=MUTED, font=("Segoe UI", 9, "italic"))
        self._file_lbl.pack(side="left", padx=(16, 0))
        self._dirty_lbl = ttk.Label(top, text="", foreground=RED,font=("Segoe UI", 9, "bold"))
        self._dirty_lbl.pack(side="right")
        ttk.Separator(self, orient="horizontal").pack(fill="x")
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=6, pady=6)
        self._status = ttk.Label(self, text="", anchor="w",padding=(8, 2), foreground=MUTED,font=("Segoe UI", 8))
        self._status.pack(side="bottom", fill="x")

    def _rebuild_tabs(self):
        for tab in self._nb.tabs():
            self._nb.forget(tab)
        self._league_tab = _LeagueTab(self._nb, self._parsed,filepath=self._filepath,on_dirty=self._mark_dirty)
        self._nb.add(self._league_tab, text="  LEAGUE  ")
        self._uefa_tab = _UefaTab(self._nb, self._parsed,on_dirty=self._mark_dirty)
        self._nb.add(self._uefa_tab, text="  UEFA  ")

    def _mark_dirty(self):
        self._dirty = True
        self._dirty_lbl.config(text="⚠  Unsaved changes")

    def _clear_dirty(self):
        self._dirty = False
        self._dirty_lbl.config(text="")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        return messagebox.askyesno(
            "Unsaved changes",
            "There are unsaved changes.\nContinue without saving?",
            parent=self)

    def cmd_open(self):
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            parent=self, title="Open MANA.DAT",
            filetypes=[("MANA data", "*.DAT *.dat"), ("All files", "*.*")])
        if path:
            self._load(path)

    def _load(self, path: str):
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
            parsed = parse_mana(raw)
        except Exception as exc:
            messagebox.showerror("Load error", str(exc), parent=self)
            return
        self._filepath = path
        self._original = raw
        self._parsed   = parsed
        self._clear_dirty()
        self._rebuild_tabs()
        name = os.path.basename(path)
        self._file_lbl.config(text=f"{name}  ({len(raw):,} bytes)")
        self._status.config(text=f"Loaded: {os.path.abspath(path)}")
        self.title(f"MANA.DAT Editor — {name}")

    def cmd_save(self):
        if not self._filepath or not self._original:
            return self.cmd_save_as()
        self._do_save(self._filepath)

    def cmd_save_as(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Save MANA.DAT as…",
            defaultextension=".DAT",
            filetypes=[("MANA data", "*.DAT *.dat"), ("All files", "*.*")])
        if path:
            self._do_save(path)

    def _do_save(self, path: str):
        if not self._original:
            messagebox.showwarning("No file", "No file loaded.", parent=self)
            return
        try:
            new_bytes = serialize_mana(self._original, self._parsed)
            with open(path, "wb") as fh:
                fh.write(new_bytes)
            self._filepath = path
            self._original = new_bytes
            self._clear_dirty()
            self._status.config(text=f"Saved: {os.path.abspath(path)}")
            self.title(f"MANA.DAT Editor — {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Save error", str(exc), parent=self)

    def _show_help(self):
        win = tk.Toplevel(self)
        win.title("MANA.DAT structure")
        win.geometry("540x420")
        win.configure(bg=BG)
        txt = tk.Text(win, wrap="word", font=("Consolas", 9),
                      bg="#1a1a2e", fg="#e0e0e0",
                      padx=10, pady=10, relief="flat")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("end", __doc__)
        txt.config(state="disabled")


def attach_to_main_editor(editor):
    root = editor.root

    def _open_mana():
        path = filedialog.askopenfilename(
            parent=root, title="Open MANA.DAT",
            filetypes=[("MANA data", "*.DAT *.dat"), ("All files", "*.*")])
        if path:
            ManaEditorWindow(root, filepath=path)

    try:
        fm = editor.file_menu
        fm.insert_separator(2)
        fm.insert_command(3, label="MANA.DAT Editor…", command=_open_mana)
    except Exception:
        pass


if __name__ == "__main__":
    import sys
    root = tk.Tk()
    root.withdraw()
    fp = sys.argv[1] if len(sys.argv) > 1 else ""
    win = ManaEditorWindow(root, filepath=fp)
    win.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

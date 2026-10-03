import os
import re
import struct
import sys

from PIL import Image

FRAME_SIZE = 164
N_RECORDS = 27
CELL_W, CELL_H = 12, 11
SHEET_COLS = 24
Y_OFFSET = 35
WIN_W, WIN_H = 182, 96
SIGNATURES = (b"BM-Ed1.0-WK\x00", b"BM-Ed1.3-WK\x00")
GOAL_L = ((0, 0, 24, 20), (0, 54)) 
GOAL_R = ((24, 0, 46, 20), (296, 54))

def _hex_palette(s, scale=1):
    return [
        (min(255, int(s[i:i + 2], 16) * scale),
         min(255, int(s[i + 2:i + 4], 16) * scale),
         min(255, int(s[i + 4:i + 6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]

PAL_DEFAULT = _hex_palette(
    "000000A0A0C08080A0707090606080505070404060303050000070907050B0A080D0C0B0506010607020608030709040600010900010B00020C07020A060207040103040C0F0F000B0A070908050806040604030503020F0F0F0C030C0000000",
    scale=1)
_ALPHA_LUT = bytes([0] + [255] * 255)
FILTERS = (("T", "Score"), ("V", "Failure"), ("E", "Penalty kick"), ("J", "Joke"))
FILTER_LETTERS = set(k for k, _ in FILTERS)
BASE_LETTERS = {"T", "V"}
MOD_LETTERS = {"E", "J"}
ALL_LABEL = ""


def ext_letters(filename):
    ext = os.path.splitext(filename)[1][1:].upper()
    letters = set(ext)
    if ext and letters <= FILTER_LETTERS:
        return letters
    return None


def leading_number(filename):
    m = re.match(r"\d+", filename)
    return int(m.group()) if m else None


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _palette_to_flat_rgb(pal, size=256):
    flat = []
    for r, g, b in pal:
        flat.extend((r, g, b))
    while len(flat) < size * 3:
        flat.extend((0, 0, 0))
    return flat[:size * 3]


def load_vga_image(vga_path, palette):
    if not os.path.isfile(vga_path):
        return None
    try:
        with open(vga_path, "rb") as f:
            data = f.read()
        header_len = 6
        if len(data) < header_len:
            return None
        width = data[0] | (data[1] << 8)
        height = data[2] | (data[3] << 8)
        payload_len = data[4] | (data[5] << 8)
        if width <= 0 or height <= 0 or width > 1280 or height > 960:
            return None
        payload_end = header_len + payload_len - 1
        if payload_end < header_len or payload_end >= len(data):
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
                pixels.extend((data[i + 1],) * (b - offset))
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
        img = Image.frombytes("P", (width, height), bytes(pixels))
        img.putpalette(_palette_to_flat_rgb(palette))
        return img
    except (OSError, ValueError, IndexError):
        return None

class TEFile:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 17 or data[:12] not in SIGNATURES:
            raise ValueError("Firma non valida: non e' un file .TE (BM-Ed1.x-WK)")
        self.version = data[:11].decode("ascii")
        n = data[16] + 1
        end = 17 + n * FRAME_SIZE
        if len(data) < end:
            raise ValueError("File troncato: %d byte, ne servono almeno %d" % (len(data), end))
        self.frames = []
        for i in range(n):
            w = struct.unpack("<82H", data[17 + i * FRAME_SIZE: 17 + (i + 1) * FRAME_SIZE])
            scroll = (w[0] & 0xFF, w[0] >> 8)
            recs = [w[1 + 3 * k: 4 + 3 * k] for k in range(N_RECORDS)]
            self.frames.append((scroll, recs))
        tail = data[end:]
        self.author = ""
        if tail:
            self.author = tail[1:1 + tail[0]].split(b"\x00")[0].decode("cp437", "replace")

def find_pic_dir(te_path):
    folder = os.path.dirname(os.path.abspath(te_path))
    for _ in range(3):
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                p = os.path.join(folder, name)
                if name.lower() == "pic" and os.path.isdir(p):
                    return p
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    return None


def find_file(folder, stem):
    if folder and os.path.isdir(folder):
        for fn in os.listdir(folder):
            if fn.lower() == stem.lower() + ".vga":
                return os.path.join(folder, fn)
    return None


def _to_rgba(img_p):
    rgba = img_p.convert("RGBA")
    mask = Image.frombytes("L", img_p.size, img_p.tobytes().translate(_ALPHA_LUT))
    rgba.putalpha(mask)
    return rgba


class Graphics:
    def __init__(self, pic_dir):
        self.pic_dir = pic_dir
        self.missing = []
        loaded = {}
        for stem, what in (("26", "campo"), ("27", "sprite"), ("29", "reti")):
            p = find_file(pic_dir, stem)
            img = load_vga_image(p, PAL_DEFAULT) if p else None
            if img is None:
                self.missing.append("%s.VGA (%s)" % (stem, what))
            loaded[stem] = img
        self.field = loaded["26"].convert("RGBA") if loaded["26"] else Image.new("RGBA", (320, 112), (40, 120, 40, 255))
        self.sheet = _to_rgba(loaded["27"]) if loaded["27"] else None
        self.goals = _to_rgba(loaded["29"]) if loaded["29"] else None
        self._cache = {}

    def sprite(self, sid):
        if not self.sheet:
            return None
        if sid not in self._cache:
            col, row = sid % SHEET_COLS, sid // SHEET_COLS
            x0, w = col * CELL_W, CELL_W
            if sid >= 142:
                x0, w = x0 + 4, 4
            box = (x0, row * CELL_H, x0 + w, row * CELL_H + CELL_H)
            self._cache[sid] = self.sheet.crop(box) if box[3] <= self.sheet.height else None
        return self._cache[sid]


def render_frame(gfx, frame, window=True):
    (sx, sy), recs = frame
    img = gfx.field.copy()
    for x, y, sid in recs:
        if sid >= 1000:
            if gfx.goals:
                box, dst = GOAL_L if sid == 1000 else GOAL_R
                part = gfx.goals.crop(box)
                img.paste(part, dst, part)
            continue
        spr = gfx.sprite(sid)
        if spr:
            img.paste(spr, (x, y + Y_OFFSET), spr)
    if window:
        sx = min(sx, max(0, img.width - WIN_W))
        sy = min(sy, max(0, img.height - WIN_H))
        img = img.crop((sx, sy, sx + WIN_W, sy + WIN_H))
    return img

def run_gui(path=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from PIL import ImageTk

    class Viewer(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("TORE Viewer")
            self.te = None
            self.gfx = Graphics(None)
            self.idx = 0
            self.playing = False
            self.window_mode = tk.BooleanVar(value=True)
            self.loop = tk.BooleanVar(value=True)
            self.fps = tk.IntVar(value=12)
            self.zoom = tk.IntVar(value=3)
            self._photo = None
            self.canvas = tk.Canvas(self, bg="black", highlightthickness=0,width=WIN_W * 3, height=WIN_H * 3)
            self.canvas.pack(padx=6, pady=6)
            self.folder = None
            self.files = {}
            self._job = None
            top = ttk.Frame(self)
            top.pack(fill="x", padx=6, pady=(6, 0))
            ttk.Button(top, text="Cartella...", command=self.choose_folder).pack(side="left")
            self.filters = {}
            for letter, label in FILTERS:
                v = tk.BooleanVar(value=True)
                self.filters[letter] = v
                ttk.Checkbutton(top, text="%s (%s)" % (label, letter), variable=v,
                                command=self.refresh_list).pack(side="left", padx=(8, 0))
            top2 = ttk.Frame(self)
            top2.pack(fill="x", padx=6, pady=(4, 0))
            ttk.Label(top2, text="N.").pack(side="left")
            self.num_var = tk.StringVar(value=ALL_LABEL)
            vcmd = (self.register(lambda s: s == "" or s.isdigit()), "%P")
            self.num_spin = ttk.Spinbox(top2, values=(ALL_LABEL,), width=6, wrap=True,textvariable=self.num_var, command=self.refresh_list,validate="key", validatecommand=vcmd)
            self.num_spin.pack(side="left", padx=(2, 10))
            self.num_spin.bind("<KeyRelease>", lambda e: self.refresh_list())
            self.num_spin.bind("<Return>", lambda e: self.focus_set())
            ttk.Button(top2, text="Reset filters", command=self.reset_filters).pack(side="left", padx=(0, 10))
            ttk.Label(top2, text="Scena").pack(side="left")
            self.combo = ttk.Combobox(top2, state="readonly", width=30)
            self.combo.pack(side="left", padx=(6, 6))
            self.combo.bind("<<ComboboxSelected>>", self.on_select)
            self.count = ttk.Label(top2, text="")
            self.count.pack(side="left")
            bar = ttk.Frame(self)
            bar.pack(fill="x", padx=6, pady=(6, 0))
            ttk.Button(bar, text="|<", width=3, command=lambda: self.goto(0)).pack(side="left", padx=(8, 0))
            ttk.Button(bar, text="<", width=3, command=lambda: self.step(-1)).pack(side="left")
            self.btn = ttk.Button(bar, text="Play", width=6, command=self.toggle)
            self.btn.pack(side="left")
            ttk.Button(bar, text=">", width=3, command=lambda: self.step(1)).pack(side="left")
            ttk.Button(bar, text=">|", width=3, command=self.goto_end).pack(side="left")
            ttk.Checkbutton(bar, text="Loop", variable=self.loop).pack(side="left", padx=4)
            ttk.Checkbutton(bar, text="Window (scroll)", variable=self.window_mode,command=self.redraw).pack(side="left")
            bar2 = ttk.Frame(self)
            bar2.pack(fill="x", padx=6, pady=(4, 0))
            ttk.Label(bar2, text="fps").pack(side="left")
            ttk.Spinbox(bar2, from_=1, to=60, width=4, textvariable=self.fps).pack(side="left", padx=(2, 10))
            ttk.Label(bar2, text="zoom").pack(side="left")
            ttk.Spinbox(bar2, from_=1, to=6, width=3, textvariable=self.zoom,command=self.redraw).pack(side="left", padx=(2, 14))
            self.info = ttk.Label(bar2, anchor="w")
            self.info.pack(side="left")
            self.slider = ttk.Scale(self, from_=0, to=0, orient="horizontal", command=self.on_slide)
            self.slider.pack(fill="x", padx=6, pady=4)
            self.status = ttk.Label(self, anchor="w")
            self.status.pack(fill="x", padx=6, pady=(0, 6))
            self.bind("<space>", self._unless_typing(self.toggle))
            self.bind("<Left>",  self._unless_typing(lambda: self.step(-1)))
            self.bind("<Right>", self._unless_typing(lambda: self.step(1)))
            self.bind("<Home>",  self._unless_typing(lambda: self.goto(0)))
            self.bind("<End>",   self._unless_typing(self.goto_end))
            self.after(100, lambda: self.startup(path))

        def _unless_typing(self, fn):
            def handler(e):
                if self.focus_get() is not self.num_spin:
                    fn()
            return handler

        def startup(self, path):
            if path and os.path.isdir(path):
                self.set_folder(path)
                return
            if path and os.path.isfile(path):
                self.set_folder(os.path.dirname(os.path.abspath(path)))
                name = os.path.basename(path)
                if name in self.files:
                    self.combo.set(name)
                    if self.load(self.files[name]):
                        self.play()
                return
            folder = filedialog.askdirectory(title="Seleziona la cartella TORE (Goal scenes)", mustexist=True)
            if not folder:
                self.destroy()
                return
            self.set_folder(folder)

        def choose_folder(self):
            folder = filedialog.askdirectory(title="Seleziona la cartella TORE (Goal scenes)",
                                             mustexist=True, initialdir=self.folder)
            if folder:
                self.set_folder(folder)

        def set_folder(self, folder):
            self.folder = folder
            nums = set()
            for fn in os.listdir(folder):
                if ext_letters(fn) and os.path.isfile(os.path.join(folder, fn)):
                    n = leading_number(fn)
                    if n is not None:
                        nums.add(n)
            self.num_spin.config(values=[ALL_LABEL] + [str(n) for n in sorted(nums)])
            self.num_var.set(ALL_LABEL)
            self.refresh_list()

        def reset_filters(self):
            for v in self.filters.values():
                v.set(True)
            self.num_var.set(ALL_LABEL)
            self.refresh_list()

        def refresh_list(self):
            selected = set(k for k, v in self.filters.items() if v.get())
            num = self.num_var.get()
            bases, mods = selected & BASE_LETTERS, selected & MOD_LETTERS
            self.files = {}
            if self.folder:
                for fn in os.listdir(self.folder):
                    full = os.path.join(self.folder, fn)
                    letters = ext_letters(fn)
                    if not letters or not os.path.isfile(full):
                        continue
                    if selected and selected != FILTER_LETTERS:
                        f_base, f_mods = letters & BASE_LETTERS, letters & MOD_LETTERS
                        if bases and not (f_base and f_base <= bases):
                            continue
                        if f_mods != mods:
                            continue
                    if num != ALL_LABEL and leading_number(fn) != int(num):
                        continue
                    self.files[fn] = full
            names = sorted(self.files, key=natural_key)
            self.combo["values"] = names
            if self.combo.get() not in self.files:
                self.combo.set("")
            self.count.config(text="%d file" % len(names))

        def on_select(self, _event=None):
            name = self.combo.get()
            if name in self.files and self.load(self.files[name]):
                self.play()
            self.focus_set()

        def load(self, p):
            try:
                self.te = TEFile(p)
            except Exception as e:
                messagebox.showerror("Errore", str(e))
                return False
            pic = find_pic_dir(p) or getattr(self, "pic_dir", None)
            if pic is None:
                pic = filedialog.askdirectory(title="Cartella PIC non trovata: selezionala (contiene 26.VGA, 27.VGA, 29.VGA)")
                pic = pic or None
            if pic:
                self.pic_dir = pic
            self.gfx = Graphics(pic)
            if pic is None:
                self.status.config(text="Cartella PIC non trovata accanto a %s" % os.path.basename(os.path.dirname(os.path.abspath(p))))
            elif self.gfx.missing:
                self.status.config(text="In %s mancano: %s" % (pic, ", ".join(self.gfx.missing)))
            else:
                self.status.config(text="Grafica da " + pic)
            self.stop()
            self.slider.config(to=len(self.te.frames) - 1)
            self.title("TE viewer - %s (%s, %s)" % (os.path.basename(p), self.te.version, self.te.author))
            self.goto(0)
            return True

        def goto(self, i):
            if not self.te:
                return
            self.idx = max(0, min(len(self.te.frames) - 1, i))
            self.slider.set(self.idx)
            self.redraw()

        def goto_end(self):
            if self.te:
                self.goto(len(self.te.frames) - 1)

        def step(self, d):
            if self.te:
                self.goto((self.idx + d) % len(self.te.frames))

        def on_slide(self, v):
            i = int(float(v))
            if self.te and i != self.idx:
                self.idx = i
                self.redraw()

        def play(self):
            if not self.te or self.playing:
                return
            self.playing = True
            self.btn.config(text="Pausa")
            self.tick()

        def stop(self):
            self.playing = False
            if self._job is not None:
                self.after_cancel(self._job)
                self._job = None
            self.btn.config(text="Play")

        def toggle(self):
            if not self.te:
                return
            if self.playing:
                self.stop()
            else:
                self.play()

        def tick(self):
            self._job = None
            if not self.playing:
                return
            if self.idx >= len(self.te.frames) - 1:
                if not self.loop.get():
                    self.stop()
                    return
                self.goto(0)
            else:
                self.goto(self.idx + 1)
            try:
                fps = max(1, int(self.fps.get()))
            except (tk.TclError, ValueError):
                fps = 12
            self._job = self.after(int(1000 / fps), self.tick)

        def redraw(self):
            if not self.te:
                return
            frame = self.te.frames[self.idx]
            img = render_frame(self.gfx, frame, self.window_mode.get())
            try:
                z = max(1, int(self.zoom.get()))
            except (tk.TclError, ValueError):
                z = 3
            img = img.resize((img.width * z, img.height * z), Image.NEAREST)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.config(width=img.width, height=img.height)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
            self.info.config(text="frame %d/%d    scroll (%d, %d)" % (self.idx + 1, len(self.te.frames), *frame[0]))

    Viewer().mainloop()


if __name__ == "__main__":
    run_gui(sys.argv[1] if len(sys.argv) > 1 else None)

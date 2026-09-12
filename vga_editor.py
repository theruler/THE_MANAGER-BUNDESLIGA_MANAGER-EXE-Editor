from __future__ import annotations
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from PIL import Image, ImageTk

def _hex_palette(s: str, scale: int = 1) -> list[tuple[int, int, int]]:
    return [
        (min(255, int(s[i:i+2], 16) * scale),
         min(255, int(s[i+2:i+4], 16) * scale),
         min(255, int(s[i+4:i+6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]

_PAL_GREYSCALE      = _hex_palette("000000808080404040C0C0C0202020A0A0A0606060E0E0E0101010909090505050D0D0D0303030B0B0B0707070F0F0F0", scale=1)
_PAL_TITLE          = _hex_palette("000000F0F0F0D0E0F0B0D0F090C0F080A0E04070C03060B0105090103070001060001040001030608030407010406010305010304010809090606060304050203040706010F0C0B0F0B090F09070E08060C06040B04030903020701000501000", scale=1)
_PAL_ADVERTISEMENTS = _hex_palette("000000A0A0C08080A0707090606080505070404060303050000070907050B0A080D0C0B0506010607020608030709040600010900010B00020C07020A06020704010000050C0C0E0806040402020705030604030503020F0F0F0A08060202040", scale=1)
_PAL_NORMAL         = _hex_palette("000000A0A0C08080A0707090606080505070404060303050000070907050B0A080D0C0B0506010607020608030709040600010900010B00020C07020A060207040103040C0F0F000B0A070908050806040604030503020F0F0F0C030C0000000", scale=1)
_PAL_LOADER         = _hex_palette("10000090A0C01020102030302060201060301060801080A01060D00090C000A0C020A0C000A0C010A0C020A0C020C0F040200040502080100070401040606040709090603080706070A0A0004000E0D070C0C0B060A0D0B0C0C0D0C0C0F0F0F0", scale=1)

_PAL_NORMAL20       = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040C10303C3C002C281C24201420181018100C140C083C3C3C300C300000003F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4)

_PAL_ADVERTISEMENTS20 = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040000143030382018101008081C140C18100C140C083C3C3C2820180808103F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4) 

BUILTIN_PALETTES: dict[str, list[tuple[int, int, int]]] = {
    "Default":          _PAL_NORMAL,
    "Default 2.0":      _PAL_NORMAL20,
    "Newspaper":        _PAL_GREYSCALE,
    "Sponsors":         _PAL_ADVERTISEMENTS,
    "Sponsors 2.0":     _PAL_ADVERTISEMENTS20,
    "Title":            _PAL_TITLE,
    "Loader":           _PAL_LOADER,
}

def _palette_to_flat_rgb(pal: list[tuple[int, int, int]], size: int = 256) -> list[int]:
    flat: list[int] = []
    for r, g, b in pal:
        flat.extend((r, g, b))
    while len(flat) < size * 3:
        flat.extend((0, 0, 0))
    return flat[:size * 3]

def load_vga_image(vga_path: str, palette: list[tuple[int, int, int]]) -> Image.Image | None:
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
                count = b - offset
                value = data[i + 1]
                pixels.extend((value,) * count)
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

_RLE_OFFSET = 127
_RLE_SENTINEL = _RLE_OFFSET + 1
_RLE_MAX_COUNT = 127

class VgaEncodeError(Exception):
    pass

def _rle_encode_indices(indices: list[int]) -> bytearray:
    if not indices:
        raise VgaEncodeError("No pixels to save.")

    out = bytearray()
    n = len(indices)
    i = 0

    while i < n:
        run_value = indices[i]
        run_length = 1

        while (
            i + run_length < n
            and indices[i + run_length] == run_value
            and run_length < _RLE_MAX_COUNT
        ):
            run_length += 1

        if run_length >= 2:
            out.append(run_length + _RLE_OFFSET)
            out.append(run_value)
            i += run_length
            continue

        start = i
        i += 1

        while i < n and (i - start) < _RLE_MAX_COUNT:
            if i + 1 < n and indices[i] == indices[i + 1]:
                break
            i += 1

        count = i - start
        out.append(count - 1)
        out.extend(indices[start:i])

    out.append(_RLE_SENTINEL)
    return out

def save_vga_image(img: Image.Image, dest_path: str) -> None:
    if img is None:
        raise VgaEncodeError("No image to save.")

    if img.mode != "P":
        raise VgaEncodeError("Internal image is not in indexed format.")

    w, h = img.size
    if w <= 0 or h <= 0:
        raise VgaEncodeError(f"Invalid image dimensions: {w}x{h}")

    indices = list(img.tobytes())
    payload = _rle_encode_indices(indices)

    if len(payload) > 0xFFFF:
        raise VgaEncodeError(
            f"Payload too large ({len(payload)} bytes > 65535). "
            "Reduce image dimensions or complexity."
        )

    header = bytearray(6)
    header[0] = w & 0xFF
    header[1] = (w >> 8) & 0xFF
    header[2] = h & 0xFF
    header[3] = (h >> 8) & 0xFF
    header[4] = len(payload) & 0xFF
    header[5] = (len(payload) >> 8) & 0xFF

    tmp_path = dest_path + ".tmp"

    try:
        with open(tmp_path, "wb") as f:
            f.write(header)
            f.write(payload)

        os.replace(tmp_path, dest_path)

    except OSError as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise VgaEncodeError(f"File write error: {exc}") from exc

BG        = "#F4F6F9"
FG        = "#2C3E50"
ACCENT    = "#3498DB"
MUTED     = "#7F8C8D"
RED       = "#C0392B"
SEL_COLOR = "#00BFFF"

TOOL_DRAW       = "draw"
TOOL_SELECT     = "select"
TOOL_PICK       = "pick"
TOOL_MOVE_PASTE = "move_paste"
TOOL_HAND       = "hand"

ZOOM_LEVELS = [1, 2, 4, 8, 16]

def _natural_key(s: str):
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r"(\d+)", s)]

def _rgb_to_palette_index(
    r: int, g: int, b: int, palette: list[tuple[int, int, int]]
) -> int:
    best_idx = 0
    best_dist = float("inf")
    for i, (pr, pg, pb) in enumerate(palette):
        if (pr, pg, pb) == (r, g, b):
            return i
        dist = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


class _ImageCanvas(tk.Frame):

    def __init__(self, parent, on_modified=None, on_color_picked=None, **kw):
        super().__init__(parent, bg="#1a1a2e", **kw)
        self._on_modified = on_modified
        self._on_color_picked = on_color_picked
        self._img: Image.Image | None = None
        self._palette: list[tuple[int, int, int]] = list(_PAL_NORMAL)
        self._zoom = 2
        self._tool = TOOL_DRAW
        self._draw_color = (255, 255, 255, 255)
        self._show_grid = True
        self._clipboard: Image.Image | None = None
        self._sel: tuple[int, int, int, int] | None = None
        self._sel_start: tuple[int, int] | None = None
        self._dragging = False
        self._paste_buf: Image.Image | None = None
        self._paste_pos: tuple[int, int] = (0, 0)
        self._paste_drag_start: tuple[int, int] | None = None
        self._paste_drag_origin: tuple[int, int] = (0, 0)
        self._paste_src: Image.Image | None = None
        self._paste_resize_corner: str | None = None
        self._paste_resize_anchor: tuple[int, int] = (0, 0)
        self._paste_resize_filter: int = Image.NEAREST
        self._paste_aspect_lock: bool = False
        self._pan_start: tuple[int, int] | None = None
        self._drawing_stroke: bool = False
        self._last_draw_pt: tuple[int, int] | None = None

        view = tk.Frame(self, bg="#1a1a2e")
        view.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(view, bg="#1a1a2e", cursor="crosshair", highlightthickness=0, xscrollincrement=1, yscrollincrement=1)
        self._vbar = ttk.Scrollbar(view, orient=tk.VERTICAL, command=self._canvas.yview)
        self._hbar = ttk.Scrollbar(view, orient=tk.HORIZONTAL, command=self._canvas.xview)
        self._canvas.configure(xscrollcommand=self._hbar.set, yscrollcommand=self._vbar.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vbar.grid(row=0, column=1, sticky="ns")
        self._hbar.grid(row=1, column=0, sticky="ew")
        self._corner = tk.Frame(view, bg="#1a1a2e", width=0, height=0)
        self._corner.grid(row=1, column=1, sticky="nsew")
        self._vbar.grid_remove()
        self._hbar.grid_remove()
        self._corner.grid_remove()
        view.grid_rowconfigure(0, weight=1)
        view.grid_columnconfigure(0, weight=1)
        self._view = view
        self._tk_img = None
        self._canvas.bind("<Button-1>", self._on_b1_press)
        self._canvas.bind("<B1-Motion>", self._on_b1_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_b1_release)
        self._canvas.bind("<Button-2>", self._on_b3_press)
        self._canvas.bind("<Button-3>", self._on_b3_press)
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Configure>", lambda _e: self._redraw())
        self._canvas.bind("<Escape>", self.deselect)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel_zoom)
        self._canvas.bind("<Button-4>", self._on_mousewheel_zoom)
        self._canvas.bind("<Button-5>", self._on_mousewheel_zoom)
        self._zoom_changed_callback = None

    def _on_mousewheel_zoom(self, event):
        old_zoom = self._zoom
        if getattr(event, 'num', None) == 4 or (hasattr(event, 'delta') and event.delta > 0):
            new_zoom = min(16, old_zoom + 1)
        elif getattr(event, 'num', None) == 5 or (hasattr(event, 'delta') and event.delta < 0):
            new_zoom = max(1, old_zoom - 1)
        else:
            return "break"

        if new_zoom == old_zoom:
            return "break"

        canvas_x = self._canvas.canvasx(event.x)
        canvas_y = self._canvas.canvasy(event.y)
        img_x = canvas_x / old_zoom
        img_y = canvas_y / old_zoom
        self._zoom = new_zoom
        self._redraw()
        new_canvas_x = img_x * new_zoom
        new_canvas_y = img_y * new_zoom
        left = new_canvas_x - event.x
        top = new_canvas_y - event.y
        region = self._canvas.cget("scrollregion")
        if region:
            parts = region.split()
            if len(parts) == 4:
                _, _, x2, y2 = map(float, parts)
                if x2 > 0:
                    self._canvas.xview_moveto(left / x2)
                if y2 > 0:
                    self._canvas.yview_moveto(top / y2)
        if self._zoom_changed_callback:
            self._zoom_changed_callback(new_zoom)
        return "break"

    def set_palette(self, palette: list[tuple[int, int, int]]):
        self._palette = list(palette)
        self._redraw()

    def set_image(self, img: Image.Image):
        self._commit_paste()
        if img.mode != "P":
            raise ValueError("The editor requires indexed images.")
        self._img = img.copy()
        self._sel = None
        self._paste_buf = None
        self._paste_drag_start = None
        self._canvas.xview_moveto(0)
        self._canvas.yview_moveto(0)
        self._redraw()

    def set_image_preserve_view(self, img: Image.Image):
        if img.mode != "P":
            raise ValueError("The editor requires indexed images.")
        xpos = self._canvas.xview()[0]
        ypos = self._canvas.yview()[0]
        self._img = img.copy()
        self._sel = None
        self._paste_buf = None
        self._paste_drag_start = None
        self._redraw()
        self._canvas.xview_moveto(xpos)
        self._canvas.yview_moveto(ypos)

    def get_image(self) -> Image.Image | None:
        self._commit_paste()
        return self._img

    def set_tool(self, tool: str):
        if tool != TOOL_MOVE_PASTE and self._tool == TOOL_MOVE_PASTE:
            self._commit_paste()
        self._tool = tool
        self._update_cursor()

    def _update_cursor(self, event=None):
        if self._tool == TOOL_HAND:
            cursor = "hand2"
        elif self._tool == TOOL_DRAW:
            cursor = "pencil"
        elif self._tool == TOOL_PICK:
            cursor = "target"
        elif self._tool == TOOL_MOVE_PASTE:
            if event is not None:
                corner = self._paste_corner_at(event.x, event.y)
                if corner in ("nw", "se"):
                    self._canvas.config(cursor="size_nw_se")
                    return
                if corner in ("ne", "sw"):
                    self._canvas.config(cursor="size_ne_sw")
                    return
            cursor = "fleur" if (event is not None and self._paste_hit(event.x, event.y)) else "crosshair"
        else:
            cursor = "crosshair"
        self._canvas.config(cursor=cursor)

    def set_draw_color(self, rgba: tuple):
        self._draw_color = rgba

    def set_zoom(self, z: int):
        self._zoom = z
        self._redraw()

    def set_show_grid(self, v: bool):
        self._show_grid = v
        self._redraw()

    def copy_selection(self):
        if self._img is None or self._sel is None or self._paste_buf is not None:
            return
        x0, y0, x1, y1 = self._normalised_sel()
        self._clipboard = self._img.crop((x0, y0, x1, y1))

    def paste_selection(self):
        if self._img is None or self._clipboard is None:
            return False
        self._commit_paste()
        self._paste_buf = self._clipboard.copy()
        self._paste_src = self._paste_buf.copy()
        self._paste_resize_corner = None
        pw, ph = self._paste_buf.size
        if self._sel is not None:
            x0, y0, _, _ = self._normalised_sel()
        else:
            x0, y0 = 0, 0
        self._paste_pos = (x0, y0)
        self._sel = (
            self._paste_pos[0], self._paste_pos[1],
            self._paste_pos[0] + pw - 1, self._paste_pos[1] + ph - 1,
        )
        self._tool = TOOL_MOVE_PASTE
        self._update_cursor()
        self._redraw()
        return True

    def commit_paste_now(self):
        if self._paste_buf is None:
            return
        self._commit_paste()
        self._tool = TOOL_SELECT
        self._canvas.config(cursor="crosshair")
        self._redraw()

    def delete_selection(self):
        if self._paste_buf is not None:
            self._paste_buf = None
            self._paste_src = None
            self._paste_resize_corner = None
            self._sel = None
            self._paste_drag_start = None
            self._tool = TOOL_SELECT
            self._canvas.config(cursor="crosshair")
            self._redraw()
        elif self._sel is not None and self._img is not None:
            self._notify_stroke_start()
            x0, y0, x1, y1 = self._normalised_sel()
            blank = Image.new("P", (x1 - x0, y1 - y0), 0)
            self._img.paste(blank, (x0, y0))
            self._sel = None
            self._notify_modified()
            self._redraw()

    def rotate_selection(self):
        if self._paste_buf is None:
            return
        self._paste_buf = self._paste_buf.transpose(Image.ROTATE_270)
        pw, ph = self._paste_buf.size
        px, py = self._paste_pos
        self._sel = (px, py, px + pw - 1, py + ph - 1)
        self._tool = TOOL_MOVE_PASTE
        self._paste_drag_start = None
        self._update_cursor()
        self._redraw()

    def mirror_selection(self):
        if self._paste_buf is None:
            return
        self._paste_buf = self._paste_buf.transpose(Image.FLIP_LEFT_RIGHT)
        self._tool = TOOL_MOVE_PASTE
        self._paste_drag_start = None
        self._update_cursor()
        self._redraw()

    def deselect(self, _event=None):
        self._commit_paste()
        self._sel = None
        self._sel_start = None
        self._dragging = False
        self._paste_drag_start = None
        if self._tool == TOOL_MOVE_PASTE:
            self._tool = TOOL_SELECT
            self._canvas.config(cursor="crosshair")
        self._redraw()
        parent = self.master
        if hasattr(parent, "_update_selection_buttons"):
            parent._update_selection_buttons(False)
        return "break"

    def _commit_paste(self):
        if self._paste_buf is None or self._img is None:
            return
        self._notify_stroke_start()
        iw, ih = self._img.size
        px, py = self._paste_pos
        pw, ph = self._paste_buf.size
        src_x0 = max(0, -px)
        src_y0 = max(0, -py)
        src_x1 = min(pw, iw - px)
        src_y1 = min(ph, ih - py)
        dst_x = max(0, px)
        dst_y = max(0, py)
        if src_x1 > src_x0 and src_y1 > src_y0:
            region = self._paste_buf.crop((src_x0, src_y0, src_x1, src_y1))
            self._img.paste(region, (dst_x, dst_y))
        self._paste_buf = None
        self._paste_src = None
        self._paste_resize_corner = None
        self._notify_modified()

    def _display_image(self) -> Image.Image:
        img = self._img.copy()
        img.putpalette(_palette_to_flat_rgb(self._palette))
        if self._paste_buf is not None:
            iw, ih = img.size
            px, py = self._paste_pos
            pw, ph = self._paste_buf.size
            src_x0 = max(0, -px)
            src_y0 = max(0, -py)
            src_x1 = min(pw, iw - px)
            src_y1 = min(ph, ih - py)
            dst_x = max(0, px)
            dst_y = max(0, py)
            if src_x1 > src_x0 and src_y1 > src_y0:
                paste = self._paste_buf.crop((src_x0, src_y0, src_x1, src_y1))
                paste.putpalette(_palette_to_flat_rgb(self._palette))
                img.paste(paste, (dst_x, dst_y))
        return img

    def _redraw(self):
        c = self._canvas
        c.delete("all")
        if self._img is None:
            c.configure(scrollregion=(0, 0, c.winfo_width(), c.winfo_height()))
            c.create_text(
                c.winfo_width() // 2 or 200,
                c.winfo_height() // 2 or 150,
                text="No image loaded",
                fill="#555",
                font=("Segoe UI", 12, "italic"),
            )
            return

        iw, ih = self._img.size
        z = self._zoom
        dw, dh = iw * z, ih * z
        self._tk_img = ImageTk.PhotoImage(
            self._display_image().resize((dw, dh), Image.NEAREST)
        )
        c.create_image(0, 0, anchor="nw", image=self._tk_img, tags="image")

        if self._show_grid and z >= 4:
            for px in range(iw + 1):
                x = px * z
                c.create_line(x, 0, x, dh, fill="#333", width=1, tags="grid")
            for py in range(ih + 1):
                y = py * z
                c.create_line(0, y, dw, y, fill="#333", width=1, tags="grid")

        if self._sel is not None:
            x0, y0, x1, y1 = self._normalised_sel()
            c.create_rectangle(
                x0 * z, y0 * z, x1 * z, y1 * z,
                outline=SEL_COLOR, width=2, dash=(4, 2), tags="selection"
            )

        if self._paste_buf is not None:
            px0, py0 = self._paste_pos
            pw, ph = self._paste_buf.size
            c.create_rectangle(
                px0 * z, py0 * z, (px0 + pw) * z, (py0 + ph) * z,
                outline="#FFD700", width=2, dash=(4, 2), tags="paste"
            )
            r = self._HANDLE_R
            for hx, hy in (
                (px0 * z,        py0 * z),
                ((px0 + pw) * z, py0 * z),
                (px0 * z,        (py0 + ph) * z),
                ((px0 + pw) * z, (py0 + ph) * z),
            ):
                c.create_rectangle(
                    hx - r, hy - r, hx + r, hy + r,
                    fill="#FFD700", outline="#000", width=1, tags="paste"
                )

        c.configure(scrollregion=(0, 0, dw + 2, dh + 2))
        self._update_scrollbars(dw, dh)

    def _update_scrollbars(self, dw: int, dh: int):
        base_w = max(1, self._view.winfo_width())
        base_h = max(1, self._view.winfo_height())
        v_w = max(1, self._vbar.winfo_reqwidth())
        h_h = max(1, self._hbar.winfo_reqheight())

        show_h = False
        show_v = False
        for _ in range(4):
            avail_w = base_w - (v_w if show_v else 0)
            avail_h = base_h - (h_h if show_h else 0)
            new_h = dw > max(1, avail_w)
            new_v = dh > max(1, avail_h)
            if (new_h, new_v) == (show_h, show_v):
                break
            show_h, show_v = new_h, new_v

        if show_v:
            self._vbar.grid(row=0, column=1, sticky="ns")
        else:
            self._vbar.grid_remove()
        if show_h:
            self._hbar.grid(row=1, column=0, sticky="ew")
        else:
            self._hbar.grid_remove()
        if show_h and show_v:
            self._corner.grid(row=1, column=1, sticky="nsew")
        else:
            self._corner.grid_remove()

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.configure(
            xscrollcommand=self._hbar.set if show_h else lambda *args: None,
            yscrollcommand=self._vbar.set if show_v else lambda *args: None,
        )

    _HANDLE_R = 5

    def _paste_corner_at(self, cx: int, cy: int) -> "str | None":
        if self._paste_buf is None:
            return None
        z = self._zoom
        px, py = self._paste_pos
        pw, ph = self._paste_buf.size
        r = self._HANDLE_R
        sx = self._canvas.canvasx(cx)
        sy = self._canvas.canvasy(cy)
        corners = {
            "nw": (px * z,        py * z),
            "ne": ((px + pw) * z, py * z),
            "sw": (px * z,        (py + ph) * z),
            "se": ((px + pw) * z, (py + ph) * z),
        }
        for name, (hx, hy) in corners.items():
            if abs(sx - hx) <= r and abs(sy - hy) <= r:
                return name
        return None

    def _paste_hit(self, cx: int, cy: int) -> bool:
        if self._paste_buf is None:
            return False
        x = self._canvas.canvasx(cx)
        y = self._canvas.canvasy(cy)
        px, py = self._paste_pos
        pw, ph = self._paste_buf.size
        z = self._zoom
        return px * z <= x < (px + pw) * z and py * z <= y < (py + ph) * z

    def _canvas_to_pixel(self, cx: int, cy: int) -> tuple[int, int] | None:
        if self._img is None:
            return None
        z = self._zoom
        x = int(self._canvas.canvasx(cx))
        y = int(self._canvas.canvasy(cy))
        px = x // z
        py = y // z
        iw, ih = self._img.size
        if 0 <= px < iw and 0 <= py < ih:
            return px, py
        return None

    def _normalised_sel(self) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = self._sel
        return min(x0, x1), min(y0, y1), max(x0, x1) + 1, max(y0, y1) + 1

    def _point_in_selection(self, pt: tuple[int, int]) -> bool:
        if self._sel is None:
            return False
        x0, y0, x1, y1 = self._normalised_sel()
        return x0 <= pt[0] < x1 and y0 <= pt[1] < y1

    def _on_motion(self, event):
        self._update_cursor(event)

    def _on_b1_press(self, event):
        if self._tool == TOOL_HAND:
            iw = ih = 0
            if self._img is not None:
                iw, ih = self._img.size
            dw, dh = iw * self._zoom, ih * self._zoom
            can_pan = (dw > self._canvas.winfo_width() or dh > self._canvas.winfo_height())
            if can_pan:
                self._pan_start = (event.x, event.y)
                self._canvas.scan_mark(event.x, event.y)
            return

        if self._tool == TOOL_MOVE_PASTE and self._paste_buf is not None:
            corner = self._paste_corner_at(event.x, event.y)
            if corner is not None and self._paste_src is not None:
                self._paste_resize_corner = corner
                px, py = self._paste_pos
                pw, ph = self._paste_buf.size
                if corner == "nw":
                    self._paste_resize_anchor = (px + pw, py + ph)
                elif corner == "ne":
                    self._paste_resize_anchor = (px, py + ph)
                elif corner == "sw":
                    self._paste_resize_anchor = (px + pw, py)
                else:
                    self._paste_resize_anchor = (px, py)
                self._paste_drag_start = None 
                return
            if self._paste_hit(event.x, event.y):
                pt = self._canvas_to_pixel(event.x, event.y)
                if pt is not None:
                    self._paste_resize_corner = None
                    self._paste_drag_start = pt
                    self._paste_drag_origin = self._paste_pos
            return

        pt = self._canvas_to_pixel(event.x, event.y)
        if pt is None:
            if self._tool == TOOL_SELECT and self._sel is not None:
                self.deselect()
            return

        if self._tool == TOOL_SELECT:
            if self._sel is not None and not self._point_in_selection(pt):
                self._sel = None
            self._sel_start = pt
            self._sel = (pt[0], pt[1], pt[0], pt[1])
            self._dragging = True

        elif self._tool == TOOL_DRAW:
            self._last_draw_pt = pt
            self._paint_pixel(*pt)

        elif self._tool == TOOL_PICK:
            rgba = self._pixel_color(pt)
            self._draw_color = rgba
            if self._on_color_picked:
                self._on_color_picked(*rgba)

    def _on_b1_motion(self, event):
        if self._tool == TOOL_HAND:
            if self._pan_start is not None:
                self._canvas.scan_dragto(event.x, event.y, gain=1)
            return

        pt = self._canvas_to_pixel(event.x, event.y)
        if self._tool == TOOL_MOVE_PASTE:
            if self._paste_resize_corner is not None and self._paste_src is not None:
                z = self._zoom
                ax, ay = self._paste_resize_anchor
                cx_raw = int(self._canvas.canvasx(event.x))
                cy_raw = int(self._canvas.canvasy(event.y))
                drag_x = max(0, cx_raw) // z
                drag_y = max(0, cy_raw) // z
                new_x0 = min(ax, drag_x)
                new_y0 = min(ay, drag_y)
                new_x1 = max(ax, drag_x)
                new_y1 = max(ay, drag_y)
                new_w = max(1, new_x1 - new_x0)
                new_h = max(1, new_y1 - new_y0)
                if (event.state & 0x0001) or self._paste_aspect_lock:
                    src_w, src_h = self._paste_src.size
                    scale = min(new_w / src_w, new_h / src_h)
                    new_w = max(1, int(src_w * scale))
                    new_h = max(1, int(src_h * scale))
                flat = _palette_to_flat_rgb(self._palette)
                pal_img = Image.new("P", (1, 1))
                pal_img.putpalette(flat)
                resized = self._paste_src.convert("RGB").resize((new_w, new_h), Image.NEAREST)
                self._paste_buf = resized.quantize(palette=pal_img, dither=0)
                self._paste_pos = (new_x0, new_y0)
                self._sel = (new_x0, new_y0, new_x0 + new_w - 1, new_y0 + new_h - 1)
                self._redraw()
                return
            if self._paste_drag_start is not None and self._paste_buf is not None and pt is not None:
                dx = pt[0] - self._paste_drag_start[0]
                dy = pt[1] - self._paste_drag_start[1]
                ox0, oy0 = self._paste_drag_origin
                pw, ph = self._paste_buf.size
                nx = ox0 + dx
                ny = oy0 + dy
                self._paste_pos = (nx, ny)
                self._sel = (nx, ny, nx + pw - 1, ny + ph - 1)
                self._redraw()
            self._update_cursor(event)
            return

        if pt is None:
            return

        if self._tool == TOOL_DRAW:
            if self._last_draw_pt is not None:
                self._draw_line(self._last_draw_pt, pt)
            else:
                self._paint_pixel(*pt)
            self._last_draw_pt = pt
        elif self._tool == TOOL_SELECT and self._dragging and self._sel_start:
            x0, y0 = self._sel_start
            self._sel = (x0, y0, pt[0], pt[1])
            self._redraw()

    def _on_b1_release(self, event):
        self._dragging = False
        self._pan_start = None
        self._drawing_stroke = False
        self._last_draw_pt = None
        if self._paste_resize_corner is not None and self._paste_src is not None and self._paste_buf is not None:
            pw, ph = self._paste_buf.size
            flat = _palette_to_flat_rgb(self._palette)
            pal_img = Image.new("P", (1, 1))
            pal_img.putpalette(flat)
            flt = self._paste_resize_filter
            if flt != Image.NEAREST:
                resized = self._paste_src.convert("RGB").resize((pw, ph), flt)
                self._paste_buf = resized.quantize(palette=pal_img, dither=0)
                self._redraw()
            self._paste_resize_corner = None
        self._paste_drag_start = None

    def _on_b3_press(self, event):
        pt = self._canvas_to_pixel(event.x, event.y)
        if self._sel is not None and (pt is None or not self._point_in_selection(pt)):
            self.deselect()
            return
        
        if pt and self._img and self._tool in (TOOL_PICK, TOOL_DRAW):
            rgba = self._pixel_color(pt)
            self._draw_color = rgba
            if self._on_color_picked:
                self._on_color_picked(*rgba)

    def _pixel_color(self, pt: tuple[int, int]) -> tuple[int, int, int, int]:
        index = self._img.getpixel(pt)
        if isinstance(index, tuple):
            index = index[0]
        if 0 <= index < len(self._palette):
            r, g, b = self._palette[index]
        else:
            r = g = b = 0
        return r, g, b, 255

    def _draw_line(self, pt0: tuple[int, int], pt1: tuple[int, int]):
        x0, y0 = pt0
        x1, y1 = pt1
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self._paint_pixel_raw(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

        self._notify_modified()
        self._redraw()

    def _paint_pixel_raw(self, px: int, py: int):
        if self._img is None:
            return
        if not self._drawing_stroke:
            self._drawing_stroke = True
            self._notify_stroke_start()
        r, g, b, _ = self._draw_color
        index = _rgb_to_palette_index(r, g, b, self._palette)
        self._img.putpixel((px, py), index)

    def _paint_pixel(self, px: int, py: int):
        self._paint_pixel_raw(px, py)
        self._notify_modified()
        self._redraw()

    def _notify_modified(self):
        if self._on_modified:
            self._on_modified(stroke_start=False)

    def _notify_stroke_start(self):
        if self._on_modified:
            self._on_modified(stroke_start=True)


class PicEditorPanel(ttk.Frame):

    def __init__(self, parent, standalone=True, **kw):
        super().__init__(parent, **kw)
        self._standalone = standalone
        self._pic_dir:      str         = ""
        self._pic_files:    list[str]   = []
        self._current_idx:  int         = -1
        self._current_path: str         = ""
        self._active_palette_name: str  = "Default"
        self._active_palette: list[tuple[int,int,int]] = list(_PAL_NORMAL)
        self._modified  = False
        self._undo_stack: list[Image.Image] = []
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 9))
        s.configure("TLabelframe", background=BG, foreground=FG, font=("Segoe UI", 9, "bold"))
        s.configure("TLabelframe.Label", background=BG, foreground=FG)
        s.configure("TButton", font=("Segoe UI", 9, "bold"), padding=5, background=ACCENT, foreground="white", borderwidth=0)
        s.map("TButton", background=[("active", "#2980B9"), ("disabled", "#BDC3C7")])
        s.configure("Toolbutton", font=("Segoe UI", 9))

    def _build_ui(self):
        sb = ttk.Frame(self, padding=(8, 2))
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_lbl = ttk.Label(sb, text="Ready.", foreground=MUTED)
        self._status_lbl.pack(side=tk.LEFT)
        self._pixel_lbl  = ttk.Label(sb, text="", foreground=MUTED)
        self._pixel_lbl.pack(side=tk.RIGHT)
        center = ttk.Frame(self)
        center.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        sidebar = ttk.Frame(center, padding=(6, 6))
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0), pady=6)
        self._build_toolbox(sidebar)
        self._canvas_frame = _ImageCanvas(
            center,
            on_modified=self._on_canvas_modified,
            on_color_picked=self._on_color_picked_from_canvas,
        )
        self._canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._canvas_frame._canvas.bind("<Motion>", self._on_mouse_move, add="+")
        self._canvas_frame._zoom_changed_callback = (lambda z: self._zoom_var.set(z))

    def _build_toolbox(self, parent):
        self._tool_var = tk.StringVar(value=TOOL_DRAW)
        f_file = ttk.LabelFrame(parent, text="File", padding=(4, 4))
        f_file.pack(fill=tk.X, pady=(0, 6))
        if self._standalone:
            ttk.Button(f_file, text="📁 PIC Folder…", command=self._browse_dir).pack(fill=tk.X, pady=(0, 4))
        self._btn_save = ttk.Button(f_file, text="Save As…", command=self._save_as, state="disabled")
        self._btn_save.pack(fill=tk.X, pady=2)
        io_row = ttk.Frame(f_file)
        io_row.pack(fill=tk.X, pady=2)
        io_row.columnconfigure(0, weight=1)
        io_row.columnconfigure(1, weight=1)
        self._btn_import = ttk.Button(io_row, text="⬆ Import…", command=self._import_image, state="disabled")
        self._btn_import.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self._btn_export = ttk.Button(io_row, text="⬇ Export…", command=self._export_image, state="disabled")
        self._btn_export.grid(row=0, column=1, sticky="ew", padx=(2, 0))
        self._file_var = tk.StringVar()
        self._file_combo = ttk.Combobox(f_file, textvariable=self._file_var, values=[], state="readonly", width=18)
        self._file_combo.pack(fill=tk.X, pady=(4, 4))
        self._file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)
        self._file_combo.bind("<MouseWheel>",         self._on_file_scroll)
        self._file_combo.bind("<Up>", self._on_file_updown)
        self._file_combo.bind("<Down>", self._on_file_updown)
        info_row = ttk.Frame(f_file)
        info_row.pack(fill=tk.X)
        self._info_lbl = ttk.Label(info_row, text="", foreground=MUTED)
        self._info_lbl.pack(side=tk.LEFT, anchor="w")
        self._dirty_lbl = ttk.Label(info_row, text="", foreground=RED, font=("Segoe UI", 9, "bold"))
        self._dirty_lbl.pack(side=tk.RIGHT, anchor="e")
        
        f_tools = ttk.LabelFrame(parent, text="Tools", padding=(4, 2))
        f_tools.pack(fill=tk.X, pady=3)
        f_tools.columnconfigure(0, weight=1)
        f_tools.columnconfigure(1, weight=1)
        ttk.Radiobutton(f_tools, text="✏ Pencil", variable=self._tool_var, value=TOOL_DRAW, command=self._on_tool_change, style="Toolbutton").grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        ttk.Radiobutton(f_tools, text="▢ Select", variable=self._tool_var, value=TOOL_SELECT, command=self._on_tool_change, style="Toolbutton").grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        ttk.Radiobutton(f_tools, text="🎯 Pick", variable=self._tool_var, value=TOOL_PICK, command=self._on_tool_change, style="Toolbutton").grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        ttk.Radiobutton(f_tools, text="✋ Hand", variable=self._tool_var, value=TOOL_HAND, command=self._on_tool_change, style="Toolbutton").grid(row=1, column=1, sticky="ew", padx=1, pady=1)

        f_sel = ttk.LabelFrame(parent, text="Pasted selection", padding=(4, 2))
        f_sel.pack(fill=tk.X, pady=3)
        sel_grid = ttk.Frame(f_sel)
        sel_grid.pack(fill=tk.X)
        sel_grid.columnconfigure(0, weight=1)
        sel_grid.columnconfigure(1, weight=1)
        sel_grid.columnconfigure(2, weight=0)
        self._btn_rotate = ttk.Button(sel_grid, text="⟳ Rotate", command=self._rotate_sel, state="disabled")
        self._btn_rotate.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self._btn_mirror = ttk.Button(sel_grid, text="⇹ Mirror", command=self._mirror_sel, state="disabled")
        self._btn_mirror.grid(row=0, column=1, columnspan=2, sticky="ew", padx=1, pady=1)
        self._btn_delete = ttk.Button(sel_grid, text="🗑 Delete", command=self._delete_sel, state="disabled")
        self._btn_delete.grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        self._aspect_lock = tk.BooleanVar(value=False)
        lock_cell = ttk.Frame(sel_grid)
        lock_cell.grid(row=1, column=1, columnspan=2, sticky="ew", padx=1, pady=1)
        lock_cell.columnconfigure(0, weight=0)
        lock_cell.columnconfigure(1, weight=1)
        self._lock_bg_off = "#c0392b"
        self._lock_bg_off_dim = "#7f2a1e"
        self._btn_lock = tk.Button(lock_cell, text="🔓", width=2,
                                    command=self._toggle_aspect_lock, state="disabled",
                                    relief="flat", bg=self._lock_bg_off_dim, fg="white",
                                    disabledforeground="white",
                                    activebackground="#e74c3c", activeforeground="white",
                                    font=("", 9), cursor="hand2", bd=0, padx=4)
        self._btn_lock.grid(row=0, column=0, sticky="ns", ipady=1)
        self._lbl_lock = tk.Label(lock_cell, text="Aspect Ratio", font=("", 8),
                                   bg=self._lock_bg_off_dim, fg="#aaaaaa", cursor="arrow")
        self._lbl_lock.bind("<Button-1>", lambda _e: self._toggle_aspect_lock() if self._btn_lock["state"] == "normal" else None)
        self._lbl_lock.grid(row=0, column=1, sticky="nsew", ipady=1)
        flt_row = ttk.Frame(f_sel)
        flt_row.pack(fill=tk.X, pady=(3, 1))
        ttk.Label(flt_row, text="Filter:", foreground=MUTED).pack(side=tk.LEFT)
        self._resize_filter_var = tk.StringVar(value="Nearest (pixel-perfect)")
        self._resize_filter_combo = ttk.Combobox(
            flt_row,
            textvariable=self._resize_filter_var,
            values=[label for label, _ in self._RESIZE_FILTERS],
            state="readonly",
            width=14,
        )
        self._resize_filter_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self._resize_filter_combo.bind("<<ComboboxSelected>>", self._on_resize_filter_changed)

        f_colors = ttk.LabelFrame(parent, text="Colors", padding=(4, 2))
        f_colors.pack(fill=tk.X, pady=3)
        crow = ttk.Frame(f_colors)
        crow.pack(fill=tk.X, pady=(0, 4))
        self._color_canvas = tk.Canvas(crow, width=22, height=22, highlightthickness=1, highlightbackground="#888", cursor="hand2")
        self._color_canvas.pack(side=tk.LEFT)
        self._color_canvas.bind("<Button-1>", self._pick_color_dialog)
        self._color_hex = ttk.Label(crow, text="#FFFFFF", font=("Consolas", 9), foreground=MUTED)
        self._color_hex.pack(side=tk.LEFT, padx=6)
        self._update_color_display((255, 255, 255, 255))
        ttk.Label(f_colors, text="Palette:", foreground=MUTED).pack(anchor="w", pady=(1, 0))
        self._swatch_frame = tk.Frame(f_colors, bg=BG)
        self._swatch_frame.pack(fill=tk.X, pady=(1, 2))
        self._swatch_canvas = tk.Canvas(self._swatch_frame, width=160, height=64, highlightthickness=0, bd=0, bg=BG, yscrollincrement=1)
        self._swatch_canvas.pack(side=tk.LEFT, anchor="center")
        self._swatch_canvas.bind("<Button-1>", self._on_swatch_click)
        self._swatch_canvas.bind("<MouseWheel>", lambda e: self._swatch_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        prow = ttk.Frame(f_colors)
        prow.pack(fill=tk.X, pady=(2, 0))
        ttk.Label(prow, text="Change:", foreground=MUTED).pack(side=tk.LEFT)
        self._pal_var = tk.StringVar(value="Default")
        pal_names = list(BUILTIN_PALETTES.keys())
        self._pal_combo = ttk.Combobox(prow, textvariable=self._pal_var, values=pal_names, state="readonly", width=12)
        self._pal_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))
        self._pal_combo.bind("<<ComboboxSelected>>", self._on_palette_changed)

        f_view = ttk.LabelFrame(parent, text="View", padding=(4, 2))
        f_view.pack(fill=tk.X, pady=3)
        zrow = ttk.Frame(f_view)
        zrow.pack(fill=tk.X)
        ttk.Label(zrow, text="Zoom:", foreground=MUTED).pack(side=tk.LEFT)
        self._zoom_var = tk.IntVar(value=2)
        self._zoom_spin = ttk.Spinbox(zrow, from_=1, to=16, width=2, textvariable=self._zoom_var, command=self._on_zoom_change)
        self._zoom_spin.pack(side=tk.LEFT, padx=(4, 0))
        self._zoom_spin.bind("<Return>", lambda e: self._on_zoom_change())
        self._zoom_spin.bind("<FocusOut>", lambda e: self._on_zoom_change())
        self._grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(zrow, text="Show grid", variable=self._grid_var, command=self._on_grid_toggle).pack(side=tk.RIGHT, padx=(10, 0))

        self._btn_undo = ttk.Button(parent, text="↩ Undo (Ctrl+Z)", command=self._undo, state="disabled")
        self._btn_undo.pack(fill=tk.X, pady=(6, 2))

        cmd_key = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{cmd_key}-c>",  lambda _e: self._copy())
        self.bind_all(f"<{cmd_key}-C>",  lambda _e: self._copy())
        self.bind_all(f"<{cmd_key}-v>",  lambda _e: self._paste())
        self.bind_all(f"<{cmd_key}-V>",  lambda _e: self._paste())
        self.bind_all(f"<{cmd_key}-z>",  lambda _e: self._undo())
        self.bind_all(f"<{cmd_key}-Z>",  lambda _e: self._undo())
        self.bind_all("<Return>",        lambda _e: self._apply_paste())
        self.bind_all("<KP_Enter>",      lambda _e: self._apply_paste())
        self.bind_all("<Delete>",        lambda _e: self._delete_sel())
        self.bind_all("<Escape>",        lambda _e: self._escape_action())
        
        self._draw_swatch()

    def _on_resize_filter_changed(self, _event=None):
        label = self._resize_filter_var.get()
        for lbl, flt in self._RESIZE_FILTERS:
            if lbl == label:
                self._canvas_frame._paste_resize_filter = flt
                break

    def _set_lock_appearance(self, locked: bool | None = None, enabled: bool = True):
        if locked is None:
            locked = self._aspect_lock.get()
        if not enabled:
            btn_kw  = dict(text="🔓", bg=self._lock_bg_off_dim,
                           activebackground="#e74c3c", state="disabled", fg="white")
            lbl_kw  = dict(bg=self._lock_bg_off_dim, fg="#888888", cursor="arrow")
        elif locked:
            btn_kw  = dict(text="🔒", bg="#27ae60",
                           activebackground="#2ecc71", state="normal", fg="white")
            lbl_kw  = dict(bg="#27ae60", fg="white", cursor="hand2")
        else:
            btn_kw  = dict(text="🔓", bg=self._lock_bg_off,
                           activebackground="#e74c3c", state="normal", fg="white")
            lbl_kw  = dict(bg=self._lock_bg_off, fg="white", cursor="hand2")
        self._btn_lock.config(**btn_kw)
        self._lbl_lock.config(**lbl_kw)

    def _toggle_aspect_lock(self):
        locked = not self._aspect_lock.get()
        self._aspect_lock.set(locked)
        self._canvas_frame._paste_aspect_lock = locked
        self._set_lock_appearance(locked)

    def _update_selection_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for btn in (self._btn_rotate, self._btn_mirror, self._btn_delete):
            btn.config(state=state)
        if not enabled:
            self._aspect_lock.set(False)
            self._canvas_frame._paste_aspect_lock = False
        self._set_lock_appearance(enabled=enabled)
    
    def _escape_action(self):
        if self._canvas_frame._paste_buf is not None:
            self._canvas_frame.delete_selection()
        else:
            self._canvas_frame.deselect()
        self._update_selection_buttons(False)

    def set_pic_dir(self, path: str):
        if not path or not os.path.isdir(path):
            self._set_status(f"Folder not found: {path}")
            return
        self._pic_dir = path
        self._scan_files()
        if self._pic_files:
            self._load_index(0)

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select PIC Folder")
        if d:
            self.set_pic_dir(d)

    def _scan_files(self):
        exts = {".vga", ".VGA", ".cp", ".CP"}
        files = [f for f in os.listdir(self._pic_dir)
                 if os.path.splitext(f)[1] in exts]
        self._pic_files = sorted(files, key=_natural_key)
        n = len(self._pic_files)
        self._file_combo.config(values=self._pic_files)
        self._set_status(f"{n} .VGA/.CP files found in {self._pic_dir}")

    def _load_index(self, idx: int):
        if not self._pic_files:
            return
        idx = max(0, min(idx, len(self._pic_files) - 1))
        self._current_idx = idx
        fname = self._pic_files[idx]
        fpath = os.path.join(self._pic_dir, fname)

        img = load_vga_image(fpath, self._active_palette)
        if img is None:
            self._set_status(f"Failed to load {fname}")
            return
        self._current_path = fpath
        self._undo_stack.clear()
        self._canvas_frame.set_palette(self._active_palette)
        self._canvas_frame.set_image(img)
        self._canvas_frame.set_zoom(self._zoom_var.get())
        w, h = img.size
        self._file_var.set(fname)
        self._info_lbl.config(
            text=f"{w}×{h}  ({os.path.getsize(fpath):,} B)")
        self._set_dirty(False)
        self._enable_file_buttons(True)
        self._set_status(f"Loaded: {fpath}  [displayed palette: {self._active_palette_name}]")

    def _on_file_selected(self, _event=None):
        fname = self._file_var.get()
        if fname in self._pic_files:
            self._load_index(self._pic_files.index(fname))

    def _on_file_scroll(self, event):
        if not self._pic_files:
            return "break"
        if event.delta > 0:
            direction = -1
        elif event.delta < 0:
            direction = 1
        else:
            return "break"
        new_idx = max(0, min(len(self._pic_files) - 1, self._current_idx + direction))
        if new_idx != self._current_idx:
            self._load_index(new_idx)
        return "break"

    def _on_file_updown(self, event):
        if not self._pic_files:
            return "break"
        direction = -1 if event.keysym == "Up" else 1
        new_idx = max(0, min(len(self._pic_files) - 1, self._current_idx + direction))
        if new_idx != self._current_idx:
            self._load_index(new_idx)
        return "break"

    def _save_as(self):
        img = self._canvas_frame.get_image()
        if img is None:
            return
        dest = filedialog.asksaveasfilename(
            title="Save Image As…",
            defaultextension=".VGA",
            filetypes=[("VGA/CP Image", "*.VGA *.vga *.CP *.cp"), ("All files", "*.*")],
            initialdir=self._pic_dir or ".",
        )
        if not dest:
            return
        self._do_save(img, dest)

    def _do_save(self, img: Image.Image, dest: str):
        self._set_status("Saving…")
        self.update_idletasks()
        try:
            save_vga_image(img, dest)
            self._set_dirty(False)
            sz = os.path.getsize(dest)
            self._info_lbl.config(text=f"{img.width}×{img.height}  ({sz:,} B)")
            self._set_status(f"Saved: {dest}  ({sz:,} B)")
        except VgaEncodeError as exc:
            messagebox.showerror("VGA Save Error", str(exc))
            self._set_status("Save failed.")
        except Exception as exc:
            messagebox.showerror("Unexpected Error", str(exc))
            self._set_status("Save failed.")

    def _enable_file_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._btn_save.config(state=state)
        self._btn_import.config(state=state)
        self._btn_export.config(state=state)
        self._btn_undo.config(state=state)

    _RESIZE_FILTERS = [
        ("Nearest (pixel-perfect)",  Image.NEAREST),
        ("Box (average)",            Image.BOX),
        ("Bilinear",                 Image.BILINEAR),
        ("Hamming",                  Image.HAMMING),
        ("Bicubic",                  Image.BICUBIC),
        ("Lanczos (best quality)",   Image.LANCZOS),
    ]

    _PREVIEW_W = 200
    _PREVIEW_H = 160

    def _ask_resize_filter(
        self,
        src_rgb: "Image.Image",
        target_size: "tuple[int,int]",
    ) -> "Image.Resampling | None":
        result: list = [None]
        tw, th = target_size
        flat = _palette_to_flat_rgb(self._active_palette)
        pal_img = Image.new("P", (1, 1))
        pal_img.putpalette(flat)
        pw, ph = self._PREVIEW_W, self._PREVIEW_H
        scale = min(pw / tw, ph / th)
        prev_w = max(1, int(tw * scale))
        prev_h = max(1, int(th * scale))

        def make_preview(flt):
            resized = src_rgb.resize((tw, th), flt)
            q = resized.quantize(palette=pal_img, dither=0)
            rgb = q.convert("RGB")
            thumb = rgb.resize((prev_w, prev_h), Image.NEAREST)
            canvas = Image.new("RGB", (pw, ph), (30, 30, 30))
            ox = (pw - prev_w) // 2
            oy = (ph - prev_h) // 2
            canvas.paste(thumb, (ox, oy))
            return ImageTk.PhotoImage(canvas)

        previews = {label: make_preview(flt) for label, flt in self._RESIZE_FILTERS}
        dlg = tk.Toplevel(self)
        dlg.title("Resize filter")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)
        body = ttk.Frame(dlg, padding=10)
        body.pack(fill=tk.BOTH)
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, anchor="n", padx=(0, 12))
        ttk.Label(left, text="Algorithm:", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
        current_label = self._resize_filter_var.get()
        filter_var = tk.StringVar(value=current_label if current_label else self._RESIZE_FILTERS[0][0])
        right = ttk.LabelFrame(body, text=f"Preview  ({tw}×{th} → quantised)", padding=4)
        right.pack(side=tk.LEFT, anchor="n")
        preview_label = ttk.Label(right)
        preview_label.pack()
        size_lbl = ttk.Label(right, text="", foreground="#888888")
        size_lbl.pack()

        def update_preview(*_):
            lbl = filter_var.get()
            preview_label.configure(image=previews[lbl])
            preview_label.image = previews[lbl]

        for label, _ in self._RESIZE_FILTERS:
            ttk.Radiobutton(
                left, text=label, variable=filter_var, value=label,
                command=update_preview,
            ).pack(anchor="w", pady=2)
        update_preview()
        btn_row = ttk.Frame(dlg, padding=(10, 4, 10, 10))
        btn_row.pack(fill=tk.X)

        def on_ok():
            chosen_label = filter_var.get()
            for label, flt in self._RESIZE_FILTERS:
                if label == chosen_label:
                    result[0] = flt
                    break
            self._resize_filter_var.set(chosen_label)
            self._on_resize_filter_changed()
            dlg.destroy()

        def on_cancel():
            dlg.destroy()
        ttk.Button(btn_row, text="OK",     command=on_ok).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_row, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)
        dlg.bind("<Return>", lambda _e: on_ok())
        dlg.bind("<Escape>", lambda _e: on_cancel())
        self.update_idletasks()
        dlg.update_idletasks()
        px = self.winfo_rootx() + self.winfo_width()  // 2
        py = self.winfo_rooty() + self.winfo_height() // 2
        dlg.geometry(f"+{px - dlg.winfo_width() // 2}+{py - dlg.winfo_height() // 2}")
        self.wait_window(dlg)
        return result[0]

    def _import_image(self):
        if self._canvas_frame._img is None:
            return
        path = filedialog.askopenfilename(
            title="Import Image…",
            filetypes=[
                ("Image files", "*.png *.PNG *.bmp *.BMP *.jpg *.JPG *.jpeg *.JPEG"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            src = Image.open(path).convert("RGB")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Cannot open image:\n{exc}")
            return

        iw, ih = self._canvas_frame._img.size
        sw, sh = src.size

        if sw > iw or sh > ih:
            answer = messagebox.askyesnocancel(
                "Image too large",
                f"The imported image ({sw}×{sh}) is larger than the canvas ({iw}×{ih}).\n\n"
                "• Yes   – resize to fit (aspect ratio preserved)\n"
                "• No    – keep original size (drag to position, cropped on commit)\n"
                "• Cancel – abort",
            )
            if answer is None:
                return
            if answer:
                scale = min(iw / sw, ih / sh)
                new_w = max(1, int(sw * scale))
                new_h = max(1, int(sh * scale))
                flt = self._ask_resize_filter(src, (new_w, new_h))
                if flt is None:
                    return
                src = src.resize((new_w, new_h), flt)
        flat = _palette_to_flat_rgb(self._active_palette)
        pal_img = Image.new("P", (1, 1))
        pal_img.putpalette(flat)
        quantised = src.quantize(palette=pal_img, dither=0)
        self._canvas_frame._clipboard = quantised
        self._canvas_frame._commit_paste()
        self._canvas_frame._paste_buf = quantised.copy()
        self._canvas_frame._paste_src = src 
        self._canvas_frame._paste_resize_corner = None
        self._canvas_frame._paste_pos = (0, 0)
        pw, ph = quantised.size
        self._canvas_frame._sel = (0, 0, pw - 1, ph - 1)
        self._canvas_frame._tool = TOOL_MOVE_PASTE
        self._canvas_frame._update_cursor()
        self._canvas_frame._redraw()
        self._update_selection_buttons(True)
        self._set_status(
            f"Imported: {os.path.basename(path)} ({quantised.width}×{quantised.height})"
            " — Paste active — drag to move  │  drag corner handle to resize (Shift or 🔒 = lock A/R)  │  Enter = commit  │  ESC = cancel"
        )

    def _export_image(self):
        img = self._canvas_frame.get_image()
        if img is None:
            return
        path = filedialog.asksaveasfilename(
            title="Export Image As…",
            defaultextension=".png",
            filetypes=[
                ("PNG",  "*.png"),
                ("BMP",  "*.bmp"),
                ("JPEG", "*.jpg"),
                ("All files", "*.*"),
            ],
            initialdir=self._pic_dir or ".",
        )
        if not path:
            return
        try:
            export = img.copy()
            export.putpalette(_palette_to_flat_rgb(self._active_palette))
            rgb = export.convert("RGB")
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                rgb.save(path, "JPEG", quality=95)
            else:
                rgb.save(path)
            self._set_status(f"Exported: {path}")
        except Exception as exc:
            messagebox.showerror("Export Error", f"Cannot save image:\n{exc}")
            self._set_status("Export failed.")

    def _on_palette_changed(self, _event=None):
        name = self._pal_var.get()
        if name in BUILTIN_PALETTES:
            self._active_palette_name = name
            self._active_palette = list(BUILTIN_PALETTES[name])
        else:
            self._pal_var.set(self._active_palette_name)
            return
        self._draw_swatch()
        self._canvas_frame.set_palette(self._active_palette)
        self._set_status(f"Palette: {self._active_palette_name}")

    def _draw_swatch(self):
        c = self._swatch_canvas
        c.delete("all")
        pal = self._active_palette
        n = len(pal)
        if n == 0:
            return

        if n > 32:
            sq = 10
            cols = 16
        else:
            sq = 20
            cols = 8

        rows = (n + cols - 1) // cols
        canvas_w = cols * sq
        canvas_h = min(rows * sq, 80)
        c.config(width=canvas_w, height=canvas_h, scrollregion=(0, 0, canvas_w, rows * sq))

        if rows * sq > canvas_h:
            if not hasattr(self, "_swatch_vbar") or not self._swatch_vbar.winfo_exists():
                self._swatch_vbar = ttk.Scrollbar(self._swatch_frame, orient=tk.VERTICAL, command=c.yview)
                self._swatch_vbar.pack(side=tk.RIGHT, fill=tk.Y)
                c.config(yscrollcommand=self._swatch_vbar.set)
        else:
            if hasattr(self, "_swatch_vbar") and self._swatch_vbar.winfo_exists():
                self._swatch_vbar.pack_forget()
            c.config(yscrollcommand="")

        for i, (r, g, b) in enumerate(pal):
            col = i % cols
            row = i // cols
            x0, y0 = col * sq, row * sq
            c.create_rectangle(x0, y0, x0 + sq, y0 + sq, fill=f"#{r:02X}{g:02X}{b:02X}", outline="")

    def _on_swatch_click(self, event):
        pal = self._active_palette
        n = len(pal)
        if n > 32:
            sq = 10
            cols = 16
        else:
            sq = 20
            cols = 8

        c = self._swatch_canvas
        cy = int(c.canvasy(event.y))
        cx = int(c.canvasx(event.x))
        if cx < 0 or cy < 0:
            return
        col = cx // sq
        row = cy // sq
        rows = (n + cols - 1) // cols
        if not (0 <= col < cols and 0 <= row < rows):
            return
        idx = row * cols + col
        if idx < len(pal):
            r, g, b = pal[idx]
            rgba = (r, g, b, 255)
            self._canvas_frame.set_draw_color(rgba)
            self._update_color_display(rgba)

    def _on_tool_change(self):
        self._canvas_frame.set_tool(self._tool_var.get())

    def _on_zoom_change(self):
        try:
            z = int(self._zoom_var.get())
        except Exception:
            z = 1
        z = max(1, min(16, z))
        self._zoom_var.set(z)
        self._canvas_frame.set_zoom(z)

    def _on_grid_toggle(self):
        self._canvas_frame.set_show_grid(self._grid_var.get())

    def _pick_color_dialog(self, _event=None):
        r, g, b, _ = self._canvas_frame._draw_color
        result = colorchooser.askcolor(
            color=f"#{r:02x}{g:02x}{b:02x}", title="Choose Color")
        if result and result[0]:
            r2, g2, b2 = (int(v) for v in result[0])
            self._apply_draw_color((r2, g2, b2, 255))

    def _on_color_picked_from_canvas(self, r, g, b, a):
        self._apply_draw_color((r, g, b, a))

    def _apply_draw_color(self, rgba: tuple):
        self._canvas_frame.set_draw_color(rgba)
        self._update_color_display(rgba)

    def _update_color_display(self, rgba: tuple):
        r, g, b, _ = rgba
        hex_str = f"#{r:02X}{g:02X}{b:02X}"
        self._color_canvas.config(bg=hex_str)
        self._color_canvas.delete("all")
        self._color_canvas.create_rectangle(0, 0, 32, 32, fill=hex_str, outline="")
        self._color_hex.config(text=hex_str)

    def _copy(self):
        self._canvas_frame.copy_selection()
        self._set_status("Copied to clipboard.")

    def _paste(self):
        if self._canvas_frame.paste_selection():
            self._update_selection_buttons(True)
            self._set_status("Paste active — drag to move  │  drag corner handle to resize (Shift or 🔒 = lock A/R)  │  Enter = commit  │  ESC = cancel")

    def _apply_paste(self):
        if self._canvas_frame._tool == TOOL_MOVE_PASTE:
            self._canvas_frame.commit_paste_now()
            self._update_selection_buttons(False)
            self._set_status("Paste applied.")

    def _rotate_sel(self):
        self._canvas_frame.rotate_selection()
        self._set_status("Selection rotated.")

    def _mirror_sel(self):
        self._canvas_frame.mirror_selection()
        self._set_status("Selection mirrored.")

    def _delete_sel(self):
        self._canvas_frame.delete_selection()
        self._update_selection_buttons(False)
        self._set_status("Selection deleted.")

    def _push_undo(self, img: Image.Image | None):
        if img is None:
            return
        self._undo_stack.append(img.copy())
        if len(self._undo_stack) > 40:
            self._undo_stack.pop(0)

    def _undo(self):
        if not self._undo_stack:
            self._set_status("Nothing to undo.")
            return
        img = self._undo_stack.pop()
        self._canvas_frame.set_image_preserve_view(img)
        self._canvas_frame._canvas.focus_set()
        self._set_dirty(True)
        self._set_status("Undone.")

    def _on_canvas_modified(self, stroke_start: bool = False):
        if stroke_start and self._canvas_frame._img is not None:
            self._push_undo(self._canvas_frame._img)
        self._set_dirty(True)

    def _set_dirty(self, v: bool):
        self._modified = v
        self._dirty_lbl.config(text="⚠ Modified" if v else "")

    def _set_status(self, msg: str):
        self._status_lbl.config(text=msg)

    def _on_mouse_move(self, event):
        pt = self._canvas_frame._canvas_to_pixel(event.x, event.y)
        img = self._canvas_frame._img
        if pt and img is not None:
            px, py = pt
            try:
                r, g, b, _ = self._canvas_frame._pixel_color(pt)
                self._pixel_lbl.config(text=f"({px}, {py})  #{r:02X}{g:02X}{b:02X}")
            except Exception:
                self._pixel_lbl.config(text=f"({px}, {py})")
        else:
            self._pixel_lbl.config(text="")


if __name__ == "__main__":
    _root = tk.Tk()
    _root.title("PIC Editor - Standalone")
    _root.geometry("1200x760")
    _panel = PicEditorPanel(_root)
    _panel.pack(fill=tk.BOTH, expand=True)
    if len(sys.argv) > 1:
        _panel.set_pic_dir(sys.argv[1])
    _root.mainloop()
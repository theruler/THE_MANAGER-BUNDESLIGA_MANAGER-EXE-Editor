import os
import sys
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from exe_handler import EXE_FONT_PROFILES
from utils import load_config, save_config, get_game_config


class EXEFontEditor:
    CELL = 20

    def __init__(self, parent, get_exe_data, on_charmap_changed=None):
        self.parent             = parent
        self.get_exe_data       = get_exe_data
        self.on_charmap_changed = on_charmap_changed
        self.raw_data:    bytearray = bytearray()
        self.game_name    = None
        self.game_profile = None
        self.current_font_key = None
        self.font_data    = []
        self.selected_idx = 0
        self._last_drag_state = None
        self.cfg          = load_config()
        self._clipboard   = None
        self._build_ui(parent)
        self._bind_shortcuts(parent)

    def _build_ui(self, parent):
        bar = ttk.Frame(parent, padding=(12, 8, 12, 4))
        bar.pack(fill=tk.X)
        ttk.Label(bar, text="Font:").pack(side=tk.LEFT)
        self.font_var   = tk.StringVar()
        self.font_combo = ttk.Combobox(bar, textvariable=self.font_var, state="readonly", width=18)
        self.font_combo.pack(side=tk.LEFT, padx=(4, 16))
        self.font_combo.bind("<<ComboboxSelected>>", self._on_font_select)
        ttk.Button(bar, text="Apply changes", command=self._write_to_exe).pack(side=tk.LEFT, padx=4)
        self.font_status = ttk.Label(bar, text="Load an EXE first.", font=("Segoe UI", 9, "italic"), foreground="#7F8C8D")
        self.font_status.pack(side=tk.LEFT, padx=12)
        body = ttk.Frame(parent, padding=(12, 0, 12, 8))
        body.pack(fill=tk.BOTH, expand=True)
        lf = ttk.LabelFrame(body, text=" Characters ", padding=6)
        lf.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.char_list = tk.Listbox(lf, width=22, font=("Consolas", 10), exportselection=False, bg="white", selectbackground="#2980B9", selectforeground="white")
        sb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self.char_list.yview)
        self.char_list.configure(yscrollcommand=sb.set)
        self.char_list.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_list.bind("<<ListboxSelect>>", self._on_char_select)
        gf = ttk.LabelFrame(body, text=" Pixel Matrix (click/drag) ", padding=8)
        gf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(gf, bg="#1E1E1E", highlightthickness=0, width=8 * self.CELL, height=8 * self.CELL)
        self.canvas.pack(anchor=tk.CENTER, expand=True)
        self.canvas.bind("<Button-1>", lambda e: setattr(self, '_last_drag_state', self._toggle_pixel(e.x, e.y)))
        self.canvas.bind("<B1-Motion>", lambda e: self._last_drag_state is not None and self._toggle_pixel(e.x, e.y, force=self._last_drag_state))
        rf = ttk.Frame(body, padding=(8, 0, 0, 0))
        rf.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(rf, text="Properties", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(rf, text="Width (px):").pack(anchor=tk.W)
        self.width_var  = tk.IntVar(value=8)
        self.width_spin = ttk.Spinbox(rf, from_=1, to=24, textvariable=self.width_var, width=5, command=self._on_width_change)
        self.width_spin.pack(anchor=tk.W, pady=(0, 12))
        self.width_spin.bind("<KeyRelease>", self._on_width_change)
        ttk.Separator(rf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(rf, text="Actions", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        copy_paste_frame = ttk.Frame(rf)
        copy_paste_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Button(copy_paste_frame, text="📋 Copy", command=self._copy_glyph).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(copy_paste_frame, text="📌 Paste", command=self._paste_glyph).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        clear_invert_frame = ttk.Frame(rf)
        clear_invert_frame.pack(fill=tk.X, pady=2)
        ttk.Button(clear_invert_frame, text="🧹 Clear",  command=lambda: self._edit_char("clear")).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(clear_invert_frame, text="🔄 Invert", command=lambda: self._edit_char("invert")).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        shift_frame = ttk.Frame(rf)
        shift_frame.pack(fill=tk.X, pady=(4, 2))
        for text, row, col, dir_ in [("▲", 0, 1, "up"), ("◀", 1, 0, "left"), ("▶", 1, 2, "right"), ("▼", 2, 1, "down")]:
            ttk.Button(shift_frame, text=text, width=3, command=lambda d=dir_: self._edit_char("shift", d)).grid(row=row, column=col, padx=1, pady=1)
        shift_frame.columnconfigure((0, 1, 2), weight=1)
        ttk.Separator(rf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        import_export_frame = ttk.Frame(rf)
        import_export_frame.pack(fill=tk.X, pady=2)
        ttk.Button(import_export_frame, text="📥 Import", command=self._import_font).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(import_export_frame, text="📤 Export", command=self._export_font).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        self.alias_label = ttk.Label(rf, text="", font=("Segoe UI", 8, "italic"), foreground="#E67E22", wraplength=120)
        self.alias_label.pack(anchor=tk.W, pady=(10, 0))
        ttk.Separator(rf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        self.charmap_title_label = ttk.Label(rf, text="Char Mapping", font=("Segoe UI", 10, "bold"))
        self.charmap_title_label.pack(anchor=tk.W, pady=(0, 4))
        map_row = ttk.Frame(rf)
        map_row.pack(fill=tk.X, pady=(4, 2))
        self.map_byte_label = ttk.Label(map_row, text="0x00 →", font=("Consolas", 10))
        self.map_byte_label.pack(side=tk.LEFT, padx=(0, 4))
        self.map_char_var = tk.StringVar()
        ttk.Entry(map_row, textvariable=self.map_char_var, width=4, font=("Consolas", 10)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(map_row, text="+", width=2, command=self._add_charmap_entry).pack(side=tk.LEFT)
        self.map_byte_var = tk.StringVar()
        self.charmap_list = tk.Listbox(rf, width=16, height=8, font=("Consolas", 9), exportselection=False)
        self.charmap_list.pack(fill=tk.X, pady=(2, 2))
        self.charmap_list.bind("<<ListboxSelect>>", self._on_charmap_select)
        ttk.Button(rf, text="✖ Remove", command=self._remove_charmap_entry).pack(fill=tk.X, pady=1)

    def sync_cfg(self, cfg: dict):
        self.cfg = cfg

    def load_from_raw(self, raw: bytearray, game_name: str):
        self.raw_data     = bytearray(raw)
        self.game_name    = game_name
        self.cfg          = load_config()
        self.game_profile = EXE_FONT_PROFILES.get(game_name)
        if not self.game_profile:
            self.font_status.config(text=f"No font profile for '{game_name}'.")
            self.font_combo.config(values=[])
            self.font_data = []
            self._refresh_list()
            return
        font_names = list(self.game_profile["fonts"].keys())
        self.font_combo.config(values=font_names)
        self.font_combo.set(font_names[0])
        self._load_current_font(font_names[0])

    def _load_current_font(self, font_key: str):
        self.current_font_key = font_key
        desc       = self.game_profile["fonts"][font_key]
        base       = self.game_profile["base_addr"]
        raw        = self.raw_data
        num_ptrs   = desc["num_ptrs"]
        ascii_start = desc["ascii_start"]
        glyph_offsets = [base + struct.unpack_from("<H", raw, desc["ptr_start"] + i * 2)[0]
                         for i in range(num_ptrs)]
        first_occurrence = {}
        for i, off in enumerate(glyph_offsets):
            first_occurrence.setdefault(off, i)

        rows      = desc["rows"]
        is_dynamic = desc["type"] == "dynamic"
        self.font_data = []

        for i, off in enumerate(glyph_offsets):
            alias_of = first_occurrence[off] if first_occurrence[off] != i else None
            if is_dynamic:
                width = max(1, min(24, raw[off]))
                bpr   = (width + 7) // 8
                bitmap = [int.from_bytes(raw[off + 1 + r * bpr:off + 1 + r * bpr + bpr], "big")
                          for r in range(rows)]
                self.font_data.append({"glyph_off": off, "width": width, "bytes_per_row": bpr, "bitmap": bitmap, "ascii": ascii_start + i, "alias_of": alias_of})
            else:
                width = max(1, min(8, raw[off]))
                self.font_data.append({"glyph_off": off, "width": width, "bytes_per_row": 1, "bitmap": list(raw[off + 1:off + 1 + rows]), "ascii": ascii_start + i, "alias_of": alias_of})
        self.selected_idx = 0
        self.width_spin.config(to=24 if is_dynamic else 8)
        self._refresh_list()
        self.char_list.selection_set(0)
        self._on_char_select(None)
        self.font_status.config(text=f"{font_key}  •  {num_ptrs} chars  •  {len(first_occurrence)} unique glyphs")
        self._refresh_charmap_list()

    def _refresh_list(self):
        self.char_list.delete(0, tk.END)
        for ch in self.font_data:
            ac      = ch["ascii"]
            char_str = chr(ac) if 0x20 <= ac <= 0x7E else "·"
            alias   = ch["alias_of"]
            if alias is not None:
                alias_ac = self.font_data[alias]["ascii"]
                label    = f"0x{ac:02X} '{char_str}'  ≡ 0x{alias_ac:02X}"
            else:
                label    = f"0x{ac:02X} ({ac:3d})  '{char_str}'"
            self.char_list.insert(tk.END, label)
            if alias is not None:
                self.char_list.itemconfig(tk.END, foreground="#999999")

    def _draw_grid(self):
        if not self.font_data:
            return
        ch      = self.font_data[self.selected_idx]
        desc    = self.game_profile["fonts"][self.current_font_key]
        rows    = desc["rows"]
        bpr     = ch["bytes_per_row"]
        cols    = bpr * 8
        width_px = ch["width"]
        cs      = self.CELL
        self.canvas.config(width=cols * cs, height=rows * cs)
        self.canvas.delete("all")
        for r in range(rows):
            row_val = ch["bitmap"][r] if r < len(ch["bitmap"]) else 0
            for c in range(cols):
                bit_idx = cols - 1 - c
                is_on   = bool(row_val & (1 << bit_idx))
                fill    = (("#1F618D" if is_on else "#1A252F") if c >= width_px else 
                          ("#3498DB" if is_on else "#2C3E50"))
                x1, y1 = c * cs, r * cs
                self.canvas.create_rectangle(x1, y1, x1 + cs, y1 + cs, fill=fill, outline="#111111")

        self.canvas.create_line(width_px * cs, 0, width_px * cs, rows * cs, fill="#E74C3C", width=2, dash=(4, 4))

    def _on_font_select(self, event=None):
        self._load_current_font(self.font_var.get())
        if hasattr(self, "charmap_title_label") and self.current_font_key:
            self.charmap_title_label.config(text=f"{self.current_font_key} char mapping:")
        self._refresh_charmap_list()

    def _on_char_select(self, event=None):
        sel = self.char_list.curselection()
        if not sel: return
        self.selected_idx = int(sel[0])
        ch    = self.font_data[self.selected_idx]
        self.width_var.set(ch["width"])
        alias = ch["alias_of"]
        if alias is not None:
            alias_ac = self.font_data[alias]["ascii"]
            self.alias_label.config(text=f"⚠ Alias of 0x{alias_ac:02X} ('{chr(alias_ac)}')\nEditing this glyph edits the original too.")
        else:
            self.alias_label.config(text="")
        byte_val = ch["ascii"]
        self.map_byte_var.set(f"{byte_val:02x}")
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text=f"0x{byte_val:02x} →")
        self._draw_grid()
        if hasattr(self, "charmap_title_label") and self.current_font_key:
            self.charmap_title_label.config(text=f"{self.current_font_key} char mapping:")

    def _on_width_change(self, event=None):
        if not self.font_data: return
        try:
            desc  = self.game_profile["fonts"][self.current_font_key]
            max_w = 24 if desc["type"] == "dynamic" else 8
            w     = max(1, min(max_w, self.width_var.get()))
            ch    = self.font_data[self.selected_idx]
            ch["width"] = w
            if desc["type"] == "dynamic":
                ch["bytes_per_row"] = (w + 7) // 8
            self._draw_grid()
        except (tk.TclError, IndexError):
            pass

    def _toggle_pixel(self, x, y, force=None):
        if not self.font_data: return None
        ch   = self.font_data[self.selected_idx]
        desc = self.game_profile["fonts"][self.current_font_key]
        cols = ch["bytes_per_row"] * 8
        cs   = self.CELL
        c, r = x // cs, y // cs
        if not (0 <= c < cols and 0 <= r < desc["rows"]): return None
        mask  = 1 << (cols - 1 - c)
        new_state = (not bool(ch["bitmap"][r] & mask)) if force is None else force
        if new_state: ch["bitmap"][r] |= mask
        else:         ch["bitmap"][r] &= ~mask
        self._draw_grid()
        return new_state

    def _edit_char(self, action, direction=None):
        if not self.font_data or not self.game_profile: return
        ch = self.font_data[self.selected_idx]
        if action == "clear":
            ch["bitmap"] = [0] * self.game_profile["fonts"][self.current_font_key]["rows"]
        elif action == "invert":
            cols, w = ch["bytes_per_row"] * 8, ch["width"]
            mask = ((1 << cols) - 1) ^ ((1 << (cols - w)) - 1) if w < cols else (1 << cols) - 1
            ch["bitmap"] = [(b ^ mask) & ((1 << cols) - 1) for b in ch["bitmap"]]
        elif action == "shift" and direction:
            bm, cols, mask = ch["bitmap"], ch["bytes_per_row"] * 8, (1 << (ch["bytes_per_row"] * 8)) - 1
            if direction == "up": ch["bitmap"] = bm[1:] + [0]
            elif direction == "down": ch["bitmap"] = [0] + bm[:-1]
            elif direction == "left": ch["bitmap"] = [(v << 1) & mask for v in bm]
            elif direction == "right": ch["bitmap"] = [v >> 1 for v in bm]
        self._draw_grid()

    def _write_glyph_to_buf(self, buf, ch, desc):
        off = ch["glyph_off"]
        buf[off] = ch["width"] & 0xFF
        if desc["type"] == "dynamic":
            bpr = ch["bytes_per_row"]
            for r, val in enumerate(ch["bitmap"]):
                r_off = off + 1 + r * bpr
                for b in range(bpr - 1, -1, -1):
                    buf[r_off + (bpr - 1 - b)] = (val >> (8 * b)) & 0xFF
        else:
            for r, val in enumerate(ch["bitmap"]):
                buf[off + 1 + r] = val & 0xFF

    def _export_font(self):
        if not self.font_data or not self.current_font_key:
            messagebox.showwarning("No data", "Load an EXE and select a font first.")
            return
        desc = self.game_profile["fonts"][self.current_font_key]
        filepath = filedialog.asksaveasfilename(title="Export Font", initialfile=self.current_font_key, 
                                               defaultextension=".FON", 
                                               filetypes=[("Font files", "*.FON *.fon *.bin"), ("All Files", "*.*")])
        if not filepath: return
        out, seen = bytearray(), set()
        rows = desc["rows"]
        for ch in self.font_data:
            if ch["glyph_off"] in seen: continue
            seen.add(ch["glyph_off"])
            out.append(ch["width"] & 0xFF)
            if desc["type"] == "dynamic":
                bpr = ch["bytes_per_row"]
                for val in ch["bitmap"]:
                    for b in range(bpr - 1, -1, -1):
                        out.append((val >> (8 * b)) & 0xFF)
            else:
                for r in range(rows):
                    out.append(ch["bitmap"][r] & 0xFF)
        with open(filepath, "wb") as f:
            f.write(out)
        self.font_status.config(text=f"✔ Exported {self.current_font_key} → {os.path.basename(filepath)}")

    def _import_font(self):
        if not self.game_profile or not self.current_font_key:
            messagebox.showwarning("No data", "Load an EXE and select a font first.")
            return
        filepath = filedialog.askopenfilename(title=f"Import Font ({self.current_font_key})", 
                                             filetypes=[("Font files", "*.FON *.fon *.bin"), ("All Files", "*.*")])
        if not filepath: return
        with open(filepath, "rb") as f:
            raw = bytearray(f.read())
        desc   = self.game_profile["fonts"][self.current_font_key]
        rows   = desc["rows"]
        seen2, unique = set(), []
        for ch in self.font_data:
            if ch["glyph_off"] not in seen2:
                seen2.add(ch["glyph_off"]); unique.append(ch)

        pos, loaded = 0, 0
        try:
            for ch in unique:
                if pos >= len(raw): break
                if desc["type"] == "dynamic":
                    width = max(1, min(24, raw[pos])); pos += 1
                    bpr   = (width + 7) // 8
                    bitmap = [int.from_bytes(raw[pos + r * bpr:pos + r * bpr + bpr], "big") for r in range(rows)]
                    pos  += rows * bpr
                    ch["width"] = width; ch["bytes_per_row"] = bpr; ch["bitmap"] = bitmap
                else:
                    width = max(1, min(8, raw[pos])); pos += 1
                    ch["width"] = width; ch["bitmap"] = list(raw[pos:pos + rows]); pos += rows
                loaded += 1
        except (IndexError, ValueError) as e:
            messagebox.showerror("Import error", f"Error at glyph {loaded}: {e}")
            return

        self._refresh_list()
        self.char_list.selection_set(self.selected_idx)
        self._on_char_select(None)
        self.font_status.config(text=f"✔ Imported {loaded} glyphs from {os.path.basename(filepath)} into {self.current_font_key}")

    def _get_charmap_entry(self, idx):
        return self.charmap_list.get(idx).split("→")[0].strip().lstrip("0x").lower()
    
    def _refresh_ui(self, what="charmap"):
        if what == "charmap":
            self._refresh_charmap_list()
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text="0x00 →")
        self.map_byte_var.set("")
        self.map_char_var.set("")

    def _font_charmap(self) -> dict:
        if not self.game_name or not self.current_font_key: return {}
        self.cfg = load_config()
        game_cfg = get_game_config(self.cfg, self.game_name)
        return game_cfg.setdefault("charmaps", {}).setdefault(self.current_font_key, {})

    def _refresh_charmap_list(self):
        if not hasattr(self, "charmap_list"): return
        self.charmap_list.delete(0, tk.END)
        for byte_hex, uni_char in sorted(self._font_charmap().items()):
            self.charmap_list.insert(tk.END, f"0x{byte_hex}  →  {uni_char}")

    def _add_charmap_entry(self):
        byte_str = self.map_byte_var.get().strip().lower().lstrip("0x") or "00"
        uni_char = self.map_char_var.get()
        if not uni_char: return
        try:
            int(byte_str, 16)
        except ValueError:
            messagebox.showerror("Invalid", f"'{byte_str}' is not a valid hex byte.")
            return
        self._font_charmap()[byte_str] = uni_char[0]
        save_config(self.cfg)
        self._refresh_ui()
        self._notify_charmap_changed()

    def _on_charmap_select(self, event=None):
        sel = self.charmap_list.curselection()
        if not sel: return
        byte_hex = self._get_charmap_entry(sel[0])
        self.map_byte_var.set(byte_hex)
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text=f"0x{byte_hex} →")
        char_part = self.charmap_list.get(sel[0]).split("→")[1].strip() if "→" in self.charmap_list.get(sel[0]) else ""
        self.map_char_var.set(char_part)

    def _remove_charmap_entry(self):
        sel = self.charmap_list.curselection()
        if not sel: return
        byte_hex = self._get_charmap_entry(sel[0])
        self._font_charmap().pop(byte_hex, None)
        save_config(self.cfg)
        self._refresh_ui()
        self._notify_charmap_changed()

    def _notify_charmap_changed(self):
        if callable(self.on_charmap_changed):
            charmap = dict(self._font_charmap())
            self.on_charmap_changed(self.game_name, self.current_font_key, charmap)

    def _write_to_exe(self):
        if not self.raw_data or not self.game_profile:
            messagebox.showwarning("No data", "Load an EXE file first.")
            return
        desc, seen, written = self.game_profile["fonts"][self.current_font_key], set(), 0
        for ch in self.font_data:
            if ch["glyph_off"] in seen: continue
            seen.add(ch["glyph_off"])
            self._write_glyph_to_buf(self.raw_data, ch, desc)
            written += 1

        main_data = self.get_exe_data()
        if main_data:
            rows = desc["rows"]
            for ch in self.font_data:
                off = ch["glyph_off"]
                if off + 1 + rows <= len(main_data):
                    self._write_glyph_to_buf(main_data, ch, desc)

        self.font_status.config(text=f"✔ {written} glyphs written to EXE data  ({self.current_font_key})")
        messagebox.showinfo("Font Written", f"{written} unique glyphs patched into EXE data.\nUse 'Save EXE' in the top bar to save the file.")

    def _copy_glyph(self):
        if not self.font_data or self.selected_idx >= len(self.font_data):
            messagebox.showwarning("No selection", "Select a character first.")
            return
        
        ch = self.font_data[self.selected_idx]
        self._clipboard = {
            "width": ch["width"],
            "bitmap": ch["bitmap"].copy(),
            "bytes_per_row": ch["bytes_per_row"]
        }
        ac = ch["ascii"]
        char_str = chr(ac) if 0x20 <= ac <= 0x7E else "·"
        self.font_status.config(text=f"✓ Copied 0x{ac:02X} '{char_str}' to clipboard")

    def _paste_glyph(self):
        if self._clipboard is None:
            messagebox.showwarning("Empty clipboard", "Copy a character first (Ctrl+C).")
            return
        
        if not self.font_data or self.selected_idx >= len(self.font_data):
            messagebox.showwarning("No selection", "Select a character first.")
            return
        ch = self.font_data[self.selected_idx]
        ch["width"] = self._clipboard["width"]
        ch["bitmap"] = self._clipboard["bitmap"].copy()
        ch["bytes_per_row"] = self._clipboard["bytes_per_row"]
        self.width_var.set(ch["width"])
        self._draw_grid()
        ac = ch["ascii"]
        char_str = chr(ac) if 0x20 <= ac <= 0x7E else "·"
        self.font_status.config(text=f"✓ Pasted to 0x{ac:02X} '{char_str}'")

    def _bind_shortcuts(self, parent):
        parent.bind("<Control-c>", lambda e: self._copy_glyph())
        parent.bind("<Control-v>", lambda e: self._paste_glyph())

__all__ = ['EXEFontEditor']

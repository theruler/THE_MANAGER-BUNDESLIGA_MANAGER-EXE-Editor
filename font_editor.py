import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from exe_handler import EXE_FONT_PROFILES
from font_safety import (
    FontSafetyError,
    atomic_save_bytes,
    change_glyph_width,
    copy_glyph_payload,
    export_font_bytes,
    import_font_bytes,
    load_font_model,
    paste_glyph_payload,
    stage_font_apply,
    unique_glyphs,
    validate_all_fonts,
    validate_font_model,
)
from utils import load_config, save_config, get_game_config


class EXEFontEditor:
    CELL = 20

    def __init__(
        self,
        parent,
        get_exe_data,
        on_charmap_changed=None,
        on_font_state_changed=None,
        can_change_charmap=None,
        on_open_charmap=None,
        on_string_font_change=None,
        translate=None,
    ):
        self.parent             = parent
        self.get_exe_data       = get_exe_data
        self.on_charmap_changed = on_charmap_changed
        self.on_font_state_changed = on_font_state_changed
        self.can_change_charmap = can_change_charmap
        self.on_open_charmap    = on_open_charmap
        self.on_string_font_change = on_string_font_change
        # Injected by the main editor; font_editor never imports main_editor.
        self.translate          = translate
        self._i18n              = []
        # Containers built outside self.parent (CharMap panel).  set_enabled()
        # must cover them, otherwise they would stay operable for an
        # unsupported executable.
        self._external_panels   = []
        self.raw_data:    bytearray = bytearray()
        self.initial_raw_data: bytearray = bytearray()
        self.game_name    = None
        self.game_profile = None
        self.is_supported = False
        self.current_font_key = None
        self.font_data    = []
        self.font_valid   = False
        self.font_pending = False
        self.font_changed = False
        self.font_errors  = []
        self.selected_idx = 0
        self._last_drag_state = None
        self.cfg          = load_config()
        self._clipboard   = None
        self.map_byte_var = tk.StringVar()
        self.map_char_var = tk.StringVar()
        self._build_ui(parent)
        self._bind_shortcuts(parent)

    def tr(self, key, **fmt):
        """Localised text via the injected translator; fail-visible fallback."""
        if callable(self.translate):
            return self.translate(key, **fmt)
        return key

    def _reg(self, widget, key):
        widget.config(text=self.tr(key))
        self._i18n.append((widget, key))
        return widget

    def retranslate(self):
        """Re-label all registered widgets; no font state is touched."""
        for widget, key in self._i18n:
            try:
                widget.config(text=self.tr(key))
            except tk.TclError:
                pass
        if self.is_supported and self.current_font_key:
            if hasattr(self, "charmap_title_label"):
                self.charmap_title_label.config(
                    text=self.tr("font.charmap_title_for", font=self.current_font_key))
        elif hasattr(self, "charmap_title_label"):
            self.charmap_title_label.config(text=self.tr("font.charmap_title"))
        if not self.is_supported and hasattr(self, "font_status"):
            self.font_status.config(text=self.tr("font.load_first"))

    def _build_ui(self, parent):
        bar = ttk.Frame(parent, padding=(12, 8, 12, 4))
        bar.pack(fill=tk.X)
        self._reg(ttk.Label(bar), "font.font").pack(side=tk.LEFT)
        self.font_var   = tk.StringVar()
        self.font_combo = ttk.Combobox(bar, textvariable=self.font_var, state="readonly", width=18)
        self.font_combo.pack(side=tk.LEFT, padx=(4, 16))
        self.font_combo.bind("<<ComboboxSelected>>", self._on_font_select)
        self._reg(ttk.Button(bar, command=self._write_to_exe),
                  "font.apply").pack(side=tk.LEFT, padx=4)
        self.font_status = ttk.Label(bar, text=self.tr("font.load_first"),
                                     font=("Segoe UI", 9, "italic"), foreground="#7F8C8D")
        self.font_status.pack(side=tk.LEFT, padx=12)
        self._reg(ttk.Label(bar, font=("Segoe UI", 9, "italic"), foreground="#566573",
                            justify=tk.RIGHT),
                  "settings.hint_text").pack(side=tk.RIGHT, padx=(8, 0))
        body = ttk.Frame(parent, padding=(12, 0, 12, 8))
        body.pack(fill=tk.BOTH, expand=True)
        lf = ttk.LabelFrame(body, padding=6)
        self._reg(lf, "font.characters")
        lf.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.char_list = tk.Listbox(lf, width=22, font=("Consolas", 10), exportselection=False, bg="white", selectbackground="#2980B9", selectforeground="white")
        sb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self.char_list.yview)
        self.char_list.configure(yscrollcommand=sb.set)
        self.char_list.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_list.bind("<<ListboxSelect>>", self._on_char_select)
        gf = ttk.LabelFrame(body, padding=8)
        self._reg(gf, "font.matrix")
        gf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(gf, bg="#1E1E1E", highlightthickness=0, width=8 * self.CELL, height=8 * self.CELL)
        self.canvas.pack(anchor=tk.CENTER, expand=True)
        self.canvas.bind("<Button-1>", lambda e: setattr(self, '_last_drag_state', self._toggle_pixel(e.x, e.y)))
        self.canvas.bind("<B1-Motion>", lambda e: self._last_drag_state is not None and self._toggle_pixel(e.x, e.y, force=self._last_drag_state))
        rf = ttk.Frame(body, padding=(8, 0, 0, 0))
        rf.pack(side=tk.RIGHT, fill=tk.Y)

        prop_group = ttk.LabelFrame(rf, padding=8)
        self._reg(prop_group, "font.props")
        prop_group.pack(fill=tk.X)
        props_inner = ttk.Frame(prop_group)
        props_inner.pack(fill=tk.X)
        width_col = ttk.Frame(props_inner)
        width_col.pack(side=tk.LEFT, padx=(0, 12))
        self._reg(ttk.Label(width_col), "font.width").pack(anchor=tk.W)
        self.width_var  = tk.IntVar(value=8)
        self.width_spin = ttk.Spinbox(width_col, from_=1, to=24, textvariable=self.width_var, width=5, command=self._on_width_change)
        self.width_spin.pack(anchor=tk.W, pady=(2, 0))
        self.width_spin.bind("<KeyRelease>", self._on_width_change)
        font_assign_col = ttk.Frame(props_inner)
        font_assign_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.string_font_label_widget = self._reg(ttk.Label(font_assign_col), "settings.font_label")
        self.string_font_label_widget.pack(anchor=tk.W)
        self.string_font_var = tk.StringVar(value="FLOW.FON")
        self.string_font_combo = ttk.Combobox(
            font_assign_col, textvariable=self.string_font_var, state="readonly",
            width=14, values=["FLOW.FON", "NORMAL.FON", "MICRO4.FON"],
        )
        self.string_font_combo.pack(anchor=tk.W, pady=(2, 0))
        self.string_font_combo.bind("<<ComboboxSelected>>", self._on_string_font_change_internal)

        tools_group = ttk.LabelFrame(rf, padding=8)
        self._reg(tools_group, "font.tools")
        tools_group.pack(fill=tk.X, pady=(8, 0))
        copy_paste_frame = ttk.Frame(tools_group)
        copy_paste_frame.pack(fill=tk.X, pady=(0, 2))
        self._reg(ttk.Button(copy_paste_frame, command=self._copy_glyph),
                  "font.copy").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self._reg(ttk.Button(copy_paste_frame, command=self._paste_glyph),
                  "font.paste").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        clear_invert_frame = ttk.Frame(tools_group)
        clear_invert_frame.pack(fill=tk.X, pady=2)
        self._reg(ttk.Button(clear_invert_frame, command=lambda: self._edit_char("clear")),
                  "font.clear").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self._reg(ttk.Button(clear_invert_frame, command=lambda: self._edit_char("invert")),
                  "font.invert").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        shift_frame = ttk.Frame(tools_group)
        shift_frame.pack(fill=tk.X, pady=(4, 2))
        for text, row, col, dir_ in [("▲", 0, 1, "up"), ("◀", 1, 0, "left"), ("▶", 1, 2, "right"), ("▼", 2, 1, "down")]:
            ttk.Button(shift_frame, text=text, width=3, command=lambda d=dir_: self._edit_char("shift", d)).grid(row=row, column=col, padx=1, pady=1)
        shift_frame.columnconfigure((0, 1, 2), weight=1)

        file_group = ttk.LabelFrame(rf, padding=8)
        self._reg(file_group, "font.file")
        file_group.pack(fill=tk.X, pady=(8, 0))
        import_export_frame = ttk.Frame(file_group)
        import_export_frame.pack(fill=tk.X)
        self._reg(ttk.Button(import_export_frame, command=self._import_font),
                  "font.import").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self._reg(ttk.Button(import_export_frame, command=self._export_font),
                  "font.export").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        charmap_group = ttk.LabelFrame(rf, padding=8)
        self._reg(charmap_group, "settings.charmap_group")
        charmap_group.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._build_charmap_inline(charmap_group)

        self.alias_label = ttk.Label(rf, text="", font=("Segoe UI", 8, "italic"), foreground="#E67E22", wraplength=150)
        self.alias_label.pack(anchor=tk.W, pady=(6, 0))

    def _build_charmap_inline(self, parent):
        """Build the CharMap controls inside the given frame (called by _build_ui)."""
        self.charmap_title_label = ttk.Label(parent, text=self.tr("font.charmap_title"),
                                             font=("Segoe UI", 9, "bold"))
        self.charmap_title_label.pack(anchor=tk.W, pady=(0, 4))
        map_row = ttk.Frame(parent)
        map_row.pack(fill=tk.X, pady=(0, 2))
        self.map_byte_label = ttk.Label(map_row, text="0x00 →", font=("Consolas", 9))
        self.map_byte_label.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(map_row, textvariable=self.map_char_var, width=4, font=("Consolas", 9)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(map_row, text="+", width=2, command=self._add_charmap_entry).pack(side=tk.LEFT)
        self.charmap_list = tk.Listbox(parent, width=20, height=8, font=("Consolas", 9), exportselection=False)
        self.charmap_list.pack(fill=tk.BOTH, expand=True, pady=(2, 2))
        self.charmap_list.bind("<<ListboxSelect>>", self._on_charmap_select)
        self._reg(ttk.Button(parent, command=self._remove_charmap_entry),
                  "font.remove").pack(fill=tk.X, pady=1)
        self._refresh_charmap_list()

    def build_charmap_panel(self, parent):
        """Build the CharMap controls in an arbitrary external parent frame.

        Kept for backwards compatibility; the charmap is now built inline
        in the right column of the Font Editor tab via _build_charmap_inline.
        """
        panel = ttk.Frame(parent)
        panel.pack(fill=tk.BOTH, expand=True)
        self._external_panels.append(panel)
        self._build_charmap_inline(panel)
        return panel

    def _open_charmap_area(self):
        if callable(self.on_open_charmap):
            self.on_open_charmap()

    def sync_cfg(self, cfg: dict):
        self.cfg = cfg

    def set_font_names(self, names: list):
        """Update the string-font assignment combo with available font names."""
        if hasattr(self, "string_font_combo"):
            self.string_font_combo.config(values=names)

    def _on_string_font_change_internal(self, event=None):
        if callable(self.on_string_font_change):
            self.on_string_font_change(event)

    def set_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED

        def apply_state(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Combobox):
                    child.config(state="readonly" if enabled else tk.DISABLED)
                elif isinstance(child, (ttk.Button, ttk.Spinbox, ttk.Entry, tk.Listbox, tk.Canvas)):
                    child.config(state=state)
                apply_state(child)

        apply_state(self.parent)
        for panel in self._external_panels:
            apply_state(panel)

    def _notify_font_state(self):
        if callable(self.on_font_state_changed):
            self.on_font_state_changed({
                "valid": bool(self.font_valid),
                "pending": bool(self.font_pending),
                "changed": bool(self.font_changed),
                "errors": list(self.font_errors),
            })

    def _set_font_state(self, *, valid=None, pending=None, changed=None, error=None):
        if valid is not None:
            self.font_valid = bool(valid)
        if pending is not None:
            self.font_pending = bool(pending)
        if changed is not None:
            self.font_changed = bool(changed)
        self.font_errors = [str(error)] if error else []
        self._notify_font_state()

    def _font_failure(self, error, *, show_dialog=True):
        detail = str(error)
        self._set_font_state(valid=False, error=detail)
        if hasattr(self, "font_status"):
            self.font_status.config(text=self.tr("font.blocked_status", error=detail))
        if show_dialog:
            messagebox.showerror(self.tr("font.blocked_title"), detail)
        return False

    def mark_saved(self):
        if self.is_supported and self.raw_data:
            self.initial_raw_data = bytearray(self.raw_data)
            self._set_font_state(
                valid=self.font_valid,
                pending=self.font_pending,
                changed=False,
                error=self.font_errors[0] if self.font_errors else None,
            )

    def validate_live_state(self):
        if not self.is_supported or not self.game_profile or not self.raw_data:
            return self._font_failure("No supported font state is loaded", show_dialog=False)
        main_data = self.get_exe_data()
        if not isinstance(main_data, bytearray) or not main_data:
            return self._font_failure("Live EXE buffer is unavailable", show_dialog=False)
        try:
            validate_all_fonts(self.raw_data, self.game_profile)
            validate_all_fonts(main_data, self.game_profile)
            for desc in self.game_profile["fonts"].values():
                for start_key, end_key in (("ptr_start", "ptr_end"), ("glyph_start", "glyph_end")):
                    start, end = desc[start_key], desc[end_key]
                    if self.raw_data[start:end] != main_data[start:end]:
                        raise FontSafetyError(
                            f"Font buffers differ in {start:#x}-{end:#x}"
                        )
            self._set_font_state(
                valid=True,
                pending=self.font_pending,
                changed=self.raw_data != self.initial_raw_data,
            )
            return True
        except (KeyError, FontSafetyError) as exc:
            return self._font_failure(exc, show_dialog=False)

    @staticmethod
    def _glyph(char):
        return char["glyph"]

    def _refresh_pending_state(self):
        if not self.font_data or not self.current_font_key:
            self._set_font_state(valid=False, pending=False, changed=False)
            return False
        try:
            staged, _ = stage_font_apply(
                self.raw_data, self.font_data, self.game_profile, self.current_font_key
            )
            pending = staged != self.raw_data
            changed = self.raw_data != self.initial_raw_data
            self._set_font_state(valid=True, pending=pending, changed=changed)
            return True
        except FontSafetyError as exc:
            return self._font_failure(exc, show_dialog=False)

    def reset_state(self, status=None):
        status = self.tr("font.load_first") if status is None else status
        self.is_supported    = False
        self.raw_data        = bytearray()
        self.initial_raw_data = bytearray()
        self.game_name       = None
        self.game_profile    = None
        self.current_font_key = None
        self.font_data       = []
        self.font_valid      = False
        self.font_pending    = False
        self.font_changed    = False
        self.font_errors     = []
        self.selected_idx    = 0
        self._last_drag_state = None
        self._clipboard      = None
        if hasattr(self, "font_combo"):
            self.font_combo.config(values=[])
            self.font_var.set("")
        if hasattr(self, "char_list"):
            self.char_list.delete(0, tk.END)
        if hasattr(self, "canvas"):
            self.canvas.delete("all")
        if hasattr(self, "alias_label"):
            self.alias_label.config(text="")
        if hasattr(self, "font_status"):
            self.font_status.config(text=status)
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text="0x00 →")
        if hasattr(self, "map_byte_var"):
            self.map_byte_var.set("")
        if hasattr(self, "map_char_var"):
            self.map_char_var.set("")
        if hasattr(self, "charmap_list"):
            self.charmap_list.delete(0, tk.END)
        self.set_enabled(False)
        self._notify_font_state()

    def load_from_raw(self, raw: bytearray, game_name: str):
        self.reset_state()
        self.cfg          = load_config()
        game_profile      = EXE_FONT_PROFILES.get(game_name)
        if not game_profile:
            self.font_status.config(text=self.tr("font.no_profile", profile=game_name))
            self._set_font_state(valid=False, error=f"No font profile for '{game_name}'")
            return False
        try:
            validate_all_fonts(raw, game_profile)
            self.raw_data       = bytearray(raw)
            self.initial_raw_data = bytearray(raw)
            self.game_name      = game_name
            self.game_profile   = game_profile
            self.is_supported   = True
            font_names = list(self.game_profile["fonts"].keys())
            self.font_combo.config(values=font_names)
            self.font_combo.set(font_names[0])
            # Listbox inserts are ignored while the widget is disabled.  Enable
            # the editor before populating it, after the font structure passed
            # its complete read-only validation above.
            self.set_enabled(True)
            if not self._load_current_font(font_names[0]):
                raise FontSafetyError("Initial font could not be loaded")
            self._set_font_state(valid=True, pending=False, changed=False)
            return True
        except (FontSafetyError, KeyError, IndexError, tk.TclError) as exc:
            self.is_supported = False
            self.set_enabled(False)
            return self._font_failure(exc)

    def _load_current_font(self, font_key: str):
        if not self.is_supported or not self.game_profile:
            return False
        try:
            desc = self.game_profile["fonts"][font_key]
            font_data = load_font_model(self.raw_data, self.game_profile, font_key)
            summary = validate_font_model(font_data, desc, len(self.raw_data))
        except (KeyError, FontSafetyError) as exc:
            return self._font_failure(exc)
        self.current_font_key = font_key
        self.font_data = font_data
        self.selected_idx = 0
        max_font_width = 24 if desc["type"] == "dynamic" else 8
        self.width_spin.config(to=max_font_width)
        self._refresh_list()
        self.char_list.selection_clear(0, tk.END)
        self.char_list.selection_set(0)
        self._on_char_select(None)
        self.font_status.config(text=self.tr(
            "font.summary", font=font_key, chars=summary["pointer_count"],
            unique=summary["unique_count"]))
        self._refresh_charmap_list()
        self._set_font_state(
            valid=True,
            pending=False,
            changed=self.raw_data != self.initial_raw_data,
        )
        return True

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
                inserted_index = self.char_list.size() - 1
                if inserted_index >= 0:
                    self.char_list.itemconfig(inserted_index, foreground="#999999")

    def _draw_grid(self):
        if not self.font_data:
            return
        ch      = self.font_data[self.selected_idx]
        glyph   = self._glyph(ch)
        desc    = self.game_profile["fonts"][self.current_font_key]
        rows    = desc["rows"]
        bpr     = glyph["bytes_per_row"]
        cols    = bpr * 8
        width_px = glyph["width"]
        cs      = self.CELL
        self.canvas.config(width=cols * cs, height=rows * cs)
        self.canvas.delete("all")
        for r in range(rows):
            row_val = glyph["bitmap"][r] if r < len(glyph["bitmap"]) else 0
            for c in range(cols):
                bit_idx = cols - 1 - c
                is_on   = bool(row_val & (1 << bit_idx))
                fill    = (("#1F618D" if is_on else "#1A252F") if c >= width_px else 
                          ("#3498DB" if is_on else "#2C3E50"))
                x1, y1 = c * cs, r * cs
                self.canvas.create_rectangle(x1, y1, x1 + cs, y1 + cs, fill=fill, outline="#111111")

        self.canvas.create_line(width_px * cs, 0, width_px * cs, rows * cs, fill="#E74C3C", width=2, dash=(4, 4))

    def _on_font_select(self, event=None):
        if not self.is_supported:
            return
        requested = self.font_var.get()
        previous = self.current_font_key
        if requested == previous:
            return
        if self.font_pending:
            decision = messagebox.askyesnocancel(
                self.tr("font.pending_title"),
                self.tr("font.pending_msg", font=previous),
            )
            if decision is None:
                self.font_var.set(previous)
                return
            if decision and not self._write_to_exe(show_success=False):
                self.font_var.set(previous)
                return
        if not self._load_current_font(requested):
            self.font_var.set(previous)
            return
        if hasattr(self, "charmap_title_label") and self.current_font_key:
            self.charmap_title_label.config(
                text=self.tr("font.charmap_title_for", font=self.current_font_key))
        self._refresh_charmap_list()

    def _on_char_select(self, event=None):
        if not self.is_supported:
            return
        sel = self.char_list.curselection()
        if not sel: return
        self.selected_idx = int(sel[0])
        ch    = self.font_data[self.selected_idx]
        glyph = self._glyph(ch)
        self.width_var.set(glyph["width"])
        self.width_spin.config(to=glyph["max_width"])
        alias = ch["alias_of"]
        if alias is not None:
            alias_ac = self.font_data[alias]["ascii"]
            self.alias_label.config(text=self.tr("font.alias", code=alias_ac, char=chr(alias_ac)))
        else:
            self.alias_label.config(text="")
        byte_val = ch["ascii"]
        self.map_byte_var.set(f"{byte_val:02x}")
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text=f"0x{byte_val:02x} →")
        self._draw_grid()
        if hasattr(self, "charmap_title_label") and self.current_font_key:
            self.charmap_title_label.config(
                text=self.tr("font.charmap_title_for", font=self.current_font_key))

    def _on_width_change(self, event=None):
        if not self.is_supported or not self.font_data: return
        try:
            desc  = self.game_profile["fonts"][self.current_font_key]
            glyph = self._glyph(self.font_data[self.selected_idx])
            old_width = glyph["width"]
            old_bpr = glyph["bytes_per_row"]
            old_bitmap = list(glyph["bitmap"])
            w = self.width_var.get()
            change_glyph_width(glyph, desc, w)
            if not self._refresh_pending_state():
                glyph["width"] = old_width
                glyph["bytes_per_row"] = old_bpr
                glyph["bitmap"] = old_bitmap
                self.width_var.set(old_width)
                return
            self._draw_grid()
        except (tk.TclError, IndexError):
            return
        except FontSafetyError as exc:
            try:
                self.width_var.set(self._glyph(self.font_data[self.selected_idx])["width"])
            except (IndexError, tk.TclError):
                pass
            self._font_failure(exc, show_dialog=False)

    def _toggle_pixel(self, x, y, force=None):
        if not self.is_supported or not self.font_data: return None
        glyph = self._glyph(self.font_data[self.selected_idx])
        desc = self.game_profile["fonts"][self.current_font_key]
        cols = glyph["bytes_per_row"] * 8
        cs   = self.CELL
        c, r = x // cs, y // cs
        if not (0 <= c < cols and 0 <= r < desc["rows"]): return None
        mask  = 1 << (cols - 1 - c)
        old_value = glyph["bitmap"][r]
        new_state = (not bool(old_value & mask)) if force is None else force
        glyph["bitmap"][r] = (old_value | mask) if new_state else (old_value & ~mask)
        if not self._refresh_pending_state():
            glyph["bitmap"][r] = old_value
            return None
        self._draw_grid()
        return new_state

    def _edit_char(self, action, direction=None):
        if not self.is_supported or not self.font_data or not self.game_profile: return
        glyph = self._glyph(self.font_data[self.selected_idx])
        old_bitmap = list(glyph["bitmap"])
        if action == "clear":
            glyph["bitmap"] = [0] * self.game_profile["fonts"][self.current_font_key]["rows"]
        elif action == "invert":
            cols, w = glyph["bytes_per_row"] * 8, glyph["width"]
            mask = ((1 << cols) - 1) ^ ((1 << (cols - w)) - 1) if w < cols else (1 << cols) - 1
            glyph["bitmap"] = [(b ^ mask) & ((1 << cols) - 1) for b in glyph["bitmap"]]
        elif action == "shift" and direction:
            bm = glyph["bitmap"]
            mask = (1 << (glyph["bytes_per_row"] * 8)) - 1
            if direction == "up": glyph["bitmap"] = bm[1:] + [0]
            elif direction == "down": glyph["bitmap"] = [0] + bm[:-1]
            elif direction == "left": glyph["bitmap"] = [(v << 1) & mask for v in bm]
            elif direction == "right": glyph["bitmap"] = [v >> 1 for v in bm]
        if not self._refresh_pending_state():
            glyph["bitmap"] = old_bitmap
            return
        self._draw_grid()

    def _export_font(self):
        if not self.is_supported or not self.font_data or not self.current_font_key:
            messagebox.showwarning(self.tr("font.no_data"), self.tr("font.no_data_msg"))
            return
        desc = self.game_profile["fonts"][self.current_font_key]
        filepath = filedialog.asksaveasfilename(title=self.tr("font.fd_export"),
                                               initialfile=self.current_font_key, 
                                               defaultextension=".FON", 
                                               filetypes=[("Font files", "*.FON *.fon *.bin"), ("All Files", "*.*")])
        if not filepath: return
        try:
            out = export_font_bytes(self.font_data, desc)
            atomic_save_bytes(filepath, out)
        except (FontSafetyError, OSError) as exc:
            messagebox.showerror(self.tr("font.export_error"), str(exc))
            return
        self.font_status.config(text=self.tr("font.exported", font=self.current_font_key,
                                             file=os.path.basename(filepath)))

    def _import_font(self):
        if not self.is_supported or not self.game_profile or not self.current_font_key:
            messagebox.showwarning(self.tr("font.no_data"), self.tr("font.no_data_msg"))
            return
        filepath = filedialog.askopenfilename(
            title=self.tr("font.fd_import", font=self.current_font_key), 
                                             filetypes=[("Font files", "*.FON *.fon *.bin"), ("All Files", "*.*")])
        if not filepath: return
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            desc = self.game_profile["fonts"][self.current_font_key]
            staged = import_font_bytes(raw, self.font_data, desc)
            stage_font_apply(self.raw_data, staged, self.game_profile, self.current_font_key)
        except (FontSafetyError, OSError) as exc:
            self._font_failure(f"Import failed without changes: {exc}")
            return
        self.font_data = staged
        self._refresh_pending_state()
        self._refresh_list()
        self.char_list.selection_clear(0, tk.END)
        self.char_list.selection_set(self.selected_idx)
        self._on_char_select(None)
        self.font_status.config(text=self.tr(
            "font.imported", n=len(unique_glyphs(staged)),
            file=os.path.basename(filepath), font=self.current_font_key))

    @staticmethod
    def _parse_charmap_byte(value: str) -> str:
        text = str(value).strip()
        if text.startswith(("0x", "0X")):
            text = text[2:]
        if not text or len(text) > 2 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
            raise ValueError("Enter one hexadecimal byte from 00 to FF.")
        number = int(text, 16)
        if not 0 <= number <= 0xFF:
            raise ValueError("Enter one hexadecimal byte from 00 to FF.")
        return f"{number:02x}"

    def _get_charmap_entry(self, idx):
        value = self.charmap_list.get(idx).split("→", 1)[0].strip()
        return self._parse_charmap_byte(value)

    def _charmap_change_allowed(self) -> bool:
        return not callable(self.can_change_charmap) or bool(self.can_change_charmap())
    
    def _refresh_ui(self, what="charmap"):
        if what == "charmap":
            self._refresh_charmap_list()
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text="0x00 →")
        self.map_byte_var.set("")
        self.map_char_var.set("")

    def _font_charmap(self) -> dict:
        if not self.is_supported or not self.game_name or not self.current_font_key: return {}
        self.cfg = load_config()
        game_cfg = get_game_config(self.cfg, self.game_name)
        return game_cfg.setdefault("charmaps", {}).setdefault(self.current_font_key, {})

    def _refresh_charmap_list(self):
        if not hasattr(self, "charmap_list"): return
        self.charmap_list.delete(0, tk.END)
        for byte_hex, uni_char in sorted(self._font_charmap().items()):
            self.charmap_list.insert(tk.END, f"0x{byte_hex}  →  {uni_char}")

    def _add_charmap_entry(self):
        if not self.is_supported:
            return
        uni_char = self.map_char_var.get()
        if not uni_char:
            messagebox.showerror(self.tr("font.invalid_entry"), self.tr("font.invalid_entry_msg"))
            return
        try:
            byte_str = self._parse_charmap_byte(self.map_byte_var.get())
        except ValueError as exc:
            messagebox.showerror(self.tr("font.invalid_byte"), str(exc))
            return
        if not self._charmap_change_allowed():
            return
        self._font_charmap()[byte_str] = uni_char[0]
        save_config(self.cfg)
        self._refresh_ui()
        self._notify_charmap_changed()

    def _on_charmap_select(self, event=None):
        sel = self.charmap_list.curselection()
        if not sel: return
        if not self._charmap_change_allowed():
            return
        byte_hex = self._get_charmap_entry(sel[0])
        self.map_byte_var.set(byte_hex)
        if hasattr(self, "map_byte_label"):
            self.map_byte_label.config(text=f"0x{byte_hex} →")
        char_part = self.charmap_list.get(sel[0]).split("→")[1].strip() if "→" in self.charmap_list.get(sel[0]) else ""
        self.map_char_var.set(char_part)

    def _remove_charmap_entry(self):
        if not self.is_supported:
            return
        sel = self.charmap_list.curselection()
        if not sel: return
        byte_hex = self._get_charmap_entry(sel[0])
        if not self._charmap_change_allowed():
            return
        self._font_charmap().pop(byte_hex, None)
        save_config(self.cfg)
        self._refresh_ui()
        self._notify_charmap_changed()

    def _notify_charmap_changed(self):
        if callable(self.on_charmap_changed):
            charmap = dict(self._font_charmap())
            self.on_charmap_changed(self.game_name, self.current_font_key, charmap)

    def _write_to_exe(self, *, show_success=True):
        if not self.is_supported or not self.raw_data or not self.game_profile:
            messagebox.showwarning(self.tr("font.no_data"), self.tr("font.no_exe_msg"))
            return False
        main_data = self.get_exe_data()
        if not isinstance(main_data, bytearray) or not main_data:
            return self._font_failure("Live EXE buffer is unavailable")
        old_raw = bytearray(self.raw_data)
        old_main = bytearray(main_data)
        selected = self.selected_idx
        committed = False
        try:
            staged_raw, raw_result = stage_font_apply(
                self.raw_data, self.font_data, self.game_profile, self.current_font_key
            )
            staged_main, main_result = stage_font_apply(
                main_data, self.font_data, self.game_profile, self.current_font_key
            )
            if raw_result["changed_offsets"] != main_result["changed_offsets"]:
                raise FontSafetyError("Font buffers do not have the same pre-commit state")
            committed = True
            self.raw_data[:] = staged_raw
            main_data[:] = staged_main
            self.font_data = load_font_model(
                self.raw_data, self.game_profile, self.current_font_key
            )
            self.selected_idx = min(selected, len(self.font_data) - 1)
            self._set_font_state(
                valid=True,
                pending=False,
                changed=self.raw_data != self.initial_raw_data,
            )
        except Exception as exc:
            if committed:
                self.raw_data[:] = old_raw
                main_data[:] = old_main
                try:
                    self.font_data = load_font_model(
                        self.raw_data, self.game_profile, self.current_font_key
                    )
                    self.selected_idx = min(selected, len(self.font_data) - 1)
                except Exception:
                    self.font_data = []
            return self._font_failure(f"Apply failed; live data was not changed: {exc}")
        written = raw_result["unique_count"]
        self.font_status.config(text=self.tr("font.written", n=written,
                                             font=self.current_font_key))
        self._refresh_list()
        self.char_list.selection_clear(0, tk.END)
        self.char_list.selection_set(self.selected_idx)
        self._on_char_select(None)
        if show_success:
            messagebox.showinfo(self.tr("font.written_title"),
                                self.tr("font.written_msg", n=written))
        return True

    def _copy_glyph(self):
        if not self.is_supported or not self.font_data or self.selected_idx >= len(self.font_data):
            messagebox.showwarning(self.tr("font.no_selection"), self.tr("font.no_selection_msg"))
            return
        
        ch = self.font_data[self.selected_idx]
        desc = self.game_profile["fonts"][self.current_font_key]
        self._clipboard = copy_glyph_payload(self._glyph(ch), desc)
        ac = ch["ascii"]
        char_str = chr(ac) if 0x20 <= ac <= 0x7E else "·"
        self.font_status.config(text=self.tr("font.copied", code=ac, char=char_str))

    def _paste_glyph(self):
        if not self.is_supported:
            return
        if self._clipboard is None:
            messagebox.showwarning(self.tr("font.empty_clipboard"),
                                   self.tr("font.empty_clipboard_msg"))
            return
        
        if not self.font_data or self.selected_idx >= len(self.font_data):
            messagebox.showwarning(self.tr("font.no_selection"), self.tr("font.no_selection_msg"))
            return
        ch = self.font_data[self.selected_idx]
        glyph = self._glyph(ch)
        desc = self.game_profile["fonts"][self.current_font_key]
        old_state = (glyph["width"], glyph["bytes_per_row"], list(glyph["bitmap"]))
        try:
            paste_glyph_payload(glyph, desc, self._clipboard)
            if not self._refresh_pending_state():
                raise FontSafetyError("Pasted glyph did not pass font validation")
        except FontSafetyError as exc:
            glyph["width"], glyph["bytes_per_row"], glyph["bitmap"] = old_state
            self.width_var.set(glyph["width"])
            self._font_failure(f"Paste rejected without changes: {exc}")
            return
        self.width_var.set(glyph["width"])
        self._draw_grid()
        ac = ch["ascii"]
        char_str = chr(ac) if 0x20 <= ac <= 0x7E else "·"
        self.font_status.config(text=self.tr("font.pasted", code=ac, char=char_str))

    def _bind_shortcuts(self, parent):
        parent.bind("<Control-c>", lambda e: self._copy_glyph())
        parent.bind("<Control-v>", lambda e: self._paste_glyph())

__all__ = ['EXEFontEditor']

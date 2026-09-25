from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from vga_editor import _PAL_NORMAL20

class _YearMixin:

    _YEAR_MIN = 1900
    _YEAR_MAX = 2099

    def _year_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("code_year")
        if not isinstance(offset, int) or offset < 0 or offset + 2 > len(self.exe_data):
            return None
        return offset

    def _sync_year_widget(self):
        if not hasattr(self, "year_spinbox"):
            return
        if self._year_offset() is not None:
            if not self.year_container.winfo_manager():
                self.year_container.pack(fill=tk.X, pady=6)
            self.year_spinbox.config(state=tk.NORMAL)
            return
        self.year_spinbox.config(state=tk.DISABLED)
        self.year_container.pack_forget()
        self.year_var.set("")
        self._last_valid_year = None

    def _revert_year(self):
        self.year_var.set("" if self._last_valid_year is None else str(self._last_valid_year))

    def _read_year_from_exe(self):
        offset = self._year_offset()
        if offset is None:
            self._last_valid_year = None
            self.year_var.set("")
        else:
            self._last_valid_year = int.from_bytes(self.exe_data[offset:offset + 2], "little")
            self.year_var.set(str(self._last_valid_year))
        self._sync_year_widget()

    def _commit_year(self, event=None):
        offset = self._year_offset()
        if offset is None:
            return
        raw = self.year_var.get().strip()
        if not raw.isdigit():
            self._revert_year()
            return
        value = int(raw)
        if not (self._YEAR_MIN <= value <= self._YEAR_MAX):
            self._revert_year()
            return
        self.year_var.set(str(value))
        self._last_valid_year = value
        payload = value.to_bytes(2, "little")
        if bytes(self.exe_data[offset:offset + 2]) == payload:
            return
        self.exe_data[offset:offset + 2] = payload
        self._invalidate_diff_preview("year-change")
        self._update_save_state()


class _RegionMixin:

    _REGION_VARIANTS = (
        ("region.1", 1),
        ("region.2", 2),
        ("region.3", 3),
        ("region.4", 4),
    )

    def _region_index(self, value):
        for index, (_key, variant) in enumerate(self._REGION_VARIANTS):
            if value == variant:
                return index
        return None

    def _region_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("region_offset")
        if not isinstance(offset, int) or offset < 0 or offset + 8 > len(self.exe_data):
            return None
        if int.from_bytes(self.exe_data[offset + 2:offset + 4], "little") != 0:
            return None
        if int.from_bytes(self.exe_data[offset + 6:offset + 8], "little") != 0:
            return None
        return offset

    def _region_values(self):
        return [self.tr(key) for key, _variant in self._REGION_VARIANTS]

    def _sync_region_widget(self):
        if not hasattr(self, "region_a_combo"):
            return
        if self._region_offset() is not None:
            values = self._region_values()
            if not self.region_container.winfo_manager():
                self.region_container.pack(fill=tk.X, pady=6)
            for combo in (self.region_a_combo, self.region_b_combo):
                combo.config(values=values, state="readonly")
            return
        for combo in (self.region_a_combo, self.region_b_combo):
            combo.config(state=tk.DISABLED)
        self.region_container.pack_forget()
        self.region_a_var.set("")
        self.region_b_var.set("")
        self._last_valid_region_a = None
        self._last_valid_region_b = None

    def _revert_region(self, combo, var, last_value):
        if last_value is None:
            var.set("")
        else:
            combo.current(last_value)

    def _read_region_from_exe(self):
        offset = self._region_offset()
        values = (None, None)
        if offset is not None:
            values = (
                int.from_bytes(self.exe_data[offset:offset + 4], "little"),
                int.from_bytes(self.exe_data[offset + 4:offset + 8], "little"),
            )

        indices = tuple(
            self._region_index(value) if value is not None else None
            for value in values
        )

        combo_specs = (
            (self.region_a_combo, self.region_a_var, "_last_valid_region_a", indices[0]),
            (self.region_b_combo, self.region_b_var, "_last_valid_region_b", indices[1]),
        )
        label_values = self._region_values()
        for combo, var, last_attr, index in combo_specs:
            combo.config(values=label_values)
            if index is None:
                var.set("")
                setattr(self, last_attr, None)
            else:
                combo.current(index)
                setattr(self, last_attr, index)

        self._sync_region_widget()

    def _commit_region(self, combo, var, last_attr, field_offset, event=None):
        offset = self._region_offset()
        if offset is None:
            return

        index = combo.current()
        if not 0 <= index < len(self._REGION_VARIANTS):
            self._revert_region(combo, var, getattr(self, last_attr))
            return

        value = self._REGION_VARIANTS[index][1]
        payload = value.to_bytes(4, "little")
        file_offset = offset + field_offset

        if bytes(self.exe_data[file_offset:file_offset + 4]) == payload:
            setattr(self, last_attr, index)
            return

        self.exe_data[file_offset:file_offset + 4] = payload
        setattr(self, last_attr, index)
        self._invalidate_diff_preview("region-change")
        self._update_save_state()

    def _commit_region_a(self, event=None):
        self._commit_region(
            self.region_a_combo, self.region_a_var,
            "_last_valid_region_a", 0, event,
        )

    def _commit_region_b(self, event=None):
        self._commit_region(
            self.region_b_combo, self.region_b_var,
            "_last_valid_region_b", 4, event,
        )


class _PointsMixin:

    def _points_rule_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("points_offset")
        if not isinstance(offset, int):
            return None
        if offset < 0 or offset + 2 > len(self.exe_data):
            return None
        val = int.from_bytes(self.exe_data[offset:offset + 2], "little")
        if val not in (2, 3):
            return None
        return offset

    def _sync_points_widget(self):
        if not hasattr(self, "points_combo"):
            return
        if self._points_rule_offset() is not None:
            if not self.points_container.winfo_manager():
                self.points_container.pack(fill=tk.X, pady=6)
            self.points_combo.config(state="readonly")
            return
        self.points_combo.config(state=tk.DISABLED)
        self.points_container.pack_forget()
        self.points_var.set("")
        self._last_valid_points = None

    def _revert_points(self):
        self.points_var.set("" if self._last_valid_points is None else str(self._last_valid_points))

    def _read_points_from_exe(self):
        offset = self._points_rule_offset()
        if offset is None:
            self._last_valid_points = None
            self.points_var.set("")
        else:
            self._last_valid_points = int.from_bytes(self.exe_data[offset:offset + 2], "little")
            self.points_var.set(str(self._last_valid_points))
        self._sync_points_widget()

    def _commit_points(self, event=None):
        offset = self._points_rule_offset()
        if offset is None:
            return
        raw = self.points_var.get().strip()
        if not raw.isdigit():
            self._revert_points()
            return
        value = int(raw)
        if value not in (2, 3):
            self._revert_points()
            return
        self.points_var.set(str(value))
        self._last_valid_points = value
        payload = value.to_bytes(2, "little")
        if bytes(self.exe_data[offset:offset + 2]) == payload:
            return
        self.exe_data[offset:offset + 2] = payload
        self._invalidate_diff_preview("points-change")
        self._update_save_state()


class _WdlMixin:

    def _wdl_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("wdl_map")
        if not isinstance(offset, int) or offset < 0 or offset + 6 > len(self.exe_data):
            return None
        return offset

    def _sync_wdl_widget(self):
        if not hasattr(self, "wdl_container"):
            return
        if self._wdl_offset() is not None:
            for i in range(6):
                combo = getattr(self, f"_wdl_combo_{i}", None)
                if combo:
                    combo.config(state="readonly")
            return
        for i in range(6):
            combo = getattr(self, f"_wdl_combo_{i}", None)
            if combo:
                combo.config(state=tk.DISABLED)
            v = getattr(self, f"_wdl_var_{i}", None)
            if v:
                v.set("")
        self._wdl_last_valid = [None] * 6

    def _wdl_char_from_byte(self, value):
        try:
            return bytes((value,)).decode("cp437")
        except (ValueError, UnicodeDecodeError):
            return ""

    def _wdl_byte_from_char(self, value):
        if not value:
            raise ValueError
        encoded = value[0].encode("cp437")
        if len(encoded) != 1:
            raise ValueError
        return encoded[0]

    def _read_wdl_from_exe(self):
        offset = self._wdl_offset()
        if offset is None:
            self._wdl_last_valid = [None] * 6
            for i in range(6):
                v = getattr(self, f"_wdl_var_{i}", None)
                if v:
                    v.set("")
        else:
            for i in range(6):
                byte_val = self.exe_data[offset + i]
                self._wdl_last_valid[i] = byte_val
                v = getattr(self, f"_wdl_var_{i}", None)
                char_value = self._wdl_char_from_byte(byte_val)
                if v:
                    v.set(char_value if char_value in self._wdl_char_values else "")
        self._sync_wdl_widget()

    def _commit_wdl(self, box_index: int, event=None):
        offset = self._wdl_offset()
        if offset is None:
            return
        v = getattr(self, f"_wdl_var_{box_index}", None)
        if v is None:
            return
        raw = v.get()
        try:
            value = self._wdl_byte_from_char(raw)
            if not 0 <= value <= 0xFF:
                raise ValueError
        except (ValueError, UnicodeEncodeError):
            prev = self._wdl_last_valid[box_index]
            v.set(self._wdl_char_from_byte(prev) if prev is not None else "")
            return
        self._wdl_last_valid[box_index] = value
        file_offset = offset + box_index
        if self.exe_data[file_offset] == value:
            return
        self.exe_data[file_offset] = value
        self._invalidate_diff_preview("wdl-change")
        self._update_save_state()



class _MatchFlagMixin:

    _FLAG_TYPES = (("flag.3v", "3v"),("flag.3h", "3h"),)

    def _get_flag_types(self):
        return [(self.tr(key), code) for key, code in self._FLAG_TYPES]

    def _match_flag_config(self):
        if not self._supported_loaded():
            return None
        config = self.profile.get("match_flag")
        if not isinstance(config, dict):
            return None
        return config

    def _flag_offsets_valid(self):
        mf = self._match_flag_config()
        if mf is None:
            return False

        detect_offset = mf.get("detect_offset")
        color_offsets = mf.get("color_offsets")
        band_offsets  = mf.get("band_offsets")
        type_sets     = mf.get("types")

        if (
            not isinstance(detect_offset, int)
            or not isinstance(color_offsets, (tuple, list))
            or len(color_offsets) != 3
            or not isinstance(band_offsets, (tuple, list))
            or len(band_offsets) != 3
            or not isinstance(type_sets, dict)
            or not type_sets
        ):
            return False

        ranges = [(detect_offset, 1)]
        for off in color_offsets:
            if not isinstance(off, int):
                return False
            ranges.append((off, 1))

        for off in band_offsets:
            if not isinstance(off, int):
                return False

        for patches in type_sets.values():
            if not isinstance(patches, dict):
                return False
            patch_values = list(patches.values())
            if len(patch_values) != len(band_offsets):
                return False
            for band_offset, patch_hex in zip(band_offsets, patch_values):
                try:
                    patch = bytes.fromhex(patch_hex)
                except (TypeError, ValueError):
                    return False
                ranges.append((band_offset, len(patch)))

        return all(
            off >= 0 and off + size <= len(self.exe_data)
            for off, size in ranges
        )

    def _detect_flag_type(self):
        mf = self._match_flag_config()
        if mf is None or not self._flag_offsets_valid():
            return None

        band_offsets = tuple(mf["band_offsets"])
        for type_key, patches in mf["types"].items():
            if not isinstance(patches, dict):
                continue
            patch_values = list(patches.values())
            if len(patch_values) != len(band_offsets):
                continue
            if all(
                bytes(self.exe_data[band_offset:band_offset + len(expected)]) == expected
                for band_offset, expected in (
                    (off, bytes.fromhex(hex_str))
                    for off, hex_str in zip(band_offsets, patch_values)
                )
            ):
                return type_key
        return None

    def _detect_flag_colors(self):
        mf = self._match_flag_config()
        if mf is None or not self._flag_offsets_valid():
            return [0, 0, 0]

        detect_offset = mf["detect_offset"]
        color_offsets = tuple(mf["color_offsets"])
        first_color = 0 if self.exe_data[detect_offset] == 0x2A else self.exe_data[color_offsets[0]]
        return [first_color, self.exe_data[color_offsets[1]], self.exe_data[color_offsets[2]]]

    def _detect_flag_font_color(self):
        mf = self._match_flag_config()
        if mf is None or not self._flag_offsets_valid():
            return 0
        offset = mf.get("font_color_offset")
        if not isinstance(offset, int) or not (0 <= offset < len(self.exe_data)):
            return 0
        value = self.exe_data[offset]
        return value if 0 <= value < len(_PAL_NORMAL20) else 0

    def _sync_flag_widget(self):
        if not hasattr(self, "flag_container"):
            return
        if self._flag_offsets_valid():
            if not self.flag_container.winfo_manager():
                self.flag_container.pack(fill=tk.X, pady=6)
            self._flag_type_combo.config(state="readonly")
            return
        self._hide_flag_palette()
        self._flag_type_combo.config(state=tk.DISABLED)
        self.flag_container.pack_forget()
        self._flag_type_var.set("")
        self._flag_last_valid_type = None
        self._flag_selected_band = None

    def _read_flag_from_exe(self):
        type_key = self._detect_flag_type()
        self._flag_colors = self._detect_flag_colors()
        self._flag_font_color = self._detect_flag_font_color()
        self._flag_selected_band = None
        self._hide_flag_palette()

        if type_key is not None:
            for label, key in self._get_flag_types():
                if key == type_key:
                    self._flag_type_var.set(label)
                    self._flag_last_valid_type = type_key
                    break
        else:
            self._flag_type_var.set("")
            self._flag_last_valid_type = None

        self._sync_flag_widget()
        self._draw_flag_preview()

    def _on_flag_type_changed(self, event=None):
        label = self._flag_type_var.get()
        type_key = next((k for lbl, k in self._get_flag_types() if lbl == label), None)
        if type_key is None or not self._flag_offsets_valid():
            return

        mf = self._match_flag_config()
        band_offsets = tuple(mf["band_offsets"])
        patches = mf["types"].get(type_key)
        if not isinstance(patches, dict):
            return

        for band_offset, hex_str in zip(band_offsets, patches.values()):
            data = bytes.fromhex(hex_str)
            self.exe_data[band_offset:band_offset + len(data)] = data

        self._flag_last_valid_type = type_key
        self._flag_selected_band = None
        self._hide_flag_palette()
        self._draw_flag_preview()
        self._invalidate_diff_preview("flag-type-change")
        self._update_save_state()

    def _commit_flag_color(self, band_index, pal_index: int):
        if not self._flag_offsets_valid():
            return

        mf = self._match_flag_config()

        if band_index == "title":
            font_color_offset = mf.get("font_color_offset")
            if not isinstance(font_color_offset, int):
                return
            if not 0 <= font_color_offset < len(self.exe_data):
                return
            self.exe_data[font_color_offset] = pal_index
            self._flag_font_color = pal_index
        else:
            color_offsets = tuple(mf["color_offsets"])
            if not isinstance(band_index, int) or not 0 <= band_index < len(color_offsets):
                return
            self._flag_colors[band_index] = pal_index
            if band_index == 0:
                detect_offset = mf["detect_offset"]
                if pal_index == 0:
                    self.exe_data[detect_offset] = 0x2A
                    self.exe_data[color_offsets[0]] = 0xC0
                else:
                    self.exe_data[detect_offset] = 0xB0
                    self.exe_data[color_offsets[0]] = pal_index
            else:
                self.exe_data[color_offsets[band_index]] = pal_index

        self._hide_flag_palette()
        self._flag_selected_band = None
        self._draw_flag_preview()
        self._invalidate_diff_preview("flag-color-change")
        self._update_save_state()

    def _hide_flag_palette(self):
        popup = getattr(self, "_flag_palette_popup", None)
        self._flag_palette_popup = None
        self._flag_pal_canvas = None
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass

    def _show_flag_palette(self):
        if not hasattr(self, "_flag_canvas") or self._flag_selected_band is None:
            return

        self._hide_flag_palette()

        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.configure(bg="#888888", bd=1, relief=tk.SOLID)
        popup.overrideredirect(True)
        popup.transient(self.root)

        pal  = list(_PAL_NORMAL20)
        cols = 16
        sq   = 14
        rows = max(1, (len(pal) + cols - 1) // cols)

        canvas = tk.Canvas(
            popup,
            width=cols * sq,
            height=rows * sq,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        canvas.pack(padx=1, pady=1)

        for i, (r, g, b) in enumerate(pal):
            cx = (i % cols) * sq
            cy = (i // cols) * sq
            canvas.create_rectangle(
                cx, cy, cx + sq, cy + sq,
                fill=f"#{r:02X}{g:02X}{b:02X}",
                outline="",
                tags=f"fpc_{i}",
            )

        self._flag_palette_popup = popup
        self._flag_pal_canvas    = canvas
        self._flag_pal_sq        = sq
        self._flag_pal_cols      = cols

        canvas.bind("<Button-1>", self._on_flag_palette_click)
        popup.bind("<Escape>", lambda _event: self._hide_flag_palette())

        self.root.update_idletasks()
        popup.update_idletasks()

        x = self._flag_canvas.winfo_rootx() + self._flag_canvas.winfo_width() + 8
        y = self._flag_canvas.winfo_rooty()

        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        popup_w  = cols * sq + 2
        popup_h  = rows * sq + 2

        if x + popup_w > screen_w:
            x = max(0, self._flag_canvas.winfo_rootx() - popup_w - 8)
        if y + popup_h > screen_h:
            y = max(0, screen_h - popup_h - 8)

        popup.geometry(f"+{x}+{y}")
        popup.deiconify()
        popup.lift()

    def _draw_flag_preview(self):
        if not hasattr(self, "_flag_canvas"):
            return
        c        = self._flag_canvas
        c.delete("all")
        w        = int(c["width"])
        h        = int(c["height"])
        pal      = list(_PAL_NORMAL20)
        type_key = self._flag_last_valid_type

        def _palette_color(idx, fallback="#000000"):
            if 0 <= idx < len(pal):
                r, g, b = pal[idx]
                return f"#{r:02X}{g:02X}{b:02X}"
            return fallback

        def _band_color(band_idx):
            idx = self._flag_colors[band_idx] if band_idx < len(self._flag_colors) else 0
            return _palette_color(idx)

        if type_key == "3v":
            bw = w // 3
            for i in range(3):
                x0      = i * bw
                x1      = x0 + bw if i < 2 else w
                col     = _band_color(i)
                outline = "#FFFF00" if self._flag_selected_band == i else ""
                width   = 2 if self._flag_selected_band == i else 0
                c.create_rectangle(x0, 0, x1, h, fill=col, outline=outline, width=width)
        
        elif type_key == "3h":
            bh = h // 3
            for i in range(3):
                y0      = i * bh
                y1      = y0 + bh if i < 2 else h
                col     = _band_color(i)
                outline = "#FFFF00" if self._flag_selected_band == i else ""
                width   = 2 if self._flag_selected_band == i else 0
                c.create_rectangle(0, y0, w, y1, fill=col, outline=outline, width=width)
        
        else:
            c.create_rectangle(0, 0, w, h, fill="#CCCCCC", outline="")
            c.create_text(w // 2, h // 2, text="?", fill="#888888",font=("Segoe UI", 14, "bold"))
            return

        title_color    = _palette_color(getattr(self, "_flag_font_color", 0), "#FFFFFF")
        title_selected = self._flag_selected_band == "title"
        title_x, title_y = w // 2, h // 2

        if title_selected:
            bbox = c.create_text(title_x, title_y, text="title",font=("Segoe UI", 8, "bold"), fill=title_color)
            x0, y0, x1, y1 = c.bbox(bbox)
            pad_x, pad_y = 4, 2
            c.tag_lower(c.create_rectangle(x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y,outline=title_color, width=2,), bbox)
        else:
            c.create_text(title_x, title_y, text="title",font=("Segoe UI", 8, "bold"), fill=title_color)

    def _on_flag_canvas_click(self, event):
        if not hasattr(self, "_flag_canvas"):
            return
        c        = self._flag_canvas
        w        = int(c["width"])
        h        = int(c["height"])
        type_key = self._flag_last_valid_type

        if type_key not in {"3v", "3h"}:
            return

        center_x, center_y = w / 2, h / 2
        if abs(event.x - center_x) <= 20 and abs(event.y - center_y) <= 8:
            self._flag_selected_band = "title"
            self._draw_flag_preview()
            self._show_flag_palette()
            return

        if type_key == "3v":
            band = min(event.x // (w // 3), 2)
        else:
            band = min(event.y // (h // 3), 2)

        self._flag_selected_band = band
        self._draw_flag_preview()
        self._show_flag_palette()

    def _on_flag_palette_click(self, event):
        if self._flag_selected_band is None:
            return
        canvas = getattr(self, "_flag_pal_canvas", None)
        if canvas is None:
            return
        sq   = self._flag_pal_sq
        cols = self._flag_pal_cols
        idx  = (event.y // sq) * cols + (event.x // sq)
        if not 0 <= idx < len(list(_PAL_NORMAL20)):
            return
        self._commit_flag_color(self._flag_selected_band, idx)



class _20TeamsMixin:

    def _teams_config(self):
        if not self._supported_loaded():
            return None, None, None
        teams_cfg = self.profile.get("teams")
        if not isinstance(teams_cfg, dict):
            return None, None, None
        offset = teams_cfg.get("offset")
        teams_dict = teams_cfg.get("number")
        if not isinstance(offset, int) or not isinstance(teams_dict, dict):
            return None, None, None
        return teams_cfg, offset, teams_dict

    def _teams_offset(self):
        _, offset, teams_dict = self._teams_config()
        if offset is None or teams_dict is None:
            return None
        sample_hex = next(iter(teams_dict.values()), "")
        byte_len = len(bytes.fromhex(sample_hex)) if sample_hex else 16
        if offset < 0 or offset + byte_len > len(self.exe_data):
            return None
        return offset

    def _sync_teams_widget(self):
        if not hasattr(self, "teams_combo"):
            return
        if self._teams_offset() is not None:
            if not self.teams_container.winfo_manager():
                self.teams_container.pack(fill=tk.X, pady=6)
            self.teams_combo.config(state="readonly")
            return
        self.teams_combo.config(state=tk.DISABLED)
        self.teams_container.pack_forget()
        self.teams_var.set("")
        self._last_valid_teams = None

    def _revert_teams(self):
        self.teams_var.set("" if self._last_valid_teams is None else str(self._last_valid_teams))

    def _read_teams_from_exe(self):
        _, offset, teams_dict = self._teams_config()
        if offset is None or teams_dict is None or self._teams_offset() is None:
            self._last_valid_teams = None
            self.teams_var.set("")
        else:
            sample_hex = next(iter(teams_dict.values()), "")
            byte_len = len(bytes.fromhex(sample_hex)) if sample_hex else 16
            current_bytes = bytes(self.exe_data[offset:offset + byte_len])
            current_hex = current_bytes.hex().upper()

            matched_key = None
            for key, hex_str in teams_dict.items():
                if hex_str.upper() == current_hex:
                    matched_key = key
                    break

            self._last_valid_teams = matched_key
            self.teams_var.set(matched_key if matched_key is not None else "")
        self._sync_teams_widget()

    def _commit_teams(self, event=None):
        _, offset, teams_dict = self._teams_config()
        if offset is None or teams_dict is None or self._teams_offset() is None:
            return
        key = self.teams_var.get().strip()
        if key not in teams_dict:
            self._revert_teams()
            return
        hex_str = teams_dict[key]
        payload = bytes.fromhex(hex_str)
        if bytes(self.exe_data[offset:offset + len(payload)]) == payload:
            self._last_valid_teams = key
            return
        self.exe_data[offset:offset + len(payload)] = payload
        self.teams_var.set(key)
        self._last_valid_teams = key
        self._invalidate_diff_preview("teams-change")
        self._update_save_state()


class _SustMixin:

    _SUBST_GK_VALUES = (1, 2)
    _SUBST_VALUES    = (2, 3, 4)

    def _subst_gk_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("subst_gk_offset")
        if not isinstance(offset, int):
            return None
        if offset < 0 or offset + 1 > len(self.exe_data):
            return None
        if self.exe_data[offset] not in self._SUBST_GK_VALUES:
            return None
        return offset

    def _subst_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("subst_offset")
        if not isinstance(offset, int):
            return None
        if offset < 0 or offset + 1 > len(self.exe_data):
            return None
        if self.exe_data[offset] not in self._SUBST_VALUES:
            return None
        return offset

    def _subst_offsets_valid(self):
        return self._subst_gk_offset() is not None or self._subst_offset() is not None

    def _sync_subst_widget(self):
        if not hasattr(self, "subst_gk_combo"):
            return
        gk_off   = self._subst_gk_offset()
        sub_off  = self._subst_offset()
        if gk_off is not None or sub_off is not None:
            if not self.subst_container.winfo_manager():
                self.subst_container.pack(fill=tk.X, pady=6)
            self.subst_gk_combo.config(state="readonly" if gk_off is not None else tk.DISABLED)
            self.subst_combo.config(state="readonly" if sub_off is not None else tk.DISABLED)
            return
        self.subst_gk_combo.config(state=tk.DISABLED)
        self.subst_combo.config(state=tk.DISABLED)
        self.subst_container.pack_forget()
        self.subst_gk_var.set("")
        self.subst_var.set("")
        self._last_valid_subst_gk = None
        self._last_valid_subst    = None

    def _revert_subst_gk(self):
        self.subst_gk_var.set(
            "" if self._last_valid_subst_gk is None else str(self._last_valid_subst_gk)
        )

    def _revert_subst(self):
        self.subst_var.set(
            "" if self._last_valid_subst is None else str(self._last_valid_subst)
        )

    def _read_subst_from_exe(self):
        gk_off = self._subst_gk_offset()
        if gk_off is None:
            self._last_valid_subst_gk = None
            self.subst_gk_var.set("")
        else:
            val = self.exe_data[gk_off]
            self._last_valid_subst_gk = val
            self.subst_gk_var.set(str(val))

        sub_off = self._subst_offset()
        if sub_off is None:
            self._last_valid_subst = None
            self.subst_var.set("")
        else:
            val = self.exe_data[sub_off]
            self._last_valid_subst = val
            self.subst_var.set(str(val))

        self._sync_subst_widget()

    def _commit_subst_gk(self, event=None):
        offset = self._subst_gk_offset()
        if offset is None:
            return
        raw = self.subst_gk_var.get().strip()
        if not raw.isdigit():
            self._revert_subst_gk()
            return
        value = int(raw)
        if value not in self._SUBST_GK_VALUES:
            self._revert_subst_gk()
            return
        self.subst_gk_var.set(str(value))
        self._last_valid_subst_gk = value
        if self.exe_data[offset] == value:
            return
        self.exe_data[offset] = value
        self._invalidate_diff_preview("subst-gk-change")
        self._update_save_state()

    def _commit_subst(self, event=None):
        offset = self._subst_offset()
        if offset is None:
            return
        raw = self.subst_var.get().strip()
        if not raw.isdigit():
            self._revert_subst()
            return
        value = int(raw)
        if value not in self._SUBST_VALUES:
            self._revert_subst()
            return
        self.subst_var.set(str(value))
        self._last_valid_subst = value
        if self.exe_data[offset] == value:
            return
        self.exe_data[offset] = value
        self._invalidate_diff_preview("subst-change")
        self._update_save_state()


class ExeSettingsMixin(_YearMixin, _RegionMixin, _PointsMixin, _SustMixin, _20TeamsMixin, _WdlMixin, _MatchFlagMixin):
    pass


__all__ = ["ExeSettingsMixin"]

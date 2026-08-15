import os
import sys
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from exe_handler import unpack_in_memory, GAME_PROFILES, EXE_FONT_PROFILES
from charmap import charmap_decode, charmap_encode
from translator import translate_string, TRANSLATION_ENGINES
from utils import load_config, save_config, get_game_config, DEFAULT_PROFILE_NAME
from font_editor import EXEFontEditor


class DOSTranslationEditor:
    
    def __init__(self, root):
        self.root = root
        self.root.title("The Manager / Bundesliga Manager Professional Editor by TheRuler76")
        self.root.geometry("980x800")
        self.root.minsize(780, 600)
        self.exe_data              = bytearray()
        self.entries               = []
        self.displayed_indices     = []
        self.current_index         = None
        self.overflow_entry_indices = set()
        self.profile_name          = DEFAULT_PROFILE_NAME
        self.profile               = GAME_PROFILES[self.profile_name]
        self._apply_modern_style()
        self.cfg = load_config()
        self._build_gui()

    def _apply_modern_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        bg, fg = "#F4F6F9", "#2C3E50"
        style.configure("TFrame",            background=bg)
        style.configure("TLabel",            background=bg, font=("Segoe UI", 10), foreground=fg)
        style.configure("TLabelframe",       background=bg, font=("Segoe UI", 10, "bold"), foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        style.configure("TButton",           font=("Segoe UI", 9, "bold"), padding=6, background="#3498DB", foreground="white", borderwidth=0)
        style.map("TButton", background=[("active", "#2980B9"), ("disabled", "#BDC3C7")])
        style.configure("Treeview",          font=("Consolas", 10), rowheight=28, background="white", fieldbackground="white", foreground=fg, borderwidth=0)
        style.configure("Treeview.Heading",  font=("Segoe UI", 10, "bold"), background="#EAECEE", foreground=fg, padding=6)
        style.map("Treeview", background=[("selected", "#2980B9")], foreground=[("selected", "white")])

    def _build_gui(self):
        self.root.configure(bg="#F4F6F9")
        top_frame = ttk.Frame(self.root, padding=(15, 12, 15, 5))
        top_frame.pack(fill=tk.X)
        ttk.Button(top_frame, text="📁 Load EXE", command=self.load_exe).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top_frame, text="💾 Save EXE", command=self.save_exe).pack(side=tk.LEFT, padx=8)
        ttk.Label(top_frame, text="Detected game:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(15, 4))
        self.profile_label  = ttk.Label(top_frame, text="—", font=("Segoe UI", 9, "bold"), foreground="#2980B9")
        self.profile_label.pack(side=tk.LEFT)
        self.filename_label = ttk.Label(top_frame, text="", font=("Segoe UI", 9, "italic"), foreground="#7F8C8D")
        self.filename_label.pack(side=tk.LEFT, padx=(8, 0))
        self.status_label   = ttk.Label(top_frame, text="No file loaded.", font=("Segoe UI", 10, "italic"))
        self.status_label.pack(side=tk.LEFT, padx=15)
        ttk.Style().configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(12, 5))
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        tab_strings = ttk.Frame(self.notebook)
        self.notebook.add(tab_strings, text="  📝 String Editor  ")
        free_space_frame = ttk.Frame(tab_strings, padding=(15, 6, 15, 0))
        free_space_frame.pack(fill=tk.X)
        self.current_range_label = ttk.Label(free_space_frame, text="", font=("Segoe UI", 9, "bold"), foreground="#27AE60")
        self.current_range_label.pack(side=tk.LEFT)
        search_frame = ttk.Frame(tab_strings, padding=(15, 5, 15, 8))
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="🔍 Search:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.search_entry.bind("<Escape>", lambda e: self.clear_search())
        ttk.Button(search_frame, text="❌ Clear", command=self.clear_search).pack(side=tk.RIGHT)
        main_frame = ttk.Frame(tab_strings, padding=(15, 0, 15, 8))
        main_frame.pack(fill=tk.BOTH, expand=True)
        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_container, columns=("num", "offset", "text"), show="headings", selectmode="browse")
        self.tree.heading("num",    text="#")
        self.tree.heading("offset", text="Offset")
        self.tree.heading("text",   text="String Text")
        self.tree.column("num",    anchor=tk.CENTER, width=30,  stretch=False)
        self.tree.column("offset", anchor=tk.CENTER, width=60, stretch=False)
        self.tree.column("text",   anchor=tk.W,      stretch=True)
        v_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.tag_configure("overflow_error", background="#F5B7B1", foreground="#641E16")
        edit_frame = ttk.LabelFrame(tab_strings, text=" Edit String (Spaces Highlighted) ", padding=15)
        edit_frame.pack(fill=tk.X, padx=15, pady=(5, 12))
        self.edit_text = self._make_text_widget(edit_frame)
        self.edit_text.bind("<KeyRelease>", self.on_text_modified)
        self.edit_text.bind("<Return>",         lambda e: [self.apply_edit(), "break"][1])
        self.edit_text.bind("<Control-Return>",  lambda e: [self.apply_edit(), "break"][1])
        info_frame = ttk.Frame(edit_frame)
        info_frame.pack(fill=tk.X)
        self.space_stats_label = ttk.Label(info_frame, text="", font=("Segoe UI", 9, "italic"), foreground="#2980B9")
        self.space_stats_label.pack(side=tk.LEFT)
        ctrl_row = ttk.Frame(edit_frame)
        ctrl_row.pack(fill=tk.X, pady=(10, 0))
        self.translate_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_row, text="🌐 Traduzione automatica", variable=self.translate_enabled_var, command=self.on_translate_toggle).pack(side=tk.LEFT)
        ttk.Button(ctrl_row, text="⚡ Translate ALL", command=self.translate_all).pack(side=tk.LEFT, padx=(6, 0))

        for label, var_attr, values, width, on_change in [
            ("Motore:", "engine_var",      list(TRANSLATION_ENGINES.keys()), 18, lambda e: self.translate_current()),
            ("Da:",     "source_lang_var", ["auto","de","en","fr","es","it"], 6,  lambda e: self.translate_current()),
            ("A:",      "target_lang_var", ["it","en","de","fr","es"],        6,  lambda e: self.translate_current()),
        ]:
            ttk.Label(ctrl_row, text=label).pack(side=tk.LEFT, padx=(12 if label == "Motore:" else 0, 3))
            var = tk.StringVar(value=values[0])
            setattr(self, var_attr, var)
            combo = ttk.Combobox(ctrl_row, textvariable=var, state="readonly", width=width, values=values)
            combo.pack(side=tk.LEFT, padx=(0, 8))
            combo.bind("<<ComboboxSelected>>", on_change)
        self.engine_var.set("Google Translate")
        self.source_lang_var.set("auto")
        self.target_lang_var.set("it")
        self.translate_status_label = ttk.Label(ctrl_row, text="", font=("Segoe UI", 9, "italic"), foreground="#7F8C8D")
        self.translate_status_label.pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(ctrl_row, text="✔ Apply Change", command=self.apply_edit).pack(side=tk.RIGHT)
        self.string_font_var = tk.StringVar(value="FLOW.FON")
        self.string_font_combo = ttk.Combobox(ctrl_row, textvariable=self.string_font_var, state="readonly", width=12, values=["FLOW.FON", "NORMAL.FON", "MICRO4.FON"])
        self.string_font_combo.pack(side=tk.RIGHT, padx=(0, 4))
        self.string_font_combo.bind("<<ComboboxSelected>>", self._on_string_font_change)
        ttk.Label(ctrl_row, text="Associated Font:").pack(side=tk.RIGHT, padx=(8, 2))
        self.translate_section = ttk.Frame(edit_frame)
        translate_header = ttk.Frame(self.translate_section)
        translate_header.pack(fill=tk.X, pady=(6, 4))
        ttk.Label(translate_header, text="Translated string:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.translate_text = self._make_text_widget(self.translate_section, bg="#FDFEFE")
        self.translate_text.bind("<KeyRelease>",        self.on_translate_text_modified)
        self.translate_text.bind("<Return>",            lambda e: [self.apply_edit(), "break"][1])
        self.translate_text.bind("<Control-Return>",    lambda e: [self.apply_edit(), "break"][1])
        tab_fonts = ttk.Frame(self.notebook)
        self.notebook.add(tab_fonts, text="  🔤 Font Editor  ")
        self.font_editor = EXEFontEditor(
            tab_fonts,
            get_exe_data=lambda: self.exe_data,
            on_charmap_changed=self._on_charmap_changed,
        )

    def _make_text_widget(self, parent, bg="#FFFFFF"):
        container = tk.Frame(parent, bg="#BDC3C7", bd=1)
        container.pack(fill=tk.X, expand=True, pady=(0, 8))
        widget = tk.Text(container, height=1, wrap="word", font=("Consolas", 12, "bold"), bg=bg, fg="#1A252F", insertbackground="black", relief="flat", padx=5, pady=4)
        widget.pack(fill=tk.X, expand=True)
        widget.tag_configure("space_bg", background="#B3E5FC", foreground="#0288D1")
        return widget

    def _game_cfg(self) -> dict:
        return get_game_config(self.cfg, self.profile_name)

    def _active_charmap(self) -> dict:
        return self._game_cfg().get("charmaps", {}).get(self.string_font_var.get(), {})

    def _get_font_for_entry(self, entry: dict) -> str:
        gcfg = self._game_cfg()
        key  = hex(entry["str_addr"])
        if key in gcfg["string_fonts"]:
            return gcfg["string_fonts"][key]
        ri = self.get_range_index(entry["str_addr"])
        return gcfg["range_font_defaults"].get(str(ri), "FLOW.FON") if ri is not None else "FLOW.FON"

    def _on_string_font_change(self, event=None):
        if self.current_index is None: return
        entry = self.entries[self.current_index]
        self.cfg = load_config()
        self._game_cfg()["string_fonts"][hex(entry["str_addr"])] = self.string_font_var.get()
        save_config(self.cfg)
        if hasattr(self, "font_editor"):
            self.font_editor.sync_cfg(self.cfg)
        self._refresh_current_entry_display()

    def _on_charmap_changed(self, game_name: str, font_key: str, charmap: dict):
        if game_name != self.profile_name:
            return
        self.cfg = load_config()
        if hasattr(self, "font_editor"):
            self.font_editor.sync_cfg(self.cfg)
        if self.current_index is not None:
            current_font = self._get_font_for_entry(self.entries[self.current_index])
            if current_font == font_key:
                self._refresh_current_entry_display()

    def _refresh_current_entry_display(self):
        if self.current_index is None:
            return
        entry = self.entries[self.current_index]
        raw_bytes = entry["text"].encode("latin-1", errors="replace")
        self.edit_text.config(state=tk.NORMAL)
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.insert("1.0", charmap_decode(raw_bytes, self._active_charmap()))
        self.highlight_spaces()

    def on_translate_toggle(self):
        if self.translate_enabled_var.get():
            self.translate_section.pack(fill=tk.X)
            self.translate_current()
        else:
            self.translate_section.pack_forget()

    def on_translate_text_modified(self, event=None):
        self._update_text_widget(self.translate_text, update_stats=False)

    def _update_text_widget(self, widget, update_stats=False):
        widget.tag_remove("space_bg", "1.0", tk.END)
        text = widget.get("1.0", "1.0 lineend")
        for i, char in enumerate(text):
            if char == " ":
                widget.tag_add("space_bg", f"1.0 + {i} chars", f"1.0 + {i + 1} chars")

        if update_stats:
            l_spaces = len(text) - len(text.lstrip(" "))
            r_spaces = len(text) - len(text.rstrip(" "))
            self.space_stats_label.config(text=f"Total length: {len(text)} chars | Leading spaces: {l_spaces} | Trailing spaces: {r_spaces}")
        widget.update_idletasks()
        last_line = int(widget.index("end-1c").split(".")[0])
        display_lines = sum(
            (widget.count(f"{ln}.0", f"{ln}.end", "displaylines") or (0,))[0] + 1
            for ln in range(1, last_line + 1)
        )
        widget.config(height=max(1, min(max(display_lines, 1), 12)))
        return text

    def ptr_to_offset(self, ptr_val): return self.profile["ds_start"] + ptr_val
    def offset_to_ptr(self, offset):  return offset - self.profile["ds_start"]

    def read_null_string(self, offset):
        end = self.exe_data.find(b"\x00", offset)
        if end == -1: return ""
        try:    return self.exe_data[offset:end].decode("latin-1", errors="replace")
        except: return ""

    def is_inside_valid_ranges(self, addr):
        return any(s <= addr < e for s, e in self.profile["valid_ranges"])

    def get_range_index(self, addr):
        for i, (s, e) in enumerate(self.profile["valid_ranges"]):
            if s <= addr < e: return i
        return None

    def scan_reverse(self):
        self.entries = []
        self.overflow_entry_indices = set()
        by_str_addr, order = {}, []
        fixed_entries = []
        for fixed_addr, fixed_max_len in self.profile.get("fixed_strings", []):
            text = self.read_null_string(fixed_addr)[:fixed_max_len - 1]
            fixed_entries.append({"ptr_addrs": [], "code_ptr_addrs": [], "ptr_base_const": None, "str_addr": fixed_addr, "text": text, "max_len": fixed_max_len, "fixed": True})

        for start_r, end_r in self.profile["ptr_ranges"]:
            for addr in range(start_r, end_r - 3, 4):
                ptr_bytes     = self.exe_data[addr:addr + 4]
                offset_le     = struct.unpack_from("<H", ptr_bytes, 0)[0]
                base_addr_const = ptr_bytes[2:4]
                str_addr      = self.ptr_to_offset(offset_le)
                if not self.is_inside_valid_ranges(str_addr): continue
                if str_addr not in by_str_addr:
                    by_str_addr[str_addr] = {"ptr_addrs": [addr], "code_ptr_addrs": [], "ptr_base_const": base_addr_const, "str_addr": str_addr, "text": self.read_null_string(str_addr), "max_len": 0}
                    order.append(str_addr)
                else:
                    by_str_addr[str_addr]["ptr_addrs"].append(addr)

        for code_addr, str_addr in self.profile.get("code_ptrs", []):
            if str_addr not in by_str_addr:
                by_str_addr[str_addr] = {"ptr_addrs": [], "code_ptr_addrs": [code_addr], "ptr_base_const": self.profile["base_const"], "str_addr": str_addr, "text": self.read_null_string(str_addr), "max_len": 0}
                order.append(str_addr)
            else:
                by_str_addr[str_addr]["code_ptr_addrs"].append(code_addr)

        dynamic = sorted((by_str_addr[a] for a in order), key=lambda x: x["str_addr"])
        self.entries = fixed_entries + dynamic
        self._recalculate_max_lengths()
        self.refresh_table()
        self.update_free_space_label()

    def _recalculate_max_lengths(self):
        sorted_entries = sorted((e for e in self.entries if not e.get("fixed")), key=lambda x: x["str_addr"])
        for i, curr in enumerate(sorted_entries):
            if i < len(sorted_entries) - 1:
                nxt = sorted_entries[i + 1]
                curr["max_len"] = nxt["str_addr"] - curr["str_addr"] if nxt["str_addr"] > curr["str_addr"] \
                                  else len(curr["text"].encode("latin-1", errors="replace")) + 1
            else:
                curr["max_len"] = len(curr["text"].encode("latin-1", errors="replace")) + 1

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        self.displayed_indices = []
        query = self.search_var.get().lower()
        for idx, entry in enumerate(self.entries):
            font_key = self._get_font_for_entry(entry)
            entry_charmap = self._game_cfg().get("charmaps", {}).get(font_key, {})
            raw_bytes = entry["text"].encode("latin-1", errors="replace")
            decoded = charmap_decode(raw_bytes, entry_charmap)
            if query and query not in entry["text"].lower() and query not in decoded.lower(): continue
            self.displayed_indices.append(idx)
            tags = ("overflow_error",) if idx in self.overflow_entry_indices else ()
            self.tree.insert("", tk.END, iid=str(len(self.displayed_indices) - 1), values=(idx + 1, hex(entry["str_addr"]), decoded), tags=tags)
        total, shown = len(self.entries), len(self.displayed_indices)
        self.status_label.config(
            text=f" Found {shown} of {total} strings matching '{query}'" if query else f" Found {total} verified strings.")

    def on_search_change(self, *args): self.refresh_table()

    def clear_search(self):
        self.search_var.set("")
        self.search_entry.focus()
        self._reselect_current()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        self.current_index = self.displayed_indices[int(selected[0])]
        entry = self.entries[self.current_index]
        self.string_font_var.set(self._get_font_for_entry(entry))
        self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
        self.edit_text.delete("1.0", tk.END)
        raw_bytes = entry["text"].encode("latin-1", errors="replace")
        self.edit_text.insert("1.0", charmap_decode(raw_bytes, self._active_charmap()))
        self.highlight_spaces()
        self.update_free_space_label()
        self.translate_current()

    def highlight_spaces(self): self._update_text_widget(self.edit_text, update_stats=True)

    def on_text_modified(self, event=None):
        full = self.edit_text.get("1.0", tk.END)
        if "\n" in full[:-1] or "\r" in full:
            cursor_pos = self.edit_text.index(tk.INSERT)
            content    = full.replace("\n", "").replace("\r", "")
            self.edit_text.delete("1.0", tk.END)
            self.edit_text.insert("1.0", content)
            try: self.edit_text.mark_set(tk.INSERT, cursor_pos)
            except tk.TclError: pass
        self.highlight_spaces()

        if self.current_index is not None:
            entry = self.entries[self.current_index]
            current_raw = charmap_encode(self.edit_text.get("1.0", "1.0 lineend"), self._active_charmap()).decode("latin-1", errors="replace")
            if entry.get("fixed"):
                max_len = entry["max_len"] - 1
                free    = max_len - len(current_raw.encode("latin-1", errors="replace"))
                self.current_range_label.config(
                    text=f"Free Bytes (Fixed String): {free} / {max_len}",
                    foreground="#C0392B" if free < 0 else "#27AE60")
            else:
                self.update_free_space_label(live_override=(entry, current_raw))
        else:
            self.update_free_space_label()

    def apply_edit(self):
        if self.current_index is None: return
        entry     = self.entries[self.current_index]
        new_bytes = charmap_encode(self.edit_text.get("1.0", "1.0 lineend"), self._active_charmap())
        new_text  = new_bytes.decode("latin-1", errors="replace")
        self.cfg = load_config()
        self._game_cfg()["string_fonts"][hex(entry["str_addr"])] = self.string_font_var.get()
        save_config(self.cfg)
        if hasattr(self, "font_editor"):
            self.font_editor.sync_cfg(self.cfg)
        if entry.get("fixed"):
            max_len = entry["max_len"]
            if len(new_bytes) > max_len - 1:
                new_bytes = new_bytes[:max_len - 1]
                new_text  = new_bytes.decode("latin-1", errors="replace")
                messagebox.showwarning("Max length exceeded", f"Max {max_len - 1} bytes for this string.")
            entry["text"] = new_text
            addr = entry["str_addr"]
            self.exe_data[addr:addr + max_len] = new_bytes + b"\x00" * (max_len - len(new_bytes))
        else:
            entry["text"] = new_text
            self.repack_all_strings()

        self.refresh_table()
        self._reselect_current()

    def translate_current(self):
        if self.current_index is None or not self.translate_enabled_var.get(): return
        original = self.edit_text.get("1.0", "1.0 lineend")
        self.translate_text.delete("1.0", tk.END)
        if not original.strip():
            self.translate_status_label.config(text="")
            self._update_text_widget(self.translate_text, update_stats=False)
            return
        self.translate_status_label.config(text="Translating...")
        self.root.update_idletasks()
        try:
            translated = translate_string(original, target_lang=self.target_lang_var.get(), source_lang=self.source_lang_var.get(), engine=self.engine_var.get())
        except Exception as exc:
            self.translate_status_label.config(text=f"Errore: {exc}")
            return
        self.translate_text.insert("1.0", translated)
        self.translate_status_label.config(text="")
        self._update_text_widget(self.translate_text, update_stats=False)

    def translate_all(self):
        if not self.entries:
            messagebox.showinfo("Translate ALL", "No string loaded.")
            return
        if not messagebox.askyesno(
            "Translate ALL",
            f"Auto translate all {len(self.entries)} strings with '{self.engine_var.get()}'?\n\n"
            "*** Sperimental ***.",
        ):
            return

        engine  = self.engine_var.get()
        src     = self.source_lang_var.get()
        tgt     = self.target_lang_var.get()
        errors  = []
        skipped = 0
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Translating ALL...")
        prog_win.resizable(False, False)
        prog_win.grab_set()
        ttk.Label(prog_win, text="Translating...", font=("Segoe UI", 10, "bold"), padding=10).pack()
        progress_var = tk.IntVar(value=0)
        bar = ttk.Progressbar(prog_win, maximum=len(self.entries), variable=progress_var, length=360)
        bar.pack(padx=20, pady=(0, 6))
        status_lbl = ttk.Label(prog_win, text="", font=("Segoe UI", 9, "italic"), padding=(10, 0, 10, 10))
        status_lbl.pack()
        prog_win.update()

        for i, entry in enumerate(self.entries):
            original = entry["text"].strip()
            status_lbl.config(text=f"{i + 1}/{len(self.entries)}: {original[:50]}")
            progress_var.set(i + 1)
            prog_win.update()

            if not original:
                skipped += 1
                continue
            try:
                translated = translate_string(original, target_lang=tgt, source_lang=src, engine=engine)
                if translated and translated != original:
                    entry["text"] = translated
            except Exception as exc:
                errors.append(f"#{i + 1}: {exc}")
                if len(errors) >= 5:
                    errors.append("too many errors, aborting.")
                    break

        prog_win.destroy()
        self.repack_all_strings()
        self.refresh_table()
        self._reselect_current()

        summary = f"Complete! {len(self.entries) - skipped - len(errors)} strings translated."
        if skipped:
            summary += f"\n{skipped} empty strings skipped."
        if errors:
            summary += f"\n\nErrori ({len(errors)}):\n" + "\n".join(errors)
            messagebox.showwarning("Result", summary)
        else:
            messagebox.showinfo("Completed", summary)

    def update_free_space_label(self, live_override=None):
        if not hasattr(self, "current_range_label") or not self.profile:
            if hasattr(self, "current_range_label"): self.current_range_label.config(text="")
            return

        if self.current_index is not None:
            current_entry = self.entries[self.current_index]
            if current_entry.get("fixed"):
                max_len = current_entry["max_len"] - 1
                free    = max_len - len(current_entry["text"].encode("latin-1", errors="replace"))
                self.current_range_label.config(text=f"Free Bytes (Fixed String): {free} / {max_len}", foreground="#C0392B" if free < 0 else "#27AE60")
                return
        live_entry, live_text = live_override if live_override else (None, None)
        usage = [{"start": s, "end": e, "size": e - s, "used": 0} for s, e in self.profile["valid_ranges"]]

        for idx, u in enumerate(usage):
            range_entries = sorted((e for e in self.entries if self.get_range_index(e["str_addr"]) == idx), key=lambda e: e["str_addr"])
            occupied = bytearray(u["size"])
            for e in range_entries:
                text     = live_text if e is live_entry else e["text"]
                text_len = len(text.encode("latin-1", errors="replace")) + 1
                start_off = e["str_addr"] - u["start"]
                for i in range(max(start_off, 0), min(start_off + text_len, len(occupied))):
                    occupied[i] = 1
            u["free"] = u["size"] - sum(occupied)

        if self.current_index is not None:
            range_idx = self.get_range_index(self.entries[self.current_index]["str_addr"])
            if range_idx is not None:
                u = usage[range_idx]
                self.current_range_label.config(
                    text=f"Free Bytes (Block {range_idx + 1}): {u['free']} / {u['size']}",
                    foreground="#C0392B" if u["free"] < 0 else "#27AE60")
                return
        self.current_range_label.config(text="")

    def repack_all_strings(self):
        if not self.profile: return True
        groups = [{"start": s, "end": e, "size": e - s, "entries": []} for s, e in self.profile["valid_ranges"]]
        for entry in self.entries:
            idx = self.get_range_index(entry["str_addr"])
            if idx is not None: groups[idx]["entries"].append(entry)

        for g in groups:
            sorted_entries = sorted(g["entries"], key=lambda e: e["str_addr"])
            for i, parent in enumerate(sorted_entries):
                parent_bytes = parent["text"].encode("latin-1", errors="replace")
                for child in sorted_entries[i + 1:]:
                    offset_in_parent = child["str_addr"] - parent["str_addr"]
                    if offset_in_parent <= 0 or offset_in_parent >= len(parent_bytes): continue
                    expected = parent_bytes[offset_in_parent:]
                    child_bytes = child["text"].encode("latin-1", errors="replace")
                    if child_bytes == expected:
                        child["_shared_parent"] = parent; child["_shared_offset"] = offset_in_parent
                    elif child.get("_shared_parent") is parent:
                        child.pop("_shared_parent", None); child.pop("_shared_offset", None)

        overflow_groups = [g for g in groups
                           if sum(len(e["text"].encode("latin-1", errors="replace")) + 1
                                  for e in g["entries"] if not e.get("_shared_parent")) > g["size"]]

        if overflow_groups:
            self.overflow_entry_indices = {self.entries.index(e) for g in overflow_groups for e in g["entries"]}
            self.refresh_table()
            deficit = sum(sum(len(e["text"].encode("latin-1", errors="replace")) + 1
                              for e in g["entries"] if not e.get("_shared_parent")) - g["size"]
                          for g in overflow_groups)
            messagebox.showerror("Not Enough Space", f"Strings highlighted in red don't fit the available space.\nShorten them by {deficit} bytes.")
            return False

        self.overflow_entry_indices.clear()

        for g in groups:
            range_start, range_end = g["start"], g["end"]
            self.exe_data[range_start:range_end] = b'\x00' * (range_end - range_start)
            for e in g["entries"]: e.pop("str_addr_fixed", None)

            writable = sorted((e for e in g["entries"] if not e.get("_shared_parent")), key=lambda e: e["str_addr"])
            write_ptr = range_start

            def write_pointers_for(entry, addr):
                new_ptr_val = self.offset_to_ptr(addr)
                base_const  = entry.get("ptr_base_const", self.profile["base_const"])
                for ptr_addr in entry["ptr_addrs"]:
                    struct.pack_into("<H", self.exe_data, ptr_addr, new_ptr_val)
                    self.exe_data[ptr_addr + 2:ptr_addr + 4] = base_const
                for code_addr in entry.get("code_ptr_addrs", []):
                    struct.pack_into("<H", self.exe_data, code_addr, new_ptr_val)
                    self.exe_data[code_addr + 3:code_addr + 5] = base_const

            for e in writable:
                b        = e["text"].encode("latin-1", errors="replace") + b"\x00"
                new_addr = write_ptr
                self.exe_data[new_addr:new_addr + len(b)] = b
                write_ptr += len(b)
                write_pointers_for(e, new_addr)
                e["str_addr"] = new_addr; e["slot_len"] = len(b)

                reconnected = True
                while reconnected:
                    reconnected = False
                    for child in g["entries"]:
                        parent_ref = child.get("_shared_parent")
                        if parent_ref is None or "str_addr_fixed" in child: continue
                        if parent_ref is e or parent_ref.get("str_addr_fixed"):
                            child_addr = parent_ref["str_addr"] + child["_shared_offset"]
                            write_pointers_for(child, child_addr)
                            child["str_addr"] = child_addr
                            child["slot_len"] = parent_ref["slot_len"] - child["_shared_offset"]
                            child["str_addr_fixed"] = True
                            reconnected = True
                e["str_addr_fixed"] = True

        self._recalculate_max_lengths()
        self.update_free_space_label()
        return True

    def _reselect_current(self):
        if self.current_index is None: return
        try:
            disp_idx = self.displayed_indices.index(self.current_index)
            row_id   = str(disp_idx)
            if self.tree.exists(row_id):
                self.tree.selection_set(row_id)
                self.tree.see(row_id)
        except ValueError:
            pass

    def detect_profile(self, data):
        best_name, best_count = None, 0
        for name, prof in GAME_PROFILES.items():
            expected = prof["base_const"]
            count    = sum(1 for s, e in prof["ptr_ranges"]
                           for addr in range(s, e - 3, 4)
                           if addr + 4 <= len(data) and bytes(data[addr + 2:addr + 4]) == expected)
            if count > best_count:
                best_count, best_name = count, name
        return best_name or self.profile_name

    def _reset_state(self):
        self.exe_data               = bytearray()
        self.entries                = []
        self.displayed_indices      = []
        self.current_index          = None
        self.overflow_entry_indices = set()
        self.profile_name           = DEFAULT_PROFILE_NAME
        self.profile                = GAME_PROFILES[self.profile_name]
        self.search_var.set("")
        self.tree.delete(*self.tree.get_children())
        for widget in (self.edit_text, self.translate_text):
            widget.config(state=tk.NORMAL, bg="#FFFFFF")
            widget.delete("1.0", tk.END)
            widget.config(height=1)
        self.space_stats_label.config(text="")
        self.translate_status_label.config(text="")
        self.profile_label.config(text="—")
        self.filename_label.config(text="")
        self.status_label.config(text="No file loaded.")
        if hasattr(self, "current_range_label"):
            self.current_range_label.config(text="")

    def load_exe(self):
        filepath = filedialog.askopenfilename(filetypes=[("DOS Executable", "*.exe"), ("All Files", "*.*")])
        if not filepath: return
        self._reset_state()
        with open(filepath, "rb") as f:
            raw_data = bytearray(f.read())
        self.exe_data     = unpack_in_memory(raw_data)
        detected          = self.detect_profile(self.exe_data)
        self.profile_name = detected
        self.profile      = GAME_PROFILES[detected]
        self.profile_label.config(text=detected)
        self.filename_label.config(text=f"({os.path.basename(filepath)})")

        gcfg = self._game_cfg()
        for k, v in self.profile.get("range_font_defaults", {}).items():
            gcfg["range_font_defaults"].setdefault(str(k), v)

        font_names = list(EXE_FONT_PROFILES[detected]["fonts"].keys()) if detected in EXE_FONT_PROFILES else ["FLOW.FON", "NORMAL.FON", "MICRO4.FON"]
        self.string_font_combo.config(values=font_names)
        self.string_font_var.set(gcfg["range_font_defaults"].get("0", "FLOW.FON"))
        self.scan_reverse()

        if hasattr(self, "font_editor"):
            self.font_editor.load_from_raw(self.exe_data, detected)

    def save_exe(self):
        if not self.exe_data: return
        filepath = filedialog.asksaveasfilename(defaultextension=".exe", filetypes=[("DOS Executable", "*.exe")])
        if not filepath: return
        with open(filepath, "wb") as f:
            f.write(self.exe_data)
        messagebox.showinfo("Save Complete", f"Executable saved to:\n{filepath}")

__all__ = ['DOSTranslationEditor']
import copy
import hashlib
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from exe_handler import unpack_in_memory, get_mz_relocation_sites, GAME_PROFILES, EXE_FONT_PROFILES
from charmap import CharmapEncodeError, charmap_decode, charmap_encode
from translator import CONTROL_TOKEN_PATTERN, translate_string, TRANSLATION_ENGINES
from utils import (load_config, save_config, get_game_config, DATA_DIR, set_translator as _set_utils_translator)
import i18n
from font_editor import EXEFontEditor
from font_safety import FontSafetyError, atomic_save_bytes, paths_equal, validate_all_fonts
import extended_layout
from mana_editor import ManaEditorPanel
from vga_editor import PicEditorPanel
import newspaper_csv
from newspaper_grammar import NewspaperGrammarError
import newspaper_editor as _ne
from repack_validator import build_reference_inventory, find_unknown_gaps, make_string_id, repack_transaction, validate_image
from string_exchange import (
    StringExchangeError,
    build_export_document,
    export_json_bytes,
    preflight_import_json,
    raw_to_exchange_text,
    stage_import_transaction,
)
from diff_preview import (
    DiffPreviewError,
    PreviewCache,
    build_diff_preview,
    reconstruct_baseline_entries,
    selected_string_status,
)
from search_filter import (
    CHANGE_FILTERS,
    KIND_FILTERS,
    STATUS_FILTERS,
    SearchFilterError,
    build_filter_records,
    filter_string_ids,
)

APP_VERSION = "2.8.2"
APP_TITLE = f"THE MANAGER / Bundesliga Manager Professional Editor v{APP_VERSION} ——— by TheRuler76 & Nobody"
DEFAULT_LANGUAGE = "en"
ICON_FILE = "THE_MANAGER_String_Editor.ico"


class TextTransactionError(RuntimeError):
    pass

def _canonical_mz_relocation_topology(data):
    if len(data) < 0x1C or bytes(data[:2]) != b"MZ":
        raise ValueError("Not a complete MZ image")
    header_size = int.from_bytes(data[0x08:0x0A], "little") * 16
    relocation_count = int.from_bytes(data[0x06:0x08], "little")
    relocation_offset = int.from_bytes(data[0x18:0x1A], "little")
    relocation_end = relocation_offset + relocation_count * 4
    if (
        header_size < 0x1C
        or header_size > len(data)
        or relocation_offset < 0x1C
        or relocation_end > header_size
    ):
        raise ValueError("Invalid MZ relocation table layout")

    pairs = []
    for pos in range(relocation_offset, relocation_end, 4):
        offset = int.from_bytes(data[pos:pos + 2], "little")
        segment = int.from_bytes(data[pos + 2:pos + 4], "little")
        site = header_size + segment * 16 + offset
        if site < header_size or site + 2 > len(data):
            raise ValueError("MZ relocation source outside image")
        pairs.append((segment, offset))

    canonical = b"".join(
        segment.to_bytes(2, "little") + offset.to_bytes(2, "little")
        for segment, offset in sorted(pairs)
    )
    return {
        "header_size": header_size,
        "relocation_count": relocation_count,
        "relocation_offset": relocation_offset,
        "sha256": hashlib.sha256(canonical).hexdigest().upper(),
    }


def _match_immutable_code_anchor(data, header_size, anchor):
    image_offset, pattern_text = anchor
    tokens = pattern_text.split()
    wildcard_offsets = tuple(i for i, token in enumerate(tokens) if token == "??")
    if wildcard_offsets != (9, 10):
        return False
    try:
        expected = tuple(None if token == "??" else int(token, 16) for token in tokens)
    except ValueError:
        return False
    if any(value is not None and not 0 <= value <= 0xFF for value in expected):
        return False
    start = header_size + image_offset
    end = start + len(expected)
    if start < header_size or end > len(data):
        return False
    return all(value is None or data[start + index] == value for index, value in enumerate(expected))


def _matches_immutable_profile(data, profile, verbose=False, collect=False):
    lines = []
    def emit(msg):
        if collect:
            lines.append(msg)
        elif verbose:
            print(msg)
    pname = profile.get("profile_name", "?") if isinstance(profile, dict) else "?"
    signature = profile.get("immutable_signature")
    if not signature:
        emit(f"[detect:{pname}] FAIL: no immutable_signature")
        return (False, lines) if collect else False
    anchors = signature.get("code_anchors", ())
    if len(anchors) != 3:
        emit(f"[detect:{pname}] FAIL: expected 3 anchors, got {len(anchors)}")
        return (False, lines) if collect else False
    try:
        topology = _canonical_mz_relocation_topology(data)
    except (TypeError, ValueError) as exc:
        emit(f"[detect:{pname}] FAIL: _canonical_mz_relocation_topology raised {exc}")
        return (False, lines) if collect else False
    expected_sha = signature["relocation_topology_sha256"]
    sha_ok = (topology["sha256"] == expected_sha) if isinstance(expected_sha, str) \
             else (topology["sha256"] in expected_sha)
    checks = [
        ("header_size",       topology["header_size"],       signature["header_size"]),
        ("relocation_offset", topology["relocation_offset"], signature["relocation_table_offset"]),
        ("relocation_count",  topology["relocation_count"],  signature["relocation_count"]),
        ("reloc_sha256",      sha_ok,                        True),
        ("entry_cs (0x16)",   int.from_bytes(data[0x16:0x18], "little"), signature["entry_cs"]),
        ("entry_ip (0x14)",   int.from_bytes(data[0x14:0x16], "little"), signature["entry_ip"]),
    ]
    failed = False
    for name, got, expected in checks:
        ok = got == expected
        if name == "reloc_sha256":
            if ok:
                status = f"ok  ({topology['sha256']})"
            else:
                expected_list = [expected_sha] if isinstance(expected_sha, str) else list(expected_sha)
                status = f"FAIL  got={topology['sha256']}  expected={expected_list}"
        else:
            got_s      = got      if isinstance(got, str)  else hex(got)
            expected_s = expected if isinstance(expected, str) else hex(expected)
            status = "ok" if ok else f"FAIL  got={got_s}  expected={expected_s}"
        emit(f"[detect:{pname}]   {name}: {status}")
        if not ok:
            failed = True
    if failed:
        return (False, lines) if collect else False
    for i, anchor in enumerate(anchors):
        ok = _match_immutable_code_anchor(data, topology["header_size"], anchor)
        img_off  = anchor[0]
        file_off = topology["header_size"] + img_off
        status   = "ok" if ok else f"FAIL  file_offset={hex(file_off)}  img_offset={hex(img_off)}"
        emit(f"[detect:{pname}]   anchor[{i}] @ img {hex(img_off)}: {status}")
        if not ok:
            return (False, lines) if collect else False
    emit(f"[detect:{pname}] MATCH")
    return (True, lines) if collect else True


class DOSTranslationEditor:

    _YEAR_MIN = 1900
    _YEAR_MAX = 2099
    _YEAR_DISP = {
        "THE MANAGER (ENGLISH)":           0x07CC,
        "BUNDESLIGA MANAGER PROFESSIONAL": 0x07E0,
        "THE MANAGER (ITALIAN)":           0x07E0,
    }
    _REGION_VARIANTS = (
        ("region.1", (1, 1)),   # German
        ("region.2", (2, 1)),   # Italian
        ("region.3", (1, 3)),   # French
        ("region.4", (4, 1)),   # English
    )
    _REGION_DISP = {
        "THE MANAGER (ENGLISH)":           0x122E,
        "BUNDESLIGA MANAGER PROFESSIONAL": 0x224E,
        "THE MANAGER (ITALIAN)":           0x13AA,
    }

    _POINTS_RULE = {
        "THE MANAGER (ENGLISH)":           0x1251,
        "BUNDESLIGA MANAGER PROFESSIONAL": 0x2271,
        "THE MANAGER (ITALIAN)":           0x13CD,
    }
    
    
    def __init__(self, root):
        self.root = root
        self.language = DEFAULT_LANGUAGE
        self.filter_status_key = None
        self.filter_status_args = {}
        self._status_state = ("header.no_file", {})
        self._profile_state = ("header.profile_none", None, "#2980B9")
        self.root.title(APP_TITLE)
        self._apply_window_icon()
        self.root.geometry("1280x800")
        self.root.minsize(780, 600)
        self.exe_data              = bytearray()
        self.entries               = []
        self.visible_string_ids    = []
        self.entry_index_by_id     = {}
        self.current_index         = None
        self.profile_name          = None
        self.profile               = None
        self.is_supported          = False
        self.relocation_sites      = []
        self.integrity_valid       = False
        self.repack_required       = False
        self.validation_errors     = []
        self.source_path           = None
        self.original_source_data  = bytearray()
        self.initial_unpacked_data = bytearray()
        self.last_saved_exe_data   = bytearray()
        self.font_valid            = False
        self.font_pending          = False
        self.font_errors           = []
        self.translation_pending   = False
        self._last_valid_year      = None
        self._last_valid_region_index = None
        self._last_valid_points    = None
        self._converted_to_extended = False
        self.diff_preview_cache    = PreviewCache()
        self.filter_records        = ()
        self.filter_records_by_id  = {}
        self.baseline_filter_data  = {}
        self.filter_refresh_pending = False
        self.filter_records_dirty  = True
        self.filter_index_error    = None
        self._filter_callbacks_suspended = False
        self._selection_guard      = False
        self._free_space_after_id  = None
        self._free_space_override  = None
        self._apply_modern_style()
        self._init_language()
        self.cfg = load_config()
        self._build_gui()

    def _init_language(self):
        i18n.set_language(self.language)
        _set_utils_translator(i18n.tr)
        self._languages = i18n.discover_languages()
        self._language_codes = {code for code, _ in self._languages}
        problems = i18n.take_problems()
        if problems:
            messagebox.showwarning(self.tr("menu.view.language"),"\n".join(problems))

    def tr(self, key, **fmt):
        return i18n.tr(key, **fmt)

    @staticmethod
    def _resource_path(relative):
        base = getattr(sys, "_MEIPASS", None)
        if not base:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, relative)

    def _apply_window_icon(self):
        try:
            self.root.iconbitmap(
                default=self._resource_path(os.path.join("assets", ICON_FILE))
            )
        except Exception:
            pass

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

    def _build_menu(self):
        self.menubar = tk.Menu(self.root, tearoff=0)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label=self.tr("menu.file.open"), command=self.load_exe)
        file_menu.add_command(label=self.tr("menu.file.save_as"), command=self.save_exe)
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("menu.file.quit"), command=self._on_close_request)
        self.menubar.add_cascade(label=self.tr("menu.file"), menu=file_menu)
        self.file_menu = file_menu
        tools_menu = tk.Menu(self.menubar, tearoff=0)
        tools_menu.add_command(label=self.tr("menu.tools.details"), command=self.show_changes_preview)
        tools_menu.add_separator()
        tools_menu.add_command(label=self.tr("menu.tools.export"), command=self.export_strings)
        tools_menu.add_command(label=self.tr("menu.tools.import"), command=self.import_strings)
        tools_menu.add_separator()
        tools_menu.add_command(label=self.tr("menu.tools.news_export"),command=self.export_newspaper_csv)
        tools_menu.add_command(label=self.tr("menu.tools.news_import"),command=self.import_newspaper_csv)
        tools_menu.add_separator()
        tools_menu.add_checkbutton(label=self.tr("menu.tools.autotranslate"),variable=self.translate_enabled_var,command=self.on_translate_toggle,)
        tools_menu.add_command(label=self.tr("menu.tools.translate_all"), command=self.translate_all)
        self.menubar.add_cascade(label=self.tr("menu.tools"), menu=tools_menu)
        self.tools_menu = tools_menu
        view_menu = tk.Menu(self.menubar, tearoff=0)
        view_menu.add_command(label=self.tr("menu.view.strings"),command=lambda: self._select_tab("tab_strings"))
        view_menu.add_command(label=self.tr("menu.view.fonts"),command=lambda: self._select_tab("tab_fonts"))
        view_menu.add_command(label="MANA.DAT Editor", command=lambda: self._select_tab("tab_mana"))
        view_menu.add_command(label="VGA Editor", command=lambda: self._select_tab("tab_vga"))
        view_menu.add_separator()
        lang_menu = tk.Menu(view_menu, tearoff=0)
        self.language_var = tk.StringVar(value=self.language)
        for code, name in self._languages:
            lang_menu.add_radiobutton(
                label=name, value=code, variable=self.language_var,
                command=self._on_language_change,
            )
        view_menu.add_cascade(label=self.tr("menu.view.language"), menu=lang_menu)
        self.menubar.add_cascade(label=self.tr("menu.view"), menu=view_menu)
        self.view_menu = view_menu
        self.language_menu = lang_menu
        self.save_menu_entries = [(file_menu, 1)]
        self.exchange_menu_entries = [(tools_menu, 2), (tools_menu, 3),
                                      (tools_menu, 5), (tools_menu, 6)]
        self.supported_menu_entries = [
            (tools_menu, 0), (tools_menu, 8), (tools_menu, 9),
            (view_menu, 0), (view_menu, 1), (view_menu, 2), (view_menu, 3) 
        ]
        self.root.config(menu=self.menubar)

    def _retranslate_menu(self):
        for index, key in ((0, "menu.file"), (1, "menu.tools"), (2, "menu.view")):
            try:
                self.menubar.entryconfig(index, label=self.tr(key))
            except tk.TclError:
                pass
        for menu, items in (
            (self.file_menu, ((0, "menu.file.open"), (1, "menu.file.save_as"),
                              (3, "menu.file.quit"))),
            (self.tools_menu, ((0, "menu.tools.details"), (2, "menu.tools.export"),
                               (3, "menu.tools.import"), (5, "menu.tools.news_export"),
                               (6, "menu.tools.news_import"), (8, "menu.tools.autotranslate"),
                               (9, "menu.tools.translate_all"))),
            (self.view_menu, ((0, "menu.view.strings"), (1, "menu.view.fonts"),
                              (3, "menu.view.language"))),
        ):
            for index, key in items:
                try:
                    menu.entryconfig(index, label=self.tr(key))
                except tk.TclError:
                    pass

    @staticmethod
    def _set_menu_state(entries, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        for menu, index in entries:
            try:
                menu.entryconfig(index, state=state)
            except tk.TclError:
                pass

    def _reg(self, widget, key):
        widget.config(text=self.tr(key))
        self._i18n_widgets.append((widget, key))
        return widget

    def _reg_tab(self, tab, key):
        self._i18n_tabs.append((tab, key))
        return tab

    def _set_filter_status(self, key, **fmt):
        self.filter_status_key = key
        self.filter_status_args = dict(fmt)
        if key is None:
            self.filter_status_label.config(text="")
            return
        colour = "#C0392B" if key == "status.filter_unavailable" else "#B9770E"
        self.filter_status_label.config(text=self.tr(key, **fmt), foreground=colour)

    def _set_status(self, key, **fmt):
        self._status_state = (key, dict(fmt))
        self._render_header()

    def _set_profile(self, key=None, value=None, colour="#2980B9"):
        self._profile_state = (key, value, colour)
        self._render_header()

    def _render_header(self):
        key, fmt = self._status_state
        self.status_label.config(text=self.tr(key, **fmt))
        key, value, colour = self._profile_state
        self.profile_label.config(text=self.tr(key) if key else value, foreground=colour)

    def _set_counter(self, shown, total):
        self.showing_label.config(
            text=self.tr("status.counter", shown=shown, total=total), foreground="#2980B9"
        )
        self._counter_state = (shown, total)

    def _on_language_change(self):
        chosen = self.language_var.get()
        if chosen not in self._language_codes or chosen == self.language:
            return
        self.language = chosen
        i18n.set_language(chosen)
        self._retranslate_menu()
        for widget, key in self._i18n_widgets:
            try:
                widget.config(text=self.tr(key))
            except tk.TclError:
                pass
        for tab, key in self._i18n_tabs:
            try:
                self.notebook.tab(tab, text=self.tr(key))
            except tk.TclError:
                pass
        for name, key in (("num", "col.num"), ("offset", "col.offset"), ("text", "col.text")):
            try:
                self.tree.heading(name, text=self.tr(key))
            except tk.TclError:
                pass
        self.filter_toggle_button.config(
            text=self.tr("filter.toggle_open" if self.filter_frame.winfo_manager()
                         else "filter.toggle_closed")
        )
        shown, total = self._counter_state
        self._set_counter(shown, total)
        self._set_filter_status(self.filter_status_key, **self.filter_status_args)
        if self._region_offset() is not None:
            index = self.region_combo.current()
            self.region_combo.config(values=self._region_values())
            if index >= 0:
                self.region_combo.current(index)
        self._render_header()
        font_editor = getattr(self, "font_editor", None)
        if font_editor is not None:
            font_editor.retranslate()

    def _select_tab(self, tab_attr):
        tab = getattr(self, tab_attr, None)
        if tab is None:
            return
        try:
            self.notebook.select(tab)
        except tk.TclError:
            pass

    def _toggle_filters(self):
        if self.filter_frame.winfo_manager():
            self.filter_frame.pack_forget()
            self.filter_toggle_button.config(text=self.tr("filter.toggle_closed"))
        else:
            self.filter_frame.pack(fill=tk.X, after=self.search_frame)
            self.filter_toggle_button.config(text=self.tr("filter.toggle_open"))

    def _build_gui(self):
        self.supported_controls = []
        self._i18n_widgets = []
        self._i18n_tabs = []
        self._counter_state = (0, 0)
        self.translate_enabled_var = tk.BooleanVar(value=False)
        self.root.configure(bg="#F4F6F9")
        self._build_menu()
        top_frame = ttk.Frame(self.root, padding=(15, 10, 15, 4))
        top_frame.pack(fill=tk.X)
        self.load_button = ttk.Button(top_frame, command=self.load_exe)
        self._reg(self.load_button, "header.choose_exe")
        self.load_button.pack(side=tk.LEFT, padx=(0, 8))
        self.save_button = ttk.Button(top_frame, command=self.save_exe)
        self._reg(self.save_button, "header.save_as")
        self.save_button.pack(side=tk.LEFT, padx=(0, 18))
        self._reg(ttk.Label(top_frame, font=("Segoe UI", 9, "bold")), "header.profile").pack(side=tk.LEFT, padx=(0, 4))
        self.profile_label  = ttk.Label(top_frame, font=("Segoe UI", 9, "bold"))
        self.profile_label.pack(side=tk.LEFT)
        self.filename_label = ttk.Label(top_frame, text="", font=("Segoe UI", 9, "italic"), foreground="#7F8C8D")
        self.filename_label.pack(side=tk.LEFT, padx=(8, 0))
        self.year_label = self._reg(ttk.Label(top_frame, font=("Segoe UI", 9, "bold")),"header.year")
        self.year_label.pack(side=tk.LEFT, padx=(18, 4))
        self.year_var = tk.StringVar()
        self.year_spinbox = ttk.Spinbox(
            top_frame, from_=self._YEAR_MIN, to=self._YEAR_MAX, increment=1,
            width=4, justify=tk.CENTER, font=("Segoe UI", 9),
            textvariable=self.year_var, command=self._commit_year,
        )
        self.year_spinbox.pack(side=tk.LEFT)
        self.year_spinbox.bind("<Return>", self._commit_year)
        self.year_spinbox.bind("<KP_Enter>", self._commit_year)
        self.year_spinbox.bind("<FocusOut>", self._commit_year)
        self.region_label = self._reg(ttk.Label(top_frame, font=("Segoe UI", 9, "bold")),"header.region")
        self.region_label.pack(side=tk.LEFT, padx=(18, 4))
        self.region_var = tk.StringVar()
        self.region_combo = ttk.Combobox(top_frame, textvariable=self.region_var, state="readonly",width=8, justify=tk.LEFT, font=("Segoe UI", 9),)
        self.region_combo.pack(side=tk.LEFT)
        self.region_combo.bind("<<ComboboxSelected>>", self._commit_region)
        self.points_label = self._reg(ttk.Label(top_frame, font=("Segoe UI", 9, "bold")),"header.point")
        self.points_label.pack(side=tk.LEFT, padx=(18, 4))
        self.points_var = tk.StringVar()
        self.points_combo = ttk.Combobox(
            top_frame, textvariable=self.points_var, state="readonly",
            width=2, justify=tk.CENTER, font=("Segoe UI", 9),
            values=["2", "3"],
        )
        self.points_combo.pack(side=tk.LEFT)
        self.points_combo.bind("<<ComboboxSelected>>", self._commit_points)
        self.points_combo.bind("<Return>", self._commit_points)
        self.points_combo.bind("<KP_Enter>", self._commit_points)
        self.points_combo.bind("<FocusOut>", self._commit_points)
        self.status_label   = ttk.Label(top_frame, font=("Segoe UI", 9, "italic"))
        self.status_label.pack(side=tk.RIGHT)
        self._render_header()
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=(10, 3))
        style.map("TNotebook.Tab",
                  font=[("selected", ("Segoe UI", 9, "bold"))],
                  padding=[("selected", (10, 4))])
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.tab_strings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_strings, text=self.tr("tab.strings"))
        self._reg_tab(self.tab_strings, "tab.strings")
        self.search_frame = ttk.Frame(self.tab_strings, padding=(15, 10, 15, 4))
        self.search_frame.pack(fill=tk.X)
        self._reg(ttk.Label(self.search_frame, font=("Segoe UI", 10, "bold")),"filter.search").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.search_entry.bind("<Escape>", lambda event: [self.clear_filters(), "break"][1])
        self.showing_label = ttk.Label(
            self.search_frame,
            text=self.tr("status.counter", shown=0, total=0),
            font=("Segoe UI", 9, "bold"),
            foreground="#2980B9",
        )
        self.showing_label.pack(side=tk.RIGHT, padx=(10, 0))
        self.filter_toggle_button = ttk.Button(self.search_frame, text=self.tr("filter.toggle_closed"), width=12,command=self._toggle_filters)
        self.filter_toggle_button.pack(side=tk.RIGHT)
        self.filter_frame = ttk.Frame(self.tab_strings, padding=(15, 0, 15, 4))
        self.kind_filter_var = tk.StringVar(value="All")
        self.font_filter_var = tk.StringVar(value="All")
        self.change_filter_var = tk.StringVar(value="All")
        self.status_filter_var = tk.StringVar(value="All")
        filter_specs = (
            ("filter.kind", self.kind_filter_var, KIND_FILTERS, 14),
            ("filter.font", self.font_filter_var, ("All",), 15),
            ("filter.change", self.change_filter_var, CHANGE_FILTERS, 12),
            ("filter.status", self.status_filter_var, STATUS_FILTERS, 13),
        )
        self.filter_combos = []
        for label, variable, values, width in filter_specs:
            self._reg(ttk.Label(self.filter_frame, font=("Segoe UI", 9, "bold")), label).pack(
                side=tk.LEFT, padx=(0 if not self.filter_combos else 10, 3)
            )
            combo = ttk.Combobox(
                self.filter_frame,
                textvariable=variable,
                values=values,
                state="readonly",
                width=width,
            )
            combo.pack(side=tk.LEFT)
            combo.bind("<<ComboboxSelected>>", self.on_filter_change)
            self.filter_combos.append(combo)
        self.clear_filters_button = ttk.Button(self.filter_frame, command=self.clear_filters)
        self._reg(self.clear_filters_button, "filter.reset")
        self.clear_filters_button.pack(side=tk.RIGHT)
        self.search_var.trace_add("write", self.on_search_change)
        self.supported_controls.extend((self.search_entry, self.clear_filters_button, self.filter_toggle_button,*self.filter_combos))
        status_frame = ttk.Frame(self.tab_strings, padding=(15, 0, 15, 4))
        status_frame.pack(fill=tk.X)
        self.filter_status_label = ttk.Label(status_frame, text="", font=("Segoe UI", 9, "bold"), foreground="#B9770E")
        self.filter_status_label.pack(side=tk.LEFT)
        main_frame = ttk.Frame(self.tab_strings, padding=(15, 0, 15, 8))
        main_frame.pack(fill=tk.BOTH, expand=True)
        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_container, columns=("num", "offset", "text"), show="headings", selectmode="browse")
        self.tree.heading("num",    text=self.tr("col.num"))
        self.tree.heading("offset", text=self.tr("col.offset"))
        self.tree.heading("text",   text=self.tr("col.text"))
        self.tree.column("num",    anchor=tk.CENTER, width=30,  stretch=False)
        self.tree.column("offset", anchor=tk.CENTER, width=60, stretch=False)
        self.tree.column("text",   anchor=tk.W,      stretch=True)
        v_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        edit_frame = ttk.LabelFrame(self.tab_strings, padding=15)
        self._reg(edit_frame, "edit.frame")
        edit_frame.pack(fill=tk.X, padx=15, pady=(5, 12))
        self.edit_text = self._make_text_widget(edit_frame)
        self.edit_text.bind("<KeyRelease>", self.on_text_modified)
        self.edit_text.bind("<Return>",         lambda e: [self.apply_edit(), "break"][1])
        self.edit_text.bind("<Control-Return>",  lambda e: [self.apply_edit(), "break"][1])
        info_frame = ttk.Frame(edit_frame)
        info_frame.pack(fill=tk.X)
        self.current_range_label = ttk.Label(info_frame, text="", font=("Segoe UI", 9, "bold"), foreground="#27AE60")
        self.current_range_label.pack(side=tk.LEFT)
        self.space_stats_label = ttk.Label(info_frame, text="", font=("Segoe UI", 9, "italic"), foreground="#2980B9")
        self.space_stats_label.pack(side=tk.RIGHT)
        ctrl_row = ttk.Frame(edit_frame)
        ctrl_row.pack(fill=tk.X, pady=(10, 0))
        self.apply_edit_button = ttk.Button(ctrl_row, command=self.apply_edit)
        self._reg(self.apply_edit_button, "edit.apply")
        self.apply_edit_button.pack(side=tk.RIGHT)
        self.discard_edit_button = ttk.Button(ctrl_row, command=self.discard_edit)
        self._reg(self.discard_edit_button, "edit.discard")
        self.discard_edit_button.pack(side=tk.RIGHT, padx=(0, 6))
        self.supported_controls.extend((self.apply_edit_button, self.discard_edit_button))
        self.newspaper_editor_var = tk.BooleanVar(value=True)
        self.newspaper_editor_check = ttk.Checkbutton(ctrl_row, variable=self.newspaper_editor_var,command=self.on_newspaper_editor_toggle)
        self._reg(self.newspaper_editor_check, "action.newspaper_editor")
        self.newspaper_editor_check.pack(side=tk.LEFT, padx=(10, 0))
        self.translate_enabled_check = ttk.Checkbutton(ctrl_row, variable=self.translate_enabled_var, command=self.on_translate_toggle)
        self._reg(self.translate_enabled_check, "action.translation")
        self.translate_enabled_check.pack(side=tk.LEFT)
        self.preview_button = ttk.Button(ctrl_row, command=self.show_changes_preview)
        self._reg(self.preview_button, "action.details")
        self.preview_button.pack(side=tk.LEFT, padx=(10, 0))
        self.export_strings_button = ttk.Button(ctrl_row, command=self.export_strings)
        self._reg(self.export_strings_button, "action.export")
        self.export_strings_button.pack(side=tk.LEFT, padx=(6, 0))
        self.import_strings_button = ttk.Button(ctrl_row, command=self.import_strings)
        self._reg(self.import_strings_button, "action.import")
        self.import_strings_button.pack(side=tk.LEFT, padx=(6, 0))
        self.font_assign_button = ttk.Button(ctrl_row, command=self._goto_font_assign)
        self._reg(self.font_assign_button, "action.font_assign")
        self.font_assign_button.pack(side=tk.LEFT, padx=(6, 0))
        self.supported_controls.extend((
            self.newspaper_editor_check,
            self.translate_enabled_check,
            self.preview_button,
            self.export_strings_button,
            self.import_strings_button,
            self.font_assign_button,
        ))
        self.translate_section = ttk.Frame(edit_frame)
        translation_options_row = ttk.Frame(self.translate_section)
        translation_options_row.pack(fill=tk.X, pady=(8, 0))
        for label, var_attr, values, width, on_change in [
            ("tr.engine", "engine_var",      list(TRANSLATION_ENGINES.keys()), 18, lambda e: self.translate_current()),
            ("tr.from",   "source_lang_var", ["auto","de","en","fr","es","it"], 6,  lambda e: self.translate_current()),
            ("tr.to",     "target_lang_var", ["it","en","de","fr","es"],        6,  lambda e: self.translate_current()),
        ]:
            self._reg(ttk.Label(translation_options_row), label).pack(
                side=tk.LEFT, padx=(0 if label == "tr.engine" else 8, 3))
            var = tk.StringVar(value=values[0])
            setattr(self, var_attr, var)
            combo = ttk.Combobox(translation_options_row, textvariable=var, state="readonly", width=width, values=values)
            combo.pack(side=tk.LEFT, padx=(0, 8))
            combo.bind("<<ComboboxSelected>>", on_change)
            self.supported_controls.append(combo)
        self.engine_var.set("Google Translate")
        self.source_lang_var.set("auto")
        self.target_lang_var.set("it")
        self.translate_all_button = ttk.Button(translation_options_row, command=self.translate_all)
        self._reg(self.translate_all_button, "tr.all")
        self.translate_all_button.pack(side=tk.RIGHT)
        self.supported_controls.append(self.translate_all_button)
        self.translate_status_label = ttk.Label(translation_options_row, text="", font=("Segoe UI", 9, "italic"), foreground="#7F8C8D")
        self.translate_status_label.pack(side=tk.LEFT, padx=(4, 0))
        translate_header = ttk.Frame(self.translate_section)
        translate_header.pack(fill=tk.X, pady=(6, 4))
        self._reg(ttk.Label(translate_header, font=("Segoe UI", 9, "bold")),"tr.translated").pack(side=tk.LEFT)
        self.apply_translation_button = ttk.Button(translate_header, command=self.apply_translation)
        self._reg(self.apply_translation_button, "tr.apply")
        self.apply_translation_button.pack(side=tk.RIGHT)
        self.supported_controls.append(self.apply_translation_button)
        self.translate_text = self._make_text_widget(self.translate_section, bg="#FDFEFE")
        self.translate_text.bind("<KeyRelease>",        self.on_translate_text_modified)
        self.translate_text.bind("<Return>",            lambda e: [self.apply_translation(), "break"][1])
        self.translate_text.bind("<Control-Return>",    lambda e: [self.apply_translation(), "break"][1])
        self.newspaper_panel = _ne.NewspaperEditorPanel(edit_frame, self)
        self.tab_fonts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_fonts, text=self.tr("tab.fonts"))
        self._reg_tab(self.tab_fonts, "tab.fonts")
        self.font_editor = EXEFontEditor(
            self.tab_fonts,
            get_exe_data=lambda: self.exe_data,
            on_charmap_changed=self._on_charmap_changed,
            on_font_state_changed=self._on_font_state_changed,
            can_change_charmap=self._can_change_charmap,
            on_string_font_change=self._on_string_font_change,
            translate=self.tr,
        )
        self.tab_mana = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_mana, text="MANA.DAT")
        self.mana_editor_panel = ManaEditorPanel(self.tab_mana)
        self.mana_editor_panel.pack(fill=tk.BOTH, expand=True)
        self.tab_vga = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_vga, text="VGA Editor")
        self.vga_editor = PicEditorPanel(self.tab_vga, standalone=False)
        self.vga_editor.pack(fill=tk.BOTH, expand=True)
        self._set_supported_state(False)
        self.notebook.select(self.tab_strings)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _set_supported_state(self, supported: bool):
        self.is_supported = bool(supported and self.profile_name and self.profile and self.exe_data)
        state = tk.NORMAL if self.is_supported else tk.DISABLED
        if hasattr(self, "save_button"):
            self.save_button.config(state=tk.NORMAL if self._can_save() else tk.DISABLED)
        if hasattr(self, "notebook"):
            for tab in (getattr(self, "tab_strings", None), getattr(self, "tab_fonts", None),
                        getattr(self, "tab_mana", None), getattr(self, "tab_vga", None)):
                if tab is not None:
                    self.notebook.tab(tab, state=state)
        self._set_menu_state(getattr(self, "supported_menu_entries", []), self.is_supported)
        for widget in getattr(self, "supported_controls", []):
            widget_state = "readonly" if self.is_supported and isinstance(widget, ttk.Combobox) else state
            widget.config(state=widget_state)
        for widget_name in ("edit_text", "translate_text"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.config(state=state)
        font_editor = getattr(self, "font_editor", None)
        if font_editor is not None:
            font_editor.set_enabled(self.is_supported and font_editor.is_supported)
        self._sync_year_widget()
        self._sync_region_widget()
        self._sync_points_widget()
        self._update_discard_button_state()

    def _year_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("code_year")
        if not isinstance(offset, int) or offset < 5 or offset + 2 > len(self.exe_data):
            return None
        if bytes(self.exe_data[offset - 5:offset - 2]) != b"\x26\xC7\x06":
            return None
        expected = self._YEAR_DISP.get(self.profile_name)
        if expected is None:
            return None
        if int.from_bytes(self.exe_data[offset - 2:offset], "little") != expected:
            return None
        return offset

    def _sync_year_widget(self):
        if not hasattr(self, "year_spinbox"):
            return
        if self._year_offset() is not None:
            if not self.year_label.winfo_manager():
                self.year_label.pack(side=tk.LEFT, padx=(10, 2))
                self.year_spinbox.pack(side=tk.LEFT)
            self.year_spinbox.config(state=tk.NORMAL)
            return
        self.year_spinbox.config(state=tk.DISABLED)
        self.year_label.pack_forget()
        self.year_spinbox.pack_forget()
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

    def _region_pair(self, data, offset):
        return (int.from_bytes(data[offset:offset + 4], "little"),
                int.from_bytes(data[offset + 4:offset + 8], "little"))

    def _region_index(self, pair):
        for index, (_key, variant) in enumerate(self._REGION_VARIANTS):
            if tuple(pair) == variant:
                return index
        return None

    def _region_anchor(self, disp, immediate, ds_start) -> bool:
        head = bytes((0x26, 0x83, 0x3E)) + disp.to_bytes(2, "little") + bytes([immediate])
        tail = bytes((0x26, 0x83, 0x3E)) + (disp + 2).to_bytes(2, "little") + bytes((0x00,))
        limit = min(len(self.exe_data), ds_start)
        index = self.exe_data.find(head, 0, limit)
        while index >= 0:
            probe = index + 6
            if (probe + 8 <= limit and self.exe_data[probe] == 0x75
                    and bytes(self.exe_data[probe + 2:probe + 8]) == tail):
                return True
            index = self.exe_data.find(head, index + 1, limit)
        return False

    def _region_offset(self):
        if not self._supported_loaded():
            return None
        offset = self.profile.get("region_offset")
        if not isinstance(offset, int) or offset < 0 or offset + 8 > len(self.exe_data):
            return None
        a_disp = self._REGION_DISP.get(self.profile_name)
        ds_start = self.profile.get("ds_start")
        if a_disp is None or not isinstance(ds_start, int):
            return None
        if offset - ds_start != a_disp:
            return None
        if (offset + 4) - ds_start != a_disp + 4:
            return None
        if int.from_bytes(self.exe_data[offset + 2:offset + 4], "little") != 0:
            return None
        if int.from_bytes(self.exe_data[offset + 6:offset + 8], "little") != 0:
            return None
        if self._region_pair(self.exe_data, offset) not in {
                variant for _key, variant in self._REGION_VARIANTS}:
            return None
        if not self._region_anchor(a_disp, 0x04, ds_start):
            return None
        if not self._region_anchor(a_disp + 4, 0x03, ds_start):
            return None
        return offset

    def _region_values(self):
        return [self.tr(key) for key, _variant in self._REGION_VARIANTS]

    def _sync_region_widget(self):
        if not hasattr(self, "region_combo"):
            return
        if self._region_offset() is not None:
            self.region_combo.config(values=self._region_values())
            if not self.region_label.winfo_manager():
                self.region_label.pack(side=tk.LEFT, padx=(18, 4))
                self.region_combo.pack(side=tk.LEFT)
            self.region_combo.config(state="readonly")
            return
        self.region_combo.config(state=tk.DISABLED)
        self.region_label.pack_forget()
        self.region_combo.pack_forget()
        self.region_var.set("")
        self._last_valid_region_index = None

    def _revert_region(self):
        if self._last_valid_region_index is None:
            self.region_var.set("")
        else:
            self.region_combo.current(self._last_valid_region_index)

    def _read_region_from_exe(self):
        offset = self._region_offset()
        index = None
        if offset is not None:
            index = self._region_index(self._region_pair(self.exe_data, offset))
        if index is None:
            self._last_valid_region_index = None
            self.region_var.set("")
        else:
            self.region_combo.config(values=self._region_values())
            self.region_combo.current(index)
            self._last_valid_region_index = index
        self._sync_region_widget()

    def _commit_region(self, event=None):
        offset = self._region_offset()
        if offset is None:
            return
        index = self.region_combo.current()
        if not 0 <= index < len(self._REGION_VARIANTS):
            self._revert_region()
            return
        _key, (a_value, b_value) = self._REGION_VARIANTS[index]
        payload = a_value.to_bytes(4, "little") + b_value.to_bytes(4, "little")
        if bytes(self.exe_data[offset:offset + 8]) == payload:
            self._last_valid_region_index = index
            return
        self.exe_data[offset:offset + 8] = payload
        self._last_valid_region_index = index
        self._invalidate_diff_preview("region-change")
        self._update_save_state()

    def _points_rule_offset(self):
        if not self._supported_loaded():
            return None
        disp = self._POINTS_RULE.get(self.profile_name)
        ds_start = self.profile.get("ds_start")
        if disp is None or not isinstance(ds_start, int):
            return None
        offset = ds_start + disp
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
            if not self.points_label.winfo_manager():
                self.points_label.pack(side=tk.LEFT, padx=(18, 4))
                self.points_combo.pack(side=tk.LEFT)
            self.points_combo.config(state="readonly")
            return
        self.points_combo.config(state=tk.DISABLED)
        self.points_label.pack_forget()
        self.points_combo.pack_forget()
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

    def _supported_loaded(self) -> bool:
        return bool(self.is_supported and self.profile_name and self.profile and self.exe_data)

    def _on_font_state_changed(self, state: dict):
        self.font_valid = bool(state.get("valid"))
        self.font_pending = bool(state.get("pending"))
        self.font_errors = list(state.get("errors", []))
        self._invalidate_diff_preview("font-state")
        if self.baseline_filter_data and hasattr(self, "tree"):
            self.refresh_table()
        self._update_save_state()

    def _invalidate_diff_preview(self, reason: str, *, refresh=True):
        if reason in {"text-edit", "translation-edit"}:
            if refresh and self.profile and hasattr(self, "current_range_label"):
                self._schedule_free_space_update()
            return

        self.diff_preview_cache.invalidate(reason)
        self.filter_records_dirty = True
        if refresh and self.profile and hasattr(self, "current_range_label"):
            self.update_free_space_label()

    def _cancel_free_space_update(self):
        after_id = self._free_space_after_id
        self._free_space_after_id = None
        self._free_space_override = None
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except (tk.TclError, ValueError):
                pass

    def _schedule_free_space_update(self, live_override=None, delay=350):
        if not hasattr(self, "root") or not hasattr(self, "current_range_label"):
            return
        self._free_space_override = live_override
        if self._free_space_after_id is not None:
            try:
                self.root.after_cancel(self._free_space_after_id)
            except (tk.TclError, ValueError):
                pass
        self._free_space_after_id = self.root.after(
            delay, self._run_scheduled_free_space_update
        )

    def _run_scheduled_free_space_update(self):
        self._free_space_after_id = None
        live_override = self._free_space_override
        self._free_space_override = None
        try:
            self.update_free_space_label(live_override=live_override)
        except (DiffPreviewError, KeyError, ValueError):
            pass

    def _is_edit_text_dirty(self) -> bool:
        if not self._supported_loaded() or self.current_index is None:
            return False
        panel = getattr(self, "newspaper_panel", None)
        if panel is not None and panel.winfo_ismapped():
            return False
        widget = getattr(self, "edit_text", None)
        if widget is None or str(widget.cget("state")) == "disabled":
            return False
        try:
            displayed = widget.get("1.0", "1.0 lineend")
            expected = self._decode_entry_text(self.entries[self.current_index])
            return displayed != expected
        except Exception:
            return False

    def _update_discard_button_state(self):
        button = getattr(self, "discard_edit_button", None)
        if button is None:
            return
        if self._has_pending_text_edit():
            button.config(state=tk.NORMAL)
        else:
            button.config(state=tk.DISABLED)

    def apply_edit(self):
        panel = getattr(self, "newspaper_panel", None)
        if panel is not None and panel.winfo_ismapped():
            for method_name in ("apply", "apply_edit", "apply_changes"):
                if hasattr(panel, method_name):
                    return getattr(panel, method_name)()
        return self._apply_text_widget(self.edit_text)

    def discard_edit(self):
        panel = getattr(self, "newspaper_panel", None)
        if panel is not None and panel.winfo_ismapped():
            for method_name in ("discard", "discard_edit", "discard_changes", "reset", "revert"):
                if hasattr(panel, method_name):
                    getattr(panel, method_name)()
                    break
            self._cancel_free_space_update()
            self.update_free_space_label()
            self._update_save_state()
            self._update_discard_button_state()
            if getattr(self, "filter_refresh_pending", False) and not self._has_pending_filter_edit():
                self.refresh_table(force=True, refresh_active_fields=True)
            return
        if not self._supported_loaded() or self.current_index is None:
            return
        entry = self.entries[self.current_index]
        original_text = self._decode_entry_text(entry)
        self.edit_text.config(state=tk.NORMAL)
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.insert("1.0", original_text)
        self.highlight_spaces()
        self.update_free_space_label()
        if getattr(self, "translate_enabled_var", None) and self.translate_enabled_var.get():
            self.translate_current(force=True)
        self._cancel_free_space_update()
        self.update_free_space_label()
        self._update_save_state()
        self._update_discard_button_state()
        
        if getattr(self, "filter_refresh_pending", False) and not self._has_pending_filter_edit():
            self.refresh_table(force=True, refresh_active_fields=True)

    def _has_pending_text_edit(self) -> bool:
        if not self._supported_loaded() or self.current_index is None:
            return False
        panel = getattr(self, "newspaper_panel", None)
        if panel is not None and panel.winfo_ismapped() and panel.is_dirty():
            return True
        return self._is_edit_text_dirty()

    def _has_committed_changes(self) -> bool:
        return bool(
            self.last_saved_exe_data
            and bytes(self.exe_data) != bytes(self.last_saved_exe_data)
        )

    def _has_unsaved_changes(self) -> bool:
        return bool(
            self._has_committed_changes()
            or self.font_pending
            or self._has_pending_text_edit()
            or self.translation_pending
        )

    def _can_save(self) -> bool:
        return bool(
            self._supported_loaded()
            and self.integrity_valid
            and not self.repack_required
            and self.font_valid
            and not self.font_pending
            and not self._has_pending_text_edit()
            and not self.translation_pending
        )

    def _can_exchange_strings(self) -> bool:
        return self._can_save()

    def _save_block_reason(self) -> str:
        if not self.integrity_valid or self.repack_required:
            return self.validation_errors[0] if self.validation_errors else self.tr("block.repack")
        if not self.font_valid:
            return self.font_errors[0] if self.font_errors else self.tr("block.font_invalid")
        if self.font_pending:
            return self.tr("block.font_pending")
        if self._has_pending_text_edit() or self.translation_pending:
            return self.tr("block.text_pending")
        return self.tr("block.generic")

    def _save_payload(self) -> tuple[bytes, bool]:
        modified_from_source = (
            bytes(self.exe_data) != bytes(self.initial_unpacked_data)
            or self._converted_to_extended
        )
        payload = bytes(self.exe_data) if modified_from_source else bytes(self.original_source_data)
        return payload, modified_from_source

    def _update_save_state(self):
        if hasattr(self, "save_button"):
            self.save_button.config(state=tk.NORMAL if self._can_save() else tk.DISABLED)
        self._set_menu_state(getattr(self, "save_menu_entries", []), self._can_save())
        exchange_state = tk.NORMAL if self._can_exchange_strings() else tk.DISABLED
        for widget_name in ("export_strings_button", "import_strings_button"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.config(state=exchange_state)
        self._set_menu_state(getattr(self, "exchange_menu_entries", []), self._can_exchange_strings())
        self._update_discard_button_state()

    def _make_text_widget(self, parent, bg="#FFFFFF"):
        container = tk.Frame(parent, bg="#BDC3C7", bd=1)
        container.pack(fill=tk.X, expand=True, pady=(0, 8))
        widget = tk.Text(container, height=1, wrap="word", font=("Consolas", 12, "bold"), bg=bg, fg="#1A252F", insertbackground="black", relief="flat", padx=5, pady=4)
        widget.pack(fill=tk.X, expand=True)
        widget.tag_configure("space_bg", background="#B3E5FC", foreground="#0288D1")
        return widget

    def _game_cfg(self) -> dict:
        return get_game_config(self.cfg, self.profile_name)

    def _get_font_for_entry(self, entry: dict) -> str:
        gcfg = self._game_cfg()
        mappings = gcfg["string_fonts"]
        key = entry["string_id"]
        if key in mappings:
            return mappings[key]
        legacy_key = hex(entry.get("original_str_addr", entry["str_addr"]))
        if legacy_key in mappings:
            return mappings[legacy_key]
        ri = self.get_range_index(entry["str_addr"])
        if ri is None:
            ri = self._extended_home_range_index(entry)
        return gcfg["range_font_defaults"].get(str(ri), "FLOW.FON") if ri is not None else "FLOW.FON"

    def _extended_home_range_index(self, entry: dict):
        if not self.profile:
            return None
        extended = extended_layout.layout_for_profile(self.profile)
        if extended is None or not extended.in_pool(entry["str_addr"]):
            return None
        return extended.home_range_index(entry)

    def _charmap_for_entry(self, entry: dict) -> dict:
        font_key = self._get_font_for_entry(entry)
        return self._game_cfg().get("charmaps", {}).get(font_key, {})

    def _font_codes_for_entry(self, entry: dict) -> set[int]:
        font_key = self._get_font_for_entry(entry)
        try:
            font_profile = EXE_FONT_PROFILES[self.profile_name]["fonts"][font_key]
            first = font_profile["ascii_start"]
            return set(range(first, first + font_profile["num_ptrs"]))
        except KeyError as exc:
            raise TextTransactionError(f"No font profile for {font_key}") from exc

    @staticmethod
    def _raw_text(raw_bytes: bytes) -> str:
        return raw_bytes.decode("latin-1")

    @staticmethod
    def _entry_raw_bytes(entry: dict) -> bytes:
        try:
            return entry["text"].encode("latin-1")
        except UnicodeEncodeError as exc:
            raise TextTransactionError(
                f"Entry {entry.get('string_id', '?')} contains non-byte Unicode text"
            ) from exc

    def _decode_raw_for_entry(self, entry: dict, raw_bytes: bytes, *, preserve_controls=False) -> str:
        charmap = self._charmap_for_entry(entry)
        if not preserve_controls:
            return charmap_decode(raw_bytes, charmap)

        raw_text = self._raw_text(raw_bytes)
        decoded = []
        cursor = 0
        for match in CONTROL_TOKEN_PATTERN.finditer(raw_text):
            decoded.append(charmap_decode(raw_bytes[cursor:match.start()], charmap))
            decoded.append(match.group(0))
            cursor = match.end()
        decoded.append(charmap_decode(raw_bytes[cursor:], charmap))
        return "".join(decoded)

    def _decode_entry_text(self, entry: dict, *, preserve_controls=False) -> str:
        return self._decode_raw_for_entry(
            entry, self._entry_raw_bytes(entry), preserve_controls=preserve_controls
        )

    def _encode_entry_text(self, entry: dict, display_text: str) -> bytes:
        charmap = self._charmap_for_entry(entry)
        allowed = self._font_codes_for_entry(entry)
        original = self._entry_raw_bytes(entry)
        encoded = bytearray()
        cursor = 0

        def encode_segment(segment: str):
            if not segment:
                return
            encoded.extend(charmap_encode(
                segment,
                charmap,
                allowed_bytes=allowed,
                preserve_bytes=original,
            ))

        for match in CONTROL_TOKEN_PATTERN.finditer(display_text):
            encode_segment(display_text[cursor:match.start()])
            try:
                token_bytes = match.group(0).encode("ascii")
            except UnicodeEncodeError as exc:
                raise CharmapEncodeError(f"Invalid control token: {match.group(0)!r}") from exc
            if any(byte_value not in allowed for byte_value in token_bytes):
                raise CharmapEncodeError(f"Control token outside active font: {match.group(0)!r}")
            encoded.extend(token_bytes)
            cursor = match.end()
        encode_segment(display_text[cursor:])
        for byte_value in set(encoded) - allowed:
            if encoded.count(byte_value) > original.count(byte_value):
                raise CharmapEncodeError(
                    f"Unconfirmed byte 0x{byte_value:02X} was introduced or duplicated"
                )
        return bytes(encoded)

    def _suffix_group_ids(self, entries=None) -> set[str]:
        entries = self.entries if entries is None else entries
        dynamic = [entry for entry in entries if not entry.get("fixed")]
        grouped = set()
        for child in dynamic:
            child_bytes = self._entry_raw_bytes(child)
            for parent in dynamic:
                offset = child["str_addr"] - parent["str_addr"]
                parent_bytes = self._entry_raw_bytes(parent)
                if 0 < offset < len(parent_bytes) and child_bytes == parent_bytes[offset:]:
                    grouped.update((child["string_id"], parent["string_id"]))
                    break
        return grouped

    def _layout_reference(self) -> dict:
        path = os.path.join(DATA_DIR, "layout-reference.json")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, ValueError):
            return {}
        if not isinstance(document, dict):
            return {}
        profiles = document.get("profiles")
        if not isinstance(profiles, dict):
            return {}
        reference = profiles.get(self.profile_name)
        if not isinstance(reference, dict):
            return {}
        return {
            key: value for key, value in reference.items()
            if isinstance(key, str) and isinstance(value, int) and value >= 0
        }

    def _string_exchange_arguments(self):
        game_cfg = self._game_cfg()
        font_codes = {}
        for font_name, font_desc in EXE_FONT_PROFILES[self.profile_name]["fonts"].items():
            first = int(font_desc["ascii_start"])
            font_codes[font_name] = set(range(first, first + int(font_desc["num_ptrs"])))
        return {
            "profile_id": self.profile_name,
            "profile": self.profile,
            "entries": self.entries,
            "charmaps": copy.deepcopy(game_cfg.get("charmaps", {})),
            "effective_font": self._get_font_for_entry,
            "font_codes": font_codes,
            "layout_reference": self._layout_reference(),
        }

    def _prepare_entry_transaction(self, entry_index: int, display_text: str):
        source_entry = self.entries[entry_index]
        new_bytes = self._encode_entry_text(source_entry, display_text)
        staged_data = bytearray(self.exe_data)
        staged_entries = copy.deepcopy(self.entries)
        staged_entry = staged_entries[entry_index]

        if staged_entry.get("fixed"):
            max_len = staged_entry["max_len"]
            if len(new_bytes) > max_len - 1:
                raise TextTransactionError(
                    f"Fixed string exceeds {max_len - 1} bytes ({len(new_bytes)} bytes)"
                )
            staged_entry["text"] = self._raw_text(new_bytes)
            address = staged_entry["str_addr"]
            staged_data[address:address + max_len] = (
                new_bytes + b"\x00" * (max_len - len(new_bytes))
            )
            validation = validate_image(
                staged_data, self.profile, staged_entries, self.relocation_sites
            )
            validation["stage"] = "fixed-output"
            return (staged_data, staged_entries, validation) if validation["ok"] else (None, None, validation)

        staged_entry["text"] = self._raw_text(new_bytes)
        return repack_transaction(
            staged_data, self.profile, staged_entries, self.relocation_sites
        )

    def _prepare_translate_all_transaction(self, translator_func, on_progress=None):
        staged_data = bytearray(self.exe_data)
        staged_entries = copy.deepcopy(self.entries)
        staged_by_id = {entry["string_id"]: entry for entry in staged_entries}
        suffix_ids = self._suffix_group_ids(self.entries)
        stats = {"translated": 0, "unchanged": 0, "blank": 0, "suffix_skipped": 0}

        for index, source_entry in enumerate(self.entries):
            if on_progress:
                on_progress(index + 1, len(self.entries), self._decode_entry_text(source_entry))
            if source_entry["string_id"] in suffix_ids:
                stats["suffix_skipped"] += 1
                continue

            original = self._decode_entry_text(source_entry, preserve_controls=True)
            if not original or original.isspace():
                stats["blank"] += 1
                continue
            translated = translator_func(original)
            if not isinstance(translated, str) or not translated:
                raise TextTransactionError(
                    f"Translator returned no text for {source_entry['string_id']}"
                )

            new_bytes = self._encode_entry_text(source_entry, translated)
            old_bytes = self._entry_raw_bytes(source_entry)
            if new_bytes == old_bytes:
                stats["unchanged"] += 1
                continue

            staged_entry = staged_by_id[source_entry["string_id"]]
            staged_entry["text"] = self._raw_text(new_bytes)
            if staged_entry.get("fixed"):
                max_len = staged_entry["max_len"]
                if len(new_bytes) > max_len - 1:
                    raise TextTransactionError(
                        f"Fixed string {staged_entry['string_id']} exceeds {max_len - 1} bytes"
                    )
                address = staged_entry["str_addr"]
                staged_data[address:address + max_len] = (
                    new_bytes + b"\x00" * (max_len - len(new_bytes))
                )
            stats["translated"] += 1

        if stats["translated"] == 0:
            return None, None, {
                "ok": True,
                "errors": [],
                "stage": "no-op",
                "noop": True,
            }, stats

        work_data, work_entries, validation = repack_transaction(
            staged_data, self.profile, staged_entries, self.relocation_sites
        )
        return work_data, work_entries, validation, stats

    def _commit_text_transaction(self, work_data, work_entries, validation):
        self.exe_data[:] = work_data
        self.entries = work_entries
        self.validation_errors = []
        self.integrity_valid = True
        self.repack_required = False
        self._recalculate_max_lengths()
        self._invalidate_diff_preview("text-commit", refresh=False)
        self._update_save_state()

    def _migrate_legacy_font_mappings(self):
        gcfg = self._game_cfg()
        mappings = gcfg["string_fonts"]
        changed = False
        for entry in self.entries:
            stable_key = entry["string_id"]
            legacy_key = hex(entry["original_str_addr"])
            if stable_key not in mappings and legacy_key in mappings:
                mappings[stable_key] = mappings.pop(legacy_key)
                changed = True
        if changed:
            save_config(self.cfg)

    def _goto_font_assign(self):
        if self.current_index is not None:
            entry = self.entries[self.current_index]
            font_key = self._get_font_for_entry(entry)
            string_combo = self.font_editor.string_font_combo
            if font_key in string_combo["values"]:
                self.font_editor.string_font_var.set(font_key)
            font_combo = self.font_editor.font_combo
            if font_key in font_combo["values"]:
                self.font_editor.font_var.set(font_key)
                self.font_editor._on_font_select()
        self._select_tab("tab_fonts")

    def _on_string_font_change(self, event=None):
        if not self._supported_loaded() or self.current_index is None: return
        entry = self.entries[self.current_index]
        string_font_var = self.font_editor.string_font_var
        self.cfg = load_config()
        self._game_cfg()["string_fonts"][entry["string_id"]] = string_font_var.get()
        save_config(self.cfg)
        if hasattr(self, "font_editor"):
            self.font_editor.sync_cfg(self.cfg)
        self._invalidate_diff_preview("string-font", refresh=False)
        self._try_rebuild_baseline_filter_index()
        self.refresh_table(force=True, refresh_active_fields=True)

    def _can_change_charmap(self) -> bool:
        if not self._has_pending_filter_edit():
            return True
        messagebox.showwarning(self.tr("dlg.pending_text.title"),
                               self.tr("dlg.pending_charmap.msg"))
        return False

    def _on_charmap_changed(self, game_name: str, font_key: str, charmap: dict):
        if not self._supported_loaded() or game_name != self.profile_name:
            return
        self.cfg = load_config()
        if hasattr(self, "font_editor"):
            self.font_editor.sync_cfg(self.cfg)
        self._invalidate_diff_preview("charmap", refresh=False)
        if self._has_pending_filter_edit():
            self.filter_refresh_pending = True
            return
        self._try_rebuild_baseline_filter_index()
        self.refresh_table(force=True, refresh_active_fields=True)

    def _refresh_current_entry_display(self):
        if not self._supported_loaded() or self.current_index is None:
            return
        entry = self.entries[self.current_index]
        self.edit_text.config(state=tk.NORMAL)
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.insert("1.0", self._decode_entry_text(entry))
        self.highlight_spaces()

    def _set_translation_text(self, text, *, pending):
        self.translate_text.delete("1.0", tk.END)
        if text:
            self.translate_text.insert("1.0", text)
        self.translation_pending = bool(pending)

    def on_newspaper_editor_toggle(self):
        if not getattr(self, "newspaper_editor_var", None):
            return

        enabled = bool(self.newspaper_editor_var.get())

        if self.current_index is None:
            if not enabled and hasattr(self, "newspaper_panel"):
                self.newspaper_panel.hide()
            return

        if not enabled:
            panel = getattr(self, "newspaper_panel", None)
            if panel is not None:
                panel.hide()

            entry = self.entries[self.current_index]
            self.edit_text.config(state=tk.NORMAL)
            self.edit_text.pack(fill=tk.BOTH, expand=True)
            self.edit_text.delete("1.0", tk.END)
            self.edit_text.insert("1.0", self._decode_entry_text(entry))
            self.highlight_spaces()

            if getattr(self, "translate_enabled_var", None) and self.translate_enabled_var.get():
                self.translate_current(force=True)
        else:
            self._display_entry(self.current_index, keep_filter=True)

        self._update_save_state()
        self._update_discard_button_state()

    def on_translate_toggle(self):
        panel = getattr(self, "newspaper_panel", None)
        if panel is not None and panel.winfo_ismapped():
            enabled = self.translate_enabled_var.get()
            translate_fn = None
            if enabled:
                engine = self.engine_var.get()
                src    = self.source_lang_var.get()
                tgt    = self.target_lang_var.get()
                def _tr(text, _e=engine, _s=src, _t=tgt):
                    from translator import translate_string as _ts
                    return _ts(text, target_lang=_t, source_lang=_s, engine=_e)
                translate_fn = _tr
            panel.refresh_translation(enabled, translate_fn)
            return
        if self.translate_enabled_var.get():
            self.translate_section.pack(fill=tk.X)
            self.translate_current(force=True)
            return
        if self.translation_pending:
            decision = messagebox.askyesnocancel(
                self.tr("dlg.pending_translation.title"),
                self.tr("dlg.pending_translation.switch"),
            )
            if decision is None:
                self.translate_enabled_var.set(True)
                return
            if decision:
                if not self.apply_translation():
                    self.translate_enabled_var.set(True)
                    return
            else:
                self._set_translation_text("", pending=False)
        self.translate_section.pack_forget()
        if self.filter_refresh_pending and not self._has_pending_filter_edit():
            self.refresh_table(force=True, refresh_active_fields=True)
        self._update_save_state()

    def on_translate_text_modified(self, event=None):
        if event is not None:
            self.translation_pending = True
        self._update_text_widget(self.translate_text, update_stats=False)

        live_override = None
        if self.current_index is not None:
            entry = self.entries[self.current_index]
            try:
                current_raw_bytes = self._encode_entry_text(
                    entry, self.translate_text.get("1.0", "1.0 lineend")
                )
                live_override = (entry, self._raw_text(current_raw_bytes))
            except (CharmapEncodeError, TextTransactionError) as exc:
                self.current_range_label.config(
                    text=self.tr("edit.encoding_blocked", error=exc),
                    foreground="#C0392B",
                )

        self._schedule_free_space_update(live_override=live_override)
        self._update_save_state()

    def _update_text_widget(self, widget, update_stats=False):
        widget.tag_remove("space_bg", "1.0", tk.END)
        text = widget.get("1.0", "1.0 lineend")
        for i, char in enumerate(text):
            if char == " ":
                widget.tag_add("space_bg", f"1.0 + {i} chars", f"1.0 + {i + 1} chars")

        if update_stats:
            l_spaces = len(text) - len(text.lstrip(" "))
            r_spaces = len(text) - len(text.rstrip(" "))
            self.space_stats_label.config(text=self.tr(
                "edit.stats", n=len(text), lead=l_spaces, trail=r_spaces))
        widget.update_idletasks()
        last_line = int(widget.index("end-1c").split(".")[0])
        display_lines = sum(
            (widget.count(f"{ln}.0", f"{ln}.end", "displaylines") or (0,))[0] + 1
            for ln in range(1, last_line + 1)
        )
        widget.config(height=max(1, min(max(display_lines, 1), 12)))
        return text

    def get_range_index(self, addr):
        for i, (s, e) in enumerate(self.profile["valid_ranges"]):
            if s <= addr < e: return i
        return None

    def _recalculate_max_lengths(self):
        sorted_entries = sorted((e for e in self.entries if not e.get("fixed")), key=lambda x: x["str_addr"])
        for i, curr in enumerate(sorted_entries):
            if i < len(sorted_entries) - 1:
                nxt = sorted_entries[i + 1]
                curr["max_len"] = nxt["str_addr"] - curr["str_addr"] if nxt["str_addr"] > curr["str_addr"] \
                                  else len(self._entry_raw_bytes(curr)) + 1
            else:
                curr["max_len"] = len(self._entry_raw_bytes(curr)) + 1

    def _sync_entry_index(self):
        mapping = {}
        for index, entry in enumerate(self.entries):
            string_id = entry.get("string_id")
            if not isinstance(string_id, str) or not string_id or string_id in mapping:
                raise SearchFilterError("Entries do not have unique string_ids")
            mapping[string_id] = index
        self.entry_index_by_id = mapping

    @staticmethod
    def _entry_filter_kind(entry):
        if entry.get("fixed"):
            return "fixed"
        if entry.get("ptr_addrs"):
            return "normal"
        if entry.get("code_ptr_addrs"):
            return "code-only"
        raise SearchFilterError(
            f"Entry {entry.get('string_id', '?')} has no supported reference kind"
        )

    def _rebuild_baseline_filter_index(self):
        if not self.profile or not self.profile_name or not self.initial_unpacked_data:
            self.baseline_filter_data = {}
            self.filter_records = ()
            self.filter_records_by_id = {}
            self.filter_records_dirty = True
            return
        self._sync_entry_index()
        if not self.integrity_valid:
            game_charmaps = self._game_cfg().get("charmaps", {})
            stub_baseline = {}
            for entry in self.entries:
                sid = entry["string_id"]
                raw = self._entry_raw_bytes(entry)
                font = self._get_font_for_entry(entry)
                try:
                    text = raw_to_exchange_text(raw, game_charmaps.get(font, {}))
                except StringExchangeError:
                    text = raw.decode("latin-1", errors="replace")
                stub_baseline[sid] = {"raw": raw, "text": text, "suffix_shared": False}
            self.baseline_filter_data = stub_baseline
            self.filter_records_dirty = True
            self._rebuild_filter_records()
            return
        baseline_entries = reconstruct_baseline_entries(
            self.initial_unpacked_data,
            self.entries,
            self.profile,
            self.relocation_sites,
        )
        exchange = self._string_exchange_arguments()
        baseline_document = build_export_document(
            self.profile_name,
            self.profile,
            baseline_entries,
            exchange["charmaps"],
            exchange["effective_font"],
            exchange["font_codes"],
            exchange["layout_reference"],
        )
        baseline_entries_by_id = {
            entry["string_id"]: entry for entry in baseline_entries
        }
        baseline_rows_by_id = {
            row["string_id"]: row for row in baseline_document["entries"]
        }
        if set(baseline_entries_by_id) != set(self.entry_index_by_id):
            raise SearchFilterError("Baseline/current string_id sets differ")
        self.baseline_filter_data = {
            string_id: {
                "raw": baseline_entries_by_id[string_id]["text"].encode("latin-1"),
                "text": baseline_rows_by_id[string_id]["source_text"],
                "suffix_shared": bool(baseline_rows_by_id[string_id]["suffix_links"]),
            }
            for string_id in self.entry_index_by_id
        }
        self.filter_records_dirty = True
        self._rebuild_filter_records()

    def _try_rebuild_baseline_filter_index(self):
        try:
            self._rebuild_baseline_filter_index()
        except (DiffPreviewError, SearchFilterError, StringExchangeError, KeyError, ValueError) as exc:
            self.baseline_filter_data = {}
            self.filter_records = ()
            self.filter_records_by_id = {}
            self.filter_records_dirty = False
            self.filter_index_error = str(exc)
            return False
        return True

    def _rebuild_filter_records(self):
        if not self.entries:
            self.filter_records = ()
            self.filter_records_by_id = {}
            self.filter_records_dirty = False
            return
        self._sync_entry_index()
        if set(self.entry_index_by_id) != set(self.baseline_filter_data):
            raise SearchFilterError("Search baseline does not match current entries")
        preview = self.diff_preview_cache.get() or {}
        preview_rows = preview.get("strings_by_id", {})
        game_charmaps = self._game_cfg().get("charmaps", {})
        rows = []
        for entry in self.entries:
            string_id = entry["string_id"]
            baseline = self.baseline_filter_data[string_id]
            font = self._get_font_for_entry(entry)
            current_raw = self._entry_raw_bytes(entry)
            try:
                current_text = raw_to_exchange_text(
                    current_raw, game_charmaps.get(font, {})
                )
            except StringExchangeError as exc:
                raise SearchFilterError(
                    f"Search text could not be decoded for {string_id}: {exc}"
                ) from exc
            preview_status = preview_rows.get(string_id, {}).get("status")
            rows.append({
                "string_id": string_id,
                "kind": self._entry_filter_kind(entry),
                "font": font,
                "current_text": current_text,
                "baseline_text": baseline["text"],
                "current_raw": current_raw,
                "baseline_raw": baseline["raw"],
                "suffix_shared": baseline["suffix_shared"],
                "preview_status": preview_status,
            })
        self.filter_records = build_filter_records(rows)
        self.filter_records_by_id = {
            record.string_id: record for record in self.filter_records
        }
        self.filter_records_dirty = False
        self.filter_index_error = None

    def _has_pending_filter_edit(self):
        return bool(self._has_pending_text_edit() or self.translation_pending)

    def _clear_current_selection(self):
        self._selection_guard = True
        try:
            selected = self.tree.selection()
            if selected:
                self.tree.selection_remove(*selected)
        finally:
            self._selection_guard = False
        self.current_index = None
        panel = getattr(self, "newspaper_panel", None)
        if panel is not None:
            panel.hide()
        self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
        self.edit_text.delete("1.0", tk.END)
        self.translate_text.config(state=tk.NORMAL)
        self._set_translation_text("", pending=False)
        self.space_stats_label.config(text="")
        self.translate_status_label.config(text="")
        self.current_range_label.config(text="")
        self._update_save_state()

    def _is_newspaper_entry(self, entry: dict) -> bool:
        if not self._supported_loaded():
            return False
        try:
            if not newspaper_csv.is_supported(self.profile_name):
                return False
            news_ids = {e["string_id"]
                        for e in newspaper_csv.collect(self.profile_name, self.entries)}
            return entry.get("string_id") in news_ids
        except Exception:
            return False

    def _newspaper_decode(self, entry: dict) -> str:
        import newspaper_grammar as _ng
        raw_text = entry["text"]
        return raw_text

    def _display_entry(self, index, keep_filter=False):
        if not self._supported_loaded():
            return
        
        self._cancel_free_space_update()
        self.current_index = index
        entry = self.entries[index]
        original_text = self._decode_entry_text(entry)
        is_news = self._is_newspaper_entry(entry)
        if getattr(self, "newspaper_editor_var", None) and self.newspaper_editor_var.get() and is_news:
            if hasattr(self, "newspaper_panel"):
                self.edit_text.pack_forget()
                self.newspaper_panel.pack(fill=tk.BOTH, expand=True)
                self.newspaper_panel.show(entry, decode_fn=self._decode_entry_text)
        else:
            if hasattr(self, "newspaper_panel"):
                self.newspaper_panel.pack_forget()
            self.edit_text.pack(fill=tk.BOTH, expand=True)
            self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
            self.edit_text.delete("1.0", tk.END)
            self.edit_text.insert("1.0", original_text)
            self.highlight_spaces()
            self.update_free_space_label()
            if not self.integrity_valid:
                self.edit_text.config(state=tk.DISABLED, bg="#F2F3F4")
            elif getattr(self, "translate_enabled_var", None) and self.translate_enabled_var.get():
                self.translate_current(force=True)
        self._update_save_state()
        self._update_discard_button_state()

    def refresh_table(self, *, force=False, refresh_active_fields=False):
        if (
            not force
            and self.current_index is not None
            and self._has_pending_filter_edit()
        ):
            self.filter_refresh_pending = True
            self._set_filter_status("status.filter_pending")
            return False

        active_id = None
        if self.current_index is not None and 0 <= self.current_index < len(self.entries):
            active_id = self.entries[self.current_index].get("string_id")
        try:
            if self.filter_records_dirty:
                self._rebuild_filter_records()
            visible = filter_string_ids(
                self.filter_records,
                query=self.search_var.get(),
                kind_filter=self.kind_filter_var.get(),
                font_filter=self.font_filter_var.get(),
                change_filter=self.change_filter_var.get(),
                status_filter=self.status_filter_var.get(),
            )
        except SearchFilterError as exc:
            self.filter_index_error = str(exc)
            visible = ()

        self.tree.delete(*self.tree.get_children())
        self.visible_string_ids = list(visible)
        for string_id in self.visible_string_ids:
            index = self.entry_index_by_id[string_id]
            entry = self.entries[index]
            self.tree.insert(
                "",
                tk.END,
                iid=string_id,
                values=(index + 1, hex(entry["str_addr"]), self._decode_entry_text(entry)),
            )
        total, shown = len(self.entries), len(self.visible_string_ids)
        self._set_counter(shown, total)
        if self.filter_index_error:
            self._set_filter_status("status.filter_unavailable", error=self.filter_index_error)
        else:
            self._set_filter_status(None)

        self.filter_refresh_pending = False
        if active_id and active_id in self.entry_index_by_id and active_id in visible:
            self.current_index = self.entry_index_by_id[active_id]
            self._selection_guard = True
            try:
                self.tree.selection_set(active_id)
                self.tree.focus(active_id)
                self.tree.see(active_id)
            finally:
                self._selection_guard = False
            if refresh_active_fields:
                self._display_entry(self.current_index)
        elif active_id:
            self._clear_current_selection()
        return True

    def on_search_change(self, *args):
        if not self._filter_callbacks_suspended:
            self.refresh_table()

    def on_filter_change(self, event=None):
        if not self._filter_callbacks_suspended:
            self.refresh_table()

    def clear_filters(self):
        self._filter_callbacks_suspended = True
        try:
            self.search_var.set("")
            self.kind_filter_var.set("All")
            self.font_filter_var.set("All")
            self.change_filter_var.set("All")
            self.status_filter_var.set("All")
        finally:
            self._filter_callbacks_suspended = False
        self.refresh_table()
        self.search_entry.focus()

    def on_select(self, event):
        if self._selection_guard:
            return
        selected = self.tree.selection()
        if not selected:
            return
        string_id = selected[0]
        if string_id not in self.entry_index_by_id:
            self._clear_current_selection()
            return
        current_id = None
        if self.current_index is not None and 0 <= self.current_index < len(self.entries):
            current_id = self.entries[self.current_index].get("string_id")
        if current_id and string_id != current_id and self._has_pending_filter_edit():
            self._selection_guard = True
            try:
                if self.tree.exists(current_id):
                    self.tree.selection_set(current_id)
                    self.tree.focus(current_id)
                else:
                    self.tree.selection_remove(string_id)
            finally:
                self._selection_guard = False
            self._set_filter_status("status.selection_blocked")
            return
        if current_id == string_id:
            return
        self._display_entry(self.entry_index_by_id[string_id])

    def highlight_spaces(self): self._update_text_widget(self.edit_text, update_stats=True)

    def on_text_modified(self, event=None):
        full = self.edit_text.get("1.0", tk.END)
        if "\n" in full[:-1] or "\r" in full:
            cursor_pos = self.edit_text.index(tk.INSERT)
            content = full.replace("\n", "").replace("\r", "")
            self.edit_text.delete("1.0", tk.END)
            self.edit_text.insert("1.0", content)
            try:
                self.edit_text.mark_set(tk.INSERT, cursor_pos)
            except tk.TclError:
                pass

        self.highlight_spaces()

        live_override = None
        if self.current_index is not None:
            entry = self.entries[self.current_index]
            try:
                current_raw_bytes = self._encode_entry_text(
                    entry, self.edit_text.get("1.0", "1.0 lineend")
                )
            except (CharmapEncodeError, TextTransactionError) as exc:
                self.current_range_label.config(
                    text=self.tr("edit.encoding_blocked", error=exc),
                    foreground="#C0392B",
                )
                self._update_save_state()
                return
            live_override = (entry, self._raw_text(current_raw_bytes))
        self._schedule_free_space_update(live_override=live_override)
        self._update_save_state()
        if self.filter_refresh_pending and not self._has_pending_filter_edit():
            self.refresh_table(force=True, refresh_active_fields=True)

    def _apply_text_widget(self, widget):
        if not self._supported_loaded() or self.current_index is None:
            return False
        if widget is self.edit_text and self.translation_pending:
            messagebox.showerror(self.tr("dlg.text_blocked.title"),
                                 self.tr("dlg.text_blocked.translation"))
            return False
        display_text = widget.get("1.0", "1.0 lineend")
        try:
            source_entry = self.entries[self.current_index]
            desired_bytes = self._encode_entry_text(source_entry, display_text)
            if desired_bytes == self._entry_raw_bytes(source_entry):
                if widget is self.translate_text:
                    self.translation_pending = False
                self.translate_status_label.config(text=self.tr("tr.no_changes"))
                self._update_save_state()
                if self.filter_refresh_pending and not self._has_pending_filter_edit():
                    self.refresh_table(force=True, refresh_active_fields=True)
                return True
            work_data, work_entries, validation = self._prepare_entry_transaction(
                self.current_index, display_text
            )
        except (CharmapEncodeError, TextTransactionError) as exc:
            messagebox.showerror(self.tr("dlg.text_blocked.title"), str(exc))
            return False

        if not validation["ok"]:
            detail = validation["errors"][0] if validation.get("errors") else "Unknown validation error"
            messagebox.showerror(self.tr("dlg.text_blocked.title"), detail)
            return False

        self._commit_text_transaction(work_data, work_entries, validation)
        if widget is self.translate_text:
            self.translation_pending = False
        self.refresh_table(force=True, refresh_active_fields=True)
        self._update_save_state()
        return True

    def apply_translation(self):
        return self._apply_text_widget(self.translate_text)

    def translate_current(self, *, force=False):
        if not self._supported_loaded() or self.current_index is None or not self.translate_enabled_var.get(): return
        if self.translation_pending and not force:
            messagebox.showwarning(self.tr("dlg.pending_translation.title"),
                                   self.tr("dlg.pending_translation.new"))
            return
        self._set_translation_text("", pending=False)
        self.translate_status_label.config(text=self.tr("tr.translating"))
        self.root.update_idletasks()
        try:
            entry = self.entries[self.current_index]
            source_bytes = self._encode_entry_text(
                entry, self.edit_text.get("1.0", "1.0 lineend")
            )
            original = self._decode_raw_for_entry(
                entry, source_bytes, preserve_controls=True
            )
            translated = translate_string(
                original,
                target_lang=self.target_lang_var.get(),
                source_lang=self.source_lang_var.get(),
                engine=self.engine_var.get(),
            )
            translated_bytes = self._encode_entry_text(entry, translated)
            translated_display = self._decode_raw_for_entry(entry, translated_bytes)
        except Exception as exc:
            self.translate_status_label.config(text=self.tr("tr.error", error=exc))
            return
        self._set_translation_text(translated_display, pending=False)
        self.translate_status_label.config(text="")
        self._update_text_widget(self.translate_text, update_stats=False)
        self._update_save_state()

    def translate_all(self):
        if not self._supported_loaded() or not self.entries:
            messagebox.showinfo(self.tr("dlg.translate_all.title"),
                                self.tr("dlg.translate_all.none"))
            return
        if not messagebox.askyesno(
            self.tr("dlg.translate_all.title"),
            self.tr("dlg.translate_all.confirm", n=len(self.entries),
                    engine=self.engine_var.get()),
        ):
            return

        engine = self.engine_var.get()
        src = self.source_lang_var.get()
        tgt = self.target_lang_var.get()
        prog_win = tk.Toplevel(self.root)
        prog_win.title(self.tr("dlg.translate_all.window"))
        prog_win.resizable(False, False)
        prog_win.grab_set()
        ttk.Label(prog_win, text=self.tr("tr.translating"), font=("Segoe UI", 10, "bold"), padding=10).pack()
        progress_var = tk.IntVar(value=0)
        bar = ttk.Progressbar(prog_win, maximum=len(self.entries), variable=progress_var, length=360)
        bar.pack(padx=20, pady=(0, 6))
        status_lbl = ttk.Label(prog_win, text="", font=("Segoe UI", 9, "italic"), padding=(10, 0, 10, 10))
        status_lbl.pack()
        prog_win.update()

        def update_progress(current, total, display_text):
            status_lbl.config(text=self.tr("dlg.translate_all.progress",
                                           current=current, total=total,
                                           text=display_text[:50]))
            progress_var.set(current)
            prog_win.update()

        try:
            work_data, work_entries, validation, stats = self._prepare_translate_all_transaction(
                lambda original: translate_string(
                    original, target_lang=tgt, source_lang=src, engine=engine
                ),
                on_progress=update_progress,
            )
        except Exception as exc:
            prog_win.destroy()
            messagebox.showerror(self.tr("dlg.translate_all.blocked"),
                                 self.tr("dlg.translate_all.nochange", detail=exc))
            return

        prog_win.destroy()
        if validation.get("noop"):
            messagebox.showinfo(self.tr("dlg.translate_all.title"),
                                self.tr("dlg.translate_all.unchanged"))
            return
        if not validation["ok"]:
            detail = "\n".join(validation.get("errors", [])[:8]) or "Unknown validation error"
            messagebox.showerror(self.tr("dlg.translate_all.blocked"),
                                 self.tr("dlg.translate_all.nochange", detail=detail))
            return

        self._commit_text_transaction(work_data, work_entries, validation)
        self.refresh_table(force=True, refresh_active_fields=True)

        summary = self.tr("dlg.translate_all.summary", translated=stats["translated"],
                          unchanged=stats["unchanged"], blank=stats["blank"])
        if stats["suffix_skipped"]:
            summary += self.tr("dlg.translate_all.suffix", n=stats["suffix_skipped"])
        messagebox.showinfo(self.tr("dlg.translate_all.done"), summary)

    def export_strings(self):
        if not self._can_exchange_strings():
            messagebox.showwarning(self.tr("dlg.export.blocked"), self._save_block_reason())
            return False
        try:
            payload = export_json_bytes(**self._string_exchange_arguments())
        except (StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.export.blocked"), str(exc))
            return False

        filepath = filedialog.asksaveasfilename(
            title=self.tr("fd.export"),
            initialfile="translations.strings.json",
            defaultextension=".strings.json",
            filetypes=[("String Exchange JSON", "*.strings.json")],
        )
        if not filepath:
            return False
        try:
            atomic_save_bytes(filepath, payload)
        except OSError as exc:
            messagebox.showerror(self.tr("dlg.export.failed"),
                                 self.tr("dlg.export.partial", error=exc))
            return False
        self._set_status("dlg.export.status", n=len(self.entries),
                         file=os.path.basename(filepath))
        messagebox.showinfo(self.tr("dlg.export.done"),
                            self.tr("dlg.export.done_msg", n=len(self.entries), path=filepath))
        return True

    def import_strings(self):
        if not self._can_exchange_strings():
            messagebox.showwarning(self.tr("dlg.import.blocked"), self._save_block_reason())
            return False
        filepath = filedialog.askopenfilename(
            title=self.tr("fd.import"),
            filetypes=[("String Exchange JSON", "*.strings.json")],
        )
        if not filepath:
            return False
        try:
            with open(filepath, "rb") as handle:
                raw_document = handle.read()
            preflight = preflight_import_json(
                raw_document, **self._string_exchange_arguments()
            )
        except (OSError, StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"),
                                 self.tr("dlg.import.nochange", error=exc))
            return False

        changed_count = preflight["changed_count"]
        if changed_count == 0:
            messagebox.showinfo(self.tr("dlg.import.done"),
                                self.tr("dlg.import.none", profile=preflight["profile_id"]))
            return True
        if not messagebox.askyesno(
            self.tr("dlg.import.title"),
            self.tr("dlg.import.confirm", profile=preflight["profile_id"], n=changed_count),
        ):
            return False
        if not self._can_exchange_strings():
            messagebox.showwarning(self.tr("dlg.import.blocked"), self._save_block_reason())
            return False

        try:
            preflight = preflight_import_json(
                raw_document, **self._string_exchange_arguments()
            )
            work_data, work_entries, validation, _font_result = stage_import_transaction(
                self.exe_data,
                self.entries,
                preflight["replacements"],
                self.profile,
                self.relocation_sites,
                EXE_FONT_PROFILES[self.profile_name],
            )
        except (StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"),
                                 self.tr("dlg.import.nochange", error=exc))
            return False
        if not self._can_exchange_strings():
            messagebox.showwarning(self.tr("dlg.import.blocked"), self._save_block_reason())
            return False

        self._commit_text_transaction(work_data, work_entries, validation)
        self.translation_pending = False
        self.refresh_table(force=True, refresh_active_fields=True)
        self._update_save_state()
        self._set_status("dlg.import.status", n=preflight["changed_count"])
        messagebox.showinfo(self.tr("dlg.import.done"),
                            self.tr("dlg.import.done_msg", profile=preflight["profile_id"],
                                    n=preflight["changed_count"]))
        return True

    def _newspaper_ready(self, blocked_key):
        if not self._can_exchange_strings():
            messagebox.showwarning(self.tr(blocked_key), self._save_block_reason())
            return False
        if not newspaper_csv.is_supported(self.profile_name):
            messagebox.showwarning(self.tr(blocked_key),
                                   self.tr("dlg.news.unsupported", profile=self.profile_name))
            return False
        return True

    def export_newspaper_csv(self):
        if not self._newspaper_ready("dlg.export.blocked"):
            return False
        try:
            payload = newspaper_csv.export_csv_bytes(
                self.profile_name, self.entries, self._decode_entry_text)
            rows = newspaper_csv.build_rows(
                self.profile_name, self.entries, self._decode_entry_text)
            count = len(newspaper_csv.collect(self.profile_name, self.entries))
        except (newspaper_csv.NewspaperCsvError, NewspaperGrammarError,
                CharmapEncodeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.export.blocked"), str(exc))
            return False

        filepath = filedialog.asksaveasfilename(
            title=self.tr("fd.news_export"),
            initialfile="newspaper.csv",
            defaultextension=".csv",
            filetypes=[("Newspaper CSV", "*.csv")],
        )
        if not filepath:
            return False
        try:
            atomic_save_bytes(filepath, payload)
        except OSError as exc:
            messagebox.showerror(self.tr("dlg.export.failed"),
                                 self.tr("dlg.export.partial", error=exc))
            return False
        self._set_status("dlg.news.status_export", n=count,
                         file=os.path.basename(filepath))
        messagebox.showinfo(self.tr("dlg.export.done"),
                            self.tr("dlg.news.export_msg", n=count, rows=len(rows),
                                    path=filepath))
        return True

    def import_newspaper_csv(self):
        if not self._newspaper_ready("dlg.import.blocked"):
            return False
        filepath = filedialog.askopenfilename(
            title=self.tr("fd.news_import"),
            filetypes=[("Newspaper CSV", "*.csv")],
        )
        if not filepath:
            return False
        try:
            with open(filepath, "rb") as handle:
                raw_document = handle.read()
            replacements = newspaper_csv.preflight_import(
                self.profile_name, self.entries, self._decode_entry_text, raw_document)
        except (OSError, newspaper_csv.NewspaperCsvError, NewspaperGrammarError,
                CharmapEncodeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"),
                                 self.tr("dlg.import.nochange", error=exc))
            return False

        if not replacements:
            messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.news.none"))
            return True
        if not messagebox.askyesno(self.tr("dlg.import.title"),
                                   self.tr("dlg.news.confirm", n=len(replacements))):
            return False
        if not self._newspaper_ready("dlg.import.blocked"):
            return False

        try:
            by_id = {entry["string_id"]: entry for entry in self.entries}
            raw_replacements = {
                string_id: self._encode_entry_text(by_id[string_id], display_text)
                for string_id, display_text in replacements.items()
            }
            work_data, work_entries, validation, _font_result = stage_import_transaction(
                self.exe_data,
                self.entries,
                raw_replacements,
                self.profile,
                self.relocation_sites,
                EXE_FONT_PROFILES[self.profile_name],
            )
        except (StringExchangeError, CharmapEncodeError, TextTransactionError,
                FontSafetyError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"),
                                 self.tr("dlg.import.nochange", error=exc))
            return False
        if not self._newspaper_ready("dlg.import.blocked"):
            return False

        self._commit_text_transaction(work_data, work_entries, validation)
        self.translation_pending = False
        self.refresh_table(force=True, refresh_active_fields=True)
        self._update_save_state()
        self._set_status("dlg.news.status_import", n=len(replacements))
        messagebox.showinfo(self.tr("dlg.import.done"),
                            self.tr("dlg.news.done_msg", n=len(replacements)))
        return True

    def _pending_preview_state(self):
        replacements = {}
        pending_ids = set()
        pending_error = None
        if self.current_index is not None and self._supported_loaded():
            edit_pending = self._has_pending_text_edit()
            translation_pending = bool(self.translation_pending)
            entry = self.entries[self.current_index]
            if edit_pending and translation_pending:
                pending_ids.add(entry["string_id"])
                pending_error = (
                    "Both edit and translation fields contain pending text; "
                    "apply or discard one before previewing."
                )
            elif edit_pending or translation_pending:
                widget = self.translate_text if translation_pending else self.edit_text
                pending_ids.add(entry["string_id"])
                try:
                    display_text = widget.get("1.0", "1.0 lineend")
                    replacements[entry["string_id"]] = self._encode_entry_text(
                        entry, display_text
                    )
                except (CharmapEncodeError, TextTransactionError) as exc:
                    pending_error = str(exc)

        pending_font_key = None
        pending_font_model = None
        if self.font_pending and hasattr(self, "font_editor"):
            pending_font_key = self.font_editor.current_font_key
            pending_font_model = self.font_editor.font_data
            if not pending_font_key or not pending_font_model:
                pending_error = pending_error or "Pending font state is incomplete."
        return {
            "replacements": replacements,
            "pending_ids": pending_ids,
            "pending_error": pending_error,
            "pending_font_key": pending_font_key,
            "pending_font_model": pending_font_model,
        }

    def _build_changes_preview(self):
        cached = self.diff_preview_cache.get()
        if cached is not None:
            return cached
        if not self._supported_loaded() or not self.initial_unpacked_data:
            raise DiffPreviewError("Load a supported executable before previewing changes.")
        exchange = self._string_exchange_arguments()
        pending = self._pending_preview_state()
        snapshot = build_diff_preview(
            baseline_data=self.initial_unpacked_data,
            current_data=self.exe_data,
            current_entries=self.entries,
            profile_id=self.profile_name,
            profile=self.profile,
            relocation_sites=self.relocation_sites,
            font_profile=EXE_FONT_PROFILES[self.profile_name],
            charmaps=exchange["charmaps"],
            effective_font=exchange["effective_font"],
            font_codes=exchange["font_codes"],
            integrity_valid=self.integrity_valid,
            repack_required_state=self.repack_required,
            validation_errors_state=self.validation_errors,
            font_valid=self.font_valid,
            font_pending=self.font_pending,
            font_errors_state=self.font_errors,
            save_possible=self._can_save(),
            pending_replacements=pending["replacements"],
            pending_string_ids=pending["pending_ids"],
            pending_font_key=pending["pending_font_key"],
            pending_font_model=pending["pending_font_model"],
            pending_error=pending["pending_error"],
        )
        return snapshot


    @staticmethod
    def _make_preview_tree(parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        names = tuple(column[0] for column in columns)
        tree = ttk.Treeview(frame, columns=names, show="headings")
        for name, heading, width, anchor in columns:
            tree.heading(name, text=heading)
            tree.column(name, width=width, anchor=anchor, stretch=name in {"old", "new", "error"})
        vertical = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side=tk.RIGHT, fill=tk.Y)
        horizontal.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree.tag_configure("FAIL", background="#F5B7B1", foreground="#641E16")
        tree.tag_configure("PASS", background="#D5F5E3", foreground="#145A32")
        tree.tag_configure("PENDING", background="#FCF3CF", foreground="#7D6608")
        tree.tag_configure("READ-ONLY", background="#EAECEE", foreground="#566573")
        return tree

    def _show_preview_dialog(self, snapshot):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.tr("dlg.preview.title", profile=snapshot["profile_id"]))
        dialog.geometry("1180x700")
        dialog.minsize(900, 520)
        dialog.transient(self.root)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        tabs = {name: ttk.Frame(notebook) for name in ("Summary", "Strings", "Blocks", "Pointers", "Fonts")}
        for name, frame in tabs.items():
            notebook.add(frame, text="  %s  " % self.tr("preview.tab." + name.lower()))

        summary = snapshot["summary"]
        none_text = self.tr("preview.val.none")
        yes_text = self.tr("preview.val.yes")
        no_text = self.tr("preview.val.no")

        def flag(value):
            return yes_text if value else no_text

        year_offset = self._year_offset()
        year_changed = (
            year_offset is not None
            and len(self.initial_unpacked_data) >= year_offset + 2
            and bytes(self.exe_data[year_offset:year_offset + 2])
            != bytes(self.initial_unpacked_data[year_offset:year_offset + 2])
        )
        region_offset = self._region_offset()
        region_changed = (
            region_offset is not None
            and len(self.initial_unpacked_data) >= region_offset + 8
            and bytes(self.exe_data[region_offset:region_offset + 8])
            != bytes(self.initial_unpacked_data[region_offset:region_offset + 8])
        )
        region_value = no_text
        if region_changed:
            before = self._region_index(
                self._region_pair(self.initial_unpacked_data, region_offset))
            after = self._region_index(self._region_pair(self.exe_data, region_offset))
            if before is None or after is None:
                region_value = yes_text
            else:
                region_value = "{} → {}".format(
                    self.tr(self._REGION_VARIANTS[before][0]),
                    self.tr(self._REGION_VARIANTS[after][0]))
        summary_lines = [
            self.tr("preview.sum.status", value=snapshot["status"]),
            self.tr("preview.sum.profile", value=snapshot["profile_id"]),
            "",
            self.tr("preview.sum.normal", value=summary["normal_changed"]),
            self.tr("preview.sum.fixed", value=summary["fixed_changed"]),
            self.tr("preview.sum.codeonly", value=summary["code_only_changed"]),
            self.tr("preview.sum.glyphs", value=summary["glyphs_changed"]),
            self.tr("preview.sum.fonts",
                    value=", ".join(summary["fonts_affected"]) or none_text),
            self.tr("preview.sum.pointers",
                    value=summary["pointer_sources_changed"]),
            *([self.tr("preview.sum.year", value=flag(year_changed))]
              if year_offset is not None else []),
            *([self.tr("preview.sum.region", value=region_value)]
              if region_offset is not None else []),
            "",
            self.tr("preview.sum.repack_needed",
                    value=flag(summary["repack_needed"])),
            self.tr("preview.sum.repack_status", value=summary["repack_status"]),
            self.tr("preview.sum.validator", value=summary["validator_status"]),
            self.tr("preview.sum.font_status", value=summary["font_status"]),
            self.tr("preview.sum.save_possible",
                    value=flag(summary["save_possible"])),
        ]
        if snapshot["errors"]:
            summary_lines.extend(["", self.tr("preview.sum.reasons")]
                                 + [f"- {value}" for value in snapshot["errors"]])
        summary_text = tk.Text(tabs["Summary"], wrap="word", font=("Consolas", 10), padx=12, pady=12)
        summary_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        summary_text.insert("1.0", "\n".join(summary_lines))
        summary_text.config(state=tk.DISABLED)

        string_tree = self._make_preview_tree(tabs["Strings"], [
            ("status", self.tr("preview.col.status"), 85, tk.CENTER),
            ("id", "string_id", 140, tk.W),
            ("kind", self.tr("preview.col.kind"), 80, tk.CENTER),
            ("font", self.tr("preview.col.font"), 95, tk.CENTER),
            ("oldlen", self.tr("preview.col.oldbytes"), 70, tk.E),
            ("newlen", self.tr("preview.col.newbytes"), 70, tk.E),
            ("delta", self.tr("preview.col.delta"), 60, tk.E),
            ("block", self.tr("preview.col.block"), 55, tk.CENTER),
            ("ptrs", self.tr("preview.col.pointers"), 65, tk.E),
            ("code", self.tr("preview.col.codeptrs"), 65, tk.E),
            ("cap", self.tr("preview.col.fixedcap"), 65, tk.E),
            ("old", self.tr("preview.col.oldtext"), 230, tk.W),
            ("new", self.tr("preview.col.newtext"), 230, tk.W),
        ])
        for row in snapshot["strings"]:
            block = "—" if row["repack_block"] is None else row["repack_block"] + 1
            capacity = "—" if row["fixed_capacity_bytes"] is None else row["fixed_capacity_bytes"]
            string_tree.insert("", tk.END, values=(
                row["status"], row["string_id"], row["kind"], row["font"],
                row["old_length"], row["new_length"], f"{row['delta']:+d}", block,
                row["pointer_count"], row["code_pointer_count"], capacity,
                row["old_text"], row["new_text"],
            ), tags=(row["status"],))

        block_tree = self._make_preview_tree(tabs["Blocks"], [
            ("status", self.tr("preview.col.status"), 80, tk.CENTER),
            ("block", self.tr("preview.col.block"), 55, tk.CENTER),
            ("range", self.tr("preview.col.range"), 180, tk.CENTER),
            ("total", self.tr("preview.col.total"), 80, tk.E),
            ("base", self.tr("preview.col.baseused"), 100, tk.E),
            ("preview", self.tr("preview.col.prevused"), 100, tk.E),
            ("delta", self.tr("preview.col.delta"), 70, tk.E),
            ("saved", self.tr("preview.col.savings"), 70, tk.E),
            ("growth", self.tr("preview.col.growth"), 70, tk.E),
            ("free", self.tr("preview.col.sharedrest"), 90, tk.E),
            ("missing", self.tr("preview.col.missing"), 70, tk.E),
            ("error", self.tr("preview.col.reason"), 250, tk.W),
        ])
        for row in snapshot["blocks"]:
            def shown(value): return "—" if value is None else value
            block_tree.insert("", tk.END, values=(
                row["status"], row["block"] + 1,
                f"0x{row['start']:X}–0x{row['end']:X}", row["total"],
                row["baseline_used"], shown(row["preview_used"]), shown(row["delta"]),
                shown(row["savings"]), shown(row["growth"]), shown(row["preview_free"]),
                row["missing_bytes"], row["error"] or "",
            ), tags=(row["status"],))

        pointer_tree = self._make_preview_tree(tabs["Pointers"], [
            ("source", self.tr("preview.col.source"), 90, tk.CENTER),
            ("kind", self.tr("preview.col.type"), 70, tk.CENTER),
            ("id", "string_id", 150, tk.W),
            ("oldlow", self.tr("preview.col.oldlowword"), 90, tk.CENTER),
            ("newlow", self.tr("preview.col.newlowword"), 90, tk.CENTER),
            ("old", self.tr("preview.col.oldtarget"), 95, tk.CENTER),
            ("new", self.tr("preview.col.newtarget"), 95, tk.CENTER),
            ("delta", self.tr("preview.col.targetdelta"), 85, tk.E),
        ])
        for row in snapshot["pointers"]:
            pointer_tree.insert("", tk.END, values=(
                f"0x{row['source']:X}", row["kind"], row["string_id"],
                f"0x{row['old_lowword']:04X}", f"0x{row['new_lowword']:04X}",
                f"0x{row['old_target']:X}", f"0x{row['new_target']:X}",
                f"{row['target_delta']:+d}",
            ))

        font_tree = self._make_preview_tree(tabs["Fonts"], [
            ("status", self.tr("preview.col.status"), 80, tk.CENTER),
            ("font", self.tr("preview.col.font"), 100, tk.CENTER),
            ("offset", self.tr("preview.col.glyphoffset"), 90, tk.CENTER),
            ("code", self.tr("preview.col.canonical"), 75, tk.CENTER),
            ("aliases", self.tr("preview.col.aliascodes"), 220, tk.W),
            ("old", self.tr("preview.col.oldwidth"), 75, tk.E),
            ("new", self.tr("preview.col.newwidth"), 75, tk.E),
            ("max", self.tr("preview.col.maxwidth"), 75, tk.E),
            ("bitmap", self.tr("preview.col.bitmap"), 70, tk.CENTER),
            ("bytes", self.tr("preview.col.changedbytes"), 95, tk.E),
        ])
        for row in snapshot["fonts"]:
            aliases = ", ".join(f"0x{value:02X}" for value in row["alias_codes"]) or "—"
            font_tree.insert("", tk.END, values=(
                row["status"], row["font"], f"0x{row['glyph_offset']:X}",
                f"0x{row['canonical_code']:02X}", aliases, row["old_width"],
                row["new_width"], row["max_width"],
                flag(row["bitmap_changed"]),
                row["changed_physical_bytes"],
            ), tags=(row["status"],))

        ttk.Button(dialog, text=self.tr("dlg.preview.close"),
                   command=dialog.destroy).pack(pady=(2, 10))

    def show_changes_preview(self):
        if not self._supported_loaded():
            messagebox.showwarning(self.tr("dlg.preview.warn"), self.tr("dlg.preview.load_first"))
            return False
        try:
            snapshot = self._build_changes_preview()
        except (DiffPreviewError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.preview.failed"),
                                 self.tr("dlg.import.nochange", error=exc))
            return False
        self.filter_records_dirty = True
        self.refresh_table()
        self.update_free_space_label()
        self._show_preview_dialog(snapshot)
        return True

    def update_free_space_label(self, live_override=None):
        if not hasattr(self, "current_range_label") or not self.profile:
            if hasattr(self, "current_range_label"): self.current_range_label.config(text="")
            return
        if self.current_index is None or not self.initial_unpacked_data:
            self.current_range_label.config(text="")
            return
        entry = self.entries[self.current_index]
        pending_raw = None
        if live_override and live_override[0] is entry:
            pending_raw = live_override[1].encode("latin-1")
        elif self.translation_pending:
            try:
                pending_raw = self._encode_entry_text(
                    entry, self.translate_text.get("1.0", "1.0 lineend")
                )
            except (CharmapEncodeError, TextTransactionError):
                pending_raw = None
        try:
            info = selected_string_status(
                self.initial_unpacked_data,
                entry,
                self.profile,
                self._get_font_for_entry(entry),
                pending_raw=pending_raw,
                cached_snapshot=self.diff_preview_cache.get(),
            )
        except (DiffPreviewError, KeyError, ValueError) as exc:
            self.current_range_label.config(
                text=self.tr("edit.diff_unavailable", error=exc), foreground="#C0392B"
            )
            return
        delta = f"{info['delta']:+d}"
        if info["kind"] == "fixed":
            capacity = info["fixed_capacity_bytes"]
            rest = info["fixed_free"]
            suffix = self.tr("edit.fixed_rest", rest=rest, cap=capacity)
        else:
            block = "—" if info["block"] is None else info["block"] + 1
            rest = info["shared_block_free"]
            suffix = (
                self.tr("edit.block_rest", block=block, rest=rest)
                if rest is not None else
                self.tr("edit.block_preview", block=block)
            )
        self.current_range_label.config(
            text=self.tr("edit.range_info", kind=info["kind"], font=info["font"],
                         old=info["old_length"], new=info["new_length"],
                         delta=delta, status=info["status"], suffix=suffix),
            foreground={
                "FAIL": "#C0392B",
                "PENDING": "#B9770E",
                "PASS": "#1E8449",
                "READ-ONLY": "#566573",
                "UNCHANGED": "#2980B9",
            }.get(info["status"], "#2980B9"),
        )

    def detect_profile(self, data):
        header = f"[detect_profile] file size={hex(len(data))}, MZ={bytes(data[:2]) if len(data) >= 2 else '?'}"
        all_logs = [header]
        matches = []
        for name, profile in GAME_PROFILES.items():
            all_logs.append(f"[detect_profile] --- testing profile: {name} ---")
            matched, lines = _matches_immutable_profile(data, profile, collect=True)
            all_logs.extend(lines)
            if matched:
                matches.append(name)
        result = matches[0] if len(matches) == 1 else None
        if result is not None:
            print(f"[detect_profile] detected={result}")
        else:
            for line in all_logs:
                print(line)
            print(f"[detect_profile] result=None  (all matches={matches})")
        return result

    def _reset_state(self):
        self._invalidate_diff_preview("reset", refresh=False)
        self.exe_data               = bytearray()
        self.entries                = []
        self.visible_string_ids     = []
        self.entry_index_by_id      = {}
        self.current_index          = None
        self.profile_name           = None
        self.profile                = None
        self.is_supported           = False
        self.relocation_sites       = []
        self.integrity_valid        = False
        self.repack_required        = False
        self.validation_errors      = []
        self.source_path            = None
        self.original_source_data   = bytearray()
        self.initial_unpacked_data  = bytearray()
        self.last_saved_exe_data    = bytearray()
        self.font_valid             = False
        self.font_pending           = False
        self.font_errors            = []
        self.translation_pending    = False
        self._last_valid_year       = None
        self.year_var.set("")
        self._last_valid_region_index = None
        self.region_var.set("")
        self._converted_to_extended = False
        self.filter_records         = ()
        self.filter_records_by_id   = {}
        self.baseline_filter_data   = {}
        self.filter_refresh_pending = False
        self.filter_records_dirty   = True
        self.filter_index_error     = None
        self._filter_callbacks_suspended = True
        try:
            self.search_var.set("")
            self.kind_filter_var.set("All")
            self.font_filter_var.set("All")
            self.change_filter_var.set("All")
            self.status_filter_var.set("All")
            self.filter_combos[1].config(values=("All",))
        finally:
            self._filter_callbacks_suspended = False
        self.tree.delete(*self.tree.get_children())
        self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.config(height=1)
        self.translate_text.config(state=tk.NORMAL, bg="#FFFFFF")
        self._set_translation_text("", pending=False)
        self.translate_text.config(height=1)
        self.space_stats_label.config(text="")
        self.translate_status_label.config(text="")
        self._set_profile("header.profile_none")
        self.filename_label.config(text="")
        self._set_status("header.no_file")
        self._set_counter(0, 0)
        self._set_filter_status(None)
        if hasattr(self, "current_range_label"):
            self.current_range_label.config(text="")
        if hasattr(self, "font_editor"):
            self.font_editor.reset_state()
        mana_panel = getattr(self, "mana_editor_panel", None)
        if mana_panel is not None:
            mana_panel.show_placeholder()
        self._set_supported_state(False)

    def _prepare_load_content(self, data: bytearray, profile: dict):
        relocation_sites = get_mz_relocation_sites(data)
        inventory = build_reference_inventory(data, profile, relocation_sites)
        by_str_addr = {}
        fixed_entries = []

        def read_null(offset):
            end = data.find(b"\x00", offset)
            return "" if end == -1 else data[offset:end].decode("latin-1")

        for fixed_addr, fixed_max_len in profile.get("fixed_strings", []):
            entry = {
                "ptr_addrs": [], "code_ptr_addrs": [], "ptr_base_const": None,
                "str_addr": fixed_addr, "original_str_addr": fixed_addr,
                "text": read_null(fixed_addr)[:fixed_max_len - 1],
                "max_len": fixed_max_len, "fixed": True,
            }
            entry["string_id"] = make_string_id(entry)
            fixed_entries.append(entry)

        def entry_for(str_addr):
            if str_addr not in by_str_addr:
                by_str_addr[str_addr] = {
                    "ptr_addrs": [], "code_ptr_addrs": [],
                    "ptr_base_const": profile["base_const"],
                    "str_addr": str_addr, "original_str_addr": str_addr,
                    "text": read_null(str_addr), "max_len": 0,
                }
            return by_str_addr[str_addr]

        for ptr_addr, str_addr in sorted(inventory["normal"].items()):
            entry_for(str_addr)["ptr_addrs"].append(ptr_addr)
        for code_addr, str_addr in sorted(inventory["code"].items()):
            entry_for(str_addr)["code_ptr_addrs"].append(code_addr)

        dynamic = sorted(by_str_addr.values(), key=lambda entry: entry["str_addr"])
        for entry in dynamic:
            entry["ptr_addrs"] = sorted(set(entry["ptr_addrs"]))
            entry["code_ptr_addrs"] = sorted(set(entry["code_ptr_addrs"]))
            entry["string_id"] = make_string_id(entry)
        entries = fixed_entries + dynamic
        validation = validate_image(data, profile, entries, relocation_sites)
        return entries, relocation_sites, validation

    def _confirm_discard_for_load(self) -> bool:
        if not self._has_unsaved_changes():
            return True
        return messagebox.askyesno(self.tr("dlg.unsaved.title"), self.tr("dlg.unsaved.load"))

    def _on_close_request(self):
        try:
            unsaved = self._has_unsaved_changes()
        except Exception:
            unsaved = True
        if unsaved and not messagebox.askyesno(
            self.tr("dlg.unsaved.title"), self.tr("dlg.unsaved.close")
        ):
            return
        self._cancel_free_space_update()
        self.root.destroy()

    def _show_integrity_dialog(self, validation, entries, relocation_sites):
        gaps = []
        try:
            gaps = find_unknown_gaps(self.exe_data, self.profile, entries, relocation_sites)
        except Exception:
            pass
        dlg = tk.Toplevel(self.root)
        dlg.title("Integrity Check Failed")
        dlg.resizable(True, True)
        dlg.grab_set()
        dlg.minsize(660, 300)
        tk.Label(
            dlg,
            text="Editing can be inspected, but Repack and Save are blocked.",
            font=("Segoe UI", 10, "bold"),
            fg="#C0392B",
            anchor="w",
            padx=12, pady=8,
        ).pack(fill=tk.X)

        if gaps:
            tk.Label(
                dlg,
                text=f"{len(gaps)} unknown gap(s) found. Auto-fix will zero-fill them.",
                font=("Segoe UI", 9),
                fg="#7D6608",
                anchor="w",
                padx=12, pady=0,
            ).pack(fill=tk.X)

        list_frame = tk.Frame(dlg, bg="#FFFFFF", bd=1, relief=tk.SUNKEN)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_inner = tk.Canvas(
            list_frame, bg="#FFFFFF", highlightthickness=0,
            yscrollcommand=vsb.set,
        )
        canvas_inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=canvas_inner.yview)
        rows_frame = tk.Frame(canvas_inner, bg="#FFFFFF")
        canvas_win = canvas_inner.create_window((0, 0), window=rows_frame, anchor="nw")

        def _on_rows_configure(event):
            canvas_inner.configure(scrollregion=canvas_inner.bbox("all"))
        def _on_canvas_resize(event):
            canvas_inner.itemconfig(canvas_win, width=event.width)
        rows_frame.bind("<Configure>", _on_rows_configure)
        canvas_inner.bind("<Configure>", _on_canvas_resize)

        if not gaps:
            tk.Label(
                rows_frame, text="No correctable gaps found.",
                font=("Segoe UI", 9), bg="#FFFFFF", fg="#555555",
                anchor="w", padx=8, pady=6,
            ).pack(fill=tk.X)
        else:
            for i, g in enumerate(gaps):
                raw = g["raw_bytes"]
                try:
                    display = raw.decode("latin-1")
                    display = "".join(
                        c if (0x20 <= ord(c) < 0x7F or ord(c) >= 0xA0) else "."
                        for c in display
                    ).rstrip(".")
                except Exception:
                    display = ""
                n_bytes = g["gap_end"] - g["gap_start"]
                line = (
                    f"{g['label']}: gap {g['gap_start']:#x}–{g['gap_end']:#x}"
                    f"  ({n_bytes} bytes)"
                    + (f"  —  Text: {display[:120]}" if display.strip(".") else "")
                )
                bg = "#FFFFFF" if i % 2 == 0 else "#F7F9FA"
                tk.Label(
                    rows_frame, text=line,
                    font=("Consolas", 9), bg=bg, fg="#2C3E50",
                    anchor="w", padx=8, pady=5,
                ).pack(fill=tk.X)
                tk.Frame(rows_frame, bg="#E8EAF0", height=1).pack(fill=tk.X)
        result = tk.BooleanVar(value=False)
        btn_row = tk.Frame(dlg)
        btn_row.pack(fill=tk.X, padx=12, pady=(0, 10))

        def _yes():
            result.set(True)
            dlg.destroy()

        def _no():
            result.set(False)
            dlg.destroy()

        if gaps:
            tk.Button(
                btn_row, text="Auto-fix",
                command=_yes, bg="#27AE60", fg="white",
                font=("Segoe UI", 9, "bold"), padx=12, pady=4,
            ).pack(side=tk.LEFT, padx=(0, 8))
            tk.Button(
                btn_row, text="Inspect only",
                command=_no, bg="#C0392B", fg="white",
                font=("Segoe UI", 9, "bold"), padx=12, pady=4,
            ).pack(side=tk.LEFT)
        else:
            tk.Button(
                btn_row, text="OK", command=_no,
                font=("Segoe UI", 9, "bold"), padx=12, pady=4,
            ).pack(side=tk.LEFT)

        dlg.wait_window()
        return result.get()

    def _zero_fill_gaps(self, gaps):
        for g in gaps:
            start, end = g["gap_start"], g["gap_end"]
            self.exe_data[start:end] = b"\x00" * (end - start)

    def load_exe(self):
        filepath = filedialog.askopenfilename(
            title=self.tr("fd.open_exe"),
            filetypes=[("DOS Executable", "*.exe"), ("All Files", "*.*")]
        )
        if not filepath or not self._confirm_discard_for_load():
            return

        try:
            with open(filepath, "rb") as handle:
                original_data = bytearray(handle.read())
            try:
                unpacked_data = unpack_in_memory(bytearray(original_data))
            except Exception:
                unpacked_data = bytearray(original_data)
            detected = self.detect_profile(unpacked_data)
            if detected is None:
                for candidate_name, candidate_profile in GAME_PROFILES.items():
                    if extended_layout.detect(unpacked_data, candidate_profile) is not None:
                        detected = candidate_name
                        break
                    if extended_layout.can_convert(unpacked_data, candidate_profile) is not None:
                        detected = candidate_name
                        break

            prepared = None
            if detected is not None:
                profile = GAME_PROFILES[detected]

                descriptor = extended_layout.can_convert(unpacked_data, profile)
                if descriptor is not None:
                    pool_start, pool_end = descriptor["pool"]
                    pool_kb = (pool_end - pool_start) // 1024
                    if messagebox.askyesno("Extended Layout",self.tr("dlg.load.extended", detected=detected, pool_kb=pool_kb)):
                        unpacked_data, _ = extended_layout.convert_to_extended(unpacked_data, profile)
                        self._converted_to_extended = True

                validate_all_fonts(unpacked_data, EXE_FONT_PROFILES[detected])
                prepared = self._prepare_load_content(unpacked_data, profile)
        except (OSError, ValueError, KeyError, FontSafetyError) as exc:
            messagebox.showerror(self.tr("dlg.load.failed"),
                                 self.tr("dlg.load.failed_msg", error=exc))
            return

        self._reset_state()
        self.source_path = os.path.abspath(filepath)
        exe_dir = os.path.dirname(os.path.abspath(self.source_path))
        pic_folder = os.path.join(exe_dir, "PIC")
        if os.path.isdir(pic_folder):
            self.vga_editor.set_pic_dir(pic_folder)
        else:
            self.vga_editor._pic_dir = ""
            self.vga_editor._pic_files = []
            self.vga_editor._file_combo.config(values=[])
            self.vga_editor._set_status("Nessuna cartella PIC trovata in questa directory.")
        self.original_source_data = bytearray(original_data)
        self.initial_unpacked_data = bytearray(unpacked_data)
        self.last_saved_exe_data = bytearray(unpacked_data)
        self.exe_data = bytearray(unpacked_data)
        self.filename_label.config(text=f"({os.path.basename(filepath)})")

        if detected is None:
            self._set_profile("dlg.load.unsupported_label", colour="#C0392B")
            self._set_status("dlg.load.unsupported_status")
            self._set_supported_state(False)
            return

        self.profile_name = detected
        self.profile = GAME_PROFILES[detected]
        extended = extended_layout.detect(self.exe_data, self.profile)
        profile_label = self.profile_name
        if extended is not None:
            profile_label = f"{self.profile_name} [EXTENDED]"
        self._set_profile(value=profile_label)
        gcfg = self._game_cfg()
        for key, value in self.profile.get("range_font_defaults", {}).items():
            gcfg["range_font_defaults"].setdefault(str(key), value)

        font_names = list(EXE_FONT_PROFILES[detected]["fonts"].keys())
        self.font_editor.set_font_names(font_names)
        self.font_editor.string_font_var.set(gcfg["range_font_defaults"].get("0", "FLOW.FON"))
        self.filter_combos[1].config(values=("All", *font_names))
        self.font_filter_var.set("All")

        entries, relocation_sites, validation = prepared
        self.entries = entries
        self.relocation_sites = relocation_sites
        self.integrity_valid = validation["ok"]
        self.repack_required = False
        self.validation_errors = list(validation["errors"])
        self._recalculate_max_lengths()
        if validation["ok"]:
            self._migrate_legacy_font_mappings()
        self._try_rebuild_baseline_filter_index()
        self.refresh_table(force=True)
        self.update_free_space_label()

        font_loaded = self.font_editor.load_from_raw(self.exe_data, detected)

        mana_panel = getattr(self, "mana_editor_panel", None)
        if mana_panel is not None:
            exe_dir = os.path.dirname(self.source_path)
            mana_path = None
            for candidate in ("MANA.DAT", "mana.dat", "Mana.dat"):
                candidate_path = os.path.join(exe_dir, candidate)
                if os.path.isfile(candidate_path):
                    mana_path = candidate_path
                    break
            if mana_path:
                mana_panel.load_file(mana_path)
            else:
                mana_panel.show_placeholder(
                    f"MANA.DAT not found in: {exe_dir}"
                )

        self._set_supported_state(True)
        self._read_year_from_exe()
        self._read_region_from_exe()
        self._read_points_from_exe()
        self.notebook.select(self.tab_strings)
        self._update_save_state()
        self.status_label.config(text="")
        if not font_loaded:
            self._set_status("dlg.load.font_failed")
            return
        if not validation["ok"]:
            self._set_status("dlg.load.integrity_status", error=validation["errors"][0])
            fix_chosen = self._show_integrity_dialog(validation, entries, relocation_sites)
            if fix_chosen:
                gaps = []
                try:
                    gaps = find_unknown_gaps(self.exe_data, self.profile, entries, relocation_sites)
                except Exception:
                    pass
                if gaps:
                    self._zero_fill_gaps(gaps)
                    new_validation = validate_image(
                        self.exe_data, self.profile, entries, relocation_sites
                    )
                    self.integrity_valid = new_validation["ok"]
                    self.validation_errors = list(new_validation["errors"])
                    if new_validation["ok"]:
                        self.initial_unpacked_data = bytearray(self.exe_data)
                        self.last_saved_exe_data   = bytearray(self.exe_data)
                        self._migrate_legacy_font_mappings()
                        self.status_label.config(text="")
                    else:
                        self._set_status("dlg.load.integrity_status",
                                         error=new_validation["errors"][0])
            self._try_rebuild_baseline_filter_index()
            self.refresh_table(force=True)
            self._update_save_state()
            if self.visible_string_ids:
                first_id = self.visible_string_ids[0]
                first_index = self.entry_index_by_id.get(first_id)
                if first_index is not None:
                    self.current_index = first_index
                    self._selection_guard = True
                    try:
                        self.tree.selection_set(first_id)
                        self.tree.focus(first_id)
                        self.tree.see(first_id)
                    finally:
                        self._selection_guard = False
                    self._display_entry(first_index)

    def save_exe(self):
        if not self._supported_loaded():
            messagebox.showwarning(self.tr("dlg.save.unsupported"),
                                   self.tr("dlg.save.unsupported_msg"))
            return False
        if self.font_valid and not self.font_pending:
            self.font_editor.validate_live_state()
        if not self._can_save():
            messagebox.showwarning(self.tr("dlg.save.blocked"), self._save_block_reason())
            return False
        filepath = filedialog.asksaveasfilename(
            title=self.tr("fd.save_exe"),
            defaultextension=".exe", filetypes=[("DOS Executable", "*.exe")]
        )
        if not filepath:
            return False

        payload, modified_from_source = self._save_payload()
        same_as_source = paths_equal(filepath, self.source_path)
        backup_original = False

        if same_as_source:
            try:
                with open(self.source_path, "rb") as handle:
                    current_source = handle.read()
            except OSError as exc:
                messagebox.showerror(self.tr("dlg.save.blocked"),
                                     self.tr("dlg.save.verify", error=exc))
                return False
            if current_source != bytes(self.original_source_data):
                messagebox.showerror(self.tr("dlg.save.blocked"), self.tr("dlg.save.external"))
                return False
            if not modified_from_source:
                messagebox.showinfo(self.tr("dlg.save.done"), self.tr("dlg.save.noop"))
                self.last_saved_exe_data = bytearray(self.exe_data)
                self._invalidate_diff_preview("save-baseline")
                self._try_rebuild_baseline_filter_index()
                self.refresh_table(force=True, refresh_active_fields=True)
                return True
            if not messagebox.askyesno(
                self.tr("dlg.save.overwrite_title"), self.tr("dlg.save.overwrite_msg")
            ):
                return False
            backup_original = True

        try:
            backup_path = atomic_save_bytes(
                filepath, payload, backup_original=backup_original
            )
        except OSError as exc:
            messagebox.showerror(self.tr("dlg.save.failed"),
                                 self.tr("dlg.save.failed_msg", error=exc))
            return False

        self.source_path = os.path.abspath(filepath)
        self.original_source_data = bytearray(payload)
        self.initial_unpacked_data = bytearray(self.exe_data)
        self.last_saved_exe_data = bytearray(self.exe_data)
        self.font_editor.mark_saved()
        self._invalidate_diff_preview("save-baseline", refresh=False)
        self._try_rebuild_baseline_filter_index()
        self.filename_label.config(text=f"({os.path.basename(filepath)})")
        self._update_save_state()
        self.refresh_table(force=True, refresh_active_fields=True)
        self.update_free_space_label()

        mana_panel = getattr(self, "mana_editor_panel", None)
        if mana_panel is not None and mana_panel.is_dirty:
            mana_panel.save_if_dirty()

        backup_note = self.tr("dlg.save.backup", path=backup_path) if backup_path else ""
        messagebox.showinfo(self.tr("dlg.save.done"),
                            self.tr("dlg.save.done_msg", path=filepath, backup=backup_note))
        return True

__all__ = ['DOSTranslationEditor']

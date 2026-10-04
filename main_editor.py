import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from exe_handler import unpack_in_memory, get_mz_relocation_sites, detect_game_profile, GAME_PROFILES, EXE_FONT_PROFILES
from charmap import CharmapEncodeError
from translation_bar import TranslationBar
from utils import (load_config, save_config, get_game_config, set_translator as _set_utils_translator)
import i18n
from font_editor import EXEFontEditor
from font_safety import FontSafetyError, atomic_save_bytes, paths_equal, validate_all_fonts
import extended_layout
from mana_editor import ManaEditorPanel
from vga_editor import PicEditorPanel
from tore_editor import ToreEditorPanel
import newspaper_csv
from newspaper_grammar import NewspaperGrammarError
import newspaper_editor as _ne
from repack_validator import build_reference_inventory, find_unknown_gaps, make_string_id, validate_image
from string_exchange import (
    StringExchangeError,
    build_export_document,
    export_json_bytes,
    export_csv_bytes,
    parse_csv_document,
    preflight_import_json,
    exchange_text_to_raw,
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
from exe_settings_mixin import ExeSettingsMixin
from string_codec_mixin import StringCodecMixin, TextTransactionError
from preview_dialog import show_preview_dialog, show_integrity_dialog

APP_VERSION = "2.9.2"
APP_TITLE = f"THE MANAGER / Bundesliga Manager Professional Editor v{APP_VERSION} ——— by TheRuler76 & Nobody"
DEFAULT_LANGUAGE = "en"
ICON_FILE = "THE_MANAGER_String_Editor.ico"


class DOSTranslationEditor(ExeSettingsMixin, StringCodecMixin):

    def __init__(self, root):
        self.root = root
        self.language = DEFAULT_LANGUAGE
        self.filter_status_key = None
        self.filter_status_args = {}
        self._status_state = ("header.no_file", {})
        self._profile_state = ("header.profile_none", None, "#2980B9")
        self.root.title(APP_TITLE)
        self._apply_window_icon()
        self.root.geometry("1280x880")
        self.root.minsize(780, 600)
        self._init_document_state()
        self.diff_preview_cache    = PreviewCache()
        self._filter_callbacks_suspended = False
        self._selection_guard      = False
        self._free_space_after_id  = None
        self._free_space_override  = None
        self._apply_modern_style()
        self._init_language()
        self.cfg = load_config()
        self._build_gui()

    def _init_document_state(self):
        self.exe_data = bytearray()
        self.entries = []
        self.visible_string_ids = []
        self.entry_index_by_id = {}
        self.current_index = None
        self.profile_name = None
        self.profile = None
        self.is_supported = False
        self.relocation_sites = []
        self.integrity_valid = False
        self.repack_required = False
        self.validation_errors = []
        self.source_path = None
        self.original_source_data = bytearray()
        self.initial_unpacked_data = bytearray()
        self.last_saved_exe_data = bytearray()
        self.font_valid = False
        self.font_pending = False
        self.font_errors = []
        self.translation_pending = False
        self._last_valid_year = None
        self._last_valid_region_a = None
        self._last_valid_region_b = None
        self._last_valid_points = None
        self._last_valid_subst_gk = None
        self._last_valid_subst = None
        self._last_valid_teams = None
        self._last_valid_goal_frames = None
        self._converted_to_extended = False
        self._integrity_fixed = False
        self.filter_records = ()
        self.filter_records_by_id = {}
        self.baseline_filter_data = {}
        self.filter_refresh_pending = False
        self.filter_records_dirty = True
        self.filter_index_error = None

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
        tools_menu.add_command(label=self.tr("menu.tools.export_csv"), command=self.export_normal_csv)
        tools_menu.add_command(label=self.tr("menu.tools.import_csv"), command=self.import_normal_csv)
        tools_menu.add_separator()
        tools_menu.add_command(label=self.tr("menu.tools.export_news"), command=self.export_newspaper_csv)
        tools_menu.add_command(label=self.tr("menu.tools.import_news"), command=self.import_newspaper_csv)
        tools_menu.add_separator()
        tools_menu.add_command(label=self.tr("menu.tools.export_json"), command=self.export_all_json)
        tools_menu.add_command(label=self.tr("menu.tools.import_json"), command=self.import_all_json)
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
        view_menu.add_command(label="TORE Editor", command=lambda: self._select_tab("tab_tore"))
        view_menu.add_separator()
        lang_menu = tk.Menu(view_menu, tearoff=0)
        self.language_var = tk.StringVar(value=self.language)
        for code, name in self._languages:
            lang_menu.add_radiobutton(label=name, value=code, variable=self.language_var,command=self._on_language_change,)
        view_menu.add_cascade(label=self.tr("menu.view.language"), menu=lang_menu)
        self.menubar.add_cascade(label=self.tr("menu.view"), menu=view_menu)
        self.view_menu = view_menu
        self.language_menu = lang_menu
        self.save_menu_entries = [(file_menu, 1)]
        self.exchange_menu_entries = [
            (tools_menu, 2), (tools_menu, 3),
            (tools_menu, 5), (tools_menu, 6),
            (tools_menu, 8), (tools_menu, 9) 
        ]
        self.supported_menu_entries = [
            (tools_menu, 0), (tools_menu, 11),
            (view_menu, 0), (view_menu, 1), (view_menu, 2), (view_menu, 3), (view_menu, 4)
        ]
        self.root.config(menu=self.menubar)
        self._set_menu_state(self.save_menu_entries + self.exchange_menu_entries, False)

    def _retranslate_menu(self):
        for index, key in ((0, "menu.file"), (1, "menu.tools"), (2, "menu.view")):
            try:
                self.menubar.entryconfig(index, label=self.tr(key))
            except tk.TclError:
                pass
                
        for menu, items in (
            (self.file_menu, (
                (0, "menu.file.open"), 
                (1, "menu.file.save_as"),
                (3, "menu.file.quit")
            )),
            (self.tools_menu, (
                (0, "menu.tools.details"),
                (2, "menu.tools.export_csv"),
                (3, "menu.tools.import_csv"),
                (5, "menu.tools.export_news"),
                (6, "menu.tools.import_news"),
                (8, "menu.tools.export_json"),
                (9, "menu.tools.import_json"),
                (11, "menu.tools.autotranslate"),
                (12, "menu.tools.translate_all")
            )),
            (self.view_menu, (
                (0, "menu.view.strings"), 
                (1, "menu.view.fonts"),
                (5, "menu.view.language")
            )),
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
    
    def _update_translate_all_state(self):
        enabled = bool(getattr(self, "is_supported", False)) and self.translate_enabled_var.get()
        self._set_menu_state([(self.tools_menu, 12)], enabled)

    def _reg(self, widget, key):
        widget.config(text=self.tr(key))
        self._i18n_widgets.append((widget, key))
        return widget

    def _reg_tab(self, tab, key):
        self._i18n_tabs.append((tab, key))
        return tab

    @staticmethod
    def _and_break(func):
        def handler(event=None):
            func()
            return "break"
        return handler

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
        self.status_label.config(text=self.tr(key, **fmt) if key else "")
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
        self._apply_translation_defaults(target=True)
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
        for name, key in (("num", "col.num"), ("offset", "col.offset"), ("pointer", "preview.col.pointers"), ("text", "col.text")):
            try:
                self.tree.heading(name, text=self.tr(key))
            except tk.TclError:
                pass
        self.filter_toggle_button.config(
            text=self.tr("filter.toggle_open" if self.filter_frame.winfo_manager() else "filter.toggle_closed"))
        shown, total = self._counter_state
        self._set_counter(shown, total)
        self._set_filter_status(self.filter_status_key, **self.filter_status_args)
        if self._region_offset() is not None:
            values = self._region_values()
            for combo in (self.region_a_combo, self.region_b_combo):
                index = combo.current()
                combo.config(values=values)
                if index >= 0:
                    combo.current(index)
        current_idx = self._flag_type_combo.current()
        new_values = [self.tr(label_key) for label_key, _ in self._FLAG_TYPES]
        self._flag_type_combo.config(values=new_values)
        if current_idx >= 0:
            self._flag_type_combo.current(current_idx)
        self._update_panel_action_buttons()
        self._render_header()
        self.font_editor.retranslate()

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
        self.status_label   = ttk.Label(top_frame, font=("Segoe UI", 9, "italic"))
        self.status_label.pack(side=tk.RIGHT)
        self._render_header()
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=(10, 3))
        style.map("TNotebook.Tab",font=[("selected", ("Segoe UI", 9, "bold"))],padding=[("selected", (10, 4))])
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
        self.search_entry.bind("<Escape>", self._and_break(self.clear_filters))
        self.showing_label = ttk.Label(self.search_frame,text=self.tr("status.counter", shown=0, total=0),font=("Segoe UI", 9, "bold"),foreground="#2980B9",)
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
            self._reg(ttk.Label(self.filter_frame, font=("Segoe UI", 9, "bold")), label).pack(side=tk.LEFT, padx=(0 if not self.filter_combos else 10, 3))
            combo = ttk.Combobox(self.filter_frame,textvariable=variable,values=values,state="readonly",width=width,)
            combo.pack(side=tk.LEFT)
            combo.bind("<<ComboboxSelected>>", self.on_filter_change)
            self.filter_combos.append(combo)
        self.clear_filters_button = ttk.Button(self.filter_frame, command=self.clear_filters)
        self._reg(self.clear_filters_button, "filter.reset")
        self.clear_filters_button.pack(side=tk.RIGHT)
        self.search_var.trace_add("write", self.on_filter_change)
        self.supported_controls.extend((self.search_entry, self.clear_filters_button, self.filter_toggle_button,*self.filter_combos))
        status_frame = ttk.Frame(self.tab_strings, padding=(15, 0, 15, 4))
        status_frame.pack(fill=tk.X)
        self.filter_status_label = ttk.Label(status_frame, text="", font=("Segoe UI", 9, "bold"), foreground="#B9770E")
        self.filter_status_label.pack(side=tk.LEFT)
        main_frame = ttk.Frame(self.tab_strings, padding=(15, 0, 15, 8))
        main_frame.pack(fill=tk.BOTH, expand=True)
        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_container, columns=("num", "offset", "pointer", "text"), show="headings", selectmode="browse")
        self.tree.heading("num",     text=self.tr("col.num"))
        self.tree.heading("offset",  text=self.tr("col.offset"))
        self.tree.heading("pointer", text=self.tr("preview.col.pointers"))
        self.tree.heading("text",    text=self.tr("col.text"))
        self.tree.column("num",     anchor=tk.CENTER, width=30,  stretch=False)
        self.tree.column("offset",  anchor=tk.CENTER, width=75, stretch=False)
        self.tree.column("pointer", anchor=tk.CENTER, width=75, stretch=False)
        self.tree.column("text",    anchor=tk.W,      stretch=True)
        v_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Button-3>", self._on_tree_right_click)
        edit_frame = ttk.LabelFrame(self.tab_strings, padding=15)
        _lf_header = ttk.Frame(edit_frame)
        self._edit_frame_title = ttk.Label(_lf_header,text=self.tr("edit.frame"),font=("Segoe UI", 10, "bold"),foreground="#2C3E50",)
        self._edit_frame_title.pack(side=tk.LEFT)
        self._copied_label = ttk.Label(_lf_header,text="",font=("Segoe UI", 9, "bold"),foreground="#27AE60",)
        self._copied_label.pack(side=tk.LEFT, padx=(6, 0))
        edit_frame.config(labelwidget=_lf_header)
        self._i18n_widgets.append((self._edit_frame_title, "edit.frame"))
        edit_frame.pack(fill=tk.X, padx=15, pady=(5, 12))
        self._copied_after_id = None
        self.edit_text = self._make_text_widget(edit_frame)
        self.edit_text.bind("<KeyRelease>", self.on_text_modified)
        self.edit_text.bind("<Return>", self._and_break(self.apply_edit))
        self.edit_text.bind("<Control-Return>", self._and_break(self.apply_edit))
        self.info_frame = info_frame = ttk.Frame(edit_frame)
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
        self.supported_controls.append(self.discard_edit_button)
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
        self.export_strings_button = ttk.Button(ctrl_row, command=self._panel_export)
        self.export_strings_button.config(text=self.tr("action.export_normal"))
        self.export_strings_button.pack(side=tk.LEFT, padx=(6, 0))
        self.import_strings_button = ttk.Button(ctrl_row, command=self._panel_import)
        self.import_strings_button.config(text=self.tr("action.import_normal"))
        self.import_strings_button.pack(side=tk.LEFT, padx=(6, 0))
        self.font_assign_button = ttk.Button(ctrl_row, command=self._goto_font_assign)
        self._reg(self.font_assign_button, "action.font_assign")
        self.font_assign_button.pack(side=tk.LEFT, padx=(6, 0))
        self.supported_controls.extend((self.newspaper_editor_check,self.translate_enabled_check,self.preview_button,))
        self.translation_bar = TranslationBar(edit_frame, on_translate=self._translate_current_entry, reg=self._reg)
        self.translate_section = self.translation_bar
        self.engine_var = self.translation_bar.engine_var
        self.source_lang_var = self.translation_bar.source_lang_var
        self.target_lang_var = self.translation_bar.target_lang_var
        self.translate_now_button = self.translation_bar.button
        self.translate_status_label = self.translation_bar.status_label
        self.supported_controls.extend(self.translation_bar.controls)
        self._apply_translation_defaults(target=True)
        self.newspaper_panel = _ne.NewspaperEditorPanel(edit_frame, self,on_show=self._hide_edit_text,on_hide=self._show_edit_text,)
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
            translate=self.tr,)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_settings, text=self.tr("tab.options"))
        self._reg_tab(self.tab_settings, "tab.options") 
        settings_frame = ttk.LabelFrame(self.tab_settings)
        settings_frame.pack(fill=tk.X, padx=15, pady=15)
        self.year_container = ttk.Frame(settings_frame)
        self.year_label = self._reg(ttk.Label(self.year_container, font=("Segoe UI", 9, "bold")), "header.year")
        self.year_label.pack(side=tk.LEFT, padx=(0, 8))
        self.year_var = tk.StringVar()
        self.year_spinbox = ttk.Spinbox(self.year_container, from_=self._YEAR_MIN, to=self._YEAR_MAX, increment=1,width=6, justify=tk.CENTER, font=("Segoe UI", 9),textvariable=self.year_var, command=self._commit_year,)
        self.year_spinbox.pack(side=tk.LEFT)
        self.year_spinbox.bind("<Return>", self._commit_year)
        self.year_spinbox.bind("<KP_Enter>", self._commit_year)
        self.year_spinbox.bind("<FocusOut>", self._commit_year)
        self.region_container = ttk.Frame(settings_frame)
        self.region_a_label = self._reg(ttk.Label(self.region_container, font=("Segoe UI", 9, "bold")), "header.region.a")
        self.region_a_label.pack(side=tk.LEFT, padx=(0, 8))
        self.region_a_var = tk.StringVar()
        self.region_a_combo = ttk.Combobox(self.region_container,textvariable=self.region_a_var,state="readonly",width=12,justify=tk.LEFT,font=("Segoe UI", 9),)
        self.region_a_combo.pack(side=tk.LEFT)
        self.region_b_label = self._reg(ttk.Label(self.region_container, font=("Segoe UI", 9, "bold")), "header.region.b")
        self.region_b_label.pack(side=tk.LEFT, padx=(18, 8))
        self.region_b_var = tk.StringVar()
        self.region_b_combo = ttk.Combobox(self.region_container,textvariable=self.region_b_var,state="readonly",width=12,justify=tk.LEFT,font=("Segoe UI", 9),)
        self.region_b_combo.pack(side=tk.LEFT)
        self.region_a_combo.bind("<<ComboboxSelected>>", self._commit_region_a)
        self.region_b_combo.bind("<<ComboboxSelected>>", self._commit_region_b)
        self.points_container = ttk.Frame(settings_frame)
        self.points_label = self._reg(ttk.Label(self.points_container, font=("Segoe UI", 9, "bold")), "header.point")
        self.points_label.pack(side=tk.LEFT, padx=(0, 8))
        self.points_var = tk.StringVar()
        self.points_combo = ttk.Combobox(self.points_container, textvariable=self.points_var, state="readonly",width=4, justify=tk.CENTER, font=("Segoe UI", 9),values=["2", "3"],)
        self.points_combo.pack(side=tk.LEFT)
        self.points_combo.bind("<<ComboboxSelected>>", self._commit_points)
        self.points_combo.bind("<Return>", self._commit_points)
        self.points_combo.bind("<KP_Enter>", self._commit_points)
        self.points_combo.bind("<FocusOut>", self._commit_points)
        self.subst_container = ttk.Frame(settings_frame)
        self.subst_label = self._reg(ttk.Label(self.subst_container, font=("Segoe UI", 9, "bold")), "header.subst")
        self.subst_label.pack(side=tk.LEFT, padx=(0, 8))
        self.subst_gk_var = tk.StringVar()
        self.subst_gk_combo = ttk.Combobox(self.subst_container, textvariable=self.subst_gk_var, state="readonly",width=3, justify=tk.CENTER, font=("Segoe UI", 9), values=["1", "2"],)
        self.subst_gk_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.subst_gk_combo.bind("<<ComboboxSelected>>", self._commit_subst_gk)
        self.subst_var = tk.StringVar()
        self.subst_combo = ttk.Combobox(self.subst_container, textvariable=self.subst_var, state="readonly",width=3, justify=tk.CENTER, font=("Segoe UI", 9), values=["2", "3", "4"],)
        self.subst_combo.pack(side=tk.LEFT)
        self.subst_combo.bind("<<ComboboxSelected>>", self._commit_subst)
        self.teams_container = ttk.Frame(settings_frame)
        self.teams_label = self._reg(ttk.Label(self.teams_container, font=("Segoe UI", 9, "bold")), "header.teams")
        self.teams_label.pack(side=tk.LEFT, padx=(0, 8))
        self.teams_var = tk.StringVar()
        self.teams_combo = ttk.Combobox(self.teams_container, textvariable=self.teams_var, state="readonly", width=4, justify=tk.CENTER, font=("Segoe UI", 9), values=["20", "18"])
        self.teams_combo.pack(side=tk.LEFT)
        self.teams_combo.bind("<<ComboboxSelected>>", self._commit_teams)
        self.teams_combo.bind("<Return>", self._commit_teams)
        self.teams_combo.bind("<KP_Enter>", self._commit_teams)
        self.teams_combo.bind("<FocusOut>", self._commit_teams)
        self.goal_frames_container = ttk.Frame(settings_frame)
        self.goal_frames_label = self._reg(ttk.Label(self.goal_frames_container, font=("Segoe UI", 9, "bold")), "header.goal_frames")
        self.goal_frames_label.pack(side=tk.LEFT, padx=(0, 8))
        self.goal_frames_var = tk.StringVar()
        self.goal_frames_combo = ttk.Combobox(self.goal_frames_container, textvariable=self.goal_frames_var, state="readonly", width=4, justify=tk.CENTER, font=("Segoe UI", 9), values=["256", "128"])
        self.goal_frames_combo.pack(side=tk.LEFT)
        self.goal_frames_combo.bind("<<ComboboxSelected>>", self._commit_goal_frames)
        self.goal_frames_combo.bind("<Return>", self._commit_goal_frames)
        self.goal_frames_combo.bind("<KP_Enter>", self._commit_goal_frames)
        self.goal_frames_combo.bind("<FocusOut>", self._commit_goal_frames)
        self._wdl_char_values = [bytes([i]).decode("cp437") for i in range(0x20, 0x7e)]
        self.flag_container = ttk.Frame(settings_frame)
        flag_title_row = ttk.Frame(self.flag_container)
        flag_title_row.pack(fill=tk.X, anchor="w", pady=(0, 2))
        self.wdl_title_label = self._reg(ttk.Label(flag_title_row, font=("Segoe UI", 9, "bold")), "header.wdl")
        self.wdl_title_label.pack(side=tk.LEFT)
        self.wdl_container = ttk.Frame(self.flag_container)
        self.wdl_container.pack(fill=tk.X, anchor="w", pady=(0, 4))
        self._wdl_title_labels = []
        for col in range(3):
            grp = tk.Frame(self.wdl_container, bg="#F4F6F9", bd=1, relief=tk.SOLID,highlightthickness=0, padx=3, pady=1)
            grp.pack(side=tk.LEFT, padx=(0 if col == 0 else 3, 0))
            lbl = self._reg(tk.Label(grp, bg="#F4F6F9", fg="#2C3E50", font=("Segoe UI", 7), anchor=tk.CENTER, justify=tk.CENTER),"wdl.awayhome")
            lbl.pack(fill=tk.X)
            self._wdl_title_labels.append(lbl)
            chars_row = tk.Frame(grp, bg="#F4F6F9")
            chars_row.pack(fill=tk.X, pady=(1, 0))
            for s_col in range(2):
                v = tk.StringVar()
                combo = ttk.Combobox(chars_row, textvariable=v, values=self._wdl_char_values,state="readonly", width=3, justify=tk.CENTER,font=("Segoe UI Symbol", 9))
                combo.pack(side=tk.LEFT, padx=(0 if s_col == 0 else 2, 0))
                box_index = col * 2 + s_col
                combo.bind("<<ComboboxSelected>>", lambda _ev, i=box_index: self._commit_wdl(i))
                setattr(self, f"_wdl_var_{box_index}", v)
                setattr(self, f"_wdl_combo_{box_index}", combo)
        self._wdl_last_valid = [None] * 6
        flag_row = ttk.Frame(self.flag_container)
        flag_row.pack(anchor="w")
        flag_type_col = ttk.Frame(flag_row)
        flag_type_col.pack(side=tk.LEFT, anchor="n", padx=(0, 8))
        self.match_label = self._reg(ttk.Label(flag_type_col, font=("Segoe UI", 9, "bold")), "header.match")
        self.match_label.pack(anchor="w")
        self._flag_type_var = tk.StringVar()
        self._flag_type_combo = ttk.Combobox(flag_type_col, textvariable=self._flag_type_var,state="readonly", width=22, font=("Segoe UI", 9),)
        new_values = [self.tr(label_key) for label_key, _ in self._FLAG_TYPES]
        self._flag_type_combo.config(values=new_values)
        self._flag_type_combo.pack(anchor="w", pady=(0, 4))
        self._flag_type_combo.bind("<<ComboboxSelected>>", self._on_flag_type_changed)
        FLAG_W, FLAG_H = 90, 60
        self._flag_canvas = tk.Canvas(flag_row, width=FLAG_W, height=FLAG_H,highlightthickness=1,highlightbackground="#888888",cursor="hand2")
        self._flag_canvas.pack(side=tk.LEFT, anchor="n", padx=(0, 8))
        self._flag_canvas.bind("<Button-1>", self._on_flag_canvas_click)
        self._flag_selected_band = None
        self._flag_palette_popup = None
        self._flag_pal_canvas = None
        self._flag_pal_sq = 14
        self._flag_pal_cols = 16
        self._flag_colors = [0, 0, 0]
        self._flag_font_color = 0
        self._flag_last_valid_type = None
        self.tab_mana = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_mana, text="MANA.DAT")
        self.mana_editor_panel = ManaEditorPanel(self.tab_mana)
        self.mana_editor_panel.pack(fill=tk.BOTH, expand=True)
        self.tab_vga = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_vga, text="VGA Editor")
        self.vga_editor = PicEditorPanel(self.tab_vga, standalone=False)
        self.vga_editor.pack(fill=tk.BOTH, expand=True)
        self.tab_tore = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tore, text="TORE Editor")
        self.tore_editor = ToreEditorPanel(self.tab_tore, standalone=False)
        self.tore_editor.pack(fill=tk.BOTH, expand=True)
        self._set_supported_state(False)
        self.notebook.select(self.tab_strings)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _set_supported_state(self, supported: bool):
        self.is_supported = bool(supported and self.profile_name and self.profile and self.exe_data)
        state = tk.NORMAL if self.is_supported else tk.DISABLED
        for tab in (self.tab_strings, self.tab_fonts, self.tab_settings, self.tab_mana, self.tab_vga, self.tab_tore):
            self.notebook.tab(tab, state=state)
        self._set_menu_state(self.supported_menu_entries, self.is_supported)
        self._update_translate_all_state()
        for widget in self.supported_controls:
            widget.config(state="readonly" if self.is_supported and isinstance(widget, ttk.Combobox) else state)
        self.edit_text.config(state=state)
        self.font_editor.set_enabled(self.is_supported and self.font_editor.is_supported)
        self._sync_year_widget()
        self._sync_region_widget()
        self._sync_points_widget()
        self._sync_subst_widget()
        self._sync_teams_widget()
        self._sync_goal_frames_widget()
        self._sync_wdl_widget()
        self._sync_flag_widget()
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

    def _active_newspaper_panel(self):
        panel = getattr(self, "newspaper_panel", None)
        return panel if panel is not None and panel.winfo_manager() else None

    def _flush_pending_refresh(self):
        if self.filter_refresh_pending and not self._has_pending_text_edit():
            self.refresh_table(force=True, refresh_active_fields=True)

    def _is_edit_text_dirty(self) -> bool:
        if not self._supported_loaded() or self.current_index is None:
            return False
        if self._active_newspaper_panel() is not None:
            return False
        widget = self.edit_text
        if str(widget.cget("state")) == "disabled":
            return False
        try:
            displayed = widget.get("1.0", "1.0 lineend")
            expected = self._decode_entry_text(self.entries[self.current_index])
            return displayed != expected
        except Exception:
            return False

    def _update_discard_button_state(self):
        button = getattr(self, "discard_edit_button", None)
        if button is not None:
            button.config(state=tk.NORMAL if self._has_pending_text_edit() else tk.DISABLED)

    def apply_edit(self):
        panel = self._active_newspaper_panel()
        if panel is not None:
            return panel.apply()
        return self._apply_text_widget(self.edit_text)

    def discard_edit(self):
        panel = self._active_newspaper_panel()
        if panel is not None:
            panel.discard()
        else:
            if not self._supported_loaded() or self.current_index is None:
                return
            self._refresh_current_entry_display()
            self.translate_status_label.config(text="")
        self._cancel_free_space_update()
        self.update_free_space_label()
        self._update_save_state()
        self._flush_pending_refresh()

    def _has_pending_text_edit(self) -> bool:
        if not self._supported_loaded() or self.current_index is None:
            return False
        panel = self._active_newspaper_panel()
        if panel is not None:
            return bool(panel.is_dirty())
        return self._is_edit_text_dirty()

    def _has_committed_changes(self) -> bool:
        return bool(
            self.last_saved_exe_data
            and bytes(self.exe_data) != bytes(self.last_saved_exe_data)
        )

    def _has_unsaved_changes(self) -> bool:
        return bool(
            self._has_committed_changes()
            or self._converted_to_extended
            or self._integrity_fixed
            or self.font_pending
            or self._has_pending_text_edit()
        )

    def _can_exchange_strings(self) -> bool:
        return bool(
            self._supported_loaded()
            and self.integrity_valid
            and not self.repack_required
            and self.font_valid
            and not self.font_pending
        )

    def _can_save(self) -> bool:
        return bool(
            self._can_exchange_strings()
            and not self._has_pending_text_edit()
            and self._has_unsaved_changes()
        )

    def _save_block_reason(self) -> str:
        if not self.integrity_valid or self.repack_required:
            return self.validation_errors[0] if self.validation_errors else self.tr("block.repack")
        if not self.font_valid:
            return self.font_errors[0] if self.font_errors else self.tr("block.font_invalid")
        if self.font_pending:
            return self.tr("block.font_pending")
        if self._has_pending_text_edit():
            return self.tr("block.text_pending")
        return self.tr("block.generic")

    def _save_payload(self) -> tuple[bytes, bool]:
        modified_from_source = (
            bytes(self.exe_data) != bytes(self.initial_unpacked_data)
            or self._converted_to_extended
            or self._integrity_fixed
        )
        payload = bytes(self.exe_data) if modified_from_source else bytes(self.original_source_data)
        return payload, modified_from_source

    def _update_save_state(self):
        can_save      = self._can_save()
        can_exchange  = self._can_exchange_strings()
        has_selection = self.current_index is not None and self._supported_loaded()
        has_pending   = self._has_pending_text_edit()

        if hasattr(self, "save_button"):
            self.save_button.config(state=tk.NORMAL if can_save else tk.DISABLED)
        self._set_menu_state(getattr(self, "save_menu_entries", []), can_save)

        apply_btn = getattr(self, "apply_edit_button", None)
        if apply_btn is not None:
            apply_btn.config(state=tk.NORMAL if has_pending else tk.DISABLED)

        font_btn = getattr(self, "font_assign_button", None)
        if font_btn is not None:
            font_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)

        panel_exc = tk.NORMAL if (can_exchange and has_selection) else tk.DISABLED
        for widget_name in ("export_strings_button", "import_strings_button"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.config(state=panel_exc)

        self._set_menu_state(getattr(self, "exchange_menu_entries", []), can_exchange)
        self._update_discard_button_state()

    def _make_text_widget(self, parent, bg="#FFFFFF"):
        container = tk.Frame(parent, bg="#BDC3C7", bd=1)
        container.pack(fill=tk.X, expand=True, pady=(0, 8))
        widget = tk.Text(container, height=1, wrap="word", font=("Consolas", 12, "bold"), bg=bg, fg="#1A252F", insertbackground="black", relief="flat", padx=5, pady=4)
        widget.pack(fill=tk.X, expand=True)
        widget.tag_configure("space_bg", background="#B3E5FC", foreground="#0288D1")
        return widget

    def _hide_edit_text(self):
        container = getattr(self.edit_text, "master", None)
        if container is not None and container.winfo_manager():
            container.pack_forget()

    def _show_edit_text(self):
        container = getattr(self.edit_text, "master", None)
        if container is not None and not container.winfo_manager():
            container.pack(fill=tk.X, expand=True, pady=(0, 8), before=self.info_frame)

    def _game_cfg(self) -> dict:
        return get_game_config(self.cfg, self.profile_name)



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
        self.font_editor.sync_cfg(self.cfg)
        self._invalidate_diff_preview("string-font", refresh=False)
        self._try_rebuild_baseline_filter_index()
        self.refresh_table(force=True, refresh_active_fields=True)

    def _can_change_charmap(self) -> bool:
        if not self._has_pending_text_edit():
            return True
        messagebox.showwarning(self.tr("dlg.pending_text.title"), self.tr("dlg.pending_charmap.msg"))
        return False

    def _on_charmap_changed(self, game_name: str, font_key: str, charmap: dict):
        if not self._supported_loaded() or game_name != self.profile_name:
            return
        self.cfg = load_config()
        self.font_editor.sync_cfg(self.cfg)
        self._invalidate_diff_preview("charmap", refresh=False)
        if self._has_pending_text_edit():
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

    def on_newspaper_editor_toggle(self):
        enabled = bool(self.newspaper_editor_var.get())
        if self.current_index is None:
            if not enabled:
                self.newspaper_panel.hide()
            return
        if enabled:
            self._display_entry(self.current_index, keep_filter=True)
        else:
            self.newspaper_panel.hide()
            self._refresh_current_entry_display()
            self._sync_translate_section()
            if self.translate_enabled_var.get():
                self.translate_status_label.config(text="")
        self._update_save_state()

    def _make_translate_fn(self):
        return self.translation_bar.make_translate_fn()

    def _sync_translate_section(self):
        section = self.translate_section
        active = self.translate_enabled_var.get()
        if active and not section.winfo_manager():
            section.pack(fill=tk.X)
        elif not active and section.winfo_manager():
            section.pack_forget()

    def _apply_translation_defaults(self, source=False, target=False):
        if source:
            self.translation_bar.set_default_source_from_profile(self.profile_name)
        if target:
            self.translation_bar.set_default_target_from_language(self.language)

    def on_translate_toggle(self):
        self._update_translate_all_state()
        panel = self._active_newspaper_panel()
        if panel is not None:
            enabled = self.translate_enabled_var.get()
            panel.refresh_translation(enabled, self._make_translate_fn() if enabled else None)
            return
        self._sync_translate_section()
        if not self.translate_enabled_var.get():
            self._flush_pending_refresh()
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
        widget.config(height=min(max(display_lines, 1), 12))
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
    def _entry_filter_kind(entry, newspaper_ids=frozenset()):
        if entry.get("fixed"):
            return "fixed"
        if entry.get("ptr_addrs"):
            if entry.get("string_id") in newspaper_ids:
                return "newspaper"
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
            stub_baseline = {}
            for entry in self.entries:
                sid = entry["string_id"]
                raw = self._entry_raw_bytes(entry)
                try:
                    text = self._decode_entry_text(entry)
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
        newspaper_ids = self._newspaper_ids()
        preview = self.diff_preview_cache.get() or {}
        preview_rows = preview.get("strings_by_id", {})
        rows = []
        for entry in self.entries:
            string_id = entry["string_id"]
            baseline = self.baseline_filter_data[string_id]
            font = self._get_font_for_entry(entry)
            current_raw = self._entry_raw_bytes(entry)
            try:
                current_text = self._decode_entry_text(entry)
            except StringExchangeError as exc:
                raise SearchFilterError(
                    f"Search text could not be decoded for {string_id}: {exc}"
                ) from exc
            preview_status = preview_rows.get(string_id, {}).get("status")
            rows.append({
                "string_id": string_id,
                "kind": self._entry_filter_kind(entry, newspaper_ids),
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

    def _clear_current_selection(self):
        self._selection_guard = True
        try:
            selected = self.tree.selection()
            if selected:
                self.tree.selection_remove(*selected)
        finally:
            self._selection_guard = False
        self.current_index = None
        self._update_panel_action_buttons()
        self.newspaper_panel.hide()
        self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
        self.edit_text.delete("1.0", tk.END)
        self.space_stats_label.config(text="")
        self.translate_status_label.config(text="")
        self.current_range_label.config(text="")
        self._update_save_state()

    def _newspaper_ids(self, strict=False):
        try:
            if not self.profile_name or not newspaper_csv.is_supported(self.profile_name):
                return set()
            return {e["string_id"] for e in newspaper_csv.collect(self.profile_name, self.entries)}
        except Exception:
            if strict:
                raise
            return set()

    def _is_newspaper_entry(self, entry: dict) -> bool:
        return self._supported_loaded() and entry.get("string_id") in self._newspaper_ids()

    def _display_entry(self, index, keep_filter=False):
        if not self._supported_loaded():
            return
        self._cancel_free_space_update()
        self.current_index = index
        entry = self.entries[index]
        original_text = self._decode_entry_text(entry)
        is_news = self._is_newspaper_entry(entry)
        self._update_panel_action_buttons(is_news)
        if self.newspaper_editor_var.get() and is_news:
            self.edit_text.config(state=tk.NORMAL)
            self.edit_text.delete("1.0", tk.END)
            self.newspaper_panel.show(entry, decode_fn=self._decode_entry_text)
            if self.translate_enabled_var.get():
                self.newspaper_panel.refresh_translation(True, self._make_translate_fn())
            if self.translate_section.winfo_manager():
                self.translate_section.pack_forget()
        else:
            if self.newspaper_panel.winfo_manager():
                self.newspaper_panel.hide()
            self._show_edit_text()
            self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
            self.edit_text.delete("1.0", tk.END)
            self.edit_text.insert("1.0", original_text)
            self.highlight_spaces()
            self.update_free_space_label()
            if not self.integrity_valid:
                self.edit_text.config(state=tk.DISABLED, bg="#F2F3F4")
            self._sync_translate_section()
        self._update_save_state()

    def refresh_table(self, *, force=False, refresh_active_fields=False):
        if (
            not force
            and self.current_index is not None
            and self._has_pending_text_edit()
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

        def _ptr_addrs(entry):
            return entry.get("ptr_addrs") or entry.get("code_ptr_addrs") or []

        def _first_ptr(sid):
            addrs = _ptr_addrs(self.entries[self.entry_index_by_id[sid]])
            return addrs[0] if addrs else 0xFFFFFFFF

        self.visible_string_ids = sorted(visible, key=_first_ptr)
        ds_start = self.profile.get("ds_start", 0) if self.profile else 0
        for string_id in self.visible_string_ids:
            index = self.entry_index_by_id[string_id]
            entry = self.entries[index]
            ptr_addrs = _ptr_addrs(entry)
            first_ptr = ""
            ptr_ds_offset = ""
            if ptr_addrs and len(self.exe_data) >= ptr_addrs[0] + 2:
                ptr_val = int.from_bytes(self.exe_data[ptr_addrs[0]:ptr_addrs[0] + 2], "little")
                first_ptr = hex(ptr_val)
                if entry.get("ptr_addrs"):
                    ptr_ds_offset = hex(ptr_addrs[0] - ds_start) if ds_start else hex(ptr_addrs[0])
            self.tree.insert("", tk.END, iid=string_id, values=(index + 1, ptr_ds_offset, first_ptr, self._decode_entry_text(entry)),)
        total, shown = len(self.entries), len(self.visible_string_ids)
        self._set_counter(shown, total)
        if self.filter_index_error:
            self._set_filter_status("status.filter_unavailable", error=self.filter_index_error)
        else:
            self._set_filter_status(None)

        self.filter_refresh_pending = False
        if active_id and active_id in self.entry_index_by_id and active_id in visible:
            self.current_index = self.entry_index_by_id[active_id]
            self._set_tree_selection(active_id)
            if refresh_active_fields:
                self._display_entry(self.current_index)
        elif active_id:
            self._clear_current_selection()
        return True

    def on_filter_change(self, *_):
        if not self._filter_callbacks_suspended:
            self.refresh_table()

    def _reset_filter_vars(self):
        self._filter_callbacks_suspended = True
        try:
            self.search_var.set("")
            for var in (self.kind_filter_var, self.font_filter_var,self.change_filter_var, self.status_filter_var):
                var.set("All")
        finally:
            self._filter_callbacks_suspended = False

    def clear_filters(self):
        self._reset_filter_vars()
        self.refresh_table()
        self.search_entry.focus()

    def _set_tree_selection(self, string_id):
        self._selection_guard = True
        try:
            self.tree.selection_set(string_id)
            self.tree.focus(string_id)
            self.tree.see(string_id)
        finally:
            self._selection_guard = False

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
        if current_id and string_id != current_id and self._has_pending_text_edit():
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
                self.current_range_label.config(text=self.tr("edit.encoding_blocked", error=exc),foreground="#C0392B",)
                self._update_save_state()
                return
            live_override = (entry, self._raw_text(current_raw_bytes))
        self._schedule_free_space_update(live_override=live_override)
        self._update_save_state()
        self._flush_pending_refresh()

    def _apply_text_widget(self, widget):
        if not self._supported_loaded() or self.current_index is None:
            return False
        display_text = widget.get("1.0", "1.0 lineend")
        try:
            source_entry = self.entries[self.current_index]
            desired_bytes = self._encode_entry_text(source_entry, display_text)
            if desired_bytes == self._entry_raw_bytes(source_entry):
                self.translate_status_label.config(text=self.tr("tr.no_changes"), foreground="#27AE60")
                self._update_save_state()
                self._flush_pending_refresh()
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
        self.refresh_table(force=True, refresh_active_fields=True)
        self._update_save_state()
        return True

    def translate_current(self, *, force=False):
        if not self._supported_loaded() or self.current_index is None or not self.translate_enabled_var.get():
            return
        self.translation_bar.run_translation()

    def _translate_current_entry(self, translate_fn):
        entry = self.entries[self.current_index]
        source_bytes = self._encode_entry_text(entry, self.edit_text.get("1.0", "1.0 lineend"))
        original = self._decode_raw_for_entry(entry, source_bytes, preserve_controls=True)
        translated = translate_fn(original)
        translated_bytes = self._encode_entry_text(entry, translated)
        translated_display = self._decode_raw_for_entry(entry, translated_bytes)
        self.edit_text.config(state=tk.NORMAL)
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.insert("1.0", translated_display)
        self.on_text_modified()
        self._update_save_state()

    def _ask_translate_all_scope(self):
        try:
            newspaper_ids = self._newspaper_ids(strict=True)
        except Exception as exc:
            messagebox.showerror(self.tr("dlg.translate_all.blocked"),self.tr("dlg.translate_all.nochange", detail=exc))
            return None
        kinds = {}
        for entry in self.entries:
            try:
                kinds[entry["string_id"]] = self._entry_filter_kind(entry, newspaper_ids)
            except SearchFilterError:
                pass
        total = len(self.entries)
        engine = self.engine_var.get()
        win = tk.Toplevel(self.root)
        win.title(self.tr("dlg.translate_all.scope_title"))
        win.resizable(False, False)
        win.transient(self.root)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)
        from_var, to_var = tk.StringVar(), tk.StringVar()
        normal_var, news_var = tk.BooleanVar(value=True), tk.BooleanVar(value=False)
        ttk.Label(frm, text=self.tr("dlg.translate_all.range", total=total)).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(frm, text=self.tr("dlg.translate_all.from")).grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=from_var, width=8).grid(row=1, column=1, padx=(4, 12))
        ttk.Label(frm, text=self.tr("dlg.translate_all.to")).grid(row=1, column=2, sticky="w")
        ttk.Entry(frm, textvariable=to_var, width=8).grid(row=1, column=3, padx=(4, 0))
        ttk.Label(frm, text=self.tr("dlg.translate_all.kinds")).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        ttk.Checkbutton(frm, text=self.tr("dlg.translate_all.kind_normal"),variable=normal_var).grid(row=3, column=0, columnspan=4, sticky="w")
        ttk.Checkbutton(frm, text=self.tr("dlg.translate_all.kind_newspaper"),variable=news_var).grid(row=4, column=0, columnspan=4, sticky="w")
        ttk.Label(frm, text=self.tr("dlg.translate_all.excluded_note"),foreground="#7F8C8D").grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))
        info_lbl = ttk.Label(frm, text="", font=("Segoe UI", 9, "bold"))
        info_lbl.grid(row=6, column=0, columnspan=4, sticky="w", pady=(8, 8))
        btn_row = ttk.Frame(frm)
        btn_row.grid(row=7, column=0, columnspan=4, sticky="e")
        ok_btn = ttk.Button(btn_row, text=self.tr("dlg.translate_all.start"))
        ok_btn.pack(side=tk.LEFT, padx=(0, 6))
        result = {"ids": None}

        def compute():
            try:
                lo = int(from_var.get().strip().lstrip("#") or 1)
                hi = int(to_var.get().strip().lstrip("#") or total)
            except ValueError:
                return None
            if lo < 1 or hi < lo:
                return None
            allowed = set()
            if normal_var.get():
                allowed.add("normal")
            if news_var.get():
                allowed.add("newspaper")
            return {entry["string_id"] for number, entry in enumerate(self.entries, 1)
                    if lo <= number <= hi and kinds.get(entry["string_id"]) in allowed}

        def update(*_):
            ids = compute()
            if ids is None:
                info_lbl.config(text=self.tr("dlg.translate_all.invalid_range"), foreground="#C0392B")
                ok_btn.config(state=tk.DISABLED)
                return
            info_lbl.config(text=self.tr("dlg.translate_all.selected", n=len(ids), total=total, engine=engine),foreground="#1565C0")
            ok_btn.config(state=tk.NORMAL if ids else tk.DISABLED)

        def accept(*_):
            ids = compute()
            if ids:
                result["ids"] = ids
                win.destroy()

        ok_btn.config(command=accept)
        ttk.Button(btn_row, text=self.tr("dlg.translate_all.cancel"), command=win.destroy).pack(side=tk.LEFT)
        for var in (from_var, to_var, normal_var, news_var):
            var.trace_add("write", update)
        win.bind("<Return>", accept)
        win.bind("<Escape>", lambda _e: win.destroy())
        update()
        win.grab_set()
        win.wait_window()
        return result["ids"]

    def translate_all(self):
        if not self._supported_loaded() or not self.entries:
            messagebox.showinfo(self.tr("dlg.translate_all.title"), self.tr("dlg.translate_all.none"))
            return
        selected = self._ask_translate_all_scope()
        if not selected:
            return

        prog_win = tk.Toplevel(self.root)
        prog_win.title(self.tr("dlg.translate_all.window"))
        prog_win.resizable(False, False)
        prog_win.grab_set()
        ttk.Label(prog_win, text=self.tr("tr.translating"), font=("Segoe UI", 10, "bold"), padding=10).pack()
        progress_var = tk.IntVar(value=0)
        bar = ttk.Progressbar(prog_win, maximum=len(selected), variable=progress_var, length=360)
        bar.pack(padx=20, pady=(0, 6))
        status_lbl = ttk.Label(prog_win, text="", font=("Segoe UI", 9, "italic"), padding=(10, 0, 10, 10))
        status_lbl.pack()
        prog_win.update()

        def update_progress(current, total, display_text):
            status_lbl.config(text=self.tr("dlg.translate_all.progress",current=current, total=total,text=display_text[:50]))
            progress_var.set(current)
            prog_win.update()

        try:
            work_data, work_entries, validation, stats = self._prepare_translate_all_transaction(
                self._make_translate_fn(),on_progress=update_progress,only_ids=selected,)
        except Exception as exc:
            prog_win.destroy()
            messagebox.showerror(self.tr("dlg.translate_all.blocked"), self.tr("dlg.translate_all.nochange", detail=exc))
            return

        prog_win.destroy()
        if validation.get("noop"):
            messagebox.showinfo(self.tr("dlg.translate_all.title"), self.tr("dlg.translate_all.unchanged"))
            return
        if not validation["ok"]:
            detail = "\n".join(validation.get("errors", [])[:8]) or "Unknown validation error"
            messagebox.showerror(self.tr("dlg.translate_all.blocked"), self.tr("dlg.translate_all.nochange", detail=detail))
            return

        self._commit_text_transaction(work_data, work_entries, validation)
        self.refresh_table(force=True, refresh_active_fields=True)

        summary = self.tr("dlg.translate_all.summary", translated=stats["translated"], unchanged=stats["unchanged"], blank=stats["blank"])
        if stats["suffix_skipped"]:
            summary += self.tr("dlg.translate_all.suffix", n=stats["suffix_skipped"])
        messagebox.showinfo(self.tr("dlg.translate_all.done"), summary)

    def _current_entry_is_newspaper(self) -> bool:
        if self.current_index is None or not self._supported_loaded():
            return False
        return self._is_newspaper_entry(self.entries[self.current_index])

    def _update_panel_action_buttons(self, is_news=None):
        if not hasattr(self, "export_strings_button"):
            return
        if is_news is None:
            is_news = self._current_entry_is_newspaper()
        if is_news:
            exp_key, imp_key = "action.export_newspaper", "action.import_newspaper"
        else:
            exp_key, imp_key = "action.export_normal", "action.import_normal"
        self.export_strings_button.config(text=self.tr(exp_key))
        self.import_strings_button.config(text=self.tr(imp_key))

    def _panel_export(self):
        if self._current_entry_is_newspaper():
            self.export_newspaper_csv()
        else:
            self.export_normal_csv()

    def _panel_import(self):
        if self._current_entry_is_newspaper():
            self.import_newspaper_csv()
        else:
            self.import_normal_csv()

    def _exchange_allowed(self, blocked_key):
        if self._can_exchange_strings():
            return True
        messagebox.showwarning(self.tr(blocked_key), self._save_block_reason())
        return False

    def _write_export(self, filepath, payload):
        try:
            atomic_save_bytes(filepath, payload)
        except OSError as exc:
            messagebox.showerror(self.tr("dlg.export.failed"), self.tr("dlg.export.partial", error=exc))
            return False
        return True

    def _stage_replacements(self, replacements):
        work_data, work_entries, validation, _font_result = stage_import_transaction(
            self.exe_data,
            self.entries,
            replacements,
            self.profile,
            self.relocation_sites,
            EXE_FONT_PROFILES[self.profile_name],
        )
        return work_data, work_entries, validation

    def _commit_import(self, staged):
        self._commit_text_transaction(*staged)
        self.translation_pending = False
        self.refresh_table(force=True, refresh_active_fields=True)
        self._update_save_state()

    def export_normal_csv(self):
        if not self._exchange_allowed("dlg.export.blocked"):
            return False
        try:
            newspaper_ids = self._newspaper_ids(strict=True)
            exchange_args = self._string_exchange_arguments()
            exchange_args["entries"] = [e for e in self.entries if e.get("string_id") not in newspaper_ids]
            payload = export_csv_bytes(**exchange_args)
            normal_count = sum(1 for e in exchange_args["entries"] if not e.get("fixed"))
        except (StringExchangeError, newspaper_csv.NewspaperCsvError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.export.blocked"), str(exc))
            return False
        filepath = filedialog.asksaveasfilename(title=self.tr("fd.export"),initialfile="translations.strings.csv",defaultextension=".csv",filetypes=[("String Exchange CSV", "*.csv")],)
        if not filepath or not self._write_export(filepath, payload):
            return False
        self._set_status("dlg.export.status", n=normal_count, file=os.path.basename(filepath))
        messagebox.showinfo(self.tr("dlg.export.done"), self.tr("dlg.export.done_msg", n=normal_count, path=filepath))
        return True

    def import_normal_csv(self):
        if not self._exchange_allowed("dlg.import.blocked"):
            return False
        filepath = filedialog.askopenfilename(
            title=self.tr("fd.import"),filetypes=[("String Exchange CSV", "*.strings.csv"), ("All CSV", "*.csv")],)
        if not filepath:
            return False

        try:
            with open(filepath, "rb") as handle:
                csv_doc = parse_csv_document(handle.read())
            if csv_doc["profile_id"] != self.profile_name:
                raise StringExchangeError(
                    f"Wrong profile: {csv_doc['profile_id']!r}, expected {self.profile_name!r}"
                )
            newspaper_ids = self._newspaper_ids(strict=True)
            entries_by_id = {entry["string_id"]: entry for entry in self.entries}
            unknown = sorted({row["string_id"] for row in csv_doc["entries"]} - set(entries_by_id))
            if unknown:
                raise StringExchangeError(f"Unknown string_id in CSV: {unknown[0]}")

            replacements = {}
            for row in csv_doc["entries"]:
                translated = row["translated_text"]
                if row["string_id"] in newspaper_ids or translated is None:
                    continue
                entry = entries_by_id[row["string_id"]]
                desired_raw, _, _ = exchange_text_to_raw(translated,self._charmap_for_entry(entry),self._font_codes_for_entry(entry),source_mode=True,)
                if desired_raw != self._entry_raw_bytes(entry):
                    replacements[row["string_id"]] = desired_raw
        except (OSError, StringExchangeError, newspaper_csv.NewspaperCsvError, KeyError, ValueError, CharmapEncodeError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"), self.tr("dlg.import.nochange", error=exc))
            return False

        changed_count = len(replacements)
        profile_id = csv_doc["profile_id"]
        if changed_count == 0:
            messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.import.none", profile=profile_id))
            return True
        if not messagebox.askyesno(self.tr("dlg.import.title"), self.tr("dlg.import.confirm", profile=profile_id, n=changed_count)):
            return False
        if not self._exchange_allowed("dlg.import.blocked"):
            return False

        try:
            staged = self._stage_replacements(replacements)
        except (StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"), self.tr("dlg.import.nochange", error=exc))
            return False

        self._commit_import(staged)
        self._set_status("dlg.import.status", n=changed_count)
        messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.import.done_msg", profile=profile_id, n=changed_count))
        return True

    def export_all_json(self):
        if not self._exchange_allowed("dlg.export.blocked"):
            return False
        filepath = filedialog.asksaveasfilename(title=self.tr("menu.tools.export_json"),initialfile="backup.strings.json",defaultextension=".json",filetypes=[("String Exchange JSON", "*.json")],)
        if not filepath:
            return False
        try:
            payload = export_json_bytes(**self._string_exchange_arguments())
        except (StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.export.blocked"), str(exc))
            return False
        if not self._write_export(filepath, payload):
            return False

        count = len(self.entries)
        self._set_status("dlg.export.status", n=count, file=os.path.basename(filepath))
        messagebox.showinfo(self.tr("dlg.export.done"), self.tr("dlg.export.done_msg", n=count, path=filepath))
        return True

    def import_all_json(self):
        if not self._exchange_allowed("dlg.import.blocked"):
            return False
        filepath = filedialog.askopenfilename(title=self.tr("fd.import_json"),filetypes=[("String Exchange JSON", "*.strings.json")],)
        if not filepath:
            return False

        try:
            with open(filepath, "rb") as handle:
                preflight = preflight_import_json(handle.read(), **self._string_exchange_arguments())
        except (OSError, StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"), self.tr("dlg.import.nochange", error=exc))
            return False

        changed_count = preflight["changed_count"]
        profile_id = preflight["profile_id"]
        if changed_count == 0:
            messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.import.none", profile=profile_id))
            return True
        if not messagebox.askyesno(self.tr("dlg.import.title"), self.tr("dlg.import.confirm", profile=profile_id, n=changed_count)):
            return False
        if not self._exchange_allowed("dlg.import.blocked"):
            return False

        try:
            staged = self._stage_replacements(preflight["replacements"])
        except (StringExchangeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"), self.tr("dlg.import.nochange", error=exc))
            return False

        self._commit_import(staged)
        self._set_status("dlg.import.status", n=changed_count)
        messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.import.done_msg", profile=profile_id, n=changed_count))
        return True

    def _newspaper_ready(self, blocked_key):
        if not self._exchange_allowed(blocked_key):
            return False
        if not newspaper_csv.is_supported(self.profile_name):
            messagebox.showwarning(self.tr(blocked_key), self.tr("dlg.news.unsupported", profile=self.profile_name))
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
        except (newspaper_csv.NewspaperCsvError, NewspaperGrammarError,CharmapEncodeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.export.blocked"), str(exc))
            return False

        filepath = filedialog.asksaveasfilename(title=self.tr("fd.news_export"),initialfile="newspaper.csv",defaultextension=".csv",filetypes=[("Newspaper CSV", "*.csv")],)
        if not filepath or not self._write_export(filepath, payload):
            return False
        self._set_status("dlg.news.status_export", n=count, file=os.path.basename(filepath))
        messagebox.showinfo(self.tr("dlg.export.done"), self.tr("dlg.news.export_msg", n=count, rows=len(rows), path=filepath))
        return True

    def import_newspaper_csv(self):
        if not self._newspaper_ready("dlg.import.blocked"):
            return False
        filepath = filedialog.askopenfilename(title=self.tr("fd.news_import"), filetypes=[("Newspaper CSV", "*.csv")])
        if not filepath:
            return False
        try:
            with open(filepath, "rb") as handle:
                raw_document = handle.read()
            replacements = newspaper_csv.preflight_import(
                self.profile_name, self.entries, self._decode_entry_text, raw_document)
        except (OSError, newspaper_csv.NewspaperCsvError, NewspaperGrammarError, CharmapEncodeError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"), self.tr("dlg.import.nochange", error=exc))
            return False

        if not replacements:
            messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.news.none"))
            return True
        if not messagebox.askyesno(self.tr("dlg.import.title"), self.tr("dlg.news.confirm", n=len(replacements))):
            return False
        if not self._newspaper_ready("dlg.import.blocked"):
            return False

        try:
            by_id = {entry["string_id"]: entry for entry in self.entries}
            raw_replacements = {
                string_id: self._encode_entry_text(by_id[string_id], display_text)
                for string_id, display_text in replacements.items()
            }
            staged = self._stage_replacements(raw_replacements)
        except (StringExchangeError, CharmapEncodeError, TextTransactionError, FontSafetyError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.import.blocked"), self.tr("dlg.import.nochange", error=exc))
            return False

        self._commit_import(staged)
        self._set_status("dlg.news.status_import", n=len(replacements))
        messagebox.showinfo(self.tr("dlg.import.done"), self.tr("dlg.news.done_msg", n=len(replacements)))
        return True

    def _pending_preview_state(self):
        replacements = {}
        pending_ids = set()
        pending_error = None
        if self.current_index is not None and self._supported_loaded():
            edit_pending = self._has_pending_text_edit()
            entry = self.entries[self.current_index]
            if edit_pending:
                pending_ids.add(entry["string_id"])
                try:
                    display_text = self.edit_text.get("1.0", "1.0 lineend")
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
        return build_diff_preview(
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
            integrity_fix_applied=self._integrity_fixed,
            extended_layout_active=self._converted_to_extended or (
                extended_layout.detect(self.exe_data, self.profile) is not None
            ),
            points_var_changed=self._points_var_changed(),
        )

    def _range_changed(self, offset, size):
        init = self.initial_unpacked_data
        return (
            offset is not None
            and len(init) >= offset + size
            and bytes(self.exe_data[offset:offset + size]) != bytes(init[offset:offset + size])
        )

    def _points_var_changed(self) -> bool:
        return self._range_changed(self._points_rule_offset(), 2)

    def _match_flag_changed(self, mf) -> bool:
        if not mf:
            return False
        ranges = set()
        detect_offset = mf.get("detect_offset")
        if isinstance(detect_offset, int):
            ranges.add((detect_offset, 1))
        ranges.update((off, 1) for off in mf.get("color_offsets", ()) if isinstance(off, int))
        raw_fc = mf.get("font_color_offsets") or mf.get("font_color_offset")
        fc_offsets = [raw_fc] if isinstance(raw_fc, int) else (raw_fc or [])
        ranges.update((off, 1) for off in fc_offsets if isinstance(off, int))
        band_offsets = mf.get("band_offsets", ())
        for patches in mf.get("types", {}).values():
            if not isinstance(patches, dict):
                continue
            for off, hex_str in zip(band_offsets, patches.values()):
                if not isinstance(off, int):
                    continue
                try:
                    ranges.add((off, len(bytes.fromhex(hex_str))))
                except (TypeError, ValueError):
                    pass
        return any(off >= 0 and self._range_changed(off, length) for off, length in ranges)

    def _show_preview_dialog(self, snapshot):
        fields = {
            "year":     (self._year_offset(), 2),
            "region":   (self._region_offset(), 8),
            "points":   (self._points_rule_offset(), 2),
            "subst_gk": (self._subst_gk_offset(), 8),
            "teams":    (self._teams_offset(), 16),
            "wdl":      (self._wdl_offset(), 6),
        }
        kwargs = {}
        for name, (offset, size) in fields.items():
            kwargs[f"{name}_offset"] = offset
            kwargs[f"{name}_changed"] = self._range_changed(offset, size)
        kwargs["goal_frames_offset"] = self._goal_frames_offset()
        kwargs["goal_frames_changed"] = self._goal_frames_changed()
        match_flag_config = self._match_flag_config()
        show_preview_dialog(
            self.root, snapshot, self.tr,
            match_flag_config=match_flag_config,
            match_flag_changed=self._match_flag_changed(match_flag_config),
            **kwargs,
        )

    def show_changes_preview(self):
        if not self._supported_loaded():
            messagebox.showwarning(self.tr("dlg.preview.warn"), self.tr("dlg.preview.load_first"))
            return False
        try:
            snapshot = self._build_changes_preview()
        except (DiffPreviewError, KeyError, ValueError) as exc:
            messagebox.showerror(self.tr("dlg.preview.failed"), self.tr("dlg.import.nochange", error=exc))
            return False
        self.filter_records_dirty = True
        self.refresh_table()
        self.update_free_space_label()
        self._show_preview_dialog(snapshot)
        return True

    def update_free_space_label(self, live_override=None):
        label = getattr(self, "current_range_label", None)
        if label is None:
            return
        if not self.profile or self.current_index is None or not self.initial_unpacked_data:
            label.config(text="")
            return
        entry = self.entries[self.current_index]
        pending_raw = None
        if live_override and live_override[0] is entry:
            pending_raw = live_override[1].encode("latin-1")
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
            self.current_range_label.config(text=self.tr("edit.diff_unavailable", error=exc), foreground="#C0392B")
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
            text=self.tr("edit.range_info", kind=info["kind"], font=info["font"],old=info["old_length"], new=info["new_length"],delta=delta, status=info["status"], suffix=suffix),
            foreground={
                "FAIL": "#C0392B",
                "PENDING": "#B9770E",
                "PASS": "#1E8449",
                "READ-ONLY": "#566573",
                "UNCHANGED": "#2980B9",
            }.get(info["status"], "#2980B9"),
        )

    def detect_profile(self, data):
        return detect_game_profile(data, GAME_PROFILES)

    def _reset_state(self):
        self._invalidate_diff_preview("reset", refresh=False)
        self._init_document_state()
        for var in (self.year_var, self.subst_gk_var, self.subst_var,self.teams_var, self.goal_frames_var, self.region_a_var, self.region_b_var):
            var.set("")
        self._reset_filter_vars()
        self.filter_combos[1].config(values=("All",))
        self.tree.delete(*self.tree.get_children())
        self.newspaper_panel.hide()
        self.edit_text.config(state=tk.NORMAL, bg="#FFFFFF")
        self.edit_text.delete("1.0", tk.END)
        self.edit_text.config(height=1)
        self.space_stats_label.config(text="")
        self.translate_status_label.config(text="")
        self.current_range_label.config(text="")
        self._set_profile("header.profile_none")
        self.filename_label.config(text="")
        self._set_status("header.no_file")
        self._set_counter(0, 0)
        self._set_filter_status(None)
        self.font_editor.reset_state()
        self.mana_editor_panel.show_placeholder()
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

    def _tore_dirty(self) -> bool:
        panel = getattr(self, "tore_editor", None)
        try:
            return bool(panel is not None and panel.is_dirty())
        except Exception:
            return False

    def _confirm_discard_for_load(self) -> bool:
        if self._tore_dirty() and not messagebox.askyesno("TORE Editor", "La scena TORE ha modifiche non salvate. Continuare e scartarle?"):
            return False
        if not self._has_unsaved_changes():
            return True
        return messagebox.askyesno(self.tr("dlg.unsaved.title"), self.tr("dlg.unsaved.load"))

    def _on_close_request(self):
        try:
            unsaved = self._has_unsaved_changes()
        except Exception:
            unsaved = True
        if unsaved and not messagebox.askyesno(self.tr("dlg.unsaved.title"), self.tr("dlg.unsaved.close")):
            return
        if self._tore_dirty() and not messagebox.askyesno("TORE Editor", "La scena TORE ha modifiche non salvate. Chiudere comunque?"):
            return
        self._cancel_free_space_update()
        self.root.destroy()

    def _find_gaps(self, entries, relocation_sites):
        try:
            return find_unknown_gaps(self.exe_data, self.profile, entries, relocation_sites)
        except Exception:
            return []

    def _zero_fill_gaps(self, gaps):
        for g in gaps:
            start, end = g["gap_start"], g["gap_end"]
            self.exe_data[start:end] = b"\x00" * (end - start)

    @staticmethod
    def _find_mana_file(directory):
        try:
            for name in os.listdir(directory):
                path = os.path.join(directory, name)
                if name.lower() == "mana.dat" and os.path.isfile(path):
                    return path
        except OSError:
            pass
        return None

    def load_exe(self):
        filepath = filedialog.askopenfilename(title=self.tr("fd.open_exe"), filetypes=[("DOS Executable", "*.exe"), ("All Files", "*.*")])
        if not filepath or not self._confirm_discard_for_load():
            return

        converted_to_extended = False
        try:
            with open(filepath, "rb") as handle:
                original_data = bytearray(handle.read())
            try:
                unpacked_data = unpack_in_memory(bytearray(original_data))
            except Exception:
                unpacked_data = bytearray(original_data)
            detected = self.detect_profile(unpacked_data)
            if detected is None:
                detected = next(
                    (name for name, candidate in GAME_PROFILES.items()
                     if extended_layout.detect(unpacked_data, candidate) is not None
                     or extended_layout.can_convert(unpacked_data, candidate) is not None),
                    None,
                )

            prepared = None
            if detected is not None:
                profile = GAME_PROFILES[detected]
                descriptor = extended_layout.can_convert(unpacked_data, profile)
                if descriptor is not None:
                    pool_start, pool_end = descriptor["pool"]
                    pool_kb = (pool_end - pool_start) // 1024
                    if messagebox.askyesno("Extended Layout", self.tr("dlg.load.extended", detected=detected, pool_kb=pool_kb)):
                        unpacked_data, _ = extended_layout.convert_to_extended(unpacked_data, profile)
                        converted_to_extended = True
                validate_all_fonts(unpacked_data, EXE_FONT_PROFILES[detected])
                prepared = self._prepare_load_content(unpacked_data, profile)
        except (OSError, ValueError, KeyError, FontSafetyError) as exc:
            messagebox.showerror(self.tr("dlg.load.failed"), self.tr("dlg.load.failed_msg", error=exc))
            return

        self._reset_state()
        self._converted_to_extended = converted_to_extended
        self.source_path = os.path.abspath(filepath)
        exe_dir = os.path.dirname(self.source_path)
        pic_folder = os.path.join(exe_dir, "PIC")
        if os.path.isdir(pic_folder):
            self.vga_editor.set_pic_dir(pic_folder)
            self.tore_editor.set_pic_dir(pic_folder)
        else:
            self.tore_editor.clear_pic_dir()
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
        self._apply_translation_defaults(source=True)
        is_extended = extended_layout.detect(self.exe_data, self.profile) is not None
        self._set_profile(value=f"{detected} [EXTENDED]" if is_extended else detected)
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

        mana_path = self._find_mana_file(exe_dir)
        if mana_path:
            self.mana_editor_panel.load_file(mana_path)
        else:
            self.mana_editor_panel.show_placeholder(f"MANA.DAT not found in: {exe_dir}")

        self._set_supported_state(True)
        for read_from_exe in (
            self._read_year_from_exe, self._read_region_from_exe,
            self._read_points_from_exe, self._read_subst_from_exe,
            self._read_teams_from_exe, self._read_goal_frames_from_exe,
            self._read_wdl_from_exe,
            self._read_flag_from_exe,
        ):
            read_from_exe()
        self.notebook.select(self.tab_strings)
        self._update_save_state()
        self._set_status(None)
        if not font_loaded:
            self._set_status("dlg.load.font_failed")
            return
        if validation["ok"]:
            return

        self._set_status("dlg.load.integrity_status", error=validation["errors"][0])
        gaps = self._find_gaps(entries, relocation_sites)
        if show_integrity_dialog(self.root, gaps) and gaps:
            self._zero_fill_gaps(gaps)
            new_validation = validate_image(self.exe_data, self.profile, entries, relocation_sites)
            self.integrity_valid = new_validation["ok"]
            self.validation_errors = list(new_validation["errors"])
            if new_validation["ok"]:
                self.initial_unpacked_data = bytearray(self.exe_data)
                self.last_saved_exe_data = bytearray(self.exe_data)
                self._integrity_fixed = True
                self._migrate_legacy_font_mappings()
                self._set_status(None)
            else:
                self._set_status("dlg.load.integrity_status", error=new_validation["errors"][0])
        self._try_rebuild_baseline_filter_index()
        self.refresh_table(force=True)
        self._update_save_state()
        if self.visible_string_ids:
            first_id = self.visible_string_ids[0]
            self._set_tree_selection(first_id)
            self._display_entry(self.entry_index_by_id[first_id])

    def _on_tree_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        columns = ("num", "offset", "pointer", "text")
        try:
            index = int(col_id.lstrip("#")) - 1
        except ValueError:
            return
        if not 1 <= index < len(columns):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(str(self.tree.set(row_id, columns[index])))
        self._copied_label.config(text=self.tr("font.copied"))
        if self._copied_after_id is not None:
            self.root.after_cancel(self._copied_after_id)
        self._copied_after_id = self.root.after(2000, lambda: self._copied_label.config(text=""))

    def save_exe(self):
        if not self._supported_loaded():
            messagebox.showwarning(self.tr("dlg.save.unsupported"), self.tr("dlg.save.unsupported_msg"))
            return False
        if self.font_valid and not self.font_pending:
            self.font_editor.validate_live_state()
        if not self._can_save():
            messagebox.showwarning(self.tr("dlg.save.blocked"), self._save_block_reason())
            return False
        filepath = filedialog.asksaveasfilename(
            title=self.tr("fd.save_exe"),
            defaultextension=".exe",
            filetypes=[("DOS Executable", "*.exe")],
            initialfile=os.path.basename(self.source_path) if self.source_path else "",
            initialdir=os.path.dirname(self.source_path) if self.source_path else "",
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
                messagebox.showerror(self.tr("dlg.save.blocked"), self.tr("dlg.save.verify", error=exc))
                return False
            if current_source != bytes(self.original_source_data):
                messagebox.showerror(self.tr("dlg.save.blocked"), self.tr("dlg.save.external"))
                return False
            if not modified_from_source:
                messagebox.showinfo(self.tr("dlg.save.done"), self.tr("dlg.save.noop"))
                self.last_saved_exe_data = bytearray(self.exe_data)
                self._converted_to_extended = False
                self._integrity_fixed = False
                self._invalidate_diff_preview("save-baseline")
                self._try_rebuild_baseline_filter_index()
                self.refresh_table(force=True, refresh_active_fields=True)
                self._update_save_state()
                return True
            if not messagebox.askyesno(self.tr("dlg.save.overwrite_title"), self.tr("dlg.save.overwrite_msg")):
                return False
            backup_original = True

        try:
            backup_path = atomic_save_bytes(filepath, payload, backup_original=backup_original)
        except OSError as exc:
            messagebox.showerror(self.tr("dlg.save.failed"), self.tr("dlg.save.failed_msg", error=exc))
            return False

        self.source_path = os.path.abspath(filepath)
        self.original_source_data = bytearray(payload)
        self.initial_unpacked_data = bytearray(self.exe_data)
        self.last_saved_exe_data = bytearray(self.exe_data)
        self._converted_to_extended = False
        self._integrity_fixed = False
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
        messagebox.showinfo(self.tr("dlg.save.done"), self.tr("dlg.save.done_msg", path=filepath, backup=backup_note))
        return True

__all__ = ['DOSTranslationEditor']
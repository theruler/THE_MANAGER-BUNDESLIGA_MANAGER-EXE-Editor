from __future__ import annotations
import tkinter as tk
from tkinter import ttk


def make_preview_tree(parent, columns) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    names = tuple(col[0] for col in columns)
    tree  = ttk.Treeview(frame, columns=names, show="headings")
    for name, heading, width, anchor in columns:
        tree.heading(name, text=heading)
        tree.column(name, width=width, anchor=anchor,
                    stretch=name in {"old", "new", "error"})
    vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side=tk.RIGHT,  fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree.tag_configure("FAIL",      background="#F5B7B1", foreground="#641E16")
    tree.tag_configure("PASS",      background="#D5F5E3", foreground="#145A32")
    tree.tag_configure("PENDING",   background="#FCF3CF", foreground="#7D6608")
    tree.tag_configure("READ-ONLY", background="#EAECEE", foreground="#566573")
    return tree


def show_preview_dialog(
    root,
    snapshot: dict,
    tr,
    *,
    year_changed: bool   = False,
    year_offset          = None,
    region_changed: bool = False,
    region_offset        = None,
    points_changed: bool = False,
    points_offset        = None,
    teams_changed: bool  = False,
    teams_offset         = None,
    wdl_changed: bool    = False,
    wdl_offset           = None,
    match_flag_changed: bool = False,
    match_flag_config        = None,
) -> None:

    dialog = tk.Toplevel(root)
    dialog.title(tr("dlg.preview.title", profile=snapshot["profile_id"]))
    dialog.geometry("1200x800")
    dialog.minsize(900, 520)
    dialog.transient(root)

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
    tab_names = ("Summary", "Strings", "Blocks", "Pointers", "Fonts")
    tabs = {name: ttk.Frame(notebook) for name in tab_names}
    for name, frame in tabs.items():
        notebook.add(frame, text="  %s  " % tr("preview.tab." + name.lower()))

    summary   = snapshot["summary"]
    none_text = tr("preview.val.none")
    yes_text  = tr("preview.val.yes")
    no_text   = tr("preview.val.no")

    def flag(value):
        return yes_text if value else no_text

    summary_lines = [
        tr("preview.sum.status",  value=snapshot["status"]),
        tr("preview.sum.profile", value=snapshot["profile_id"]),
        "",
        tr("preview.sum.normal",    value=summary["normal_changed"]),
        tr("preview.sum.fixed",     value=summary["fixed_changed"]),
        tr("preview.sum.codeonly",  value=summary["code_only_changed"]),
        tr("preview.sum.pointers",  value=summary["pointer_sources_changed"]),
        tr("preview.sum.integrity_fix",
           value=flag(summary.get("integrity_fix_applied", False))),
        "",
        tr("preview.sum.glyphs", value=summary["glyphs_changed"]),
        tr("preview.sum.fonts", value=", ".join(summary["fonts_affected"]) or none_text),
        "",
        tr("preview.sum.year", value=flag(year_changed)),
        tr("preview.sum.region", value=flag(region_changed)),
        tr("preview.sum.points", value=flag(points_changed)),
        tr("preview.sum.teams", value=flag(teams_changed)),
        tr("preview.sum.wdl", value=flag(wdl_changed)),
        tr("preview.sum.match", value=flag(match_flag_changed)),
        "",
        tr("preview.sum.extended_layout",
           value=flag(summary.get("extended_layout_active", False))),
        "",
        tr("preview.sum.repack_needed",  value=flag(summary["repack_needed"])),
        tr("preview.sum.repack_status",  value=summary["repack_status"]),
        tr("preview.sum.validator",      value=summary["validator_status"]),
        tr("preview.sum.font_status",    value=summary["font_status"]),
        tr("preview.sum.save_possible",  value=flag(summary["save_possible"])),
    ]
    if snapshot["errors"]:
        summary_lines.extend(
            ["", tr("preview.sum.reasons")]
            + [f"- {v}" for v in snapshot["errors"]]
        )

    summary_text = tk.Text(tabs["Summary"], wrap="word",font=("Consolas", 10), padx=12, pady=12)
    summary_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    summary_text.insert("1.0", "\n".join(summary_lines))
    summary_text.config(state=tk.DISABLED)

    string_tree = make_preview_tree(tabs["Strings"], [
        ("status", tr("preview.col.status"),    85, tk.CENTER),
        ("id",     "string_id",                140, tk.W),
        ("kind",   tr("preview.col.kind"),      80, tk.CENTER),
        ("font",   tr("preview.col.font"),      95, tk.CENTER),
        ("oldlen", tr("preview.col.oldbytes"),  70, tk.E),
        ("newlen", tr("preview.col.newbytes"),  70, tk.E),
        ("delta",  tr("preview.col.delta"),     60, tk.E),
        ("block",  tr("preview.col.block"),     55, tk.CENTER),
        ("ptrs",   tr("preview.col.pointers"),  65, tk.E),
        ("code",   tr("preview.col.codeptrs"),  65, tk.E),
        ("cap",    tr("preview.col.fixedcap"),  65, tk.E),
        ("old",    tr("preview.col.oldtext"),  230, tk.W),
        ("new",    tr("preview.col.newtext"),  230, tk.W),
    ])
    for row in snapshot["strings"]:
        block    = "—" if row["repack_block"] is None else row["repack_block"] + 1
        capacity = "—" if row["fixed_capacity_bytes"] is None else row["fixed_capacity_bytes"]
        string_tree.insert("", tk.END, values=(
            row["status"], row["string_id"], row["kind"], row["font"],
            row["old_length"], row["new_length"], f"{row['delta']:+d}", block,
            row["pointer_count"], row["code_pointer_count"], capacity,
            row["old_text"], row["new_text"],
        ), tags=(row["status"],))

    block_tree = make_preview_tree(tabs["Blocks"], [
        ("status",  tr("preview.col.status"),      80, tk.CENTER),
        ("block",   tr("preview.col.block"),        55, tk.CENTER),
        ("range",   tr("preview.col.range"),       180, tk.CENTER),
        ("total",   tr("preview.col.total"),        80, tk.E),
        ("base",    tr("preview.col.baseused"),    100, tk.E),
        ("preview", tr("preview.col.prevused"),    100, tk.E),
        ("delta",   tr("preview.col.delta"),        70, tk.E),
        ("saved",   tr("preview.col.savings"),      70, tk.E),
        ("growth",  tr("preview.col.growth"),       70, tk.E),
        ("free",    tr("preview.col.sharedrest"),   90, tk.E),
        ("missing", tr("preview.col.missing"),      70, tk.E),
        ("error",   tr("preview.col.reason"),      250, tk.W),
    ])
    for row in snapshot["blocks"]:
        def shown(v): return "—" if v is None else v
        block_tree.insert("", tk.END, values=(
            row["status"], row["block"] + 1,
            f"0x{row['start']:X}–0x{row['end']:X}", row["total"],
            row["baseline_used"], shown(row["preview_used"]), shown(row["delta"]),
            shown(row["savings"]), shown(row["growth"]), shown(row["preview_free"]),
            row["missing_bytes"], row["error"] or "",
        ), tags=(row["status"],))

    pointer_tree = make_preview_tree(tabs["Pointers"], [
        ("source", tr("preview.col.source"),       90, tk.CENTER),
        ("kind",   tr("preview.col.type"),          70, tk.CENTER),
        ("id",     "string_id",                    150, tk.W),
        ("oldlow", tr("preview.col.oldlowword"),    90, tk.CENTER),
        ("newlow", tr("preview.col.newlowword"),    90, tk.CENTER),
        ("old",    tr("preview.col.oldtarget"),     95, tk.CENTER),
        ("new",    tr("preview.col.newtarget"),     95, tk.CENTER),
        ("delta",  tr("preview.col.targetdelta"),   85, tk.E),
    ])
    for row in snapshot["pointers"]:
        pointer_tree.insert("", tk.END, values=(
            f"0x{row['source']:X}", row["kind"], row["string_id"],
            f"0x{row['old_lowword']:04X}", f"0x{row['new_lowword']:04X}",
            f"0x{row['old_target']:X}", f"0x{row['new_target']:X}",
            f"{row['target_delta']:+d}",
        ))

    font_tree = make_preview_tree(tabs["Fonts"], [
        ("status",  tr("preview.col.status"),        80, tk.CENTER),
        ("font",    tr("preview.col.font"),          100, tk.CENTER),
        ("offset",  tr("preview.col.glyphoffset"),   90, tk.CENTER),
        ("code",    tr("preview.col.canonical"),     75, tk.CENTER),
        ("aliases", tr("preview.col.aliascodes"),   220, tk.W),
        ("old",     tr("preview.col.oldwidth"),      75, tk.E),
        ("new",     tr("preview.col.newwidth"),      75, tk.E),
        ("max",     tr("preview.col.maxwidth"),      75, tk.E),
        ("bitmap",  tr("preview.col.bitmap"),        70, tk.CENTER),
        ("bytes",   tr("preview.col.changedbytes"),  95, tk.E),
    ])
    for row in snapshot["fonts"]:
        aliases = ", ".join(f"0x{v:02X}" for v in row["alias_codes"]) or "—"
        font_tree.insert("", tk.END, values=(
            row["status"], row["font"], f"0x{row['glyph_offset']:X}",
            f"0x{row['canonical_code']:02X}", aliases,
            row["old_width"], row["new_width"], row["max_width"],
            flag(row["bitmap_changed"]),
            row["changed_physical_bytes"],
        ), tags=(row["status"],))
    ttk.Button(dialog, text=tr("dlg.preview.close"),command=dialog.destroy).pack(pady=(2, 10))


def show_integrity_dialog(root, gaps: list) -> bool:
    dlg = tk.Toplevel(root)
    dlg.title("Integrity Check Failed")
    dlg.resizable(True, True)
    dlg.grab_set()
    dlg.minsize(660, 300)

    tk.Label(dlg,text="Editing can be inspected, but Repack and Save are blocked.",font=("Segoe UI", 10, "bold"),fg="#C0392B",anchor="w",padx=12, pady=8,).pack(fill=tk.X)

    if gaps:
        tk.Label(dlg,text=f"{len(gaps)} unknown gap(s) found. Auto-fix will zero-fill them.",font=("Segoe UI", 9),fg="#7D6608",anchor="w",padx=12, pady=0,).pack(fill=tk.X)

    list_frame = tk.Frame(dlg, bg="#FFFFFF", bd=1, relief=tk.SUNKEN)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
    vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas_inner = tk.Canvas(list_frame, bg="#FFFFFF", highlightthickness=0,yscrollcommand=vsb.set,)
    canvas_inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.config(command=canvas_inner.yview)
    rows_frame  = tk.Frame(canvas_inner, bg="#FFFFFF")
    canvas_win  = canvas_inner.create_window((0, 0), window=rows_frame, anchor="nw")

    def _on_rows_configure(event):
        canvas_inner.configure(scrollregion=canvas_inner.bbox("all"))

    def _on_canvas_resize(event):
        canvas_inner.itemconfig(canvas_win, width=event.width)

    rows_frame.bind("<Configure>",   _on_rows_configure)
    canvas_inner.bind("<Configure>", _on_canvas_resize)

    if not gaps:
        tk.Label(rows_frame, text="No correctable gaps found.",font=("Segoe UI", 9), bg="#FFFFFF", fg="#555555",anchor="w", padx=8, pady=6,).pack(fill=tk.X)
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

    result  = tk.BooleanVar(value=False)
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


__all__ = [
    "make_preview_tree",
    "show_preview_dialog",
    "show_integrity_dialog",
]

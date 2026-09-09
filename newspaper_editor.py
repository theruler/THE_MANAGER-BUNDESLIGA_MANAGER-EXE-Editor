from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk
from typing import Callable
import newspaper_grammar as NG
from charmap import CharmapEncodeError
from repack_validator import repack_transaction, validate_image

_MARKER_COLOURS: dict[str, tuple[str, str]] = {
    "TEAM_A":     ("#1565C0", "#FFFFFF"),
    "TEAM_B":     ("#AD1457", "#FFFFFF"),
    "SCORE_0":    ("#2E7D32", "#FFFFFF"),
    "SCORE_1":    ("#00796B", "#FFFFFF"),
    "PREV_0":     ("#E65100", "#FFFFFF"),
    "PREV_1":     ("#BF360C", "#FFFFFF"),
    "LEAD_0":     ("#6A1B9A", "#FFFFFF"),
    "LEAD_1":     ("#4527A0", "#FFFFFF"),
    "ATTENDANCE": ("#00838F", "#FFFFFF"),
    "PLAYER_1":   ("#558B2F", "#FFFFFF"),
    "PLAYER_2":   ("#827717", "#FFFFFF"),
    "MANAGER":    ("#4E342E", "#FFFFFF"),
}
_SEL_COLOUR   = ("#78909C", "#FFFFFF")
_BREAK_COLOUR = ("#F57F17", "#000000")

_SELECTOR_CODE_NAMES: dict[str, str] = {
    "02": "RANDOM_2",
    "03": "RANDOM_3",
    "04": "RANDOM_4",
    "10": "CONTEXT_1",
    "20": "CONTEXT_2",
    "30": "CONTEXT_3",
    "40": "CONTEXT_4",
    "50": "CONTEXT_5",
}

_RANDOM_PALETTE: list[tuple[str, str]] = [
    ("#4A235A", "#FFFFFF"),
    ("#6C3483", "#FFFFFF"),
    ("#8E44AD", "#E8DAEF"),
    ("#A569BD", "#FFFFFF"),
    ("#D2B4DE", "#1A0030"),
]

_CONTEXT_PALETTE: list[tuple[str, str]] = [
    ("#784212", "#FFFFFF"),
    ("#935116", "#FFFFFF"),
    ("#B9770E", "#FFFFFF"),
    ("#D68910", "#1A0A00"),
    ("#F0B27A", "#3E1F00"),
]

def _semantic_name_from_code(selector_code: str) -> str:
    return _SELECTOR_CODE_NAMES.get(selector_code.upper(), f"SEL:{selector_code}")

def _is_random_code(selector_code: str) -> bool:
    return selector_code[:1] == "0"

def _instance_colour(instance_index: int, is_random: bool) -> tuple[str, str]:
    palette = _RANDOM_PALETTE if is_random else _CONTEXT_PALETTE
    return palette[instance_index % len(palette)]

_GROUP_COLOURS: list[tuple[str, str]] = [
    ("#1A237E", "#C5CAE9"),
    ("#1B5E20", "#C8E6C9"),
    ("#4A148C", "#E1BEE7"),
    ("#E65100", "#FFE0B2"),
    ("#006064", "#B2EBF2"),
    ("#880E4F", "#FCE4EC"),
]

class _DragState:
    def __init__(self):
        self.active:  "_TagLabel | None" = None
        self._ghost:  "tk.Toplevel | None" = None
        self._cursor: "str | None" = None 

    def show_ghost(self, text: str, bg: str, fg: str, x: int, y: int):
        self.hide_ghost()
        g = tk.Toplevel()
        g.overrideredirect(True)
        g.attributes("-topmost", True)
        try:
            g.attributes("-alpha", 0.75)
        except Exception:
            pass
        tk.Label(g, text=text, bg=bg, fg=fg,
                 font=("Segoe UI", 8, "bold"),
                 padx=6, pady=2, relief="solid", bd=1).pack()
        g.geometry(f"+{x+12}+{y+4}")
        self._ghost = g

    def move_ghost(self, x: int, y: int):
        if self._ghost:
            self._ghost.geometry(f"+{x+12}+{y+4}")

    def hide_ghost(self):
        if self._ghost:
            try:
                self._ghost.destroy()
            except Exception:
                pass
            self._ghost = None

    def show_cursor(self, tw: "tk.Text", index: str):
        if self._cursor:
            try:
                tw.tag_remove("_drop_cursor", "1.0", tk.END)
            except Exception:
                pass
        self._cursor = index
        tw.tag_configure("_drop_cursor",
                         background="#1565C0", foreground="#FFFFFF")
        try:
            tw.tag_add("_drop_cursor", index, f"{index}+1c")
        except Exception:
            pass

    def hide_cursor(self, tw: "tk.Text | None"):
        if tw and self._cursor:
            try:
                tw.tag_remove("_drop_cursor", "1.0", tk.END)
            except Exception:
                pass
        self._cursor = None

def _tokens_to_display(tokens: list[tuple[str, str]]) -> str:
    parts = []
    for kind, val in tokens:
        if kind == "marker":
            parts.append(f"[[{val}]]")
        else:
            parts.append(val)
    return "".join(parts)

class _TagLabel(tk.Label):
    def __init__(self, text_widget: tk.Text, marker_name: str, display: str,
                 bg: str, fg: str, drag_state: _DragState,
                 deletable: bool = False,
                 on_change: Callable | None = None,
                 row: "_ComponentEditor | None" = None):
        super().__init__(
            text_widget,
            text=display,
            bg=bg, fg=fg,
            font=("Segoe UI", 8, "bold"),
            padx=5, pady=1,
            relief="flat",
            cursor="hand2",
        )
        self._tw         = text_widget
        self.marker_name = marker_name
        self._bg         = bg
        self._fg         = fg
        self._display    = display
        self._ds         = drag_state
        self._deletable  = deletable
        self._on_change  = on_change
        self._row        = row

        self.bind("<ButtonPress-1>",   self._press)
        self.bind("<B1-Motion>",       self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Button-3>",        self._delete)
        if deletable:
            self.bind("<Double-Button-1>", self._delete)
            self.bind("<Delete>",          self._delete)
            self.bind("<BackSpace>",       self._delete)
            self.bind("<FocusIn>",  lambda e: self.config(relief="solid", bd=1))
            self.bind("<FocusOut>", lambda e: self.config(relief="flat",  bd=0))

    def _my_index(self) -> str:
        my_name = str(self)
        for w in self._tw.window_names():
            if w == my_name:
                return self._tw.index(w)
        return "1.0"

    def _press(self, event):
        self._ds.active = self
        self.focus_set()
        self._ds.show_ghost(self._display, self._bg, self._fg,
                            event.x_root, event.y_root)

    def _motion(self, event):
        if self._ds.active is not self:
            return
        self._ds.move_ghost(event.x_root, event.y_root)
        if self._row is None:
            return
        rx = max(0, min(event.x_root - self._tw.winfo_rootx(),
                        self._tw.winfo_width() - 1))
        ry = max(0, min(event.y_root - self._tw.winfo_rooty(),
                        self._tw.winfo_height() - 1))
        try:
            drop_tk = self._tw.index(f"@{rx},{ry}")
            self._ds.show_cursor(self._tw, drop_tk)
        except Exception:
            pass

    def _release(self, event):
        if self._ds.active is not self:
            return
        self._ds.active = None
        self._ds.hide_ghost()
        self._ds.hide_cursor(self._tw if self._row else None)

        if self._row is None:
            return

        rx = max(0, min(event.x_root - self._tw.winfo_rootx(),
                        self._tw.winfo_width() - 1))
        ry = max(0, min(event.y_root - self._tw.winfo_rooty(),
                        self._tw.winfo_height() - 1))
        drop_tk  = self._tw.index(f"@{rx},{ry}")
        src_tk   = self._my_index()

        tokens   = self._row._tokenise(self._tw)
        drag_pos = self._find_token_pos(tokens, src_tk)
        drop_pos, split_at = self._find_drop_pos(tokens, drop_tk)

        if drag_pos is None:
            return
        if split_at > 0 and drop_pos < len(tokens):
            kind, val = tokens[drop_pos]
            if kind == "text" and split_at < len(val):
                tokens[drop_pos] = ("text", val[:split_at])
                tokens.insert(drop_pos + 1, ("text", val[split_at:]))
                if drop_pos < drag_pos:
                    drag_pos += 1
                drop_pos += 1

        if drop_pos == drag_pos:
            return

        dragged = tokens.pop(drag_pos)
        if drop_pos > drag_pos:
            drop_pos -= 1
        tokens.insert(drop_pos, dragged)

        self._row._populate_widget(self._tw, _tokens_to_display(tokens))
        self._row._push_undo()
        if self._on_change:
            self._on_change()

    def _find_token_pos(self, tokens, target_tk):
        cur = "1.0"
        for i, (kind, val) in enumerate(tokens):
            if kind == "marker":
                if self._tw.compare(cur, "==", target_tk):
                    return i
                cur = self._tw.index(f"{cur}+1c")
            else:
                cur = self._tw.index(f"{cur}+{len(val)}c")
        return None

    def _find_drop_pos(self, tokens, drop_tk):
        cur = "1.0"
        for i, (kind, val) in enumerate(tokens):
            if self._tw.compare(cur, ">=", drop_tk):
                return i, 0
            if kind == "marker":
                cur = self._tw.index(f"{cur}+1c")
            else:
                for ci in range(len(val)):
                    char_idx = self._tw.index(f"{cur}+{ci}c")
                    if self._tw.compare(char_idx, ">=", drop_tk):
                        return i, ci
                cur = self._tw.index(f"{cur}+{len(val)}c")
        return len(tokens), 0

    def _delete(self, event=None):
        if self._row is None:
            return "break"
        src_tk = self._my_index()
        tokens = self._row._tokenise(self._tw)
        pos    = self._find_token_pos(tokens, src_tk)
        if pos is not None:
            tokens.pop(pos)
        self._row._populate_widget(self._tw, _tokens_to_display(tokens))
        self._row._push_undo()
        if self._on_change:
            self._on_change()
        if self.marker_name.startswith("SEL:"):
            sel_key = self.marker_name[4:]
            panel = getattr(self._row, "_panel", None)
            if panel is not None:
                panel._remove_sel_component(sel_key)
        return "break"

class _ComponentEditor:
    def __init__(self, parent: tk.Widget, component: dict,
                 drag_state: _DragState,
                 on_change: Callable | None = None,
                 sel_meta: "dict[str, tuple[str, tuple[str,str]]] | None" = None,
                 decode_fn: "Callable[[str], str] | None" = None,
                 encode_fn: "Callable[[str], str] | None" = None,
                 fixed_width: bool = False,
                 panel: "NewspaperEditorPanel | None" = None):
        self._comp        = component
        self._ds          = drag_state
        self._on_change   = on_change
        self._sel_meta    = sel_meta or {}
        self._decode_fn   = decode_fn or (lambda t: t)
        self._encode_fn   = encode_fn or (lambda t: t)
        self._fixed_width = fixed_width
        self._panel       = panel
        self._undo:        list[str] = []
        self._committed: str       = component["source_text"]

        outer = tk.Frame(parent, bg="#BDC3C7", bd=1)
        outer.pack(side=tk.LEFT, anchor="nw")
        self.widget = tk.Text(
            outer, height=1, wrap="none",
            font=("Consolas", 10, "bold"),
            bg="#FFFFFF", fg="#1A252F",
            insertbackground="#1A252F",
            relief="flat", padx=4, pady=2,
        )
        self.widget.pack(side=tk.LEFT)
        self.widget.bind("<KeyRelease>", self._on_key)
        self.widget.bind("<Return>",     self._on_return)
        self.widget.bind("<Control-z>",  self._undo_cb)
        self.widget.bind("<Control-Z>",  self._undo_cb)

        self._populate(component["source_text"])
        self._push_undo()

    def translate_content(self, translate_fn: Callable):
        tokens = self._tokenise(self.widget)
        changed = False
        for i, (kind, val) in enumerate(tokens):
            if kind == "text" and val.strip():
                lspace = len(val) - len(val.lstrip())
                rspace = len(val) - len(val.rstrip())
                stripped = val.strip()
                if stripped:
                    try:
                        translated = translate_fn(stripped)
                        tokens[i] = ("text", val[:lspace] + translated + (val[-rspace:] if rspace else ""))
                        changed = True
                    except Exception:
                        pass
        if changed:
            self._populate(_tokens_to_display(tokens))
            self._push_undo()
            if self._on_change:
                self._on_change()

    def _apply_char_map(self, text: str) -> str:
        return self._decode_fn(text)

    def _reverse_char_map(self, text: str) -> str:
        return self._encode_fn(text)

    _SPACE_TAG = "_space_bg"

    def _apply_space_highlight(self, tw: tk.Text):
        tw.tag_configure(self._SPACE_TAG,
                         background="#BBDEFB", foreground="#0D47A1")
        tw.tag_remove(self._SPACE_TAG, "1.0", tk.END)
        idx = "1.0"
        while True:
            idx = tw.search(" ", idx, stopindex=tk.END)
            if not idx:
                break
            tw.tag_add(self._SPACE_TAG, idx, f"{idx}+1c")
            idx = f"{idx}+1c"

    def _populate(self, display_text: str):
        tw = self.widget
        prev = tw.cget("state")
        tw.config(state=tk.NORMAL)
        tw.delete("1.0", tk.END)
        pos = 0
        for m in NG.MARKER_PATTERN.finditer(display_text):
            lit = display_text[pos:m.start()]
            if lit:
                tw.insert(tk.END, self._apply_char_map(lit))
            self._insert_marker(tw, m.group(1))
            pos = m.end()
        remainder = display_text[pos:]
        if remainder:
            tw.insert(tk.END, self._apply_char_map(remainder))
        tw.config(state=prev)
        self._apply_space_highlight(tw)
        self._resize()

    def _insert_marker(self, tw: tk.Text, name: str):
        if name == "BREAK":
            badge = _TagLabel(tw, "BREAK", "⏎", *_BREAK_COLOUR,
                              self._ds, deletable=True,
                              on_change=self._on_change, row=self)
            tw.window_create(tk.END, window=badge)
        elif name.startswith("SEL:"):
            sel_key = name[4:]
            if sel_key in self._sel_meta:
                display, colour = self._sel_meta[sel_key]
            elif sel_key.upper() in _SELECTOR_CODE_NAMES:
                display = _semantic_name_from_code(sel_key)
                colour  = (_RANDOM_PALETTE[0] if _is_random_code(sel_key)
                           else _CONTEXT_PALETTE[0])
            else:
                display = sel_key
                colour  = _SEL_COLOUR
            badge = _TagLabel(tw, name, display, *colour,
                              self._ds, deletable=False,
                              on_change=self._on_change, row=self)
            tw.window_create(tk.END, window=badge)
        else:
            colours = _MARKER_COLOURS.get(name, ("#607D8B", "#FFFFFF"))
            badge = _TagLabel(tw, name, name, *colours,
                              self._ds, deletable=False,
                              on_change=self._on_change, row=self)
            tw.window_create(tk.END, window=badge)

    def _tokenise(self, tw: tk.Text) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        index   = "1.0"
        end     = tw.index("end-1c")
        buf: list[str] = [] 

        def flush():
            if buf:
                raw = self._reverse_char_map("".join(buf))
                tokens.append(("text", raw))
                buf.clear()

        while tw.compare(index, "<=", end):
            win = ""
            try:
                win = tw.window_cget(index, "window")
            except tk.TclError:
                pass
            if win:
                flush()
                try:
                    w = tw.nametowidget(win)
                except KeyError:
                    w = None
                if isinstance(w, _TagLabel):
                    tokens.append(("marker", w.marker_name))
                index = tw.index(f"{index}+1c")
                continue
            ch = tw.get(index)
            if ch and ch != "\n":
                buf.append(ch)
            index = tw.index(f"{index}+1c")

        flush()
        return tokens

    def _populate_widget(self, tw: tk.Text, display_text: str):
        self._populate(display_text)

    def get_source(self) -> str:
        return _tokens_to_display(self._tokenise(self.widget))

    def get_display(self) -> str:
        tokens = self._tokenise(self.widget)
        parts = []
        for kind, val in tokens:
            if kind == "marker":
                parts.append(f"[[{val}]]")
            else:
                parts.append(self._decode_fn(val))
        return "".join(parts)

    def component_id(self) -> str:
        return self._comp["component_id"]

    def _resize(self):
        tw = self.widget
        tw.update_idletasks()

        import tkinter.font as tkfont
        f = tkfont.Font(font=tw.cget("font"))
        char_w_px = f.measure("W")
        if char_w_px < 1:
            char_w_px = 8

        n_windows = len(tw.window_names())
        raw_text  = tw.get("1.0", "end-1c").replace("\n", "")
        text_px   = f.measure(raw_text) if raw_text else 0
        badge_px = 0
        for wname in tw.window_names():
            try:
                w = tw.nametowidget(wname)
                badge_px += w.winfo_reqwidth()
            except Exception:
                badge_px += char_w_px * 5 
        total_px  = text_px + badge_px + 12 
        content_chars = max(int(total_px / char_w_px) + 1, 1)
        new_width = content_chars + 3
        tw.config(width=max(new_width, 4))

        tw.update_idletasks()
        total_lines = int(tw.index("end-1c").split(".")[0])
        lines = 0
        for ln in range(1, total_lines + 1):
            result = tw.count(f"{ln}.0", f"{ln}.end", "displaylines")
            dl = (result[0] if isinstance(result, tuple) else result) or 0
            lines += dl + 1
        tw.config(height=max(lines, 1))

    def _push_undo(self):
        try:
            snap = self.get_source()
        except CharmapEncodeError:
            return
        if not self._undo or self._undo[-1] != snap:
            self._undo.append(snap)

    def _undo_cb(self, event=None):
        if len(self._undo) > 1:
            self._undo.pop()
            self._populate(self._undo[-1])
            if self._on_change:
                self._on_change()
        return "break"

    def _on_key(self, _e=None):
        self._apply_space_highlight(self.widget)
        self._push_undo()
        self._resize()
        if self._panel is not None:
            try:
                self.get_source()
                self._panel._err_lbl.config(text="")
            except CharmapEncodeError as exc:
                self._panel._err_lbl.config(text=str(exc))
        if self._on_change:
            self._on_change()

    def _on_return(self, _e=None):
        cursor = self.widget.index(tk.INSERT)
        tokens = self._tokenise(self.widget)
        cur    = "1.0"
        ins_at = len(tokens)
        for i, (kind, val) in enumerate(tokens):
            if self.widget.compare(cur, ">=", cursor):
                ins_at = i
                break
            cur = self.widget.index(
                f"{cur}+1c" if kind == "marker" else f"{cur}+{len(val)}c")
        tokens.insert(ins_at, ("marker", "BREAK"))
        self._populate(_tokens_to_display(tokens))
        self._push_undo()
        if self._on_change:
            self._on_change()
        return "break"

    def is_dirty(self) -> bool:
        return self.get_source() != self._committed

    def discard(self):
        self._undo.clear()
        self._populate(self._committed)
        self._push_undo()

    def commit(self):
        try:
            self._committed = self.get_source()
            self._undo.clear()
            self._push_undo()
        except CharmapEncodeError:
            pass


def _group_components(comps: list[dict]) -> list[dict | list[dict]]:
    groups: dict[str, list[dict]] = {}
    order:  list[str] = []
    root   = None

    for c in comps:
        if c["component_id"] == "ROOT":
            root = c
        elif c.get("selector"):
            sel = c["selector"]
            if sel not in groups:
                groups[sel] = []
                order.append(sel)
            groups[sel].append(c)

    result: list = []
    if root:
        result.append(root)
    for sel in order:
        result.append(groups[sel])
    return result

def _group_bg(index: int) -> tuple[str, str]:
    return _GROUP_COLOURS[index % len(_GROUP_COLOURS)]


class _PoolDragBadge:
    def __init__(self, label: tk.Label, marker_name: str, display: str,
                 bg: str, fg: str, drag_state: _DragState,
                 panel: "NewspaperEditorPanel"):
        self._lbl         = label
        self.marker_name  = marker_name
        self._display     = display
        self._bg          = bg
        self._fg          = fg
        self._ds          = drag_state
        self._panel       = panel

        label.bind("<ButtonPress-1>",   self._press)
        label.bind("<B1-Motion>",       self._motion)
        label.bind("<ButtonRelease-1>", self._release)

    def _press(self, event):
        self._ds.active = self
        self._ds.show_ghost(self._display, self._bg, self._fg,
                            event.x_root, event.y_root)

    def _motion(self, event):
        self._ds.move_ghost(event.x_root, event.y_root)
        tw = self._find_tw_under(event.x_root, event.y_root)
        if tw:
            rx = event.x_root - tw.winfo_rootx()
            ry = event.y_root - tw.winfo_rooty()
            try:
                idx = tw.index(f"@{rx},{ry}")
                self._ds.show_cursor(tw, idx)
            except Exception:
                pass

    def _release(self, event):
        self._ds.active = None
        self._ds.hide_ghost()

        tw, ed = self._find_editor_under(event.x_root, event.y_root)
        if tw is None or ed is None:
            self._ds.hide_cursor(None)
            return

        self._ds.hide_cursor(tw)
        rx = event.x_root - tw.winfo_rootx()
        ry = event.y_root - tw.winfo_rooty()
        try:
            drop_idx = tw.index(f"@{rx},{ry}")
        except Exception:
            drop_idx = "end"

        tokens = ed._tokenise(tw)
        cur = "1.0"
        insert_at = len(tokens)
        split_at  = 0
        for i, (kind, val) in enumerate(tokens):
            if tw.compare(cur, ">=", drop_idx):
                insert_at = i
                split_at  = 0
                break
            if kind == "marker":
                cur = tw.index(f"{cur}+1c")
            else:
                for ci in range(len(val)):
                    char_idx = tw.index(f"{cur}+{ci}c")
                    if tw.compare(char_idx, ">=", drop_idx):
                        insert_at = i
                        split_at  = ci
                        break
                else:
                    cur = tw.index(f"{cur}+{len(val)}c")
                    continue
                break

        if split_at > 0 and insert_at < len(tokens):
            kind, val = tokens[insert_at]
            if kind == "text" and split_at < len(val):
                tokens[insert_at] = ("text", val[:split_at])
                tokens.insert(insert_at + 1, ("text", val[split_at:]))
                insert_at += 1

        if self.marker_name.startswith("SEL:"):
            raw_key = self.marker_name[4:]
            code_upper = raw_key.upper()
            if code_upper in _SELECTOR_CODE_NAMES:
                selector, selector_code, label, colour, n_branches = \
                    self._panel._allocate_selector(code_upper)
                final_marker = f"SEL:{selector}"
            else:
                selector = raw_key
                final_marker = self.marker_name
            tokens.insert(insert_at, ("marker", final_marker))
            ed._populate_widget(tw, _tokens_to_display(tokens))
            ed._push_undo()
            if ed._on_change:
                ed._on_change()
            self._panel._add_sel_component_for(self.marker_name, selector_override=selector)
        else:
            tokens.insert(insert_at, ("marker", self.marker_name))
            ed._populate_widget(tw, _tokens_to_display(tokens))
            ed._push_undo()
            if ed._on_change:
                ed._on_change()

    def _find_tw_under(self, x_root: int, y_root: int) -> "tk.Text | None":
        tw, _ = self._find_editor_under(x_root, y_root)
        return tw

    def _find_editor_under(self, x_root: int,
                           y_root: int) -> "tuple[tk.Text | None, _ComponentEditor | None]":
        for ed in self._panel._editors:
            tw = ed.widget
            try:
                wx = tw.winfo_rootx()
                wy = tw.winfo_rooty()
                ww = tw.winfo_width()
                wh = tw.winfo_height()
                if wx <= x_root <= wx + ww and wy <= y_root <= wy + wh:
                    return tw, ed
            except Exception:
                pass
        return None, None

class NewspaperEditorPanel(ttk.Frame):

    def __init__(self, parent: tk.Widget, editor):
        super().__init__(parent)
        self._editor  = editor
        self._editors: list[_ComponentEditor] = [] 
        self._ds      = _DragState()
        self._entry:  dict | None = None
        self._comps:  list[dict]  = []
        self._decode_fn: "Callable[[str], str]" = lambda t: t
        self._encode_fn: "Callable[[str], str]" = lambda t: t
        self._dirty_hint = False

        self._build_shell()

    def _build_shell(self):
        self._hdr = ttk.Frame(self)
        self._hdr.pack(fill=tk.X, pady=(8, 2))
        ttk.Label(self._hdr,
                  text="📰  Newspaper String Editor",
                  font=("Segoe UI", 10, "bold"),
                  foreground="#1565C0").pack(side=tk.LEFT)
        self._status_lbl = ttk.Label(self._hdr, text="",font=("Segoe UI", 9, "italic"),foreground="#27AE60")
        self._status_lbl.pack(side=tk.RIGHT, padx=(0, 8))
        self._err_lbl = ttk.Label(self._hdr, text="",font=("Segoe UI", 9, "italic"),foreground="#C0392B")
        self._err_lbl.pack(side=tk.RIGHT, padx=(0, 8))
        self._tr_frame = tk.Frame(self, bg="#EDE7F6")
        from translator import TRANSLATION_ENGINES
        engine_var = tk.StringVar(value="Google Translate")
        eng_cb = ttk.Combobox(self._tr_frame, textvariable=engine_var, values=list(TRANSLATION_ENGINES.keys()), width=16, state="readonly", font=("Segoe UI", 7))
        eng_cb.pack(side=tk.LEFT, padx=(2, 2), pady=4)
        src_var = tk.StringVar(value="auto")
        src_cb = ttk.Combobox(self._tr_frame, textvariable=src_var, values=["auto","de","en","fr","es","it"], width=5, state="readonly", font=("Segoe UI", 7))
        src_cb.pack(side=tk.LEFT, padx=(0, 2), pady=4)
        tgt_default = "it"
        try:
            if hasattr(self._editor, "target_lang_var"):
                tgt_default = self._editor.target_lang_var.get()
        except Exception:
            pass
        tgt_var = tk.StringVar(value=tgt_default)
        tgt_cb = ttk.Combobox(self._tr_frame, textvariable=tgt_var, values=["it","en","de","fr","es"], width=5, state="readonly", font=("Segoe UI", 7))
        tgt_cb.pack(side=tk.LEFT, padx=(0, 4), pady=4)
        
        tr_status_lbl = ttk.Label(self._tr_frame, text="", font=("Segoe UI", 7, "italic"), foreground="#7F8C8D")
        tr_status_lbl.pack(side=tk.LEFT, padx=(0, 4), pady=4)
        
        def _apply_global_tr():
            from translator import translate_string as _ts, TranslationIntegrityError
            engine = engine_var.get()
            src = src_var.get()
            tgt = tgt_var.get()
            tr_status_lbl.config(text="…", foreground="#1565C0")
            self._tr_frame.update_idletasks()
            
            def do_tr(text):
                return _ts(text, target_lang=tgt, source_lang=src, engine=engine)
                
            errors = []
            for ed in self._editors:
                try:
                    ed.translate_content(do_tr)
                except TranslationIntegrityError as exc:
                    errors.append(str(exc))
                except Exception as exc:
                    errors.append(str(exc))
                    
            if errors:
                tr_status_lbl.config(text=f"⚠ {errors[0][:40]}", foreground="#C0392B")
            else:
                tr_status_lbl.config(text="✔ Translated", foreground="#27AE60")
                self.after(2000, lambda: tr_status_lbl.config(text=""))
                
        apply_btn = ttk.Button(self._tr_frame, text="▶ Translate", command=_apply_global_tr)
        apply_btn.pack(side=tk.LEFT, padx=(0, 2), pady=4)
        self._pool_frame = tk.Frame(self, bg="#E8EAF6", bd=1, relief="groove")
        self._pool_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        self._pool_inner = tk.Frame(self._pool_frame, bg="#E8EAF6")
        self._pool_inner.pack(fill=tk.X, padx=4, pady=3)
        sf = ttk.Frame(self)
        sf.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(sf, highlightthickness=0, bg="#F4F6F9")
        vsb = ttk.Scrollbar(sf, orient=tk.VERTICAL,command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._inner = ttk.Frame(self._canvas)
        self._win_id = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",  self._on_inner_cfg)
        self._canvas.bind("<Configure>", self._on_canvas_cfg)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._canvas.bind(seq, self._scroll)
        

    def _build_pool(self, sel_meta: "dict[str, tuple[str, tuple[str,str]]] | None" = None):
        for w in self._pool_inner.winfo_children():
            w.destroy()
        row1 = tk.Frame(self._pool_inner, bg="#E8EAF6")
        row1.pack(fill=tk.X, pady=1)
        ttk.Label(row1, text="TAG:",
                  font=("Segoe UI", 7, "bold"),
                  foreground="#546E7A",
                  background="#E8EAF6").pack(side=tk.LEFT, padx=(0, 6))
        self._make_pool_badge(row1, "BREAK", "⏎", *_BREAK_COLOUR)
        for name, (bg, fg) in _MARKER_COLOURS.items():
            self._make_pool_badge(row1, name, name, bg, fg)
        row2 = tk.Frame(self._pool_inner, bg="#E8EAF6")
        row2.pack(fill=tk.X, pady=1)
        ttk.Label(row2, text="RANDOM / CONTEXT:",
                  font=("Segoe UI", 7, "bold"),
                  foreground="#546E7A",
                  background="#E8EAF6").pack(side=tk.LEFT, padx=(0, 6))
        _GREY_RANDOM  = ("#78909C", "#FFFFFF")
        _GREY_CONTEXT = ("#90A4AE", "#1A252F")
        for code, semantic in _SELECTOR_CODE_NAMES.items():
            colour = _GREY_RANDOM if _is_random_code(code) else _GREY_CONTEXT
            self._make_pool_badge(row2, f"SEL:{code}", semantic, *colour)

    def _make_pool_badge(self, parent, marker_name: str, display: str, bg: str, fg: str):
        lbl = tk.Label(parent, text=display,
                       bg=bg, fg=fg,
                       font=("Segoe UI", 8, "bold"),
                       padx=5, pady=1, relief="flat", cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=2)
        pdb = _PoolDragBadge(lbl, marker_name, display, bg, fg, self._ds, panel=self)
        lbl._pdb = pdb 

    def _on_inner_cfg(self, _e=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        h = self._inner.winfo_reqheight()
        self._canvas.configure(height=max(h, 40))

    def _on_canvas_cfg(self, event=None):
        if event:
            self._canvas.itemconfig(self._win_id, width=event.width)

    def _scroll(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _allocate_selector(self, generic_code: str) -> tuple:
        code_upper = generic_code.upper()
        existing_nums = []
        for c in self._comps:
            s = c.get("selector", "")
            if s.startswith("S") and s[1:].isdigit():
                existing_nums.append(int(s[1:]))
        next_num = max(existing_nums, default=0) + 1
        selector = f"S{next_num:02d}"

        is_rnd = _is_random_code(code_upper)
        if is_rnd:
            try:
                n_branches = int(code_upper[1], 16)
            except Exception:
                n_branches = 2
        else:
            n_branches = 2

        instance_index = sum(
            1 for c in self._comps
            if c.get("selector_code", "").upper() in _SELECTOR_CODE_NAMES
            and _is_random_code(c.get("selector_code", "")) == is_rnd
            and c.get("branch_index") == "1"
        )
        semantic = _semantic_name_from_code(code_upper)
        colour = _instance_colour(instance_index, is_rnd)
        label = f"{semantic}({instance_index + 1})"

        return selector, code_upper, label, colour, n_branches

    def _add_sel_component_for(self, marker_name: str, selector_override: str | None = None):
        raw_key = marker_name[4:]
        code_upper = raw_key.upper()
        ed_by_id = {e.component_id(): e for e in self._editors}
        for comp in self._comps:
            ed = ed_by_id.get(comp["component_id"])
            if ed is not None:
                try:
                    comp["source_text"] = ed.get_source()
                except CharmapEncodeError:
                    pass

        if code_upper in _SELECTOR_CODE_NAMES:
            if selector_override:
                selector = selector_override
                selector_code = code_upper
                is_rnd = _is_random_code(code_upper)
                if is_rnd:
                    try:
                        n_branches = int(code_upper[1], 16)
                    except Exception:
                        n_branches = 2
                else:
                    n_branches = 2
            else:
                selector, selector_code, _label, _colour, n_branches = \
                    self._allocate_selector(code_upper)

            root_comp = next((c for c in self._comps if not c.get("selector", "")), None)
            parent_id = root_comp["component_id"] if root_comp else "ROOT"

            for branch_idx in range(1, n_branches + 1):
                new_comp = {
                    "component_id":  f"{selector}.{branch_idx}",
                    "parent_id":     parent_id,
                    "selector":      selector,
                    "selector_code": selector_code,
                    "branch_index":  str(branch_idx),
                    "source_text":   "",
                }
                self._comps.append(new_comp)
        else:
            selector = raw_key
            selector_code = next(
                (c.get("selector_code", "") for c in self._comps
                 if c.get("selector") == selector), "")
            existing_branches = [c for c in self._comps if c.get("selector") == selector]
            idx = len(existing_branches)
            root_comp = next((c for c in self._comps if not c.get("selector", "")), None)
            parent_id = root_comp["component_id"] if root_comp else "ROOT"
            new_comp = {
                "component_id":  f"{selector}.{idx + 1}",
                "parent_id":     parent_id,
                "selector":      selector,
                "selector_code": selector_code,
                "branch_index":  str(idx + 1),
                "source_text":   "",
            }
            self._comps.append(new_comp)

        self._build_layout(False, None)
        

    def _remove_sel_component(self, sel_key: str):
        ed_by_id = {e.component_id(): e for e in self._editors}
        for comp in self._comps:
            ed = ed_by_id.get(comp["component_id"])
            if ed is not None:
                try:
                    comp["source_text"] = ed.get_source()
                except CharmapEncodeError:
                    pass
        root_comp = next((c for c in self._comps if not c.get("selector", "")), None)
        if root_comp:
            root_comp["source_text"] = root_comp["source_text"].replace(
                f"[[SEL:{sel_key}]]", "")
        self._comps = [c for c in self._comps if c.get("selector", "") != sel_key]
        self._build_layout(False, None)
        
        self._on_any_change()

    def _remove_branch_field(self, branch: dict, ed: "_ComponentEditor"):
        sel_key = branch.get("selector", "")
        siblings = [c for c in self._comps if c.get("selector") == sel_key]
        if len(siblings) <= 1:
            self._remove_sel_component(sel_key)
        else:
            comp_id = branch.get("component_id", "")
            self._comps = [c for c in self._comps if c.get("component_id") != comp_id]
            self._build_layout(False, None)
            
            self._on_any_change()

    def show(self, entry: dict, decode_fn: Callable,
             translate_enabled: bool = False,
             translate_fn: Callable | None = None):
        self._entry    = entry

        try:
            self._decode_fn = lambda text, _e=entry: self._editor._decode_raw_for_entry(
                _e, text.encode("latin-1", errors="replace")
            )
            self._encode_fn = lambda text, _e=entry: self._editor._encode_entry_text(
                _e, text
            ).decode("latin-1")
        except Exception:
            self._decode_fn = lambda t: t
            self._encode_fn = lambda t: t

        self._err_lbl.config(text="")
        self._status_lbl.config(text="")

        try:
            raw_template = decode_fn(entry)
            self._comps  = NG.components(raw_template,
                                         entry.get("string_id", "?"))
        except Exception as exc:
            self._err_lbl.config(text=f"Parse error: {exc}")
            self._comps = []

        if translate_enabled:
            self._tr_frame.pack(fill=tk.X, after=self._hdr, padx=4, pady=(0, 4))
        else:
            self._tr_frame.pack_forget()

        self._build_layout(translate_enabled, translate_fn)
        self._dirty_hint = False

        self.pack(fill=tk.X, pady=(4, 4))

    def hide(self):
        self.pack_forget()
        self._clear_layout()
        self._entry = None
        self._comps = []
        self._dirty_hint = False

    def _clear_layout(self):
        for child in self._inner.winfo_children():
            child.destroy()
        self._editors.clear()

    def _build_layout(self, translate_enabled: bool,
                      translate_fn: Callable | None):
        self._clear_layout()
        groups = _group_components(self._comps)
        sel_meta: dict[str, tuple[str, tuple[str, str]]] = {}
        instance_counter = 0
        fallback_index   = 0
        for item in groups:
            if isinstance(item, list) and item:
                sel  = item[0]["selector"] 
                code = item[0].get("selector_code", "") 
                if sel in sel_meta:
                    continue
                if code.upper() in _SELECTOR_CODE_NAMES:
                    semantic = _semantic_name_from_code(code) 
                    is_rnd   = _is_random_code(code)
                    colour   = _instance_colour(instance_counter, is_rnd)
                    label    = f"{semantic}({instance_counter + 1})"
                    instance_counter += 1
                else:
                    colour = _group_bg(fallback_index)
                    label  = sel
                    fallback_index += 1
                sel_meta[sel] = (label, colour)

        self._build_pool(sel_meta)

        for item in groups:
            if isinstance(item, dict):
                self._add_root_row(item, translate_enabled, translate_fn, sel_meta)
            else:
                sel_name = item[0]["selector"]
                label, (bg, fg) = sel_meta.get(sel_name, (sel_name, _SEL_COLOUR))
                self._add_sel_row(item, label, bg, fg, translate_enabled, translate_fn, sel_meta)

    def _add_root_row(self, comp: dict,
                      translate_enabled: bool,
                      translate_fn: Callable | None,
                      sel_meta: "dict[str, tuple[str, tuple[str,str]]] | None" = None):
        outer = ttk.Frame(self._inner)
        outer.pack(fill=tk.X, padx=4, pady=(0, 2))

        ttk.Label(outer,
                  text="ROOT",
                  font=("Segoe UI", 8, "bold"),
                  foreground="#546E7A").pack(anchor=tk.W)

        ed = _ComponentEditor(outer, comp, self._ds,
                              on_change=self._on_any_change,
                              sel_meta=sel_meta or {},
                              decode_fn=self._decode_fn,
                              encode_fn=self._encode_fn,
                              panel=self)
        self._editors.append(ed)

        if translate_enabled and translate_fn:
            ed.translate_content(translate_fn)

    def _add_sel_row(self, branches: list[dict],
                     label: str,
                     bg: str, fg: str,
                     translate_enabled: bool,
                     translate_fn: Callable | None,
                     sel_meta=None):

        if not branches:
            return

        if sel_meta is None:
            sel_meta = {}

        sel_name = branches[0]["selector"]

        outer = tk.Frame(self._inner, bg="#F4F6F9")
        outer.pack(fill=tk.X, padx=4, pady=(0, 3))
        tag_lbl = tk.Label(outer,
                           text=label,
                           font=("Segoe UI", 8, "bold"),
                           bg=bg, fg=fg,
                           padx=4, pady=3,
                           relief="flat",
                           cursor="hand2")
        tag_lbl.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 4))
        tag_lbl.bind("<Button-3>", lambda e, _s=sel_name: self._remove_sel_component(_s))

        fields_frame = tk.Frame(outer, bg="#F4F6F9")
        fields_frame.pack(side=tk.LEFT, fill=tk.NONE, expand=False)

        def add_branch_field(branch: dict):
            cell = tk.Frame(fields_frame, bg="#F4F6F9")
            cell.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=(0, 4))
            ed = _ComponentEditor(cell, branch, self._ds,
                                  on_change=self._on_any_change,
                                  fixed_width=False,
                                  sel_meta=sel_meta,
                                  decode_fn=self._decode_fn,
                                  encode_fn=self._encode_fn,
                                  panel=self)
            self._editors.append(ed)
            ed.widget.bind("<Button-3>", lambda e, _b=branch, _ed=ed: self._remove_branch_field(_b, _ed))

            if translate_enabled and translate_fn:
                ed.translate_content(translate_fn)

        for branch in branches:
            add_branch_field(branch)

    def refresh_translation(self, enabled: bool,
                            translate_fn: Callable | None = None):
        if enabled:
            self._tr_frame.pack(fill=tk.X, after=self._hdr, padx=4, pady=(0, 4))
        else:
            self._tr_frame.pack_forget()

        if self._entry and self._comps:
            was_dirty = self._dirty_hint
            self._build_layout(enabled, translate_fn)
            self._dirty_hint = was_dirty

    def _on_any_change(self):
        self._dirty_hint = True
        self._status_lbl.config(text="")
        try:
            self._editor._update_save_state()
        except Exception:
            pass

    def is_dirty(self) -> bool:
        return self._dirty_hint


    def _get_rebuilt_template(self) -> str | None:
        if not self._editors or not self._comps:
            return None
        ed_by_id = {e.component_id(): e for e in self._editors}
        rows_data = []
        for comp in self._comps:
            ed = ed_by_id.get(comp["component_id"])
            if ed:
                try:
                    display_text = ed.get_display()
                except CharmapEncodeError as exc:
                    self._err_lbl.config(text=str(exc))
                    return None
            else:
                display_text = self._decode_fn(comp["source_text"])

            rows_data.append({
                "component_id":   comp["component_id"],
                "parent_id":      comp.get("parent_id", ""),
                "selector":       comp.get("selector", ""),
                "selector_code":  comp.get("selector_code", ""),
                "branch_index":   comp.get("branch_index", ""),
                "source_text":    comp["source_text"],
                "translated_text": display_text,
            })
        sid = self._entry.get("string_id", "?") if self._entry else "?"
        try:
            return NG.rebuild(rows_data, sid)
        except Exception as exc:
            self._err_lbl.config(text=f"Rebuild error: {exc}")
            return None

    def apply(self):
        rebuilt = self._get_rebuilt_template()
        if rebuilt is None:
            return

        editor = self._editor
        if editor.current_index is None or not editor._supported_loaded():
            self._err_lbl.config(text="No entry selected")
            return

        entry_index = editor.current_index
        source_entry = editor.entries[entry_index]

        try:
            new_bytes = rebuilt.encode("latin-1")
        except UnicodeEncodeError as exc:
            self._err_lbl.config(text=f"Encode error: {exc}")
            return

        try:
            old_bytes = source_entry["text"].encode("latin-1")
        except UnicodeEncodeError:
            old_bytes = b""
        if new_bytes == old_bytes:
            for ed in self._editors:
                ed.commit()
            self._dirty_hint = False

            self._err_lbl.config(text="")
            self._status_lbl.config(text="✔ No changes")
            self.after(2500, lambda: self._status_lbl.config(text=""))
            return

        staged_data = bytearray(editor.exe_data)
        staged_entries = copy.deepcopy(editor.entries)
        staged_entry = staged_entries[entry_index]

        if staged_entry.get("fixed"):
            max_len = staged_entry["max_len"]
            if len(new_bytes) > max_len - 1:
                self._err_lbl.config(
                    text=f"Fixed string exceeds {max_len - 1} bytes ({len(new_bytes)} bytes)")
                return
            staged_entry["text"] = rebuilt
            address = staged_entry["str_addr"]
            staged_data[address:address + max_len] = (
                new_bytes + b"\x00" * (max_len - len(new_bytes))
            )
            validation = validate_image(
                staged_data, editor.profile, staged_entries, editor.relocation_sites)
            validation["stage"] = "fixed-output"
        else:
            staged_entry["text"] = rebuilt

            work_data, work_entries, validation = repack_transaction(
                staged_data, editor.profile, staged_entries, editor.relocation_sites)
            if validation["ok"]:
                staged_data, staged_entries = work_data, work_entries

        if not validation["ok"]:
            detail = validation["errors"][0] if validation.get("errors") else "Unknown error"
            self._err_lbl.config(text=detail)
            return

        editor._commit_text_transaction(staged_data, staged_entries, validation)
        editor.translation_pending = False
        editor.refresh_table(force=True, refresh_active_fields=True)
        editor._update_save_state()

        for ed in self._editors:
            ed.commit()
        self._dirty_hint = False

        self._err_lbl.config(text="")
        self._status_lbl.config(text="✔ Saved")
        self.after(2500, lambda: self._status_lbl.config(text=""))

    def discard(self):
        for ed in self._editors:
            ed.discard()
        self._dirty_hint = False

        self._err_lbl.config(text="")
        self._status_lbl.config(text="")
        try:
            self._editor._update_save_state()
        except Exception:
            pass

import re

MARKER_META: dict[str, tuple[str, str, str]] = {
    "a": ("TEAM_A",      "TEAM A",      "#1565C0"),
    "b": ("TEAM_B",      "TEAM B",      "#AD1457"),
    "0": ("SCORE_A",     "END SCORE A", "#2E7D32"),
    "1": ("SCORE_B",     "END SCORE B", "#00796B"),
    "2": ("PREV_A",      "DISADV. A",   "#E65100"),
    "3": ("PREV_B",      "DISADV. B",   "#BF360C"),
    "4": ("LEAD_A",      "ADVANTAGE A", "#6A1B9A"),
    "5": ("LEAD_B",      "ADVANTAGE B", "#4527A0"),
    "9": ("ATTENDANCE",  "ATTENDANCE",  "#00838F"),
    "c": ("BEST_PLAYER", "BEST PLAYER", "#558B2F"),
    "d": ("WORST_PLAYER","WORST PLAYER","#827717"),
    "t": ("MANAGER",     "MANAGER",     "#DAA520"),
    "e": ("BREAK",       "\\n",         "#F57F17"),
}

SELECTOR_META: dict[str, tuple[str, str]] = {
    "02": ("RANDOM2",      "#4A235A"),
    "03": ("RANDOM3",      "#6C3483"),
    "04": ("RANDOM4",      "#8E44AD"),
    "10": ("LOCATION",     "#3A1F14"),
    "20": ("JUDGEMENT",    "#512A18"),
    "30": ("OUTCOME",      "#6B3518"),
    "40": ("SATISFACTION", "#874415"),
    "50": ("MERIT",        "#A65D20"),
}


MARKERS = {code: meta[0] for code, meta in MARKER_META.items()}
MARKER_BY_NAME = {meta[0]: code for code, meta in MARKER_META.items()}
KNOWN_SELECTORS = set(SELECTOR_META.keys())
HEX_DIGITS = set("0123456789ABCDEFabcdef")
MARKER_PATTERN = re.compile(r"\[\[([A-Z0-9_:]+)\]\]")
SELECTOR_REF_PATTERN = re.compile(r"\[\[SEL:(S\d{2})\]\]")

class NewspaperGrammarError(ValueError):
    pass


class Dialect:
    """Same template language, different spelling.  Shared by the newspaper strings of the MZ games
    (selector closed by "#%") and the commentary strings of Bundesliga Manager Hattrick (closed by "#x").

    %xNN opens a selector, "#" separates its branches, `terminator` closes it, %<marker> is a placeholder.
    """

    def __init__(self, name, terminator, marker_meta):
        self.name = name
        self.terminator = terminator
        self.marker_meta = marker_meta
        self.markers = {code: meta[0] for code, meta in marker_meta.items()}
        self.marker_by_name = {meta[0]: code for code, meta in marker_meta.items()}

    def needs_guard(self, encoded):
        """True when a branch (after the first) would be read as the terminator ("#" + its 2nd char)."""
        return encoded.startswith(self.terminator[1:])


NEWSPAPER = Dialect("newspaper", "#%", MARKER_META)

# Commentary strings of BMH.EXE / BMH_1.EXE / FLTD.EXE.  Which game value each placeholder stands for
# is only known from context (%c = the acting player, %z = the other player, %0 = a number ...), so the
# names stay neutral.
BMH_MARKER_META: dict[str, tuple[str, str, str]] = {
    "c": ("MARK_C", "%c", "#558B2F"),
    "d": ("MARK_D", "%d", "#827717"),
    "f": ("MARK_F", "%f", "#2E7D32"),
    "z": ("MARK_Z", "%z", "#00838F"),
    "0": ("MARK_0", "%0", "#1565C0"),
}
BMH_COMMENTARY = Dialect("bmh-commentary", "#x", BMH_MARKER_META)


def _parse_sequence(raw, index, depth, selectors, string_id, dialect=NEWSPAPER):
    nodes, literal = [], []

    def flush():
        if literal:
            nodes.append(("text", "".join(literal)))
            literal.clear()

    while index < len(raw):
        char = raw[index]
        if char == "#":
            if depth == 0:
                raise NewspaperGrammarError(
                    f"{string_id}: '#' outside a selector at offset {index}")
            flush()
            return nodes, index
        if char == "%":
            nxt = raw[index + 1:index + 2]
            if nxt == "x" and len(raw) >= index + 4 \
                    and raw[index + 2] in HEX_DIGITS and raw[index + 3] in HEX_DIGITS:
                flush()
                code = raw[index + 2:index + 4].upper()
                node, index = _parse_selector(raw, index + 4, depth, code,
                                              selectors, string_id, dialect)
                nodes.append(node)
                continue
            if nxt in dialect.markers:
                flush()
                nodes.append(("marker", nxt))
                index += 2
                continue
            raise NewspaperGrammarError(
                f"{string_id}: unknown token '%{nxt}' at offset {index}")
        literal.append(char)
        index += 1

    if depth:
        raise NewspaperGrammarError(f"{string_id}: selector is not closed")
    flush()
    return nodes, index


def _parse_selector(raw, index, depth, code, selectors, string_id, dialect=NEWSPAPER):
    selectors.append(code)
    number = len(selectors)
    branches = []
    while True:
        nodes, index = _parse_sequence(raw, index, depth + 1, selectors, string_id, dialect)
        branches.append(nodes)
        if raw[index:index + 2] == dialect.terminator:
            return ("selector", number, code, branches), index + 2
        if raw[index:index + 1] != "#":
            raise NewspaperGrammarError(f"{string_id}: selector %x{code} is not closed")
        index += 1


def parse(raw, string_id="?", dialect=NEWSPAPER):
    selectors = []
    nodes, index = _parse_sequence(raw, 0, 0, selectors, string_id, dialect)
    if index != len(raw):
        raise NewspaperGrammarError(f"{string_id}: trailing input at offset {index}")
    return nodes


def _render_display(nodes, dialect=NEWSPAPER):
    out = []
    for node in nodes:
        if node[0] == "text":
            out.append(node[1])
        elif node[0] == "marker":
            out.append(f"[[{dialect.markers[node[1]]}]]")
        else:
            out.append(f"[[SEL:S{node[1]:02d}]]")
    return "".join(out)


def _walk(nodes, component_id, parent_id, components, context, dialect=NEWSPAPER):
    components.append({
        "component_id": component_id,
        "parent_id": parent_id,
        "selector": "",
        "selector_code": "",
        "branch_index": "",
        "condition": "",
        "context": context,
        "source_text": _render_display(nodes, dialect),
        "nodes": nodes,
    })
    for node in nodes:
        if node[0] != "selector":
            continue
        _number, code, branches = node[1], node[2], node[3]
        frame = _render_display(nodes, dialect)
        for position, branch in enumerate(branches, start=1):
            _walk_branch(node, position, branch, component_id, components, frame, dialect)


def _walk_branch(selector_node, position, branch, parent_id, components, frame, dialect=NEWSPAPER):
    number, code, branches = selector_node[1], selector_node[2], selector_node[3]
    condition = (f"random 1..{int(code[1], 16)}" if code[0] == "0"
                 else f"context {int(code[0], 16)}")
    components.append({
        "component_id": f"S{number:02d}.{position}",
        "parent_id": parent_id,
        "selector": f"S{number:02d}",
        "selector_code": code,
        "branch_index": position,
        "condition": condition,
        "context": frame,
        "source_text": _render_display(branch, dialect),
        "nodes": branch,
    })
    for node in branch:
        if node[0] != "selector":
            continue
        inner_frame = _render_display(branch, dialect)
        for inner_position, inner_branch in enumerate(node[3], start=1):
            _walk_branch(node, inner_position, inner_branch,
                         f"S{number:02d}.{position}", components, inner_frame, dialect)


def components(raw, string_id="?", dialect=NEWSPAPER):
    nodes = parse(raw, string_id, dialect)
    rows = []
    _walk(nodes, "ROOT", "", rows, "", dialect)
    for row in rows:
        row.pop("nodes", None)
    return rows


def selector_codes(raw, string_id="?", dialect=NEWSPAPER):
    codes = []

    def visit(nodes):
        for node in nodes:
            if node[0] == "selector":
                codes.append(node[2])
                for branch in node[3]:
                    visit(branch)

    visit(parse(raw, string_id, dialect))
    return codes


def _encode_display(display, string_id, component_id, selector_lookup, dialect=NEWSPAPER):
    out, index = [], 0
    for match in MARKER_PATTERN.finditer(display):
        literal = display[index:match.start()]
        if "#" in literal or "%" in literal:
            raise NewspaperGrammarError(
                f"{string_id}/{component_id}: '#' and '%' are not allowed in text")
        out.append(literal)
        name = match.group(1)
        if name.startswith("SEL:"):
            key = name[4:]
            if key not in selector_lookup:
                raise NewspaperGrammarError(
                    f"{string_id}/{component_id}: unknown selector reference {name}")
            out.append(selector_lookup[key])
        elif name in dialect.marker_by_name:
            out.append("%" + dialect.marker_by_name[name])
        else:
            raise NewspaperGrammarError(
                f"{string_id}/{component_id}: unknown marker [[{name}]]")
        index = match.end()
    tail = display[index:]
    if "#" in tail or "%" in tail:
        raise NewspaperGrammarError(
            f"{string_id}/{component_id}: '#' and '%' are not allowed in text")
    out.append(tail)
    return "".join(out)


def rebuild(rows, string_id="?", dialect=NEWSPAPER):
    by_id = {}
    for row in rows:
        key = row["component_id"]
        if key in by_id:
            raise NewspaperGrammarError(f"{string_id}: duplicate component {key}")
        by_id[key] = row
    if "ROOT" not in by_id:
        raise NewspaperGrammarError(f"{string_id}: ROOT component is missing")

    structure = {}
    for row in rows:
        if not row["selector"]:
            continue
        structure.setdefault(row["selector"], []).append(int(row["branch_index"]))
    for key, positions in structure.items():
        if sorted(positions) != list(range(1, len(positions) + 1)):
            raise NewspaperGrammarError(
                f"{string_id}: branches of {key} are not 1..{len(positions)}")

    codes = {}
    for row in rows:
        if row["selector"]:
            codes[row["selector"]] = row.get("selector_code", "")

    resolved = {}
    for key in sorted(structure, reverse=True):
        parts = []
        for position in range(1, len(structure[key]) + 1):
            row = by_id.get(f"{key}.{position}")
            if row is None:
                raise NewspaperGrammarError(f"{string_id}: {key}.{position} is missing")
            encoded = _encode_display(
                _text_of(row), string_id, row["component_id"], resolved, dialect)
            # Guard: a branch (after the first) that starts like the terminator ("#%" for the
            # newspaper, "#x" for BMH commentary) would be read as the end of the selector.
            if position > 1 and dialect.needs_guard(encoded):
                encoded = " " + encoded
            parts.append(encoded)
        resolved[key] = "%x" + codes[key] + "#".join(parts) + dialect.terminator

    root = by_id["ROOT"]
    return _encode_display(_text_of(root), string_id, "ROOT", resolved, dialect)


def _text_of(row):
    value = row.get("translated_text")
    if value is None or value == "":
        return row["source_text"]
    return value


__all__ = ["MARKER_META", "SELECTOR_META", "BMH_MARKER_META", "Dialect", "NEWSPAPER", "BMH_COMMENTARY",
           "MARKERS", "MARKER_BY_NAME", "KNOWN_SELECTORS", "NewspaperGrammarError",
           "parse", "components", "rebuild", "selector_codes"]

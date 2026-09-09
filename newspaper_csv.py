import csv
import io
import newspaper_grammar as NG

FORMAT_NAME = "bmh-newspaper-csv"
FORMAT_VERSION = 1
COLUMNS = [
    "string_id", "block", "component_id", "parent_id", "selector",
    "branch_index", "condition", "context", "source_text", "translated_text",
    "note",
]

NEWSPAPER_SOURCES = {
    "THE MANAGER (ITALIAN)": ((0x58E6A, 0x58F7E), (0x5D1AC, 0x5D364)),
    "BUNDESLIGA MANAGER PROFESSIONAL": ((0x58770, 0x58884), (0x5C8B2, 0x5CA6A)),
    "THE MANAGER (ENGLISH)": ((0x56CB8, 0x56DCC), (0x5ADE8, 0x5AFA0)),
}

MAX_WORD_LENGTH = 49

NOTE_UNKNOWN_SELECTOR = ("ORIGINAL DEFECT: selector code {code} is not a valid context; "
                         "the engine eats it and prints the rest as literal text")


class NewspaperCsvError(ValueError):
    pass


def is_supported(profile_id):
    return profile_id in NEWSPAPER_SOURCES


def _source_of(entry):
    sources = sorted(set(entry.get("ptr_addrs", [])))
    return sources[0] if len(sources) == 1 else None


def collect(profile_id, entries):
    if not is_supported(profile_id):
        raise NewspaperCsvError(f"Profile {profile_id} has no newspaper tables")
    headlines, articles = NEWSPAPER_SOURCES[profile_id]
    buckets = {}
    for entry in entries:
        if entry.get("fixed") or entry.get("code_ptr_addrs"):
            continue
        source = _source_of(entry)
        if source is None:
            continue
        if headlines[0] <= source < headlines[1]:
            buckets[(0, source)] = entry
        elif articles[0] <= source < articles[1]:
            buckets[(1, source)] = entry
    expected = ((headlines[1] - headlines[0]) + (articles[1] - articles[0])) // 4
    if len(buckets) != expected:
        raise NewspaperCsvError(
            f"Expected {expected} newspaper strings, found {len(buckets)}")
    return [buckets[key] for key in sorted(buckets)]

def build_rows(profile_id, entries, decode):
    rows = []
    for entry in collect(profile_id, entries):
        string_id = entry["string_id"]
        block = "B1" if _source_of(entry) < NEWSPAPER_SOURCES[profile_id][1][0] else "B3"
        display = decode(entry)
        for component in NG.components(display, string_id):
            code = component.get("selector_code", "")
            note = ""
            if code and code not in NG.KNOWN_SELECTORS:
                note = NOTE_UNKNOWN_SELECTOR.format(code=code)
            rows.append({
                "selector_code": code,
                "string_id": string_id,
                "block": block,
                "component_id": component["component_id"],
                "parent_id": component["parent_id"],
                "selector": component["selector"],
                "branch_index": component["branch_index"],
                "condition": component["condition"],
                "context": component["context"],
                "source_text": component["source_text"],
                "translated_text": "",
                "note": note,
            })
    return rows


def export_csv_bytes(profile_id, entries, decode):
    rows = build_rows(profile_id, entries, decode)
    buffer = io.StringIO(newline="")
    buffer.write(f"# {FORMAT_NAME} v{FORMAT_VERSION} | profile={profile_id} | "
                 f"strings={len(collect(profile_id, entries))} | rows={len(rows)}\r\n")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\r\n",
                            quoting=csv.QUOTE_ALL, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8-sig")

def parse_csv_bytes(raw):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise NewspaperCsvError("CSV is not valid UTF-8") from exc
    lines = text.splitlines()
    if not lines or not lines[0].startswith(f"# {FORMAT_NAME}"):
        raise NewspaperCsvError(f"Missing '# {FORMAT_NAME}' header line")
    header = lines[0]
    reader = csv.DictReader(io.StringIO("\n".join(lines[1:]), newline=""))
    if reader.fieldnames != COLUMNS:
        raise NewspaperCsvError(f"Unexpected columns: {reader.fieldnames}")
    rows = []
    for number, row in enumerate(reader, start=3):
        if any(value is None for value in row.values()) or None in row:
            raise NewspaperCsvError(f"Line {number}: wrong number of fields")
        rows.append(row)
    return header, rows


def _tokens(text):
    counts = {}
    for match in NG.MARKER_PATTERN.finditer(text):
        counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return counts


def _literal_words(text):
    stripped = NG.MARKER_PATTERN.sub(" ", text)
    return [word for word in stripped.split(" ") if word]


def preflight_import(profile_id, entries, decode, raw_csv):
    header, rows = parse_csv_bytes(raw_csv)
    if f"profile={profile_id}" not in header:
        raise NewspaperCsvError(f"CSV was exported for a different profile: {header}")

    expected_rows = build_rows(profile_id, entries, decode)
    expected_by_key = {(row["string_id"], row["component_id"]): row for row in expected_rows}
    seen = set()
    errors = []

    for row in rows:
        key = (row["string_id"], row["component_id"])
        if key in seen:
            errors.append(f"{key[0]}/{key[1]}: duplicate row")
            continue
        seen.add(key)
        reference = expected_by_key.get(key)
        if reference is None:
            errors.append(f"{key[0]}/{key[1]}: unknown component")
            continue
        if row["source_text"] != reference["source_text"]:
            errors.append(f"{key[0]}/{key[1]}: source_text does not match the loaded EXE")
            continue
        translated = row["translated_text"]
        if translated == "":
            continue
        if "#" in translated or "%" in translated:
            errors.append(f"{key[0]}/{key[1]}: '#' and '%' are not allowed")
            continue
        if _tokens(translated) != _tokens(reference["source_text"]):
            errors.append(f"{key[0]}/{key[1]}: markers were added, lost or duplicated")
            continue
        if str(row["branch_index"]) not in ("", "1") and translated.startswith("[["):
            errors.append(f"{key[0]}/{key[1]}: a branch after the first must not start "
                          f"with a marker")
            continue
        long_words = [word for word in _literal_words(translated)
                      if len(word) > MAX_WORD_LENGTH]
        if long_words:
            errors.append(f"{key[0]}/{key[1]}: word longer than {MAX_WORD_LENGTH} "
                          f"characters: {long_words[0]!r}")

    missing = sorted(set(expected_by_key) - seen)
    if missing:
        errors.append(f"{len(missing)} rows are missing, first {missing[0][0]}/{missing[0][1]}")
    if errors:
        raise NewspaperCsvError("; ".join(errors[:8])
                                + (f" (+{len(errors) - 8} more)" if len(errors) > 8 else ""))

    by_string = {}
    for row in rows:
        by_string.setdefault(row["string_id"], []).append({
            "component_id": row["component_id"],
            "selector": row["selector"],
            "selector_code": expected_by_key[(row["string_id"],
                                              row["component_id"])]["selector_code"],
            "branch_index": row["branch_index"],
            "source_text": row["source_text"],
            "translated_text": row["translated_text"],
        })

    replacements = {}
    current = {entry["string_id"]: decode(entry) for entry in collect(profile_id, entries)}
    for string_id, component_rows in by_string.items():
        rebuilt = NG.rebuild(component_rows, string_id)
        try:
            NG.parse(rebuilt, string_id)
        except NG.NewspaperGrammarError as exc:
            raise NewspaperCsvError(f"{string_id}: rebuilt template is invalid: {exc}") from exc
        if rebuilt != current[string_id]:
            replacements[string_id] = rebuilt
    return replacements


__all__ = ["FORMAT_NAME", "FORMAT_VERSION", "COLUMNS", "NEWSPAPER_SOURCES",
           "MAX_WORD_LENGTH", "NewspaperCsvError", "is_supported", "collect",
           "build_rows", "export_csv_bytes", "parse_csv_bytes", "preflight_import"]

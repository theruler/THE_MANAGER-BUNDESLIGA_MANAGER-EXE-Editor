"""Pure, immutable search/filter records for the string-list GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


class SearchFilterError(ValueError):
    """Raised when filter metadata or a filter value is inconsistent."""


KIND_FILTERS = ("All", "Normal", "Fixed", "Code-only", "Suffix-Shared")
CHANGE_FILTERS = ("All", "Changed", "Unchanged")
STATUS_FILTERS = (
    "All",
    "PASS",
    "FAIL",
    "PENDING",
    "READ-ONLY",
    "UNCHANGED",
    "Problems",
)
ROW_STATUSES = frozenset(("PASS", "FAIL", "PENDING", "READ-ONLY", "UNCHANGED"))


@dataclass(frozen=True, slots=True)
class FilterRecord:
    """One immutable logical string row; never owns editor/live objects."""

    source_index: int
    string_id: str
    kind: str
    font: str
    current_text: str
    baseline_text: str
    current_raw: bytes = field(repr=False)
    baseline_raw: bytes = field(repr=False)
    suffix_shared: bool
    status: str
    problem: bool
    search_blob: str = field(repr=False)

    @property
    def changed(self) -> bool:
        return self.current_raw != self.baseline_raw


def _row_status(
    *,
    changed: bool,
    suffix_shared: bool,
    preview_status: str | None,
    status_override: str | None,
) -> str:
    evidence = (status_override, preview_status)
    if "FAIL" in evidence:
        return "FAIL"
    if "PENDING" in evidence:
        return "PENDING"
    if suffix_shared:
        return "READ-ONLY"
    return "PASS" if changed else "UNCHANGED"


def build_filter_records(rows: Iterable[Mapping]) -> tuple[FilterRecord, ...]:
    """Validate detached row metadata and return records in source order."""
    records = []
    seen_ids = set()
    for source_index, row in enumerate(rows):
        try:
            string_id = row["string_id"]
            kind = row["kind"]
            font = row["font"]
            current_text = row["current_text"]
            baseline_text = row["baseline_text"]
            current_raw = bytes(row["current_raw"])
            baseline_raw = bytes(row["baseline_raw"])
            suffix_shared = bool(row["suffix_shared"])
            preview_status = row.get("preview_status")
            status_override = row.get("status_override")
        except (KeyError, TypeError, ValueError) as exc:
            raise SearchFilterError(f"Invalid filter metadata at row {source_index}") from exc

        if not isinstance(string_id, str) or not string_id or string_id in seen_ids:
            raise SearchFilterError(f"Missing or duplicate string_id at row {source_index}")
        if kind not in {"normal", "fixed", "code-only"}:
            raise SearchFilterError(f"Invalid string kind for {string_id}: {kind!r}")
        if not isinstance(font, str) or not font:
            raise SearchFilterError(f"Invalid effective font for {string_id}")
        if not isinstance(current_text, str) or not isinstance(baseline_text, str):
            raise SearchFilterError(f"Invalid searchable text for {string_id}")
        if preview_status is not None and preview_status not in ROW_STATUSES:
            raise SearchFilterError(f"Invalid preview status for {string_id}")
        if status_override is not None and status_override not in {"FAIL", "PENDING"}:
            raise SearchFilterError(f"Invalid status override for {string_id}")

        changed = current_raw != baseline_raw
        status = _row_status(
            changed=changed,
            suffix_shared=suffix_shared,
            preview_status=preview_status,
            status_override=status_override,
        )
        search_blob = "\x00".join((current_text, baseline_text, string_id)).casefold()
        records.append(FilterRecord(
            source_index=source_index,
            string_id=string_id,
            kind=kind,
            font=font,
            current_text=current_text,
            baseline_text=baseline_text,
            current_raw=current_raw,
            baseline_raw=baseline_raw,
            suffix_shared=suffix_shared,
            status=status,
            problem=status in {"FAIL", "PENDING"},
            search_blob=search_blob,
        ))
        seen_ids.add(string_id)
    return tuple(records)


def filter_string_ids(
    records: Iterable[FilterRecord],
    *,
    query: str = "",
    kind_filter: str = "All",
    font_filter: str = "All",
    change_filter: str = "All",
    status_filter: str = "All",
) -> tuple[str, ...]:
    """Return matching IDs in original order without changing any input."""
    if not isinstance(query, str):
        raise SearchFilterError("Search query must be text")
    if kind_filter not in KIND_FILTERS:
        raise SearchFilterError(f"Unknown Kind filter: {kind_filter!r}")
    if not isinstance(font_filter, str) or not font_filter:
        raise SearchFilterError("Font filter must be a non-empty name")
    if change_filter not in CHANGE_FILTERS:
        raise SearchFilterError(f"Unknown Change filter: {change_filter!r}")
    if status_filter not in STATUS_FILTERS:
        raise SearchFilterError(f"Unknown Status filter: {status_filter!r}")

    folded_query = query.casefold()
    result = []
    for record in records:
        if folded_query and folded_query not in record.search_blob:
            continue
        if kind_filter == "Normal" and (record.kind != "normal" or record.suffix_shared):
            continue
        if kind_filter == "Fixed" and record.kind != "fixed":
            continue
        if kind_filter == "Code-only" and record.kind != "code-only":
            continue
        if kind_filter == "Suffix-Shared" and not record.suffix_shared:
            continue
        if font_filter != "All" and record.font != font_filter:
            continue
        if change_filter == "Changed" and not record.changed:
            continue
        if change_filter == "Unchanged" and record.changed:
            continue
        if status_filter == "Problems" and not record.problem:
            continue
        if status_filter not in {"All", "Problems"} and record.status != status_filter:
            continue
        result.append(record.string_id)
    return tuple(result)


__all__ = [
    "CHANGE_FILTERS",
    "FilterRecord",
    "KIND_FILTERS",
    "ROW_STATUSES",
    "STATUS_FILTERS",
    "SearchFilterError",
    "build_filter_records",
    "filter_string_ids",
]

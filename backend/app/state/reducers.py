from typing import Any

RESET_SENTINEL = "__reset__"


def append_list(existing: list[Any] | None, update: list[Any] | None) -> list[Any]:
    """Append-only reducer preserving full history without mutating existing lists."""
    base = list(existing or [])
    if not update:
        return base
    return base + list(update)


def merge_specialist_reports(
    existing: list[dict[str, Any]] | None,
    update: list[dict[str, Any]] | dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Iteration-scoped reducer for parallel specialist reports.

    Supports:
    - Resetting reports at the start of a new Commander cycle via `{"__reset__": True}`
      so stale specialist reports from previous iterations do not leak into the new plan.
    - Fan-in merging of parallel specialist outputs during the same superstep without
      mutating input lists, deduplicating by `(agent, iteration)`.
    """
    if update is None:
        return list(existing or [])

    if isinstance(update, dict) and update.get(RESET_SENTINEL):
        return []

    items = [update] if isinstance(update, dict) else list(update)
    if any(isinstance(item, dict) and item.get(RESET_SENTINEL) for item in items):
        filtered = [item for item in items if not (isinstance(item, dict) and item.get(RESET_SENTINEL))]
        return filtered

    merged: list[dict[str, Any]] = list(existing or [])
    seen: dict[tuple[Any, Any], int] = {
        (item.get("agent"), item.get("iteration")): idx
        for idx, item in enumerate(merged)
        if isinstance(item, dict)
    }

    for item in items:
        if not isinstance(item, dict):
            continue
        key = (item.get("agent"), item.get("iteration"))
        if key in seen:
            merged[seen[key]] = item
        else:
            seen[key] = len(merged)
            merged.append(item)

    return merged

"""Dashboard widget helpers for Analytics Copilot."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from uuid import uuid4

import pandas as pd


SUPPORTED_WIDGET_TYPES = {"kpi", "chart", "insight", "text"}


def create_widget(widget_type: str, **config: Any) -> dict[str, Any]:
    """Create one validated dashboard widget."""
    normalized_type = str(widget_type).lower().strip()

    if normalized_type not in SUPPORTED_WIDGET_TYPES:
        raise ValueError(f"Unsupported widget type: {widget_type}")

    title = str(config.pop("title", normalized_type.title())).strip()

    return {
        "id": str(uuid4()),
        "type": normalized_type,
        "title": title or normalized_type.title(),
        "config": deepcopy(config),
    }


def normalize_widget(widget: dict[str, Any]) -> dict[str, Any] | None:
    """Return a safe widget dictionary or None when invalid."""
    if not isinstance(widget, dict):
        return None

    widget_type = str(widget.get("type", "")).lower().strip()

    if widget_type not in SUPPORTED_WIDGET_TYPES:
        return None

    widget_id = str(widget.get("id") or uuid4())
    title = str(widget.get("title") or widget_type.title()).strip()
    config = widget.get("config", {})

    if not isinstance(config, dict):
        config = {}

    return {
        "id": widget_id,
        "type": widget_type,
        "title": title or widget_type.title(),
        "config": deepcopy(config),
    }


def replace_dashboard_widgets(
    widgets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert a recommendation into a valid editable widget list."""
    normalized: list[dict[str, Any]] = []

    for widget in widgets:
        safe_widget = normalize_widget(widget)

        if safe_widget is not None:
            normalized.append(safe_widget)

    return normalized


def add_widget(
    widgets: list[dict[str, Any]],
    widget: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return a new list with one widget added."""
    safe_widget = normalize_widget(widget)

    if safe_widget is None:
        raise ValueError("Invalid dashboard widget.")

    updated = deepcopy(widgets)
    updated.append(safe_widget)
    return updated


def duplicate_widget(
    widgets: list[dict[str, Any]],
    widget_id: str,
) -> list[dict[str, Any]]:
    """Duplicate a widget with a new ID."""
    updated = deepcopy(widgets)

    for index, widget in enumerate(updated):
        if widget.get("id") == widget_id:
            duplicate = deepcopy(widget)
            duplicate["id"] = str(uuid4())
            duplicate["title"] = f"{duplicate.get('title', 'Widget')} Copy"
            updated.insert(index + 1, duplicate)
            break

    return updated


def update_widget(
    widgets: list[dict[str, Any]],
    widget_id: str,
    *,
    title: str | None = None,
    config_updates: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Update one widget without changing the original list."""
    updated = deepcopy(widgets)

    for widget in updated:
        if widget.get("id") != widget_id:
            continue

        if title is not None:
            cleaned_title = str(title).strip()
            widget["title"] = cleaned_title or widget.get("title", "Widget")

        if config_updates:
            widget.setdefault("config", {}).update(deepcopy(config_updates))

        break

    return updated


def remove_widget(
    widgets: list[dict[str, Any]],
    widget_id: str,
) -> list[dict[str, Any]]:
    """Remove one widget."""
    return [
        deepcopy(widget)
        for widget in widgets
        if widget.get("id") != widget_id
    ]


def move_widget(
    widgets: list[dict[str, Any]],
    widget_id: str,
    direction: str,
) -> list[dict[str, Any]]:
    """Move a widget up or down by one position."""
    updated = deepcopy(widgets)

    index = next(
        (
            position
            for position, widget in enumerate(updated)
            if widget.get("id") == widget_id
        ),
        None,
    )

    if index is None:
        return updated

    if direction == "up" and index > 0:
        updated[index - 1], updated[index] = updated[index], updated[index - 1]

    elif direction == "down" and index < len(updated) - 1:
        updated[index + 1], updated[index] = updated[index], updated[index + 1]

    return updated


def calculate_kpi(
    df: pd.DataFrame,
    column: str,
    aggregation: str,
) -> float | int | None:
    """Calculate one KPI value."""
    if column not in df.columns:
        return None

    selected = str(aggregation).lower().strip()

    if selected == "count":
        return int(df[column].count())

    if selected == "unique":
        return int(df[column].nunique(dropna=True))

    values = pd.to_numeric(df[column], errors="coerce").dropna()

    if values.empty:
        return None

    if selected == "sum":
        return float(values.sum())
    if selected == "mean":
        return float(values.mean())
    if selected == "median":
        return float(values.median())
    if selected == "min":
        return float(values.min())
    if selected == "max":
        return float(values.max())

    raise ValueError(f"Unsupported KPI aggregation: {aggregation}")


def refresh_kpi_widgets(
    df: pd.DataFrame,
    widgets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recalculate all KPI values using the current dataset."""
    updated = replace_dashboard_widgets(widgets)

    for widget in updated:
        if widget.get("type") != "kpi":
            continue

        config = widget.setdefault("config", {})
        config["value"] = calculate_kpi(
            df,
            str(config.get("column", "")),
            str(config.get("aggregation", "count")),
        )

    return updated


def build_dashboard_from_recommendation(
    df: pd.DataFrame,
    recommendation: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], str]:
    """Turn an AI recommendation into an actual editable dashboard."""
    if not isinstance(recommendation, dict):
        raise ValueError("Dashboard recommendation must be a dictionary.")

    title = str(
        recommendation.get("title", "Recommended Dashboard")
    ).strip() or "Recommended Dashboard"

    reason = str(recommendation.get("reason", "")).strip()
    raw_widgets = recommendation.get("widgets", [])

    if not isinstance(raw_widgets, list):
        raise ValueError("Dashboard recommendation widgets must be a list.")

    widgets = refresh_kpi_widgets(
        df,
        replace_dashboard_widgets(raw_widgets),
    )

    if not widgets:
        raise ValueError("The recommendation did not contain usable dashboard widgets.")

    return title, widgets, reason


def dashboard_to_json(
    title: str,
    widgets: list[dict[str, Any]],
) -> str:
    """Save a dashboard layout as JSON."""
    payload = {
        "title": str(title).strip() or "Dashboard",
        "widgets": replace_dashboard_widgets(widgets),
    }

    return json.dumps(payload, indent=2, default=str)


def dashboard_from_json(
    content: str | bytes,
) -> tuple[str, list[dict[str, Any]]]:
    """Load and validate a saved dashboard JSON file."""
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    payload = json.loads(text)

    if not isinstance(payload, dict):
        raise ValueError("Dashboard JSON must contain an object.")

    title = str(payload.get("title", "Imported Dashboard")).strip()
    widgets = payload.get("widgets", [])

    if not isinstance(widgets, list):
        raise ValueError("Dashboard widgets must be a list.")

    valid_widgets = replace_dashboard_widgets(widgets)

    if not valid_widgets:
        raise ValueError("The dashboard file does not contain usable widgets.")

    return title or "Imported Dashboard", valid_widgets
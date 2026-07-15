"""Reliable dashboard recommendations built by Python."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.dashboard import create_widget


def _friendly_name(column: str) -> str:
    return str(column).replace("_", " ").strip().title()


def build_recommended_dashboard(
    df: pd.DataFrame,
    column_types: dict[str, list[str]],
    *,
    ai_reason: str = "",
    ai_insight: str = "",
    target_column: str | None = None,
) -> dict[str, Any]:
    """
    Build a real editable dashboard deterministically.

    Gemini may provide the short reason and insight, but Python selects and
    constructs every KPI and chart.
    """
    numeric = [
        column for column in column_types.get("numeric", [])
        if column in df.columns
    ]
    categories = [
        column
        for column in (
            column_types.get("categorical", [])
            + column_types.get("boolean", [])
        )
        if column in df.columns
    ]
    dates = [
        column for column in column_types.get("datetime", [])
        if column in df.columns
    ]

    widgets: list[dict[str, Any]] = []

    # Always include dataset size.
    first_column = str(df.columns[0])
    widgets.append(
        create_widget(
            "kpi",
            title="Total Records",
            column=first_column,
            aggregation="count",
            prefix="",
            suffix="",
        )
    )

    # Prefer the selected target, then other numeric columns.
    prioritized_numeric: list[str] = []
    if target_column and target_column in numeric:
        prioritized_numeric.append(target_column)

    prioritized_numeric.extend(
        column for column in numeric
        if column not in prioritized_numeric
    )

    for column in prioritized_numeric[:2]:
        widgets.append(
            create_widget(
                "kpi",
                title=f"Total {_friendly_name(column)}",
                column=column,
                aggregation="sum",
                prefix="",
                suffix="",
            )
        )

    # Best category breakdown.
    if categories:
        category = categories[0]

        if prioritized_numeric:
            metric = prioritized_numeric[0]
            widgets.append(
                create_widget(
                    "chart",
                    title=f"{_friendly_name(metric)} by {_friendly_name(category)}",
                    chart_type="Bar",
                    x_column=category,
                    y_column=metric,
                    color_column=None,
                    aggregation="Sum",
                    top_n=15,
                )
            )
        else:
            widgets.append(
                create_widget(
                    "chart",
                    title=f"{_friendly_name(category)} Distribution",
                    chart_type="Pie",
                    x_column=category,
                    y_column=None,
                    color_column=None,
                    aggregation="None",
                    top_n=12,
                )
            )

    # Time trend.
    if dates and prioritized_numeric:
        widgets.append(
            create_widget(
                "chart",
                title=f"{_friendly_name(prioritized_numeric[0])} Over Time",
                chart_type="Line",
                x_column=dates[0],
                y_column=prioritized_numeric[0],
                color_column=None,
                aggregation="Sum",
                top_n=30,
            )
        )

    # Numeric distribution or relationship.
    if len(prioritized_numeric) >= 2:
        widgets.append(
            create_widget(
                "chart",
                title=(
                    f"{_friendly_name(prioritized_numeric[1])} vs "
                    f"{_friendly_name(prioritized_numeric[0])}"
                ),
                chart_type="Scatter",
                x_column=prioritized_numeric[0],
                y_column=prioritized_numeric[1],
                color_column=categories[0] if categories else None,
                aggregation="None",
                top_n=50,
            )
        )
    elif prioritized_numeric:
        widgets.append(
            create_widget(
                "chart",
                title=f"{_friendly_name(prioritized_numeric[0])} Distribution",
                chart_type="Histogram",
                x_column=prioritized_numeric[0],
                y_column=None,
                color_column=None,
                aggregation="None",
                top_n=30,
            )
        )

    insight_text = ai_insight.strip()
    if not insight_text:
        insight_text = (
            "This dashboard was created automatically from the detected "
            "numeric, categorical, and date columns. Every widget can be edited."
        )

    widgets.append(
        create_widget(
            "insight",
            title="Key Insight",
            text=insight_text,
        )
    )

    title = "Recommended Executive Dashboard"

    if target_column:
        title = f"{_friendly_name(target_column)} Dashboard"

    reason = ai_reason.strip() or (
        "The dashboard emphasizes the most useful KPIs, category breakdowns, "
        "time trends, and numeric relationships available in this dataset."
    )

    return {
        "title": title,
        "reason": reason,
        "widgets": widgets[:8],
    }


def build_ai_dashboard_prompt(
    context_json: str,
    target_column: str | None,
) -> str:
    """
    Ask Gemini only for short text.

    No JSON is requested, so malformed JSON can no longer break dashboard creation.
    """
    target_text = target_column or "No specific target was selected."

    return f"""
You are a senior BI analyst.

Using only the computed evidence below, write exactly two short paragraphs:

Paragraph 1:
Explain what the dashboard should focus on in one sentence.

Paragraph 2:
Give one important evidence-based insight in one or two sentences.

Do not use headings.
Do not use bullet points.
Do not invent facts or causes.
Do not mention unavailable business context.

Selected target:
{target_text}

Computed evidence:
{context_json}
""".strip()


def split_ai_dashboard_text(response_text: str) -> tuple[str, str]:
    """Split Gemini text into a reason and an insight."""
    cleaned = response_text.strip()

    if not cleaned:
        return "", ""

    paragraphs = [
        paragraph.strip()
        for paragraph in cleaned.split("\n\n")
        if paragraph.strip()
    ]

    if len(paragraphs) >= 2:
        return paragraphs[0], paragraphs[1]

    sentences = [
        sentence.strip()
        for sentence in cleaned.replace("\n", " ").split(". ")
        if sentence.strip()
    ]

    if len(sentences) >= 2:
        return f"{sentences[0]}.", ". ".join(sentences[1:]).strip()

    return cleaned, ""

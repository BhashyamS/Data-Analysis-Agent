"""Report generation helpers for Analytics Copilot."""

from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any

import pandas as pd

from src.ai_context import build_ai_context
from src.profiling import detect_column_types, profile_dataset


REPORT_SECTIONS = [
    "Executive Summary",
    "Dataset Overview",
    "Data Preparation",
    "Exploratory Analysis",
    "Statistical Analysis",
    "AI Insights",
    "Dashboard",
    "Recommendations",
    "Limitations",
]


def build_report_data(
    df: pd.DataFrame,
    *,
    filename: str | None,
    title: str,
    audience: str,
    detail_level: str,
    selected_sections: list[str],
    cleaning_history: list[dict[str, Any]] | None = None,
    cleaning_recipe: dict[str, Any] | None = None,
    ai_report: str = "",
    dashboard_title: str = "",
    dashboard_widgets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Collect all report evidence into one serializable structure."""
    profile = profile_dataset(df)
    column_types = detect_column_types(df)
    context = build_ai_context(df, filename=filename)

    widgets = dashboard_widgets or []
    widget_summary = [
        {
            "type": widget.get("type"),
            "title": widget.get("title"),
            "config": widget.get("config", {}),
        }
        for widget in widgets
        if isinstance(widget, dict)
    ]

    return {
        "metadata": {
            "title": title.strip() or "Analytics Report",
            "audience": audience,
            "detail_level": detail_level,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "filename": filename,
            "selected_sections": selected_sections,
        },
        "dataset": {
            **profile.to_dict(),
            "column_types": column_types,
        },
        "preparation": {
            "history": cleaning_history or [],
            "recipe": cleaning_recipe or {},
        },
        "analysis": context,
        "ai_report": ai_report.strip(),
        "dashboard": {
            "title": dashboard_title or "Dashboard",
            "widgets": widget_summary,
        },
    }


def default_executive_summary(report_data: dict[str, Any]) -> str:
    """Create a deterministic summary when AI is unavailable."""
    dataset = report_data["dataset"]
    filename = report_data["metadata"].get("filename") or "the uploaded dataset"
    dashboard = report_data["dashboard"]

    return (
        f"{filename} contains {dataset['rows']:,} rows across "
        f"{dataset['columns']:,} columns. The dataset currently has "
        f"{dataset['missing_cells']:,} missing cells "
        f"({dataset['missing_percentage']:.2f}%) and "
        f"{dataset['duplicate_rows']:,} duplicate rows. "
        f"The final dashboard contains {len(dashboard['widgets'])} widgets."
    )


def build_report_prompt(report_data: dict[str, Any]) -> str:
    """Build a grounded prompt for the report narrative."""
    compact = {
        "metadata": report_data["metadata"],
        "dataset": report_data["dataset"],
        "preparation": report_data["preparation"],
        "analysis": report_data["analysis"],
        "dashboard": report_data["dashboard"],
    }

    return f"""
You are a senior data analyst preparing a stakeholder report.

Use only the evidence below.
Do not invent facts, causes, business context, or column meanings.
Do not claim causation from correlations.
Use exact computed values where useful.
Keep the writing appropriate for the selected audience and detail level.

Return Markdown with these sections:
## Executive Summary
## Key Findings
## Recommendations
## Limitations

Evidence:
{json.dumps(compact, indent=2, default=str)}
""".strip()


def _format_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.3f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No data available._"

    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = [
        "| " + " | ".join(_format_value(row.get(column)) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def build_markdown_report(
    report_data: dict[str, Any],
    narrative: str = "",
) -> str:
    """Create the final Markdown report."""
    meta = report_data["metadata"]
    dataset = report_data["dataset"]
    preparation = report_data["preparation"]
    analysis = report_data["analysis"]
    dashboard = report_data["dashboard"]
    selected = set(meta["selected_sections"])

    parts = [
        f"# {meta['title']}",
        "",
        f"**Audience:** {meta['audience']}  ",
        f"**Detail level:** {meta['detail_level']}  ",
        f"**Generated:** {meta['generated_at']}  ",
        f"**Source file:** {meta.get('filename') or 'Not provided'}",
        "",
    ]

    if "Executive Summary" in selected:
        parts.extend([
            "## Executive Summary",
            "",
            narrative.strip() or default_executive_summary(report_data),
            "",
        ])

    if "Dataset Overview" in selected:
        parts.extend([
            "## Dataset Overview",
            "",
            f"- Rows: **{dataset['rows']:,}**",
            f"- Columns: **{dataset['columns']:,}**",
            f"- Missing cells: **{dataset['missing_cells']:,}** "
            f"({dataset['missing_percentage']:.2f}%)",
            f"- Duplicate rows: **{dataset['duplicate_rows']:,}**",
            f"- Memory usage: **{dataset['memory_mb']:.3f} MB**",
            "",
        ])

    if "Data Preparation" in selected:
        parts.extend(["## Data Preparation", ""])
        history = preparation.get("history", [])
        if history:
            for item in history:
                description = (
                    item.get("description")
                    or item.get("action")
                    or str(item)
                )
                parts.append(f"- {description}")
        else:
            parts.append("_No preparation history was recorded._")
        parts.append("")

    if "Exploratory Analysis" in selected:
        parts.extend(["## Exploratory Analysis", ""])
        numeric = analysis.get("numeric_summary", [])
        if numeric:
            columns = ["column", "count", "missing", "mean", "median", "minimum", "maximum"]
            parts.append(_markdown_table(numeric[:12], columns))
        else:
            parts.append("_No numeric summary was available._")
        parts.append("")

    if "Statistical Analysis" in selected:
        parts.extend(["## Statistical Analysis", ""])
        relationships = analysis.get("strongest_correlations", [])
        if relationships:
            columns = ["variable_1", "variable_2", "correlation", "strength"]
            parts.append(_markdown_table(relationships[:12], columns))
        else:
            parts.append("_No qualifying correlations were detected._")
        parts.append("")

    if "AI Insights" in selected:
        parts.extend(["## AI Insights", ""])
        ai_report = report_data.get("ai_report", "")
        parts.append(ai_report or "_No saved AI report was available._")
        parts.append("")

    if "Dashboard" in selected:
        parts.extend([
            "## Dashboard",
            "",
            f"**Dashboard title:** {dashboard['title']}",
            "",
        ])
        if dashboard["widgets"]:
            for widget in dashboard["widgets"]:
                parts.append(
                    f"- **{widget.get('title', 'Widget')}** "
                    f"({widget.get('type', 'unknown')})"
                )
        else:
            parts.append("_No dashboard widgets were available._")
        parts.append("")

    if "Recommendations" in selected and narrative:
        parts.extend([
            "## Recommendations",
            "",
            "See the recommendations included in the generated narrative above.",
            "",
        ])

    if "Limitations" in selected:
        parts.extend([
            "## Limitations",
            "",
            "- Results describe the uploaded data and may not generalize beyond it.",
            "- Correlation and group differences do not establish causation.",
            "- Missing values, small groups, and outliers may affect findings.",
            "- AI-generated text should be reviewed before use in decisions.",
            "",
        ])

    return "\n".join(parts).strip() + "\n"


def markdown_to_html(markdown_text: str, title: str) -> str:
    """Create a self-contained readable HTML report."""
    escaped = html.escape(markdown_text)
    lines = escaped.splitlines()
    rendered: list[str] = []

    in_list = False
    for line in lines:
        if line.startswith("# "):
            rendered.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_list:
                rendered.append("</ul>")
                in_list = False
            rendered.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            if not in_list:
                rendered.append("<ul>")
                in_list = True
            rendered.append(f"<li>{line[2:]}</li>")
        elif line.startswith("|"):
            if in_list:
                rendered.append("</ul>")
                in_list = False
            rendered.append(f"<pre>{line}</pre>")
        elif not line.strip():
            if in_list:
                rendered.append("</ul>")
                in_list = False
            rendered.append("<br>")
        else:
            rendered.append(f"<p>{line}</p>")

    if in_list:
        rendered.append("</ul>")

    body = "\n".join(rendered)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    max-width: 980px;
    margin: 40px auto;
    padding: 0 24px;
    color: #172033;
    line-height: 1.6;
}}
h1 {{ font-size: 2.4rem; margin-bottom: 0.4rem; }}
h2 {{ margin-top: 2rem; border-bottom: 1px solid #d9deea; padding-bottom: 0.4rem; }}
p {{ margin: 0.45rem 0; }}
li {{ margin: 0.35rem 0; }}
pre {{
    white-space: pre-wrap;
    background: #f4f6fa;
    padding: 0.65rem;
    border-radius: 8px;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""


def report_to_json(report_data: dict[str, Any], narrative: str = "") -> str:
    """Serialize the complete report package."""
    payload = {
        **report_data,
        "generated_narrative": narrative,
    }
    return json.dumps(payload, indent=2, default=str)

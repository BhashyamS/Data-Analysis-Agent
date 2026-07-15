"""Reusable card components for Analytics Copilot."""

from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st


def metric_card(
    label: str,
    value: str | int | float,
    *,
    description: str | None = None,
    icon: str = "◆",
    status: str | None = None,
    status_type: str = "neutral",
) -> None:
    """
    Render a polished metric card.

    Parameters
    ----------
    label:
        Short metric title.
    value:
        Main value displayed on the card.
    description:
        Optional supporting text.
    icon:
        Small icon or emoji shown above the value.
    status:
        Optional badge text, such as "Healthy" or "Needs review".
    status_type:
        Badge style: neutral, success, warning, or danger.
    """
    allowed_status_types = {"neutral", "success", "warning", "danger"}

    if status_type not in allowed_status_types:
        status_type = "neutral"

    safe_label = escape(str(label))
    safe_value = escape(str(value))
    safe_description = escape(str(description)) if description else ""
    safe_icon = escape(str(icon))
    safe_status = escape(str(status)) if status else ""

    status_html = ""

    if status:
        status_html = f"""
        <span class="ac-metric-badge ac-metric-badge--{status_type}">
            {safe_status}
        </span>
        """

    description_html = ""

    if description:
        description_html = f"""
        <p class="ac-metric-description">
            {safe_description}
        </p>
        """

    st.markdown(
        f"""
        <div class="ac-metric-card">
            <div class="ac-metric-card__top">
                <div class="ac-metric-icon">{safe_icon}</div>
                {status_html}
            </div>

            <p class="ac-metric-label">{safe_label}</p>
            <p class="ac-metric-value">{safe_value}</p>

            {description_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_grid(
    metrics: Iterable[dict[str, object]],
    *,
    columns: int = 4,
) -> None:
    """
    Render multiple metric cards in a responsive Streamlit grid.

    Each metric dictionary may contain:

    {
        "label": "Rows",
        "value": "5,240",
        "description": "Records currently loaded",
        "icon": "▤",
        "status": "Complete",
        "status_type": "success",
    }
    """
    metric_items = list(metrics)

    if not metric_items:
        return

    safe_column_count = max(1, min(columns, len(metric_items)))
    grid_columns = st.columns(safe_column_count)

    for index, metric in enumerate(metric_items):
        column = grid_columns[index % safe_column_count]

        with column:
            metric_card(
                label=str(metric.get("label", "Metric")),
                value=metric.get("value", "—"),
                description=(
                    str(metric["description"])
                    if metric.get("description") is not None
                    else None
                ),
                icon=str(metric.get("icon", "◆")),
                status=(
                    str(metric["status"])
                    if metric.get("status") is not None
                    else None
                ),
                status_type=str(metric.get("status_type", "neutral")),
            )


def inject_card_styles() -> None:
    """Inject the CSS required by the reusable card components."""
    st.markdown(
        """
        <style>
            .ac-metric-card {
                min-height: 178px;
                padding: 1.25rem;
                margin-bottom: 0.75rem;
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 18px;
                background:
                    linear-gradient(
                        145deg,
                        rgba(30, 41, 59, 0.96),
                        rgba(15, 23, 42, 0.96)
                    );
                box-shadow:
                    0 10px 30px rgba(2, 6, 23, 0.22),
                    inset 0 1px 0 rgba(255, 255, 255, 0.03);
                transition:
                    transform 0.2s ease,
                    border-color 0.2s ease,
                    box-shadow 0.2s ease;
            }

            .ac-metric-card:hover {
                transform: translateY(-3px);
                border-color: rgba(96, 165, 250, 0.36);
                box-shadow:
                    0 14px 34px rgba(2, 6, 23, 0.34),
                    0 0 0 1px rgba(96, 165, 250, 0.06);
            }

            .ac-metric-card__top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                min-height: 30px;
                margin-bottom: 1rem;
            }

            .ac-metric-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 34px;
                height: 34px;
                border: 1px solid rgba(96, 165, 250, 0.22);
                border-radius: 11px;
                background: rgba(59, 130, 246, 0.1);
                color: #93c5fd;
                font-size: 0.95rem;
                line-height: 1;
            }

            .ac-metric-label {
                margin: 0 0 0.3rem 0;
                color: #94a3b8;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .ac-metric-value {
                margin: 0;
                color: #f8fafc;
                font-size: clamp(1.65rem, 3vw, 2.15rem);
                font-weight: 760;
                letter-spacing: -0.04em;
                line-height: 1.05;
            }

            .ac-metric-description {
                margin: 0.65rem 0 0 0;
                color: #94a3b8;
                font-size: 0.82rem;
                line-height: 1.45;
            }

            .ac-metric-badge {
                display: inline-flex;
                align-items: center;
                padding: 0.28rem 0.55rem;
                border: 1px solid transparent;
                border-radius: 999px;
                font-size: 0.68rem;
                font-weight: 700;
                letter-spacing: 0.03em;
                white-space: nowrap;
            }

            .ac-metric-badge--neutral {
                border-color: rgba(148, 163, 184, 0.2);
                background: rgba(148, 163, 184, 0.1);
                color: #cbd5e1;
            }

            .ac-metric-badge--success {
                border-color: rgba(52, 211, 153, 0.24);
                background: rgba(16, 185, 129, 0.12);
                color: #6ee7b7;
            }

            .ac-metric-badge--warning {
                border-color: rgba(251, 191, 36, 0.24);
                background: rgba(245, 158, 11, 0.12);
                color: #fcd34d;
            }

            .ac-metric-badge--danger {
                border-color: rgba(248, 113, 113, 0.24);
                background: rgba(239, 68, 68, 0.12);
                color: #fca5a5;
            }

            @media (max-width: 900px) {
                .ac-metric-card {
                    min-height: 155px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
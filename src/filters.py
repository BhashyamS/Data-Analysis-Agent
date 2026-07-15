
"""Dynamic filtering helpers for Streamlit and tests."""

from __future__ import annotations

from typing import Any

import pandas as pd


def apply_filter_specs(
    df: pd.DataFrame,
    specs: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Apply reusable filter specifications to a DataFrame."""
    result = df.copy()

    for column, spec in specs.items():
        if column not in result.columns:
            continue

        filter_type = spec.get("type")

        if filter_type == "category":
            selected = spec.get("values", [])
            include_missing = bool(spec.get("include_missing", False))

            if selected:
                mask = result[column].astype(str).isin([str(value) for value in selected])
                if include_missing:
                    mask = mask | result[column].isna()
                result = result.loc[mask]
            elif include_missing:
                result = result.loc[result[column].isna()]

        elif filter_type == "numeric":
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            numeric = pd.to_numeric(result[column], errors="coerce")

            if minimum is not None:
                result = result.loc[numeric >= float(minimum)]
                numeric = pd.to_numeric(result[column], errors="coerce")
            if maximum is not None:
                result = result.loc[numeric <= float(maximum)]

        elif filter_type == "datetime":
            start = spec.get("start")
            end = spec.get("end")
            dates = pd.to_datetime(result[column], errors="coerce")

            if start is not None:
                result = result.loc[dates >= pd.Timestamp(start)]
                dates = pd.to_datetime(result[column], errors="coerce")
            if end is not None:
                end_timestamp = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
                result = result.loc[dates <= end_timestamp]

        elif filter_type == "text":
            query = str(spec.get("query", "")).strip()
            if query:
                result = result.loc[
                    result[column]
                    .fillna("")
                    .astype(str)
                    .str.contains(query, case=False, regex=False)
                ]

    return result.copy()


def render_dynamic_filters(
    df: pd.DataFrame,
    column_types: dict[str, list[str]],
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Render sidebar filters and return the filtered dataset plus filter specs."""
    import streamlit as st

    specs: dict[str, dict[str, Any]] = {}

    with st.sidebar:
        st.markdown("## Explore filters")
        st.caption("Filters only affect the Explore page.")

        categorical_options = (
            column_types.get("categorical", [])
            + column_types.get("boolean", [])
        )
        selected_categories = st.multiselect(
            "Categorical filters",
            options=categorical_options,
            key="explore_category_filter_columns",
        )

        for column in selected_categories:
            values = sorted(df[column].dropna().astype(str).unique().tolist())
            selected_values = st.multiselect(
                column,
                options=values,
                key=f"explore_values_{column}",
            )
            include_missing = st.checkbox(
                f"Include missing {column}",
                value=False,
                key=f"explore_missing_{column}",
            )
            specs[column] = {
                "type": "category",
                "values": selected_values,
                "include_missing": include_missing,
            }

        selected_numeric = st.multiselect(
            "Numeric filters",
            options=column_types.get("numeric", []),
            key="explore_numeric_filter_columns",
        )

        for column in selected_numeric:
            values = pd.to_numeric(df[column], errors="coerce").dropna()
            if values.empty:
                continue

            minimum = float(values.min())
            maximum = float(values.max())

            if minimum == maximum:
                st.caption(f"{column}: constant value {minimum:g}")
                continue

            selected_range = st.slider(
                column,
                min_value=minimum,
                max_value=maximum,
                value=(minimum, maximum),
                key=f"explore_range_{column}",
            )
            specs[column] = {
                "type": "numeric",
                "minimum": selected_range[0],
                "maximum": selected_range[1],
            }

        selected_dates = st.multiselect(
            "Date filters",
            options=column_types.get("datetime", []),
            key="explore_date_filter_columns",
        )

        for column in selected_dates:
            values = pd.to_datetime(df[column], errors="coerce").dropna()
            if values.empty:
                continue

            selected_range = st.date_input(
                column,
                value=(values.min().date(), values.max().date()),
                key=f"explore_date_{column}",
            )
            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                specs[column] = {
                    "type": "datetime",
                    "start": selected_range[0],
                    "end": selected_range[1],
                }

        text_options = column_types.get("text", []) + column_types.get("identifier", [])
        selected_text = st.selectbox(
            "Text search column",
            options=["None"] + text_options,
            key="explore_text_column",
        )
        if selected_text != "None":
            query = st.text_input(
                "Contains",
                key="explore_text_query",
            )
            specs[selected_text] = {"type": "text", "query": query}

    return apply_filter_specs(df, specs), specs

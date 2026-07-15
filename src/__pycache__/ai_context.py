"""Build compact, computed context for the AI Analyst."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.analysis import (
    category_target_comparison,
    numeric_target_drivers,
    target_outliers,
    target_summary,
)
from src.eda import (
    categorical_summary,
    correlation_matrix,
    numeric_summary,
    strongest_correlations,
)
from src.profiling import detect_column_types, profile_dataset


def _records(frame: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.head(limit).where(pd.notna(frame), None).to_dict(orient="records")


def build_ai_context(
    df: pd.DataFrame,
    *,
    filename: str | None = None,
    target_column: str | None = None,
) -> dict[str, Any]:
    """Create structured evidence without sending raw dataset rows."""
    profile = profile_dataset(df)
    column_types = detect_column_types(df)

    numeric_columns = column_types.get("numeric", [])
    category_columns = (
        column_types.get("categorical", [])
        + column_types.get("boolean", [])
    )

    numeric_stats = numeric_summary(df, numeric_columns)
    category_stats = categorical_summary(
        df,
        category_columns[:8],
        top_n=8,
    )

    corr = correlation_matrix(df, numeric_columns)
    strongest = strongest_correlations(
        corr,
        limit=15,
        minimum_strength=0.2,
    )

    missing = (
        df.isna()
        .sum()
        .rename("missing")
        .reset_index()
        .rename(columns={"index": "column"})
    )
    missing["missing_percentage"] = (
        missing["missing"] / max(len(df), 1) * 100
    ).round(2)
    missing = missing[missing["missing"] > 0].sort_values(
        "missing",
        ascending=False,
    )

    context: dict[str, Any] = {
        "dataset": {
            "filename": filename,
            **profile.to_dict(),
        },
        "column_types": column_types,
        "numeric_summary": _records(numeric_stats, 30),
        "category_summaries": {
            column: _records(summary, 8)
            for column, summary in category_stats.items()
        },
        "strongest_correlations": _records(strongest, 15),
        "missing_values": _records(missing, 20),
    }

    if target_column and target_column in numeric_columns:
        drivers = numeric_target_drivers(
            df,
            target_column=target_column,
            numeric_columns=numeric_columns,
        )

        category_results = {
            column: category_target_comparison(
                df,
                category_column=column,
                target_column=target_column,
                top_n=10,
            )
            for column in category_columns[:5]
        }

        outlier_summary, _ = target_outliers(df, target_column)

        context["target_analysis"] = {
            "target": target_column,
            "summary": target_summary(df, target_column),
            "numeric_drivers": _records(drivers, 15),
            "category_comparisons": {
                column: _records(result, 10)
                for column, result in category_results.items()
                if not result.empty
            },
            "outliers": outlier_summary,
        }

    return context


def context_to_json(context: dict[str, Any]) -> str:
    """Serialize AI context safely."""
    return json.dumps(context, indent=2, default=str)

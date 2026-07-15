
"""Reusable exploratory data analysis helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NumericSummary:
    column: str
    count: int
    missing: int
    mean: float | None
    median: float | None
    std_dev: float | None
    minimum: float | None
    maximum: float | None
    skewness: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 4)


def numeric_summary(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return summary statistics for selected numeric columns."""
    rows: list[dict[str, Any]] = []

    for column in columns:
        if column not in df.columns:
            continue

        values = pd.to_numeric(df[column], errors="coerce")
        valid = values.dropna()

        summary = NumericSummary(
            column=column,
            count=int(valid.count()),
            missing=int(values.isna().sum()),
            mean=_safe_float(valid.mean()) if not valid.empty else None,
            median=_safe_float(valid.median()) if not valid.empty else None,
            std_dev=_safe_float(valid.std()) if len(valid) > 1 else None,
            minimum=_safe_float(valid.min()) if not valid.empty else None,
            maximum=_safe_float(valid.max()) if not valid.empty else None,
            skewness=_safe_float(valid.skew()) if len(valid) > 2 else None,
        )
        rows.append(summary.to_dict())

    return pd.DataFrame(rows)


def categorical_summary(
    df: pd.DataFrame,
    columns: list[str],
    top_n: int = 10,
) -> dict[str, pd.DataFrame]:
    """Return top value counts for categorical columns."""
    output: dict[str, pd.DataFrame] = {}

    for column in columns:
        if column not in df.columns:
            continue

        values = df[column].fillna("Missing").astype(str)
        counts = (
            values.value_counts(dropna=False)
            .head(top_n)
            .rename_axis("value")
            .reset_index(name="count")
        )
        counts["percentage"] = (counts["count"] / max(len(df), 1) * 100).round(2)
        output[column] = counts

    return output


def correlation_matrix(
    df: pd.DataFrame,
    numeric_columns: list[str],
    method: str = "pearson",
) -> pd.DataFrame:
    """Return a correlation matrix for numeric columns."""
    valid_method = method if method in {"pearson", "spearman", "kendall"} else "pearson"
    columns = [column for column in numeric_columns if column in df.columns]

    if len(columns) < 2:
        return pd.DataFrame()

    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.corr(method=valid_method).round(3)


def strongest_correlations(
    corr: pd.DataFrame,
    limit: int = 10,
    minimum_strength: float = 0.2,
) -> pd.DataFrame:
    """Return the strongest unique correlation pairs."""
    if corr.empty:
        return pd.DataFrame(columns=["variable_1", "variable_2", "correlation", "strength"])

    rows: list[dict[str, Any]] = []
    columns = list(corr.columns)

    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            value = corr.loc[left, right]
            if pd.isna(value) or abs(float(value)) < minimum_strength:
                continue

            absolute = abs(float(value))
            if absolute >= 0.8:
                strength = "Very strong"
            elif absolute >= 0.6:
                strength = "Strong"
            elif absolute >= 0.4:
                strength = "Moderate"
            else:
                strength = "Weak"

            rows.append(
                {
                    "variable_1": left,
                    "variable_2": right,
                    "correlation": round(float(value), 3),
                    "strength": strength,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["variable_1", "variable_2", "correlation", "strength"])

    return (
        pd.DataFrame(rows)
        .assign(abs_correlation=lambda frame: frame["correlation"].abs())
        .sort_values("abs_correlation", ascending=False)
        .drop(columns="abs_correlation")
        .head(limit)
        .reset_index(drop=True)
    )


def grouped_numeric_summary(
    df: pd.DataFrame,
    category_column: str,
    numeric_column: str,
    aggregation: str = "mean",
    top_n: int = 20,
) -> pd.DataFrame:
    """Aggregate a numeric column by a category."""
    if category_column not in df.columns or numeric_column not in df.columns:
        return pd.DataFrame()

    working = df[[category_column, numeric_column]].copy()
    working[category_column] = working[category_column].fillna("Missing").astype(str)
    working[numeric_column] = pd.to_numeric(working[numeric_column], errors="coerce")
    working = working.dropna(subset=[numeric_column])

    if working.empty:
        return pd.DataFrame()

    supported = {"mean", "median", "sum", "min", "max", "count"}
    selected = aggregation if aggregation in supported else "mean"

    if selected == "count":
        grouped = (
            working.groupby(category_column, dropna=False)[numeric_column]
            .count()
            .reset_index(name="value")
        )
    else:
        grouped = (
            working.groupby(category_column, dropna=False)[numeric_column]
            .agg(selected)
            .reset_index(name="value")
        )

    return (
        grouped.sort_values("value", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def time_series_summary(
    df: pd.DataFrame,
    date_column: str,
    numeric_column: str,
    aggregation: str = "sum",
    frequency: str = "M",
) -> pd.DataFrame:
    """Aggregate a numeric metric over time."""
    if date_column not in df.columns or numeric_column not in df.columns:
        return pd.DataFrame()

    working = df[[date_column, numeric_column]].copy()
    working[date_column] = pd.to_datetime(working[date_column], errors="coerce")
    working[numeric_column] = pd.to_numeric(working[numeric_column], errors="coerce")
    working = working.dropna(subset=[date_column, numeric_column])

    if working.empty:
        return pd.DataFrame()

    frequency_map = {
        "Day": "D",
        "Week": "W",
        "Month": "MS",
        "Quarter": "QS",
        "Year": "YS",
        "D": "D",
        "W": "W",
        "M": "MS",
        "Q": "QS",
        "Y": "YS",
    }
    selected_frequency = frequency_map.get(frequency, "M")
    supported = {"mean", "median", "sum", "min", "max", "count"}
    selected_aggregation = aggregation if aggregation in supported else "sum"

    indexed = working.set_index(date_column)[numeric_column]
    if selected_aggregation == "count":
        result = indexed.resample(selected_frequency).count()
    else:
        result = indexed.resample(selected_frequency).agg(selected_aggregation)

    return result.dropna().rename("value").reset_index()


def distribution_outliers(df: pd.DataFrame, column: str) -> dict[str, float | int | None]:
    """Return IQR-based outlier information for one numeric column."""
    if column not in df.columns:
        return {"count": 0, "percentage": 0.0, "lower_bound": None, "upper_bound": None}

    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if len(values) < 4:
        return {"count": 0, "percentage": 0.0, "lower_bound": None, "upper_bound": None}

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    if iqr == 0:
        return {
            "count": 0,
            "percentage": 0.0,
            "lower_bound": _safe_float(q1),
            "upper_bound": _safe_float(q3),
        }

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    count = int(((values < lower) | (values > upper)).sum())

    return {
        "count": count,
        "percentage": round(count / len(values) * 100, 2),
        "lower_bound": _safe_float(lower),
        "upper_bound": _safe_float(upper),
    }

"""Analysis helpers for target and driver discovery."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _strength_label(value: float) -> str:
    absolute = abs(value)
    if absolute >= 0.8:
        return "Very strong"
    if absolute >= 0.6:
        return "Strong"
    if absolute >= 0.4:
        return "Moderate"
    if absolute >= 0.2:
        return "Weak"
    return "Very weak"


def numeric_target_drivers(
    df: pd.DataFrame,
    target_column: str,
    numeric_columns: list[str],
    method: str = "pearson",
) -> pd.DataFrame:
    """Rank numeric columns by correlation with a numeric target."""
    if target_column not in df.columns:
        return pd.DataFrame(
            columns=["feature", "correlation", "absolute_correlation", "direction", "strength"]
        )

    valid_method = method if method in {"pearson", "spearman", "kendall"} else "pearson"
    target = pd.to_numeric(df[target_column], errors="coerce")
    rows: list[dict[str, Any]] = []

    for column in numeric_columns:
        if column == target_column or column not in df.columns:
            continue

        feature = pd.to_numeric(df[column], errors="coerce")
        paired = pd.DataFrame({"target": target, "feature": feature}).dropna()

        if len(paired) < 3:
            continue
        if paired["target"].nunique() < 2 or paired["feature"].nunique() < 2:
            continue

        correlation = paired["target"].corr(paired["feature"], method=valid_method)

        if pd.isna(correlation):
            continue

        correlation = float(correlation)
        rows.append(
            {
                "feature": column,
                "correlation": round(correlation, 3),
                "absolute_correlation": round(abs(correlation), 3),
                "direction": "Positive" if correlation > 0 else "Negative",
                "strength": _strength_label(correlation),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["feature", "correlation", "absolute_correlation", "direction", "strength"]
        )

    return (
        pd.DataFrame(rows)
        .sort_values("absolute_correlation", ascending=False)
        .reset_index(drop=True)
    )


def category_target_comparison(
    df: pd.DataFrame,
    category_column: str,
    target_column: str,
    top_n: int = 20,
) -> pd.DataFrame:
    """Compare a numeric target across category values."""
    if category_column not in df.columns or target_column not in df.columns:
        return pd.DataFrame()

    working = df[[category_column, target_column]].copy()
    working[category_column] = working[category_column].fillna("Missing").astype(str)
    working[target_column] = pd.to_numeric(working[target_column], errors="coerce")
    working = working.dropna(subset=[target_column])

    if working.empty:
        return pd.DataFrame()

    result = (
        working.groupby(category_column, dropna=False)[target_column]
        .agg(["count", "mean", "median", "sum", "min", "max"])
        .reset_index()
    )

    result["mean"] = result["mean"].round(3)
    result["median"] = result["median"].round(3)
    result["sum"] = result["sum"].round(3)
    result["min"] = result["min"].round(3)
    result["max"] = result["max"].round(3)

    return (
        result.sort_values("mean", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def target_outliers(
    df: pd.DataFrame,
    target_column: str,
) -> tuple[dict[str, float | int | None], pd.DataFrame]:
    """Return IQR outlier statistics and matching rows for a target."""
    if target_column not in df.columns:
        return {
            "count": 0,
            "percentage": 0.0,
            "lower_bound": None,
            "upper_bound": None,
        }, pd.DataFrame()

    values = pd.to_numeric(df[target_column], errors="coerce")

    if values.notna().sum() < 4:
        return {
            "count": 0,
            "percentage": 0.0,
            "lower_bound": None,
            "upper_bound": None,
        }, pd.DataFrame()

    valid = values.dropna()
    q1 = valid.quantile(0.25)
    q3 = valid.quantile(0.75)
    iqr = q3 - q1

    if iqr == 0:
        return {
            "count": 0,
            "percentage": 0.0,
            "lower_bound": round(float(q1), 3),
            "upper_bound": round(float(q3), 3),
        }, pd.DataFrame()

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (values < lower) | (values > upper)

    outlier_rows = df.loc[mask].copy()
    if not outlier_rows.empty:
        outlier_rows.insert(0, "source_row", outlier_rows.index)

    count = int(mask.sum())
    percentage = round(count / max(valid.count(), 1) * 100, 2)

    return {
        "count": count,
        "percentage": percentage,
        "lower_bound": round(float(lower), 3),
        "upper_bound": round(float(upper), 3),
    }, outlier_rows


def target_summary(df: pd.DataFrame, target_column: str) -> dict[str, float | int | None]:
    """Return core statistics for a numeric target."""
    if target_column not in df.columns:
        return {}

    values = pd.to_numeric(df[target_column], errors="coerce")
    valid = values.dropna()

    if valid.empty:
        return {}

    return {
        "count": int(valid.count()),
        "missing": int(values.isna().sum()),
        "mean": round(float(valid.mean()), 3),
        "median": round(float(valid.median()), 3),
        "minimum": round(float(valid.min()), 3),
        "maximum": round(float(valid.max()), 3),
        "standard_deviation": (
            round(float(valid.std()), 3) if len(valid) > 1 else None
        ),
    }


def generate_target_insights(
    target_column: str,
    drivers: pd.DataFrame,
    category_results: dict[str, pd.DataFrame],
    outlier_summary: dict[str, float | int | None],
) -> list[str]:
    """Create plain-English findings from computed results."""
    insights: list[str] = []

    if not drivers.empty:
        top_driver = drivers.iloc[0]
        insights.append(
            f"{top_driver['feature']} has the strongest numeric association with "
            f"{target_column} ({top_driver['direction'].lower()}, "
            f"r = {top_driver['correlation']:.3f})."
        )

        strong_negative = drivers[
            (drivers["direction"] == "Negative")
            & (drivers["absolute_correlation"] >= 0.4)
        ]
        if not strong_negative.empty:
            row = strong_negative.iloc[0]
            insights.append(
                f"{row['feature']} has a notable negative association with "
                f"{target_column} (r = {row['correlation']:.3f})."
            )

    for category, result in category_results.items():
        if result.empty:
            continue

        highest = result.iloc[0]
        lowest = result.iloc[-1]

        insights.append(
            f"{highest[category]} has the highest average {target_column} "
            f"within {category} ({highest['mean']:.3f})."
        )

        if len(result) > 1:
            insights.append(
                f"{lowest[category]} has the lowest average {target_column} "
                f"within {category} ({lowest['mean']:.3f})."
            )

        if len(insights) >= 6:
            break

    outlier_count = int(outlier_summary.get("count") or 0)
    if outlier_count > 0:
        insights.append(
            f"{target_column} contains {outlier_count} IQR outliers "
            f"({float(outlier_summary.get('percentage') or 0):.2f}% of valid values)."
        )

    if not insights:
        insights.append(
            f"Not enough variation or complete data was available to produce strong findings for {target_column}."
        )

    return insights[:8]

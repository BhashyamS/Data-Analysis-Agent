from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CleaningRecipe:
    remove_duplicates: bool = True
    drop_empty_columns: bool = True
    trim_whitespace: bool = True
    text_case: str = "Keep original"
    numeric_missing: str = "Keep missing"
    categorical_missing: str = "Keep missing"
    columns_to_drop: tuple[str, ...] = ()
    datetime_columns: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["columns_to_drop"] = list(self.columns_to_drop)
        data["datetime_columns"] = list(self.datetime_columns)
        return data


def _log(action: str, details: str, rows_affected: int = 0) -> dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "details": details,
        "rows_or_cells_affected": int(rows_affected),
    }


def _text_columns(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in df.columns
        if pd.api.types.is_object_dtype(df[column])
        or pd.api.types.is_string_dtype(df[column])
    ]


def apply_cleaning_recipe(
    df: pd.DataFrame,
    recipe: CleaningRecipe,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Apply a reproducible set of cleaning operations to a dataframe."""
    cleaned = df.copy(deep=True)
    history: list[dict[str, Any]] = []

    if recipe.columns_to_drop:
        existing = [column for column in recipe.columns_to_drop if column in cleaned.columns]
        if existing:
            cleaned = cleaned.drop(columns=existing)
            history.append(
                _log("Dropped selected columns", ", ".join(map(str, existing)), len(existing))
            )

    if recipe.drop_empty_columns:
        empty_columns = [column for column in cleaned.columns if cleaned[column].isna().all()]
        if empty_columns:
            cleaned = cleaned.drop(columns=empty_columns)
            history.append(
                _log("Dropped empty columns", ", ".join(map(str, empty_columns)), len(empty_columns))
            )

    if recipe.remove_duplicates:
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        removed = before - len(cleaned)
        if removed:
            history.append(_log("Removed duplicate rows", f"Removed {removed} duplicate rows.", removed))

    text_columns = _text_columns(cleaned)
    if recipe.trim_whitespace and text_columns:
        changed = 0
        for column in text_columns:
            original = cleaned[column].copy()
            cleaned[column] = cleaned[column].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
            changed += int((original.fillna("<NA>") != cleaned[column].fillna("<NA>")).sum())
        if changed:
            history.append(_log("Trimmed whitespace", f"Trimmed {changed} text cells.", changed))

    if recipe.text_case != "Keep original" and text_columns:
        changed = 0
        for column in text_columns:
            original = cleaned[column].copy()
            if recipe.text_case == "Title case":
                cleaned[column] = cleaned[column].map(
                    lambda value: value.title() if isinstance(value, str) else value
                )
            elif recipe.text_case == "Lowercase":
                cleaned[column] = cleaned[column].map(
                    lambda value: value.lower() if isinstance(value, str) else value
                )
            elif recipe.text_case == "Uppercase":
                cleaned[column] = cleaned[column].map(
                    lambda value: value.upper() if isinstance(value, str) else value
                )
            changed += int((original.fillna("<NA>") != cleaned[column].fillna("<NA>")).sum())
        if changed:
            history.append(
                _log("Standardized text case", f"Applied {recipe.text_case} to {changed} cells.", changed)
            )

    datetime_columns = [column for column in recipe.datetime_columns if column in cleaned.columns]
    for column in datetime_columns:
        before_non_null = int(cleaned[column].notna().sum())
        converted = pd.to_datetime(cleaned[column], errors="coerce")
        valid_after = int(converted.notna().sum())
        cleaned[column] = converted
        history.append(
            _log(
                "Converted to datetime",
                f"Converted {column}; {valid_after}/{before_non_null} non-null values parsed successfully.",
                valid_after,
            )
        )

    numeric_columns = cleaned.select_dtypes(include=np.number).columns.tolist()
    if recipe.numeric_missing != "Keep missing":
        affected = 0
        for column in numeric_columns:
            missing = int(cleaned[column].isna().sum())
            if not missing:
                continue
            if recipe.numeric_missing == "Median":
                fill_value = cleaned[column].median()
            elif recipe.numeric_missing == "Mean":
                fill_value = cleaned[column].mean()
            else:
                fill_value = 0
            if pd.notna(fill_value):
                cleaned[column] = cleaned[column].fillna(fill_value)
                affected += missing
        if affected:
            history.append(
                _log(
                    "Filled numeric missing values",
                    f"Filled {affected} cells using {recipe.numeric_missing.lower()}.",
                    affected,
                )
            )

    categorical_columns = [
        column
        for column in cleaned.columns
        if not pd.api.types.is_numeric_dtype(cleaned[column])
        and not pd.api.types.is_datetime64_any_dtype(cleaned[column])
    ]
    if recipe.categorical_missing != "Keep missing":
        affected = 0
        for column in categorical_columns:
            missing = int(cleaned[column].isna().sum())
            if not missing:
                continue
            if recipe.categorical_missing == "Mode":
                mode = cleaned[column].mode(dropna=True)
                fill_value = mode.iloc[0] if not mode.empty else "Unknown"
            else:
                fill_value = "Unknown"
            cleaned[column] = cleaned[column].fillna(fill_value)
            affected += missing
        if affected:
            history.append(
                _log(
                    "Filled categorical missing values",
                    f"Filled {affected} cells using {recipe.categorical_missing.lower()}.",
                    affected,
                )
            )

    if not history:
        history.append(_log("No transformations applied", "The prepared dataset matches the raw dataset."))

    return cleaned, history


def recommend_cleaning_actions(df: pd.DataFrame) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []

    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        recommendations.append(
            {
                "severity": "High",
                "title": "Remove duplicate rows",
                "message": f"{duplicate_count:,} duplicate rows may inflate totals and bias analysis.",
            }
        )

    empty_columns = [column for column in df.columns if df[column].isna().all()]
    if empty_columns:
        recommendations.append(
            {
                "severity": "High",
                "title": "Drop empty columns",
                "message": f"{len(empty_columns)} columns contain no usable values.",
            }
        )

    missing = int(df.isna().sum().sum())
    if missing:
        recommendations.append(
            {
                "severity": "Medium",
                "title": "Review missing values",
                "message": f"{missing:,} cells are missing. Choose an imputation strategy only when analytically justified.",
            }
        )

    whitespace_cells = 0
    for column in _text_columns(df):
        whitespace_cells += int(
            df[column].dropna().map(
                lambda value: isinstance(value, str) and value != value.strip()
            ).sum()
        )
    if whitespace_cells:
        recommendations.append(
            {
                "severity": "Medium",
                "title": "Trim text whitespace",
                "message": f"{whitespace_cells:,} text values contain leading or trailing spaces.",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "severity": "Ready",
                "title": "No critical preparation issues detected",
                "message": "The dataset appears structurally ready for exploratory analysis.",
            }
        )

    return recommendations

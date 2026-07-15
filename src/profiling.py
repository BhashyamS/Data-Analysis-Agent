from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd


@dataclass(frozen=True)
class DatasetProfile:
    rows: int
    columns: int
    missing_cells: int
    missing_percentage: float
    duplicate_rows: int
    memory_mb: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def profile_dataset(df: pd.DataFrame) -> DatasetProfile:
    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_cells = int(df.isna().sum().sum())
    return DatasetProfile(
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        missing_cells=missing_cells,
        missing_percentage=round(missing_cells / total_cells * 100, 2),
        duplicate_rows=int(df.duplicated().sum()),
        memory_mb=round(float(df.memory_usage(deep=True).sum()) / (1024**2), 3),
    )


def detect_column_types(df: pd.DataFrame) -> dict[str, list[str]]:
    """Classify columns into mutually exclusive practical analytics types."""
    result: dict[str, list[str]] = {
        "numeric": [],
        "categorical": [],
        "datetime": [],
        "boolean": [],
        "identifier": [],
        "text": [],
        "empty": [],
    }

    for column in df.columns:
        series = df[column]
        non_null = series.dropna()

        if non_null.empty:
            result["empty"].append(column)
            continue

        if pd.api.types.is_bool_dtype(series):
            result["boolean"].append(column)
            continue

        if pd.api.types.is_datetime64_any_dtype(series):
            result["datetime"].append(column)
            continue

        unique_ratio = non_null.nunique(dropna=True) / max(len(non_null), 1)
        column_name = str(column).lower()

        if pd.api.types.is_numeric_dtype(series):
            likely_id = unique_ratio >= 0.95 and any(
                token in column_name for token in ("id", "code", "number", "key")
            )
            result["identifier" if likely_id else "numeric"].append(column)
            continue

        date_name_hint = any(
            token in column_name
            for token in ("date", "time", "timestamp", "created", "updated", "month", "year")
        )
        if date_name_hint:
            parsed = pd.to_datetime(non_null, errors="coerce")
            if parsed.notna().mean() >= 0.8:
                result["datetime"].append(column)
                continue

        text_values = non_null.astype(str)
        average_length = float(text_values.str.len().mean())
        likely_id = unique_ratio >= 0.95 and average_length <= 40

        if likely_id:
            result["identifier"].append(column)
        elif average_length > 60 or (unique_ratio > 0.5 and average_length > 30):
            result["text"].append(column)
        else:
            result["categorical"].append(column)

    return result


def column_summary(df: pd.DataFrame, types: dict[str, list[str]]) -> pd.DataFrame:
    type_lookup = {
        column: type_name
        for type_name, columns in types.items()
        for column in columns
    }
    rows: list[dict[str, object]] = []
    for column in df.columns:
        rows.append(
            {
                "column": column,
                "detected_type": type_lookup.get(column, "unknown"),
                "pandas_dtype": str(df[column].dtype),
                "non_null": int(df[column].notna().sum()),
                "missing": int(df[column].isna().sum()),
                "missing_%": round(float(df[column].isna().mean() * 100), 2),
                "unique": int(df[column].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)

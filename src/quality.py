from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd


@dataclass(frozen=True)
class QualityScore:
    overall: int
    completeness: int
    uniqueness: int
    structure: int
    usability: int
    status: str
    deductions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def calculate_quality_score(df: pd.DataFrame) -> QualityScore:
    if df.empty and len(df.columns) == 0:
        return QualityScore(0, 0, 0, 0, 0, "Not usable", ("No data was loaded.",))

    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_rate = float(df.isna().sum().sum()) / total_cells
    duplicate_rate = float(df.duplicated().sum()) / max(len(df), 1)
    empty_column_rate = sum(df[column].isna().all() for column in df.columns) / max(len(df.columns), 1)
    constant_column_rate = sum(df[column].nunique(dropna=True) <= 1 for column in df.columns) / max(len(df.columns), 1)

    completeness = max(0, round(100 * (1 - missing_rate)))
    uniqueness = max(0, round(100 * (1 - duplicate_rate)))
    structure = max(0, round(100 * (1 - empty_column_rate)))
    usability = max(0, round(100 * (1 - 0.5 * constant_column_rate - 0.5 * empty_column_rate)))
    overall = round(
        completeness * 0.35
        + uniqueness * 0.25
        + structure * 0.20
        + usability * 0.20
    )

    deductions: list[str] = []
    if missing_rate:
        deductions.append(f"Missing values reduce completeness by {100 - completeness} points.")
    if duplicate_rate:
        deductions.append(f"Duplicate rows reduce uniqueness by {100 - uniqueness} points.")
    if empty_column_rate:
        deductions.append(f"Empty columns reduce structural quality by {100 - structure} points.")
    if constant_column_rate:
        deductions.append("Constant or low-information columns reduce usability.")
    if not deductions:
        deductions.append("No material structural deductions were detected.")

    if overall >= 90:
        status = "Ready for analysis"
    elif overall >= 75:
        status = "Mostly ready"
    elif overall >= 60:
        status = "Needs preparation"
    else:
        status = "High preparation need"

    return QualityScore(
        overall=overall,
        completeness=completeness,
        uniqueness=uniqueness,
        structure=structure,
        usability=usability,
        status=status,
        deductions=tuple(deductions),
    )

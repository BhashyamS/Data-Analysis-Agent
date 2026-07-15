
import pandas as pd

from src.eda import (
    categorical_summary,
    correlation_matrix,
    grouped_numeric_summary,
    numeric_summary,
    strongest_correlations,
    time_series_summary,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02"]
            ),
            "region": ["West", "West", "East", "East"],
            "sales": [100.0, 200.0, 300.0, 400.0],
            "profit": [10.0, 20.0, 30.0, 40.0],
        }
    )


def test_numeric_summary_returns_expected_mean() -> None:
    summary = numeric_summary(sample_frame(), ["sales"])
    assert summary.loc[0, "mean"] == 250.0
    assert summary.loc[0, "count"] == 4


def test_categorical_summary_counts_values() -> None:
    summary = categorical_summary(sample_frame(), ["region"])["region"]
    assert summary["count"].sum() == 4
    assert set(summary["value"]) == {"West", "East"}


def test_correlation_and_strongest_pairs() -> None:
    correlation = correlation_matrix(sample_frame(), ["sales", "profit"])
    assert correlation.loc["sales", "profit"] == 1.0

    strongest = strongest_correlations(correlation)
    assert len(strongest) == 1
    assert strongest.loc[0, "variable_1"] == "sales"
    assert strongest.loc[0, "variable_2"] == "profit"


def test_grouped_numeric_summary() -> None:
    grouped = grouped_numeric_summary(
        sample_frame(),
        "region",
        "sales",
        aggregation="sum",
    )
    totals = dict(zip(grouped["region"], grouped["value"]))
    assert totals["West"] == 300.0
    assert totals["East"] == 700.0


def test_time_series_summary() -> None:
    trend = time_series_summary(
        sample_frame(),
        "date",
        "sales",
        aggregation="sum",
        frequency="Month",
    )
    assert trend["value"].tolist() == [300.0, 700.0]

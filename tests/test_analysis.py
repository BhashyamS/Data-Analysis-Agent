import pandas as pd

from src.analysis import (
    category_target_comparison,
    generate_target_insights,
    numeric_target_drivers,
    target_outliers,
    target_summary,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sales": [100, 200, 300, 400, 500, 1000],
            "profit": [10, 20, 30, 40, 50, 400],
            "discount": [0.0, 0.1, 0.2, 0.3, 0.4, 0.9],
            "region": ["East", "East", "West", "West", "West", "South"],
        }
    )


def test_numeric_target_drivers_ranks_correlations():
    df = sample_frame()
    result = numeric_target_drivers(
        df,
        target_column="profit",
        numeric_columns=["sales", "profit", "discount"],
    )

    assert not result.empty
    assert "sales" in result["feature"].tolist()
    assert result.iloc[0]["absolute_correlation"] >= result.iloc[-1]["absolute_correlation"]


def test_category_target_comparison_returns_grouped_metrics():
    df = sample_frame()
    result = category_target_comparison(
        df,
        category_column="region",
        target_column="profit",
    )

    assert set(["region", "count", "mean", "median", "sum"]).issubset(result.columns)
    assert result.iloc[0]["mean"] >= result.iloc[-1]["mean"]


def test_target_outliers_returns_summary_and_rows():
    df = sample_frame()
    summary, rows = target_outliers(df, "profit")

    assert "count" in summary
    assert isinstance(rows, pd.DataFrame)


def test_target_summary_returns_basic_statistics():
    result = target_summary(sample_frame(), "profit")

    assert result["count"] == 6
    assert result["mean"] > 0
    assert result["maximum"] == 400.0


def test_generate_target_insights_returns_text():
    df = sample_frame()
    drivers = numeric_target_drivers(
        df,
        target_column="profit",
        numeric_columns=["sales", "profit", "discount"],
    )
    categories = {
        "region": category_target_comparison(df, "region", "profit")
    }
    outliers, _ = target_outliers(df, "profit")

    insights = generate_target_insights(
        "profit",
        drivers,
        categories,
        outliers,
    )

    assert insights
    assert all(isinstance(item, str) for item in insights)

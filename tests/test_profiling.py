import pandas as pd

from src.profiling import detect_column_types, profile_dataset


def test_profile_dataset() -> None:
    df = pd.DataFrame({"a": [1, 1, None], "b": ["x", "x", None]})
    profile = profile_dataset(df)
    assert profile.rows == 3
    assert profile.columns == 2
    assert profile.missing_cells == 2
    assert profile.duplicate_rows == 1


def test_detect_column_types() -> None:
    df = pd.DataFrame(
        {
            "order_id": ["A1", "A2", "A3"],
            "sales": [10.0, 20.0, 30.0],
            "region": ["West", "East", "West"],
            "order_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        }
    )
    types = detect_column_types(df)
    assert "order_id" in types["identifier"]
    assert "sales" in types["numeric"]
    assert "region" in types["categorical"]
    assert "order_date" in types["datetime"]

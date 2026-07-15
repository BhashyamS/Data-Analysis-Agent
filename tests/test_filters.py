
import pandas as pd

from src.filters import apply_filter_specs


def test_category_and_numeric_filters() -> None:
    frame = pd.DataFrame(
        {
            "region": ["West", "East", "West"],
            "sales": [100, 200, 300],
        }
    )
    result = apply_filter_specs(
        frame,
        {
            "region": {"type": "category", "values": ["West"]},
            "sales": {"type": "numeric", "minimum": 150, "maximum": 350},
        },
    )
    assert len(result) == 1
    assert result.iloc[0]["sales"] == 300


def test_datetime_filter_is_inclusive() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "sales": [1, 2, 3],
        }
    )
    result = apply_filter_specs(
        frame,
        {
            "date": {
                "type": "datetime",
                "start": "2026-01-02",
                "end": "2026-01-03",
            }
        },
    )
    assert result["sales"].tolist() == [2, 3]


def test_text_filter_is_case_insensitive() -> None:
    frame = pd.DataFrame({"name": ["Alpha Store", "beta shop", "Gamma"]})
    result = apply_filter_specs(
        frame,
        {"name": {"type": "text", "query": "STORE"}},
    )
    assert result["name"].tolist() == ["Alpha Store"]

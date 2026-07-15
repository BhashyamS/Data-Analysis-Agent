import pandas as pd

from src.ai_context import build_ai_context, context_to_json


def test_ai_context_contains_evidence():
    df = pd.DataFrame(
        {
            "sales": [100, 200, 300, 400],
            "profit": [10, 20, 25, 50],
            "region": ["East", "East", "West", "West"],
        }
    )

    context = build_ai_context(
        df,
        filename="sales.csv",
        target_column="profit",
    )

    assert context["dataset"]["filename"] == "sales.csv"
    assert "numeric_summary" in context
    assert "category_summaries" in context
    assert "strongest_correlations" in context
    assert context["target_analysis"]["target"] == "profit"


def test_context_json_is_text():
    df = pd.DataFrame({"value": [1, 2, 3]})
    result = context_to_json(build_ai_context(df))

    assert isinstance(result, str)
    assert '"dataset"' in result

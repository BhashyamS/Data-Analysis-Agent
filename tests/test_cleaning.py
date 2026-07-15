import numpy as np
import pandas as pd

from src.cleaning import CleaningRecipe, apply_cleaning_recipe, recommend_cleaning_actions


def dirty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": [" Alice ", " Alice ", "BOB", None],
            "sales": [10.0, 10.0, np.nan, 30.0],
            "order_date": ["2026-01-01", "2026-01-01", "2026-01-03", "2026-01-04"],
            "empty": [np.nan, np.nan, np.nan, np.nan],
        }
    )


def test_cleaning_recipe_applies_expected_transformations():
    recipe = CleaningRecipe(
        remove_duplicates=True,
        drop_empty_columns=True,
        trim_whitespace=True,
        text_case="Title case",
        numeric_missing="Median",
        categorical_missing="Unknown",
        datetime_columns=("order_date",),
    )
    cleaned, history = apply_cleaning_recipe(dirty_dataframe(), recipe)

    assert len(cleaned) == 3
    assert "empty" not in cleaned.columns
    assert cleaned["sales"].isna().sum() == 0
    assert pd.api.types.is_datetime64_any_dtype(cleaned["order_date"])
    assert cleaned.loc[0, "name"] == "Alice"
    assert len(history) >= 4


def test_recommendations_detect_dirty_data():
    recommendations = recommend_cleaning_actions(dirty_dataframe())
    titles = {item["title"] for item in recommendations}
    assert "Remove duplicate rows" in titles
    assert "Drop empty columns" in titles
    assert "Review missing values" in titles

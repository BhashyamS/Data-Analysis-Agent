import numpy as np
import pandas as pd

from src.quality import calculate_quality_score


def test_quality_improves_after_basic_cleaning():
    raw = pd.DataFrame({"a": [1, 1, np.nan], "empty": [np.nan, np.nan, np.nan]})
    clean = pd.DataFrame({"a": [1]})
    assert calculate_quality_score(clean).overall > calculate_quality_score(raw).overall


def test_quality_score_is_bounded():
    df = pd.DataFrame({"a": [1, 2, 3]})
    score = calculate_quality_score(df)
    assert 0 <= score.overall <= 100

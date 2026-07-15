from io import BytesIO

import pandas as pd
import pytest

from src.loader import UnsupportedFileTypeError, load_table, make_unique_column_names


def test_load_csv() -> None:
    data = BytesIO(b"name,value\nA,10\nB,20\n")
    df = load_table(data, "sample.csv")
    assert df.shape == (2, 2)
    assert df["value"].sum() == 30


def test_reject_unsupported_file() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        load_table(BytesIO(b"hello"), "notes.txt")


def test_unique_column_names() -> None:
    df = pd.DataFrame([[1, 2, 3]], columns=["value", "value", ""])
    result = make_unique_column_names(df)
    assert list(result.columns) == ["value", "value_2", "column_3"]

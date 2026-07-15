from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class UnsupportedFileTypeError(ValueError):
    """Raised when the uploaded file type is unsupported."""


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def load_table(file_obj: BinaryIO | BytesIO, filename: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame.

    The file pointer is reset before reading so repeated Streamlit reruns are safe.
    """
    extension = _extension(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension or 'unknown'}'. Upload CSV, XLSX, or XLS."
        )

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    if extension == ".csv":
        try:
            return pd.read_csv(file_obj)
        except UnicodeDecodeError:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            return pd.read_csv(file_obj, encoding="latin-1")

    return pd.read_excel(file_obj)


def make_unique_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with non-empty, unique string column names."""
    result = df.copy()
    seen: dict[str, int] = {}
    names: list[str] = []

    for index, raw_name in enumerate(result.columns, start=1):
        base = str(raw_name).strip() or f"column_{index}"
        count = seen.get(base, 0)
        name = base if count == 0 else f"{base}_{count + 1}"
        while name in seen:
            count += 1
            name = f"{base}_{count + 1}"
        seen[base] = count + 1
        seen[name] = 1
        names.append(name)

    result.columns = names
    return result

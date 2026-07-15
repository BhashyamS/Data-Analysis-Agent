from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd
import streamlit as st

DATAFRAME_KEY = "analytics_raw_df"
PREPARED_DATAFRAME_KEY = "analytics_prepared_df"
FILENAME_KEY = "analytics_filename"
FILE_HASH_KEY = "analytics_file_hash"
RECIPE_KEY = "analytics_cleaning_recipe"
HISTORY_KEY = "analytics_transformation_history"


def initialize_state() -> None:
    st.session_state.setdefault(DATAFRAME_KEY, None)
    st.session_state.setdefault(PREPARED_DATAFRAME_KEY, None)
    st.session_state.setdefault(FILENAME_KEY, None)
    st.session_state.setdefault(FILE_HASH_KEY, None)
    st.session_state.setdefault(RECIPE_KEY, None)
    st.session_state.setdefault(HISTORY_KEY, [])


def file_fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_dataset(df: pd.DataFrame, filename: str, fingerprint: str) -> None:
    st.session_state[DATAFRAME_KEY] = df
    st.session_state[PREPARED_DATAFRAME_KEY] = None
    st.session_state[FILENAME_KEY] = filename
    st.session_state[FILE_HASH_KEY] = fingerprint
    st.session_state[RECIPE_KEY] = None
    st.session_state[HISTORY_KEY] = []


def store_prepared_dataset(
    df: pd.DataFrame,
    recipe: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    st.session_state[PREPARED_DATAFRAME_KEY] = df
    st.session_state[RECIPE_KEY] = recipe
    st.session_state[HISTORY_KEY] = history


def reset_preparation() -> None:
    st.session_state[PREPARED_DATAFRAME_KEY] = None
    st.session_state[RECIPE_KEY] = None
    st.session_state[HISTORY_KEY] = []


def clear_dataset() -> None:
    for key in (
        DATAFRAME_KEY,
        PREPARED_DATAFRAME_KEY,
        FILENAME_KEY,
        FILE_HASH_KEY,
        RECIPE_KEY,
        HISTORY_KEY,
    ):
        st.session_state[key] = [] if key == HISTORY_KEY else None


def has_dataset() -> bool:
    return isinstance(st.session_state.get(DATAFRAME_KEY), pd.DataFrame)


def get_dataset() -> pd.DataFrame | None:
    value = st.session_state.get(DATAFRAME_KEY)
    return value if isinstance(value, pd.DataFrame) else None


def get_prepared_dataset() -> pd.DataFrame | None:
    value = st.session_state.get(PREPARED_DATAFRAME_KEY)
    return value if isinstance(value, pd.DataFrame) else None


def get_active_dataset() -> pd.DataFrame | None:
    prepared = get_prepared_dataset()
    return prepared if prepared is not None else get_dataset()

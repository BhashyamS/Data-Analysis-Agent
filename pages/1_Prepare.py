from __future__ import annotations

import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from components.cards import inject_card_styles, metric_grid
from src.cleaning import CleaningRecipe, apply_cleaning_recipe, recommend_cleaning_actions
from src.exports import dataframe_to_csv_bytes, json_bytes, transformation_log_text
from src.profiling import column_summary, detect_column_types, profile_dataset
from src.quality import calculate_quality_score
from src.state import (
    get_dataset,
    get_prepared_dataset,
    initialize_state,
    reset_preparation,
    store_prepared_dataset,
)

st.set_page_config(page_title="Prepare · Analytics Copilot", page_icon="✦", layout="wide")
apply_app_styles()
initialize_state()

render_workflow_navigation(active_step=2)
st.title("Prepare")
st.caption("Clean, validate, and document your dataset before analysis.")

raw_df = get_dataset()
if raw_df is None:
    st.warning("No dataset is loaded. Return to the home page and upload a CSV or Excel file.")
    if st.button("← Return to Import"):
        st.switch_page("app.py")
    st.stop()

prepared_df = get_prepared_dataset()
active_df = prepared_df if prepared_df is not None else raw_df
raw_profile = profile_dataset(raw_df)
active_profile = profile_dataset(active_df)
raw_quality = calculate_quality_score(raw_df)
active_quality = calculate_quality_score(active_df)
raw_types = detect_column_types(raw_df)

with st.sidebar:
    st.markdown("## Preparation workspace")
    st.caption(st.session_state.get("analytics_filename", "Dataset"))
    st.metric("Current readiness", f"{active_quality.overall}%", active_quality.overall - raw_quality.overall)
    st.progress(active_quality.overall / 100)
    st.caption(active_quality.status)
    if prepared_df is not None and st.button("Reset preparation", use_container_width=True):
        reset_preparation()
        st.rerun()

st.markdown("## Dataset readiness")
readiness_left, readiness_right = st.columns([0.34, 0.66], gap="large")
with readiness_left:
    st.metric("Readiness score", f"{active_quality.overall}%", active_quality.overall - raw_quality.overall)
    st.progress(active_quality.overall / 100)
    st.markdown(f"**{active_quality.status}**")
    if prepared_df is not None:
        st.success(f"Preparation improved readiness from {raw_quality.overall}% to {active_quality.overall}%.")
    else:
        st.info("Apply a cleaning recipe to generate the prepared version.")

with readiness_right:
    score_columns = st.columns(4)
    score_columns[0].metric("Completeness", f"{active_quality.completeness}%")
    score_columns[1].metric("Uniqueness", f"{active_quality.uniqueness}%")
    score_columns[2].metric("Structure", f"{active_quality.structure}%")
    score_columns[3].metric("Usability", f"{active_quality.usability}%")
    with st.expander("Why this score?"):
        for deduction in active_quality.deductions:
            st.write(f"• {deduction}")

st.divider()
st.markdown("## Cleaning recommendations")
recommendations = recommend_cleaning_actions(raw_df)
recommendation_columns = st.columns(min(3, len(recommendations)))
for index, recommendation in enumerate(recommendations):
    with recommendation_columns[index % len(recommendation_columns)]:
        severity = recommendation["severity"]
        if severity == "High":
            st.error(f"**{recommendation['title']}**\n\n{recommendation['message']}")
        elif severity == "Medium":
            st.warning(f"**{recommendation['title']}**\n\n{recommendation['message']}")
        else:
            st.success(f"**{recommendation['title']}**\n\n{recommendation['message']}")

st.divider()
st.markdown("## Cleaning center")
st.caption("Choose a reproducible recipe. The raw dataset is never overwritten.")

with st.form("cleaning_recipe_form"):
    operation_col, missing_col, schema_col = st.columns(3, gap="large")

    with operation_col:
        st.markdown("#### Structural cleanup")
        remove_duplicates = st.checkbox(
            "Remove duplicate rows",
            value=raw_profile.duplicate_rows > 0,
            help="Keeps the first occurrence of each duplicated row.",
        )
        drop_empty_columns = st.checkbox(
            "Drop completely empty columns",
            value=bool(raw_types["empty"]),
        )
        trim_whitespace = st.checkbox("Trim text whitespace", value=True)
        text_case = st.selectbox(
            "Standardize text capitalization",
            ["Keep original", "Title case", "Lowercase", "Uppercase"],
        )

    with missing_col:
        st.markdown("#### Missing values")
        numeric_missing = st.selectbox(
            "Numeric columns",
            ["Keep missing", "Median", "Mean", "Zero"],
            help="Median is usually safer for skewed numeric distributions.",
        )
        categorical_missing = st.selectbox(
            "Categorical and text columns",
            ["Keep missing", "Mode", "Unknown"],
        )
        st.caption("Imputation changes the data. Use it only when the analytical context supports it.")

    with schema_col:
        st.markdown("#### Schema controls")
        columns_to_drop = st.multiselect(
            "Drop selected columns",
            options=list(raw_df.columns),
            help="Useful for empty, irrelevant, or sensitive fields.",
        )
        suggested_dates = raw_types["datetime"]
        datetime_columns = st.multiselect(
            "Convert to datetime",
            options=list(raw_df.columns),
            default=suggested_dates,
        )

    apply_recipe = st.form_submit_button(
        "Apply cleaning recipe",
        type="primary",
        use_container_width=True,
    )

if apply_recipe:
    recipe = CleaningRecipe(
        remove_duplicates=remove_duplicates,
        drop_empty_columns=drop_empty_columns,
        trim_whitespace=trim_whitespace,
        text_case=text_case,
        numeric_missing=numeric_missing,
        categorical_missing=categorical_missing,
        columns_to_drop=tuple(columns_to_drop),
        datetime_columns=tuple(datetime_columns),
    )
    cleaned_df, history = apply_cleaning_recipe(raw_df, recipe)
    store_prepared_dataset(cleaned_df, recipe.to_dict(), history)
    st.success("Cleaning recipe applied. The raw dataset remains unchanged.")
    st.rerun()

st.divider()
st.markdown("## Before and after")
comparison = st.columns(5)
comparison[0].metric("Rows", f"{active_profile.rows:,}", active_profile.rows - raw_profile.rows)
comparison[1].metric("Columns", active_profile.columns, active_profile.columns - raw_profile.columns)
comparison[2].metric("Missing cells", f"{active_profile.missing_cells:,}", active_profile.missing_cells - raw_profile.missing_cells, delta_color="inverse")
comparison[3].metric("Duplicate rows", f"{active_profile.duplicate_rows:,}", active_profile.duplicate_rows - raw_profile.duplicate_rows, delta_color="inverse")
comparison[4].metric("Readiness", f"{active_quality.overall}%", active_quality.overall - raw_quality.overall)

raw_tab, prepared_tab, schema_tab = st.tabs(["Raw data", "Prepared data", "Prepared schema"])
with raw_tab:
    st.dataframe(raw_df.head(50), use_container_width=True, hide_index=True)
with prepared_tab:
    if prepared_df is None:
        st.info("Apply a cleaning recipe to create a prepared dataset.")
    else:
        st.dataframe(prepared_df.head(50), use_container_width=True, hide_index=True)
with schema_tab:
    st.dataframe(
        column_summary(active_df, detect_column_types(active_df)),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.markdown("## Transformation timeline")
history = st.session_state.get("analytics_transformation_history", [])
if not history:
    st.info("No cleaning recipe has been applied yet.")
else:
    for index, item in enumerate(history, start=1):
        st.markdown(
            f"**{index}. {item['action']}**  \n"
            f"{item['details']}  \n"
            f"<span class='small-muted'>{item['timestamp']}</span>",
            unsafe_allow_html=True,
        )
        if index < len(history):
            st.markdown("↓")

st.divider()

navigation_left, navigation_right = st.columns(2)

with navigation_left:
    if st.button(
        "← Back to Import",
        use_container_width=True,
    ):
        st.switch_page("app.py")

with navigation_right:
    if st.button(
        "Continue to Explore →",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/2_Explore.py")

st.divider()
st.markdown("## Export")
if prepared_df is None:
    st.info("Apply a cleaning recipe before exporting Version 1 deliverables.")
else:
    recipe_payload = st.session_state.get("analytics_cleaning_recipe", {})
    package = {
        "source_filename": st.session_state.get("analytics_filename"),
        "raw_profile": raw_profile.to_dict(),
        "prepared_profile": active_profile.to_dict(),
        "raw_quality": raw_quality.to_dict(),
        "prepared_quality": active_quality.to_dict(),
        "cleaning_recipe": recipe_payload,
        "transformation_history": history,
        "prepared_schema": column_summary(
            prepared_df, detect_column_types(prepared_df)
        ).to_dict(orient="records"),
    }
    base_name = str(st.session_state.get("analytics_filename", "dataset")).rsplit(".", 1)[0]
    export_columns = st.columns(3)
    export_columns[0].download_button(
        "Download prepared CSV",
        data=dataframe_to_csv_bytes(prepared_df),
        file_name=f"{base_name}_prepared.csv",
        mime="text/csv",
        use_container_width=True,
    )
    export_columns[1].download_button(
        "Download cleaning recipe",
        data=json_bytes(recipe_payload),
        file_name=f"{base_name}_cleaning_recipe.json",
        mime="application/json",
        use_container_width=True,
    )
    export_columns[2].download_button(
        "Download preparation package",
        data=json_bytes(package),
        file_name=f"{base_name}_preparation_package.json",
        mime="application/json",
        use_container_width=True,
    )
    st.download_button(
        "Download transformation log",
        data=transformation_log_text(history).encode("utf-8"),
        file_name=f"{base_name}_transformation_log.txt",
        mime="text/plain",
        use_container_width=True,
    )


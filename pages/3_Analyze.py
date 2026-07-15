from __future__ import annotations

import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from src.analysis import (
    category_target_comparison,
    generate_target_insights,
    numeric_target_drivers,
    target_outliers,
    target_summary,
)
from src.charts import grouped_bar_chart, scatter_chart
from src.profiling import detect_column_types
from src.state import get_active_dataset, initialize_state

st.set_page_config(
    page_title="Analyze · Analytics Copilot",
    page_icon="✦",
    layout="wide",
)

apply_app_styles()
initialize_state()
render_workflow_navigation(active_step=4)

st.title("Analyze")
st.caption("Choose an outcome and investigate its strongest associations.")

df = get_active_dataset()

if df is None:
    st.warning("No dataset is loaded.")
    if st.button("← Return to Import"):
        st.switch_page("app.py")
    st.stop()

column_types = detect_column_types(df)
numeric_columns = column_types.get("numeric", [])
category_columns = (
    column_types.get("categorical", [])
    + column_types.get("boolean", [])
)

if not numeric_columns:
    st.warning("This page needs at least one numeric column.")
    st.stop()

with st.sidebar:
    st.markdown("## Analysis settings")

    target_column = st.selectbox("Target column", numeric_columns)
    correlation_method = st.selectbox(
        "Correlation method",
        ["pearson", "spearman", "kendall"],
    )
    selected_categories = st.multiselect(
        "Category comparisons",
        category_columns,
        default=category_columns[:2],
    )
    top_n_categories = st.slider(
        "Maximum categories",
        5,
        30,
        15,
    )

st.info("Associations do not prove causation.")

summary = target_summary(df, target_column)
drivers = numeric_target_drivers(
    df,
    target_column,
    numeric_columns,
    correlation_method,
)
outlier_summary, outlier_rows = target_outliers(df, target_column)

st.markdown("## Target overview")
overview = st.columns(5)
overview[0].metric("Valid", f"{summary.get('count', 0):,}")
overview[1].metric("Missing", f"{summary.get('missing', 0):,}")
overview[2].metric("Mean", summary.get("mean", "—"))
overview[3].metric("Median", summary.get("median", "—"))
overview[4].metric("Outliers", f"{outlier_summary.get('count', 0):,}")

st.divider()
st.markdown("## Numeric drivers")

if drivers.empty:
    st.info("No usable numeric relationships found.")
else:
    st.dataframe(drivers, use_container_width=True, hide_index=True)
    top_driver = str(drivers.iloc[0]["feature"])
    st.plotly_chart(
        scatter_chart(df, top_driver, target_column),
        use_container_width=True,
    )

st.divider()
st.markdown("## Category comparisons")

category_results = {}

for category in selected_categories:
    result = category_target_comparison(
        df,
        category,
        target_column,
        top_n_categories,
    )
    category_results[category] = result

    if result.empty:
        continue

    st.markdown(f"### {target_column} by {category}")
    chart_data = result[[category, "mean"]].rename(
        columns={"mean": "value"}
    )
    st.plotly_chart(
        grouped_bar_chart(
            chart_data,
            category,
            target_column,
            "mean",
        ),
        use_container_width=True,
    )

st.divider()
st.markdown("## Key findings")

for insight in generate_target_insights(
    target_column,
    drivers,
    category_results,
    outlier_summary,
):
    st.write(f"• {insight}")

st.divider()
st.markdown("## Outliers")

if outlier_rows.empty:
    st.success("No target outliers detected.")
else:
    st.dataframe(
        outlier_rows.head(100),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

left, right = st.columns(2)

with left:
    if st.button("← Back to Explore", use_container_width=True):
        st.switch_page("pages/2_Explore.py")

with right:
    if st.button(
        "Continue to AI Analyst →",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/4_AI_Copilot.py")

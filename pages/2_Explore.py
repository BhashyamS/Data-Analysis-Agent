from __future__ import annotations

import pandas as pd
import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from src.charts import (
    box_chart,
    category_bar_chart,
    correlation_heatmap,
    custom_chart,
    grouped_bar_chart,
    histogram_chart,
    scatter_chart,
    time_series_chart,
)
from src.eda import (
    categorical_summary,
    correlation_matrix,
    distribution_outliers,
    grouped_numeric_summary,
    numeric_summary,
    strongest_correlations,
    time_series_summary,
)
from src.filters import render_dynamic_filters
from src.profiling import detect_column_types, profile_dataset
from src.state import get_active_dataset, initialize_state

st.set_page_config(page_title="Explore · Analytics Copilot", page_icon="✦", layout="wide")
apply_app_styles()
initialize_state()

render_workflow_navigation(active_step=3)
st.title("Explore")
st.caption("Understand distributions, categories, trends, and relationships.")

top_back, top_next = st.columns(2)

with top_back:
    if st.button(
        "← Back to Prepare",
        key="explore_top_back",
        use_container_width=True,
    ):
        st.switch_page("pages/1_Prepare.py")

with top_next:
    if st.button(
        "Continue to Analyze →",
        key="explore_top_next",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/3_Analyze.py")

st.divider()

df = get_active_dataset()
if df is None:
    st.warning("No dataset is loaded. Return to the home page and upload a file.")
    if st.button("← Return to Import"):
        st.switch_page("app.py")
    st.stop()

column_types = detect_column_types(df)
filtered_df, filter_specs = render_dynamic_filters(df, column_types)
filtered_types = detect_column_types(filtered_df)
profile = profile_dataset(filtered_df)

st.markdown("## Filtered dataset")
metric_columns = st.columns(5)
metric_columns[0].metric("Rows", f"{profile.rows:,}", profile.rows - len(df))
metric_columns[1].metric("Columns", profile.columns)
metric_columns[2].metric("Missing", f"{profile.missing_cells:,}")
metric_columns[3].metric("Numeric", len(filtered_types["numeric"]))
metric_columns[4].metric(
    "Filters",
    sum(
        1
        for specification in filter_specs.values()
        if any(
            value not in (None, "", [], False)
            for value in specification.values()
            if value != specification.get("type")
        )
    ),
)

if filtered_df.empty:
    st.error("The selected filters returned no rows. Adjust the sidebar filters.")
    st.stop()

overview_tab, distributions_tab, categories_tab, trends_tab, relationships_tab, builder_tab = st.tabs(
    [
        "Overview",
        "Distributions",
        "Categories",
        "Trends",
        "Relationships",
        "Chart builder",
    ]
)

with overview_tab:
    st.markdown("### Data preview")
    st.dataframe(filtered_df.head(100), use_container_width=True, hide_index=True)

    numeric_columns = filtered_types["numeric"]
    if numeric_columns:
        st.markdown("### Numeric summary")
        st.dataframe(
            numeric_summary(filtered_df, numeric_columns),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No numeric columns were detected.")

with distributions_tab:
    numeric_columns = filtered_types["numeric"]
    if not numeric_columns:
        st.info("No numeric columns are available for distribution analysis.")
    else:
        selected_numeric = st.selectbox(
            "Numeric column",
            options=numeric_columns,
            key="distribution_numeric_column",
        )
        bins = st.slider("Histogram bins", 10, 100, 30, key="distribution_bins")
        outlier_info = distribution_outliers(filtered_df, selected_numeric)

        outlier_columns = st.columns(3)
        outlier_columns[0].metric("Outliers", int(outlier_info["count"] or 0))
        outlier_columns[1].metric(
            "Outlier rate",
            f"{float(outlier_info['percentage'] or 0):.2f}%",
        )
        outlier_columns[2].metric(
            "Valid values",
            f"{pd.to_numeric(filtered_df[selected_numeric], errors='coerce').notna().sum():,}",
        )

        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.plotly_chart(
                histogram_chart(filtered_df, selected_numeric, bins),
                use_container_width=True,
            )
        with chart_right:
            st.plotly_chart(
                box_chart(filtered_df, selected_numeric),
                use_container_width=True,
            )

with categories_tab:
    category_columns = (
        filtered_types["categorical"]
        + filtered_types["boolean"]
        + filtered_types["identifier"]
    )
    if not category_columns:
        st.info("No categorical columns were detected.")
    else:
        selected_category = st.selectbox(
            "Category column",
            options=category_columns,
            key="category_column",
        )
        top_n = st.slider("Top values", 5, 30, 10, key="category_top_n")
        summary = categorical_summary(
            filtered_df,
            [selected_category],
            top_n=top_n,
        )[selected_category]

        chart_col, table_col = st.columns([0.62, 0.38])
        with chart_col:
            st.plotly_chart(
                category_bar_chart(summary, selected_category),
                use_container_width=True,
            )
        with table_col:
            st.dataframe(summary, use_container_width=True, hide_index=True)

        numeric_columns = filtered_types["numeric"]
        if numeric_columns:
            st.markdown("### Compare a metric by category")
            comparison_columns = st.columns(3)
            selected_metric = comparison_columns[0].selectbox(
                "Metric",
                options=numeric_columns,
                key="category_metric",
            )
            aggregation = comparison_columns[1].selectbox(
                "Aggregation",
                options=["mean", "median", "sum", "count", "min", "max"],
                key="category_aggregation",
            )
            comparison_top_n = comparison_columns[2].slider(
                "Groups",
                5,
                30,
                15,
                key="category_groups",
            )
            grouped = grouped_numeric_summary(
                filtered_df,
                selected_category,
                selected_metric,
                aggregation,
                comparison_top_n,
            )
            if not grouped.empty:
                st.plotly_chart(
                    grouped_bar_chart(
                        grouped,
                        selected_category,
                        selected_metric,
                        aggregation,
                    ),
                    use_container_width=True,
                )

with trends_tab:
    date_columns = filtered_types["datetime"]
    numeric_columns = filtered_types["numeric"]

    if not date_columns or not numeric_columns:
        st.info("Trend analysis requires at least one date column and one numeric column.")
    else:
        trend_columns = st.columns(4)
        date_column = trend_columns[0].selectbox(
            "Date",
            options=date_columns,
            key="trend_date",
        )
        value_column = trend_columns[1].selectbox(
            "Metric",
            options=numeric_columns,
            key="trend_metric",
        )
        trend_aggregation = trend_columns[2].selectbox(
            "Aggregation",
            options=["sum", "mean", "median", "count", "min", "max"],
            key="trend_aggregation",
        )
        frequency = trend_columns[3].selectbox(
            "Frequency",
            options=["Day", "Week", "Month", "Quarter", "Year"],
            index=2,
            key="trend_frequency",
        )

        trend_data = time_series_summary(
            filtered_df,
            date_column,
            value_column,
            trend_aggregation,
            frequency,
        )
        if trend_data.empty:
            st.warning("No valid date and numeric combinations were found.")
        else:
            st.plotly_chart(
                time_series_chart(
                    trend_data,
                    date_column,
                    value_column,
                    trend_aggregation,
                ),
                use_container_width=True,
            )
            st.dataframe(trend_data, use_container_width=True, hide_index=True)

with relationships_tab:
    numeric_columns = filtered_types["numeric"]
    if len(numeric_columns) < 2:
        st.info("Relationship analysis requires at least two numeric columns.")
    else:
        relationship_controls = st.columns(2)
        method = relationship_controls[0].selectbox(
            "Correlation method",
            options=["pearson", "spearman", "kendall"],
            key="correlation_method",
        )
        minimum_strength = relationship_controls[1].slider(
            "Minimum absolute correlation",
            0.0,
            1.0,
            0.2,
            0.05,
            key="minimum_correlation",
        )

        correlation = correlation_matrix(filtered_df, numeric_columns, method)
        st.plotly_chart(correlation_heatmap(correlation), use_container_width=True)

        strongest = strongest_correlations(
            correlation,
            limit=15,
            minimum_strength=minimum_strength,
        )
        st.markdown("### Strongest relationships")
        if strongest.empty:
            st.info("No relationships meet the selected threshold.")
        else:
            st.dataframe(strongest, use_container_width=True, hide_index=True)

        st.markdown("### Scatter explorer")
        scatter_controls = st.columns(3)
        x_column = scatter_controls[0].selectbox(
            "X-axis",
            options=numeric_columns,
            key="scatter_x",
        )
        y_options = [column for column in numeric_columns if column != x_column]
        y_column = scatter_controls[1].selectbox(
            "Y-axis",
            options=y_options,
            key="scatter_y",
        )
        color_options = ["None"] + filtered_types["categorical"] + filtered_types["boolean"]
        color_column = scatter_controls[2].selectbox(
            "Color",
            options=color_options,
            key="scatter_color",
        )
        st.plotly_chart(
            scatter_chart(
                filtered_df,
                x_column,
                y_column,
                None if color_column == "None" else color_column,
            ),
            use_container_width=True,
        )

with builder_tab:
    st.markdown("### Build a custom chart")
    all_columns = list(filtered_df.columns)
    numeric_columns = filtered_types["numeric"]
    category_columns = filtered_types["categorical"] + filtered_types["boolean"]

    builder_controls = st.columns(3)
    chart_type = builder_controls[0].selectbox(
        "Chart type",
        options=["Bar", "Line", "Scatter", "Histogram", "Box", "Pie"],
        key="builder_chart_type",
    )
    x_column = builder_controls[1].selectbox(
        "X-axis",
        options=all_columns,
        key="builder_x",
    )
    y_options = ["None"] + numeric_columns
    y_column = builder_controls[2].selectbox(
        "Y-axis",
        options=y_options,
        key="builder_y",
    )

    extra_controls = st.columns(3)
    color_options = ["None"] + category_columns
    color_column = extra_controls[0].selectbox(
        "Color/group",
        options=color_options,
        key="builder_color",
    )
    aggregation = extra_controls[1].selectbox(
        "Aggregation",
        options=["None", "Mean", "Median", "Sum", "Count", "Min", "Max"],
        key="builder_aggregation",
    )
    top_n = extra_controls[2].slider(
        "Top groups",
        5,
        50,
        20,
        key="builder_top_n",
    )

    selected_y = None if y_column == "None" else y_column
    selected_color = None if color_column == "None" else color_column

    chart_requires_y = chart_type in {"Line", "Scatter"}
    if chart_requires_y and selected_y is None:
        st.info(f"{chart_type} charts require a numeric Y-axis.")
    else:
        try:
            figure = custom_chart(
                filtered_df,
                chart_type,
                x_column,
                selected_y,
                selected_color,
                aggregation,
                top_n,
            )
            figure.update_layout(title=f"{chart_type}: {x_column}")
            st.plotly_chart(figure, use_container_width=True)
        except (TypeError, ValueError, KeyError) as error:
            st.error(f"Unable to build this chart: {error}")

st.divider()
st.markdown("## Export filtered data")
filename = str(st.session_state.get("analytics_filename", "dataset"))
base_name = filename.rsplit(".", 1)[0]
st.download_button(
    "Download filtered CSV",
    data=filtered_df.to_csv(index=False).encode("utf-8"),
    file_name=f"{base_name}_filtered.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption("Version 2: filter → summarize → visualize → compare → export.")

st.divider()

bottom_back, bottom_next = st.columns(2)

with bottom_back:
    if st.button(
        "← Back to Prepare",
        key="explore_bottom_back",
        use_container_width=True,
    ):
        st.switch_page("pages/1_Prepare.py")

with bottom_next:
    if st.button(
        "Continue to Analyze →",
        key="explore_bottom_next",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/3_Analyze.py")
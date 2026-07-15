from __future__ import annotations

import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from src.ai_context import build_ai_context, context_to_json
from src.ai_service import AIServiceError, generate_ai_response
from src.charts import custom_chart
from src.dashboard import (
    add_widget,
    calculate_kpi,
    create_widget,
    dashboard_from_json,
    dashboard_to_json,
    duplicate_widget,
    move_widget,
    refresh_kpi_widgets,
    remove_widget,
    update_widget,
)
from src.dashboard_recommendation import (
    build_ai_dashboard_prompt,
    build_recommended_dashboard,
    split_ai_dashboard_text,
)
from src.profiling import detect_column_types
from src.state import get_active_dataset, initialize_state

st.set_page_config(
    page_title="Dashboard Studio · Analytics Copilot",
    page_icon="✦",
    layout="wide",
)

apply_app_styles()
initialize_state()
render_workflow_navigation(active_step=6)

st.title("Dashboard Studio")
st.caption("Generate, edit, save, and reuse stakeholder dashboards.")

df = get_active_dataset()

if df is None:
    st.warning("No dataset is loaded.")
    if st.button("← Return to Import"):
        st.switch_page("app.py")
    st.stop()

try:
    api_key = str(st.secrets["GEMINI_API_KEY"])
except Exception:
    api_key = ""

st.session_state.setdefault("analytics_dashboard_title", "Executive Dashboard")
st.session_state.setdefault("analytics_dashboard_widgets", [])
st.session_state.setdefault("analytics_saved_dashboards", {})

column_types = detect_column_types(df)
numeric_columns = column_types.get("numeric", [])
category_columns = (
    column_types.get("categorical", [])
    + column_types.get("boolean", [])
)
all_columns = list(df.columns)

dashboard_title = st.text_input(
    "Dashboard title",
    value=st.session_state["analytics_dashboard_title"],
)
st.session_state["analytics_dashboard_title"] = dashboard_title

workspace_options = [
    "AI recommendation",
    "Add widgets",
    "Preview and edit",
    "Save and load",
]

st.session_state.setdefault("dashboard_workspace", "AI recommendation")

selected_workspace = st.radio(
    "Dashboard workspace",
    workspace_options,
    index=workspace_options.index(st.session_state["dashboard_workspace"]),
    horizontal=True,
    label_visibility="collapsed",
)

st.session_state["dashboard_workspace"] = selected_workspace

if selected_workspace == "AI recommendation":
    st.markdown("## AI dashboard recommendation")
    st.caption(
        "The AI creates a dashboard specification from computed analysis. "
        "You can edit every widget afterward."
    )

    optional_target = st.selectbox(
        "Optional target",
        options=["None"] + numeric_columns,
        key="dashboard_ai_target",
    )
    target_column = None if optional_target == "None" else optional_target

    if st.button(
        "Generate recommended dashboard",
        type="primary",
        use_container_width=True,
    ):
        if not api_key:
            st.error("Gemini API key was not found in .streamlit/secrets.toml.")
        else:
            context = build_ai_context(
                df,
                filename=st.session_state.get("analytics_filename"),
                target_column=target_column,
            )

            ai_reason = ""
            ai_insight = ""

            try:
                with st.spinner("Designing the recommended dashboard..."):
                    prompt = build_ai_dashboard_prompt(
                        context_to_json(context),
                        target_column,
                    )
                    response = generate_ai_response(
                        api_key=api_key,
                        prompt=prompt,
                        temperature=0.1,
                        max_output_tokens=700,
                    )
                    ai_reason, ai_insight = split_ai_dashboard_text(response)

            except AIServiceError as exc:
                st.warning(
                    f"AI explanation was unavailable: {exc}. "
                    "A complete dashboard will still be created."
                )

            recommendation = build_recommended_dashboard(
                df,
                column_types,
                ai_reason=ai_reason,
                ai_insight=ai_insight,
                target_column=target_column,
            )

            st.session_state["analytics_dashboard_title"] = recommendation["title"]
            st.session_state["analytics_dashboard_widgets"] = refresh_kpi_widgets(
                df,
                recommendation["widgets"],
            )
            st.session_state["analytics_dashboard_reason"] = recommendation["reason"]
            st.session_state["dashboard_workspace"] = "Preview and edit"
            st.success("Dashboard created.")
            st.rerun()

    reason = st.session_state.get("analytics_dashboard_reason")
    if reason:
        st.info(reason)

elif selected_workspace == "Add widgets":
    st.markdown("## Add a widget")

    widget_type = st.selectbox(
        "Widget type",
        ["KPI", "Chart", "AI Insight", "Text"],
    )

    if widget_type == "KPI":
        kpi_title = st.text_input("KPI title", value="Key Metric")
        kpi_column = st.selectbox("Column", all_columns)
        kpi_aggregation = st.selectbox(
            "Calculation",
            ["count", "unique", "sum", "mean", "median", "min", "max"],
        )
        prefix = st.text_input("Prefix", value="")
        suffix = st.text_input("Suffix", value="")

        if st.button("Add KPI", type="primary", use_container_width=True):
            widget = create_widget(
                "kpi",
                title=kpi_title,
                column=kpi_column,
                aggregation=kpi_aggregation,
                value=calculate_kpi(df, kpi_column, kpi_aggregation),
                prefix=prefix,
                suffix=suffix,
            )
            st.session_state["analytics_dashboard_widgets"] = add_widget(
                st.session_state["analytics_dashboard_widgets"],
                widget,
            )
            st.success("KPI added.")

    elif widget_type == "Chart":
        chart_title = st.text_input("Chart title", value="Dashboard Chart")
        chart_type = st.selectbox(
            "Chart type",
            ["Bar", "Line", "Scatter", "Box", "Pie", "Histogram"],
        )
        x_column = st.selectbox("X column", all_columns)
        y_selection = st.selectbox("Y column", ["None"] + numeric_columns)
        y_column = None if y_selection == "None" else y_selection
        color_selection = st.selectbox("Color/group", ["None"] + category_columns)
        color_column = None if color_selection == "None" else color_selection
        aggregation = st.selectbox(
            "Aggregation",
            ["None", "Sum", "Mean", "Median", "Min", "Max", "Count"],
        )
        top_n = st.slider("Top N", 5, 50, 20)

        if st.button("Add chart", type="primary", use_container_width=True):
            widget = create_widget(
                "chart",
                title=chart_title,
                chart_type=chart_type,
                x_column=x_column,
                y_column=y_column,
                color_column=color_column,
                aggregation=aggregation,
                top_n=top_n,
            )
            st.session_state["analytics_dashboard_widgets"] = add_widget(
                st.session_state["analytics_dashboard_widgets"],
                widget,
            )
            st.success("Chart added.")

    else:
        default_text = (
            st.session_state.get("analytics_ai_report", "")[:700]
            if widget_type == "AI Insight"
            else ""
        )
        title = st.text_input(
            "Title",
            value="AI Insight" if widget_type == "AI Insight" else "Notes",
        )
        text = st.text_area("Text", value=default_text, height=180)

        if st.button("Add widget", type="primary", use_container_width=True):
            if not text.strip():
                st.error("Enter text first.")
            else:
                widget = create_widget(
                    "insight" if widget_type == "AI Insight" else "text",
                    title=title,
                    text=text.strip(),
                )
                st.session_state["analytics_dashboard_widgets"] = add_widget(
                    st.session_state["analytics_dashboard_widgets"],
                    widget,
                )
                st.success("Widget added.")

elif selected_workspace == "Preview and edit":
    widgets = st.session_state["analytics_dashboard_widgets"]

    toolbar_left, toolbar_right = st.columns(2)

    with toolbar_left:
        if st.button("Refresh KPI values", use_container_width=True):
            st.session_state["analytics_dashboard_widgets"] = refresh_kpi_widgets(
                df,
                widgets,
            )
            st.rerun()

    with toolbar_right:
        if st.button("Clear dashboard", use_container_width=True):
            st.session_state["analytics_dashboard_widgets"] = []
            st.rerun()

    st.markdown(f"## {dashboard_title}")

    if not widgets:
        st.info("Generate a recommendation or add widgets.")
    else:
        for index, widget in enumerate(widgets):
            config = widget.get("config", {})
            widget_id = str(widget.get("id"))
            widget_type = widget.get("type")

            with st.container(border=True):
                title_col, up_col, down_col, copy_col, delete_col = st.columns(
                    [0.58, 0.105, 0.105, 0.105, 0.105]
                )

                with title_col:
                    st.markdown(f"### {widget.get('title', 'Widget')}")

                with up_col:
                    if st.button("↑", key=f"up_{widget_id}", disabled=index == 0):
                        st.session_state["analytics_dashboard_widgets"] = move_widget(
                            widgets, widget_id, "up"
                        )
                        st.rerun()

                with down_col:
                    if st.button(
                        "↓",
                        key=f"down_{widget_id}",
                        disabled=index == len(widgets) - 1,
                    ):
                        st.session_state["analytics_dashboard_widgets"] = move_widget(
                            widgets, widget_id, "down"
                        )
                        st.rerun()

                with copy_col:
                    if st.button("⧉", key=f"copy_{widget_id}"):
                        st.session_state["analytics_dashboard_widgets"] = duplicate_widget(
                            widgets, widget_id
                        )
                        st.rerun()

                with delete_col:
                    if st.button("✕", key=f"remove_{widget_id}"):
                        st.session_state["analytics_dashboard_widgets"] = remove_widget(
                            widgets, widget_id
                        )
                        st.rerun()

                with st.expander("Edit widget"):
                    edited_title = st.text_input(
                        "Title",
                        value=str(widget.get("title", "Widget")),
                        key=f"title_{widget_id}",
                    )

                    config_updates = {}

                    if widget_type in {"insight", "text"}:
                        config_updates["text"] = st.text_area(
                            "Text",
                            value=str(config.get("text", "")),
                            key=f"text_{widget_id}",
                        )

                    if widget_type == "kpi":
                        config_updates["prefix"] = st.text_input(
                            "Prefix",
                            value=str(config.get("prefix", "")),
                            key=f"prefix_{widget_id}",
                        )
                        config_updates["suffix"] = st.text_input(
                            "Suffix",
                            value=str(config.get("suffix", "")),
                            key=f"suffix_{widget_id}",
                        )

                    if st.button("Save changes", key=f"save_{widget_id}"):
                        st.session_state["analytics_dashboard_widgets"] = update_widget(
                            widgets,
                            widget_id,
                            title=edited_title,
                            config_updates=config_updates,
                        )
                        st.rerun()

                if widget_type == "kpi":
                    value = config.get("value")
                    display = "—" if value is None else f"{value:,.2f}"
                    st.metric(
                        widget.get("title", "KPI"),
                        f"{config.get('prefix', '')}{display}{config.get('suffix', '')}",
                    )

                elif widget_type == "chart":
                    try:
                        figure = custom_chart(
                            df,
                            chart_type=str(config.get("chart_type", "Bar")),
                            x_column=str(config.get("x_column")),
                            y_column=config.get("y_column"),
                            color_column=config.get("color_column"),
                            aggregation=str(config.get("aggregation", "None")),
                            top_n=int(config.get("top_n", 20)),
                        )
                        figure.update_layout(title=widget.get("title", "Chart"))
                        st.plotly_chart(figure, use_container_width=True)
                    except Exception as exc:
                        st.error(f"Chart could not be rendered: {exc}")

                else:
                    st.write(config.get("text", ""))

elif selected_workspace == "Save and load":
    st.markdown("## Save dashboard")

    save_name = st.text_input(
        "Saved dashboard name",
        value=dashboard_title,
    )

    if st.button("Save current dashboard", use_container_width=True):
        st.session_state["analytics_saved_dashboards"][save_name] = {
            "title": dashboard_title,
            "widgets": st.session_state["analytics_dashboard_widgets"],
        }
        st.success(f"Saved {save_name}.")

    saved_names = list(st.session_state["analytics_saved_dashboards"].keys())

    if saved_names:
        selected_saved = st.selectbox("Saved dashboards", saved_names)

        load_col, delete_col = st.columns(2)

        with load_col:
            if st.button("Load selected", use_container_width=True):
                saved = st.session_state["analytics_saved_dashboards"][selected_saved]
                st.session_state["analytics_dashboard_title"] = saved["title"]
                st.session_state["analytics_dashboard_widgets"] = saved["widgets"]
                st.rerun()

        with delete_col:
            if st.button("Delete selected", use_container_width=True):
                del st.session_state["analytics_saved_dashboards"][selected_saved]
                st.rerun()

    st.markdown("### Import dashboard")
    imported = st.file_uploader(
        "Upload dashboard JSON",
        type=["json"],
        label_visibility="collapsed",
    )

    if imported is not None and st.button("Import dashboard", use_container_width=True):
        try:
            imported_title, imported_widgets = dashboard_from_json(imported.getvalue())
            st.session_state["analytics_dashboard_title"] = imported_title
            st.session_state["analytics_dashboard_widgets"] = refresh_kpi_widgets(
                df,
                imported_widgets,
            )
            st.success("Dashboard imported.")
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(str(exc))

    st.markdown("### Export dashboard")
    dashboard_json = dashboard_to_json(
        dashboard_title,
        st.session_state["analytics_dashboard_widgets"],
    )
    st.download_button(
        "Download dashboard JSON",
        data=dashboard_json.encode("utf-8"),
        file_name="dashboard_layout.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()

left, right = st.columns(2)

with left:
    if st.button("← Back to AI Analyst", use_container_width=True):
        st.switch_page("pages/4_AI_Copilot.py")

with right:
    if st.button(
        "Continue to Report Builder →",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/6_Report.py")

from __future__ import annotations

import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from src.ai_service import AIServiceError, generate_ai_response
from src.report_exports import build_pdf_export, build_powerpoint_export
from src.reporting import (
    REPORT_SECTIONS,
    build_markdown_report,
    build_report_data,
    build_report_prompt,
    markdown_to_html,
    report_to_json,
)
from src.state import (
    HISTORY_KEY,
    RECIPE_KEY,
    get_active_dataset,
    initialize_state,
)

st.set_page_config(
    page_title="Report Builder · Analytics Copilot",
    page_icon="✦",
    layout="wide",
)

apply_app_styles()
initialize_state()
render_workflow_navigation(active_step=7)

st.title("Report Builder")
st.caption("Assemble and export a stakeholder-ready analytics report.")

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

settings_tab, preview_tab, export_tab = st.tabs(
    ["Configure", "Preview", "Export"]
)

with settings_tab:
    st.markdown("## Report settings")

    report_title = st.text_input(
        "Report title",
        value=st.session_state.get(
            "analytics_report_title",
            "Executive Analytics Report",
        ),
    )

    left, right = st.columns(2)

    with left:
        audience = st.selectbox(
            "Audience",
            ["Executive", "Manager", "Technical", "Client"],
        )

    with right:
        detail_level = st.selectbox(
            "Detail level",
            ["Short", "Standard", "Detailed"],
            index=1,
        )

    selected_sections = st.multiselect(
        "Sections",
        options=REPORT_SECTIONS,
        default=REPORT_SECTIONS,
    )

    use_ai_narrative = st.checkbox(
        "Generate AI narrative",
        value=True,
        disabled=not bool(api_key),
    )

    if not api_key:
        st.caption(
            "Gemini key not found. The report will still be generated with "
            "deterministic text."
        )

    if st.button(
        "Generate report",
        type="primary",
        use_container_width=True,
    ):
        report_data = build_report_data(
            df,
            filename=st.session_state.get("analytics_filename"),
            title=report_title,
            audience=audience,
            detail_level=detail_level,
            selected_sections=selected_sections,
            cleaning_history=st.session_state.get(HISTORY_KEY, []),
            cleaning_recipe=st.session_state.get(RECIPE_KEY, {}),
            ai_report=st.session_state.get("analytics_ai_report", ""),
            dashboard_title=st.session_state.get(
                "analytics_dashboard_title",
                "Dashboard",
            ),
            dashboard_widgets=st.session_state.get(
                "analytics_dashboard_widgets",
                [],
            ),
        )

        narrative = ""

        if use_ai_narrative and api_key:
            try:
                with st.spinner("Writing the report narrative..."):
                    narrative = generate_ai_response(
                        api_key=api_key,
                        prompt=build_report_prompt(report_data),
                        temperature=0.1,
                        max_output_tokens=1800,
                    )
            except AIServiceError as exc:
                st.warning(
                    f"AI narrative was unavailable: {exc}. "
                    "The report was generated without it."
                )

        markdown_report = build_markdown_report(
            report_data,
            narrative=narrative,
        )

        st.session_state["analytics_report_title"] = report_title
        st.session_state["analytics_report_data"] = report_data
        st.session_state["analytics_report_narrative"] = narrative
        st.session_state["analytics_report_markdown"] = markdown_report
        st.success("Report generated.")

with preview_tab:
    markdown_report = st.session_state.get("analytics_report_markdown", "")

    if not markdown_report:
        st.info("Generate the report from the Configure tab first.")
    else:
        st.markdown(markdown_report)

with export_tab:
    markdown_report = st.session_state.get("analytics_report_markdown", "")
    report_data = st.session_state.get("analytics_report_data")
    narrative = st.session_state.get("analytics_report_narrative", "")
    report_title = st.session_state.get(
        "analytics_report_title",
        "Analytics Report",
    )

    if not markdown_report or not report_data:
        st.info("Generate the report before exporting.")
    else:
        html_report = markdown_to_html(markdown_report, report_title)
        json_report = report_to_json(report_data, narrative)

        st.download_button(
            "Download Markdown",
            data=markdown_report.encode("utf-8"),
            file_name="analytics_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

        st.download_button(
            "Download HTML",
            data=html_report.encode("utf-8"),
            file_name="analytics_report.html",
            mime="text/html",
            use_container_width=True,
        )

        st.download_button(
            "Download report package",
            data=json_report.encode("utf-8"),
            file_name="analytics_report.json",
            mime="application/json",
            use_container_width=True,
        )

        try:
            pdf_report = build_pdf_export(
                report_data,
                df,
                narrative=narrative,
            )
            st.download_button(
                "Download PDF",
                data=pdf_report,
                file_name="analytics_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"PDF export could not be created: {exc}")

        try:
            powerpoint_report = build_powerpoint_export(
                report_data,
                df,
                narrative=narrative,
            )
            st.download_button(
                "Download PowerPoint",
                data=powerpoint_report,
                file_name="analytics_report.pptx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"PowerPoint export could not be created: {exc}")

st.divider()

left, right = st.columns(2)

with left:
    if st.button("← Back to Dashboard Studio", use_container_width=True):
        st.switch_page("pages/5_Dashboard.py")

with right:
    if st.button("Return to Import", use_container_width=True):
        st.switch_page("app.py")

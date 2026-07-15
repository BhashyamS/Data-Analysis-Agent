from __future__ import annotations

from io import BytesIO

import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from src.loader import UnsupportedFileTypeError, load_table, make_unique_column_names
from src.profiling import detect_column_types, profile_dataset
from src.state import (
    FILE_HASH_KEY,
    clear_dataset,
    file_fingerprint,
    get_dataset,
    has_dataset,
    initialize_state,
    store_dataset,
)

st.set_page_config(
    page_title="Analytics Copilot",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_app_styles()
initialize_state()


def workflow_card(
    number: str,
    title: str,
    description: str,
    status: str | None = None,
) -> None:
    """Render a workflow card without importing components.cards."""
    status_html = (
        f'<div class="status-ready" style="margin-top:.75rem;">● {status}</div>'
        if status
        else ""
    )

    st.markdown(
        f"""
        <div class="workflow-card">
            <div class="workflow-number">{number}</div>
            <div class="workflow-title">{title}</div>
            <div class="workflow-copy">{description}</div>
            {status_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown("## ✦ Analytics Copilot")
    st.caption("End-to-end analytics workflow")
    st.divider()

    if has_dataset():
        st.success("Dataset loaded")
        st.caption(st.session_state.get("analytics_filename"))

        if st.button("Clear dataset", use_container_width=True):
            clear_dataset()
            st.rerun()
    else:
        st.info("Upload a dataset to begin.")

    st.divider()
    st.caption("Version 2 · Explore")


render_workflow_navigation(active_step=1)

st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">Analytics workflow, simplified</div>
      <h1>Analytics Copilot</h1>
      <p>
        Upload messy data, prepare it, and explore it through a transparent
        analytics workflow.
      </p>
    </section>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.35, 0.65], gap="large")

with left:
    st.subheader("Import a dataset")

    uploaded = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"],
        help="Supported formats: CSV, XLSX, XLS.",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        fingerprint = file_fingerprint(file_bytes)

        if fingerprint != st.session_state.get(FILE_HASH_KEY):
            try:
                dataframe = load_table(BytesIO(file_bytes), uploaded.name)
                dataframe = make_unique_column_names(dataframe)

                if dataframe.empty and len(dataframe.columns) == 0:
                    st.error("The uploaded file does not contain a readable table.")
                else:
                    store_dataset(dataframe, uploaded.name, fingerprint)
                    st.success(f"Loaded {uploaded.name}")

            except (UnsupportedFileTypeError, ValueError) as exc:
                st.error(str(exc))

            except Exception as exc:
                st.error(f"The file could not be read: {exc}")

    df = get_dataset()

    if df is not None:
        profile = profile_dataset(df)
        types = detect_column_types(df)

        st.markdown("### Import summary")

        metric_columns = st.columns(4)
        metric_columns[0].metric("Rows", f"{profile.rows:,}")
        metric_columns[1].metric("Columns", profile.columns)
        metric_columns[2].metric("Missing", f"{profile.missing_percentage:.1f}%")
        metric_columns[3].metric("Duplicates", f"{profile.duplicate_rows:,}")

        st.dataframe(df.head(12), use_container_width=True, hide_index=True)

        st.caption(
            f"Detected {len(types['numeric'])} numeric, "
            f"{len(types['categorical'])} categorical, "
            f"{len(types['datetime'])} datetime, and "
            f"{len(types['identifier'])} identifier columns."
        )

        action_columns = st.columns(2)

        with action_columns[0]:
            if st.button(
                "Continue to Prepare →",
                type="primary",
                use_container_width=True,
            ):
                st.switch_page("pages/1_Prepare.py")

        with action_columns[1]:
            if st.button("Open Explore →", use_container_width=True):
                st.switch_page("pages/2_Explore.py")


with right:
    st.markdown("### Project status")

    st.markdown(
        """
        <div class="info-card">
          <div class="status-ready">● Version 1 complete</div>
          <p class="small-muted">
            Upload, profile, clean, validate, document, and export data.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(" ")

    st.markdown(
        """
        <div class="info-card">
          <div class="status-ready">● Version 2 available</div>
          <p class="small-muted">
            Filter data, review summaries, explore relationships, and build charts.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("## Product workflow")

cols = st.columns(3)

with cols[0]:
    workflow_card(
        "01",
        "Prepare",
        "Profile, clean, validate, and document data transformations.",
        "Complete",
    )

with cols[1]:
    workflow_card(
        "02",
        "Explore",
        "Understand distributions, categories, trends, and relationships.",
        "Available",
    )

with cols[2]:
    workflow_card(
        "03",
        "Analyze",
        "Discover drivers, compare segments, and investigate outcomes.",
    )

cols = st.columns(3)

with cols[0]:
    workflow_card(
        "04",
        "Dashboard",
        "Assemble stakeholder-ready visual narratives.",
    )

with cols[1]:
    workflow_card(
        "05",
        "AI Copilot",
        "Ask grounded questions and generate evidence-backed findings.",
    )

with cols[2]:
    workflow_card(
        "06",
        "Report",
        "Export methods, visuals, findings, and recommendations.",
    )
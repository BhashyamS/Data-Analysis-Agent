from __future__ import annotations

import os

import streamlit as st

from components.navigation import render_workflow_navigation
from components.styles import apply_app_styles
from src.ai_context import build_ai_context, context_to_json
from src.ai_service import AIServiceError, DEFAULT_MODEL, generate_ai_response
from src.profiling import detect_column_types
from src.state import get_active_dataset, initialize_state

st.set_page_config(
    page_title="AI Analyst · Analytics Copilot",
    page_icon="✦",
    layout="wide",
)

apply_app_styles()
initialize_state()
render_workflow_navigation(active_step=5)

st.title("AI Analyst")
st.caption("Explain computed analysis with AI. Raw dataset rows are not sent.")

df = get_active_dataset()

if df is None:
    st.warning("No dataset is loaded.")
    if st.button("← Return to Import"):
        st.switch_page("app.py")
    st.stop()

column_types = detect_column_types(df)
numeric_columns = column_types.get("numeric", [])

secret_key = ""
try:
    secret_key = str(st.secrets.get("GEMINI_API_KEY", ""))
except Exception:
    secret_key = ""

default_key = secret_key or os.getenv("GEMINI_API_KEY", "")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error(
        "Gemini API key not found. Please add GEMINI_API_KEY to .streamlit/secrets.toml"
    )
    st.stop()

model = "gemini-2.5-flash"

selected_target = st.selectbox(
    "Optional target",
    ["None"] + numeric_columns,
)

target_column = (
    None if selected_target == "None" else selected_target
)

target_column = None if selected_target == "None" else selected_target


context = build_ai_context(
    df,
    filename=st.session_state.get("analytics_filename"),
    target_column=target_column,
)
context_json = context_to_json(context)

st.info(
    "The AI only sees computed summaries. Review all recommendations before using them."
)

metrics = st.columns(4)
metrics[0].metric("Rows", f"{len(df):,}")
metrics[1].metric("Columns", f"{len(df.columns):,}")
metrics[2].metric("Numeric", f"{len(numeric_columns):,}")
metrics[3].metric(
    "Categories",
    f"{len(column_types.get('categorical', [])):,}",
)

report_tab, chat_tab, evidence_tab = st.tabs(
    ["Generate", "Ask AI", "Evidence"]
)

REPORT_TYPES = {
    "Executive Summary": """
Create a concise executive summary with:
- dataset overview
- three most important findings
- two risks
- three recommended actions
""",
    "Business Insights": """
Create a business insight report with:
- strongest relationships
- best and worst segments
- unusual patterns
- opportunities worth investigating
""",
    "Data Quality Review": """
Create a data quality review with:
- missing data
- duplicates
- weak or unusable fields
- possible risks
- cleaning recommendations
""",
    "Risk Assessment": """
Create a risk assessment with:
- outliers
- weak evidence
- small samples
- possible bias
- misleading relationships
""",
    "Recommendations": """
Create practical recommendations with:
- next analyses
- useful KPIs
- needed data
- dashboard ideas
- decision risks
""",
    "Full Report": """
Create a full stakeholder report with:
1. Executive summary
2. Data quality
3. Key findings
4. Target analysis
5. Risks
6. Recommendations
7. Questions requiring more data
""",
}


def make_prompt(instruction: str) -> str:
    return f"""
You are a careful senior data analyst.

Use only the structured evidence below.
Do not invent facts, causes, business context, or column meanings.
Do not claim causation from correlation.
Use specific computed values where useful.
When evidence is insufficient, say so.

TASK:
{instruction}

STRUCTURED EVIDENCE:
{context_json}
""".strip()


with report_tab:
    st.markdown("## Generate analysis")

    columns = st.columns(3)
    selected_report = None

    for index, report_name in enumerate(REPORT_TYPES):
        with columns[index % 3]:
            if st.button(report_name, use_container_width=True):
                selected_report = report_name

    if selected_report:
        if not api_key.strip():
            st.error("Enter a Gemini API key in the sidebar.")
        else:
            try:
                with st.spinner(f"Generating {selected_report.lower()}..."):
                    result = generate_ai_response(
                        api_key=api_key,
                        model=model,
                        prompt=make_prompt(REPORT_TYPES[selected_report]),
                    )
                st.session_state["analytics_ai_report"] = result
                st.session_state["analytics_ai_report_type"] = selected_report
            except AIServiceError as exc:
                st.error(str(exc))

    saved_report = st.session_state.get("analytics_ai_report")
    saved_type = st.session_state.get("analytics_ai_report_type", "AI Report")

    if saved_report:
        st.markdown(f"### {saved_type}")
        st.markdown(saved_report)

        st.download_button(
            "Download report",
            data=saved_report.encode("utf-8"),
            file_name=f"{str(saved_type).lower().replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    else:
        st.caption("Choose a report type above.")

with chat_tab:
    st.markdown("## Ask the analyst")

    st.session_state.setdefault("analytics_ai_messages", [])

    for message in st.session_state["analytics_ai_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Ask about trends, drivers, segments, quality, or anomalies"
    )

    if question:
        st.session_state["analytics_ai_messages"].append(
            {"role": "user", "content": question}
        )

        with st.chat_message("user"):
            st.markdown(question)

        if not api_key.strip():
            answer = "Enter a Gemini API key in the sidebar."
        else:
            history = st.session_state["analytics_ai_messages"][-8:]
            conversation = "\n".join(
                f"{item['role'].upper()}: {item['content']}"
                for item in history
            )

            prompt = f"""
You are a careful data analyst.

Use only the structured evidence.
Do not invent unavailable calculations.
Do not claim causation.
If the evidence cannot answer the question, say what is missing.
Keep the answer practical and clear.

CONVERSATION:
{conversation}

STRUCTURED EVIDENCE:
{context_json}
""".strip()

            try:
                with st.spinner("Reviewing the evidence..."):
                    answer = generate_ai_response(
                        api_key=api_key,
                        model=model,
                        prompt=prompt,
                        max_output_tokens=1800,
                    )
            except AIServiceError as exc:
                answer = str(exc)

        st.session_state["analytics_ai_messages"].append(
            {"role": "assistant", "content": answer}
        )

        with st.chat_message("assistant"):
            st.markdown(answer)

    if st.session_state["analytics_ai_messages"]:
        if st.button("Clear conversation"):
            st.session_state["analytics_ai_messages"] = []
            st.rerun()

with evidence_tab:
    st.markdown("## Evidence used")
    st.caption("This is the exact computed information available to the AI.")
    st.json(context)

st.divider()

left, right = st.columns(2)

with left:
    if st.button("← Back to Analyze", use_container_width=True):
        st.switch_page("pages/3_Analyze.py")

with right:
    if st.button(
        "Continue to Dashboard Studio →",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/5_Dashboard.py")

import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

st.set_page_config(page_title="AI Data-to-Insight Agent", page_icon="📊", layout="wide")

st.title("📊 AI Data-to-Insight Agent")
st.caption(
    "Upload CSV/Excel data, generate an interactive EDA dashboard, detect risks/anomalies, "
    "and ask an AI analyst chatbot grounded in the dashboard outputs."
)

# -----------------------------
# Helpers
# -----------------------------
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().replace(" ", "_").lower() for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def load_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Unsupported file type")

def detect_columns(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    date_cols = []
    for col in df.columns:
        if col not in numeric_cols:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.75:
                date_cols.append(col)
    return numeric_cols, categorical_cols, date_cols

def build_profile(df: pd.DataFrame, numeric_cols, categorical_cols, date_cols):
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values_total": int(df.isna().sum().sum()),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "date_columns": date_cols,
    }

def find_anomalies(df: pd.DataFrame, numeric_cols, threshold=3.0):
    results = []
    for col in numeric_cols[:12]:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 10 or series.std() == 0:
            continue
        z = ((series - series.mean()) / series.std()).abs()
        count = int((z > threshold).sum())
        if count > 0:
            results.append(
                {
                    "column": col,
                    "anomaly_count": count,
                    "anomaly_rate_%": round((count / len(series)) * 100, 2),
                    "max_value": float(series.max()),
                    "min_value": float(series.min()),
                }
            )
    return pd.DataFrame(results)

def get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", None)
    except Exception:
        return os.getenv("GEMINI_API_KEY")

def generate_ai_text(prompt: str):
    api_key = get_api_key()
    if not api_key:
        st.error("Gemini API key not found. Add GEMINI_API_KEY in Streamlit secrets.")
        st.stop()
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text

def safe_mean(df: pd.DataFrame, col: str):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").mean()
    return None

def pct_true(df: pd.DataFrame, col: str, true_value=1):
    if col in df.columns:
        s = df[col]
        if s.dtype == bool:
            return s.mean() * 100
        return (s == true_value).mean() * 100
    return None

def format_metric(value, suffix="", digits=2):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{digits}f}{suffix}"

def value_counts_summary(df: pd.DataFrame, col: str, top_n=10):
    if col not in df.columns:
        return pd.DataFrame()
    out = df[col].astype(str).value_counts(dropna=False).head(top_n).reset_index()
    out.columns = [col, "count"]
    out["percentage"] = (out["count"] / len(df) * 100).round(2)
    return out

def add_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    needed = {"daily_usage_hours", "screen_time_before_sleep", "night_usage"}
    if needed.issubset(df.columns):
        df["risk_score"] = (
            pd.to_numeric(df["daily_usage_hours"], errors="coerce").fillna(0) * 0.35
            + pd.to_numeric(df["screen_time_before_sleep"], errors="coerce").fillna(0) * 0.03
            + pd.to_numeric(df["night_usage"], errors="coerce").fillna(0) * 1.5
        )
        df["risk_category"] = pd.cut(
            df["risk_score"],
            bins=[-np.inf, 3, 6, np.inf],
            labels=["Low Risk", "Medium Risk", "High Risk"],
        )
    return df

def make_eda_context(profile, kpi_summary, chart_summaries, anomaly_df, missing_table):
    anomaly_summary = (
        anomaly_df.to_string(index=False) if not anomaly_df.empty else "No major z-score anomalies detected."
    )
    missing_summary = missing_table.head(10).to_string(index=False)
    return f"""
DATASET PROFILE:
{profile}

KPI SUMMARY:
{kpi_summary}

CHART / EDA SUMMARIES:
{chr(10).join(chart_summaries)}

ANOMALY SUMMARY:
{anomaly_summary}

DATA QUALITY SUMMARY:
{missing_summary}
"""

def make_report_prompt(eda_context: str):
    return f"""
You are a senior business data analyst.

Create an executive insight report using ONLY the EDA context below. The EDA context contains KPI metrics, chart summaries, data quality checks, and anomaly scans. Do not claim that you reviewed raw rows directly, and do not invent unsupported findings.

Return the answer in this exact format:
1. Executive Summary: 3-4 sentences.
2. Key Insights: 5 bullet points with business meaning.
3. Risks / Anomalies: 2-3 bullets.
4. Recommended Actions: 3 practical next steps.
5. Data Quality Notes: missing values, duplicates, or limitations.

EDA Context:
{eda_context}
"""

def make_chat_prompt(eda_context: str, user_question: str):
    return f"""
You are an AI analyst chatbot.

Answer the user's question using ONLY the EDA context below. This means your answer must come from KPI metrics, chart summaries, grouped tables, anomaly scans, or data quality checks. Do not use or imply access to raw dataset rows. If the context does not contain enough information, say what is missing and suggest which chart or metric should be added.

EDA Context:
{eda_context}

User Question:
{user_question}
"""

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("How it works")
    st.write("1. Upload a heavier CSV or Excel dataset")
    st.write("2. Apply filters to explore segments")
    st.write("3. App generates KPIs, charts, EDA summaries, and anomalies")
    st.write("4. Gemini answers only from those EDA outputs")
    st.divider()
    st.write("Best demo: use the 1M-row Gen Z social media usage dataset.")

uploaded_file = st.file_uploader("Upload a CSV or Excel dataset", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("Upload a dataset to begin. For the recruiter demo, use the heavier Gen Z social media usage dataset.")
    st.stop()

try:
    df = clean_column_names(load_file(uploaded_file))
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

df = add_risk_features(df)
numeric_cols, categorical_cols, date_cols = detect_columns(df)
profile = build_profile(df, numeric_cols, categorical_cols, date_cols)

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Dashboard Filters")
filtered_df = df.copy()
filterable_cols = [
    c for c in ["country", "gender", "primary_platform", "purpose", "addiction_level", "risk_category"]
    if c in filtered_df.columns
]

for col in filterable_cols:
    options = sorted(filtered_df[col].dropna().astype(str).unique().tolist())
    if len(options) <= 50:
        selected = st.sidebar.multiselect(
            col.replace("_", " ").title(),
            options,
            default=options,
        )
        filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)]

if filtered_df.empty:
    st.error("No records match the selected filters.")
    st.stop()

filtered_numeric_cols, filtered_categorical_cols, filtered_date_cols = detect_columns(filtered_df)
filtered_profile = build_profile(filtered_df, filtered_numeric_cols, filtered_categorical_cols, filtered_date_cols)
anomaly_df = find_anomalies(filtered_df, filtered_numeric_cols)

# -----------------------------
# Executive overview
# -----------------------------
st.subheader("1. Executive Dashboard")

avg_usage = safe_mean(filtered_df, "daily_usage_hours")
avg_mental = safe_mean(filtered_df, "mental_health_score")
avg_sleep_screen = safe_mean(filtered_df, "screen_time_before_sleep")
high_addiction_rate = None
if "addiction_level" in filtered_df.columns:
    high_addiction_rate = filtered_df["addiction_level"].astype(str).str.lower().eq("high").mean() * 100
night_usage_rate = pct_true(filtered_df, "night_usage", 1)
high_risk_rate = None
if "risk_category" in filtered_df.columns:
    high_risk_rate = filtered_df["risk_category"].astype(str).eq("High Risk").mean() * 100

kpi_cols = st.columns(7)
kpi_cols[0].metric("Records", f"{len(filtered_df):,}")
kpi_cols[1].metric("Columns", f"{filtered_df.shape[1]:,}")
kpi_cols[2].metric("Avg Daily Usage", format_metric(avg_usage, " hrs"))
kpi_cols[3].metric("Avg Mental Health", format_metric(avg_mental))
kpi_cols[4].metric("High Addiction", format_metric(high_addiction_rate, "%", 1))
kpi_cols[5].metric("Night Usage", format_metric(night_usage_rate, "%", 1))
kpi_cols[6].metric("High Risk", format_metric(high_risk_rate, "%", 1))

kpi_summary = f"""
Records after filters: {len(filtered_df):,}
Columns: {filtered_df.shape[1]}
Average daily usage hours: {format_metric(avg_usage, ' hrs')}
Average mental health score: {format_metric(avg_mental)}
Average screen time before sleep: {format_metric(avg_sleep_screen, ' minutes')}
High addiction rate: {format_metric(high_addiction_rate, '%', 1)}
Night usage rate: {format_metric(night_usage_rate, '%', 1)}
High calculated risk rate: {format_metric(high_risk_rate, '%', 1)}
Missing values: {int(filtered_df.isna().sum().sum())}
Duplicate rows: {int(filtered_df.duplicated().sum())}
"""

with st.expander("Dataset Preview"):
    st.dataframe(filtered_df.head(50), use_container_width=True)

with st.expander("Detected Column Types"):
    st.write("**Numeric:**", filtered_numeric_cols)
    st.write("**Categorical:**", filtered_categorical_cols)
    st.write("**Date-like:**", filtered_date_cols)

# -----------------------------
# Data quality
# -----------------------------
st.subheader("2. Data Quality & Profiling")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Missing Values", f"{int(filtered_df.isna().sum().sum()):,}")
q2.metric("Duplicate Rows", f"{int(filtered_df.duplicated().sum()):,}")
q3.metric("Numeric Columns", f"{len(filtered_numeric_cols):,}")
q4.metric("Categorical Columns", f"{len(filtered_categorical_cols):,}")

missing_table = (
    filtered_df.isna().sum().sort_values(ascending=False).reset_index()
)
missing_table.columns = ["column", "missing_values"]
missing_table["missing_%"] = (missing_table["missing_values"] / len(filtered_df) * 100).round(2)

with st.expander("Missing Values by Column"):
    st.dataframe(missing_table, use_container_width=True)

# -----------------------------
# EDA visual insights
# -----------------------------
st.subheader("3. Trend & Segment Dashboard")
st.caption("These charts generate the analysis layer that the AI report and chatbot use as context.")

chart_summaries = []

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Behavior Trends",
    "Risk & Addiction",
    "Platform Analysis",
    "Country / Purpose",
    "Generic Explorer",
])

with tab1:
    c1, c2 = st.columns(2)
    if {"daily_usage_hours", "mental_health_score"}.issubset(filtered_df.columns):
        temp = filtered_df.copy()
        max_usage = max(float(temp["daily_usage_hours"].max()), 10.0)
        bins = [0, 2, 4, 6, 8, 10, max_usage + 0.01]
        labels = ["0-2 hrs", "2-4 hrs", "4-6 hrs", "6-8 hrs", "8-10 hrs", "10+ hrs"]
        temp["usage_bucket"] = pd.cut(temp["daily_usage_hours"], bins=bins, labels=labels, include_lowest=True)
        usage_health = temp.groupby("usage_bucket", observed=False)["mental_health_score"].mean().reset_index()
        fig = px.line(
            usage_health,
            x="usage_bucket",
            y="mental_health_score",
            markers=True,
            title="Mental Health Score by Daily Usage Bucket",
        )
        c1.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("Mental health score by daily usage bucket:\n" + usage_health.to_string(index=False))

    if {"daily_usage_hours", "avg_session_minutes"}.issubset(filtered_df.columns):
        sample_df = filtered_df.sample(min(len(filtered_df), 8000), random_state=42) if len(filtered_df) > 8000 else filtered_df
        fig = px.scatter(
            sample_df,
            x="daily_usage_hours",
            y="avg_session_minutes",
            color="addiction_level" if "addiction_level" in sample_df.columns else None,
            opacity=0.45,
            title="Daily Usage vs Average Session Length",
        )
        c2.plotly_chart(fig, use_container_width=True)
        corr = sample_df[["daily_usage_hours", "avg_session_minutes"]].corr().iloc[0, 1]
        chart_summaries.append(f"Correlation between daily usage hours and average session minutes: {corr:.3f}")

with tab2:
    c1, c2 = st.columns(2)
    if {"addiction_level", "screen_time_before_sleep"}.issubset(filtered_df.columns):
        sleep_addiction = (
            filtered_df.groupby("addiction_level")["screen_time_before_sleep"]
            .mean()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig = px.bar(
            sleep_addiction,
            x="addiction_level",
            y="screen_time_before_sleep",
            text="screen_time_before_sleep",
            title="Avg Screen Time Before Sleep by Addiction Level",
        )
        fig.update_traces(texttemplate="%{text:.1f} min", textposition="outside")
        c1.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("Screen time before sleep by addiction level:\n" + sleep_addiction.to_string(index=False))

    if {"risk_category"}.issubset(filtered_df.columns):
        risk_counts = filtered_df["risk_category"].value_counts(normalize=True).mul(100).reset_index()
        risk_counts.columns = ["risk_category", "percentage"]
        fig = px.pie(
            risk_counts,
            names="risk_category",
            values="percentage",
            title="Calculated Risk Category Distribution",
            hole=0.45,
        )
        c2.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("Calculated risk category distribution:\n" + risk_counts.to_string(index=False))

with tab3:
    c1, c2 = st.columns(2)
    if {"primary_platform", "addiction_level"}.issubset(filtered_df.columns):
        platform_addiction = pd.crosstab(
            filtered_df["primary_platform"],
            filtered_df["addiction_level"],
            normalize="index",
        ).mul(100).round(2).reset_index()
        platform_addiction_melted = platform_addiction.melt(
            id_vars="primary_platform",
            var_name="addiction_level",
            value_name="percentage",
        )
        fig = px.bar(
            platform_addiction_melted,
            x="primary_platform",
            y="percentage",
            color="addiction_level",
            title="Addiction Level Distribution by Platform (%)",
            barmode="stack",
        )
        c1.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("Addiction level distribution by platform (%):\n" + platform_addiction.to_string(index=False))

    if {"primary_platform", "risk_category"}.issubset(filtered_df.columns):
        risk_platform = pd.crosstab(
            filtered_df["primary_platform"],
            filtered_df["risk_category"],
            normalize="index",
        ).mul(100).round(2).reset_index()
        risk_platform_melted = risk_platform.melt(
            id_vars="primary_platform",
            var_name="risk_category",
            value_name="percentage",
        )
        fig = px.bar(
            risk_platform_melted,
            x="primary_platform",
            y="percentage",
            color="risk_category",
            title="Calculated Risk Category by Platform (%)",
            barmode="stack",
        )
        c2.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("Calculated risk category by platform (%):\n" + risk_platform.to_string(index=False))

with tab4:
    c1, c2 = st.columns(2)
    if {"country", "addiction_level"}.issubset(filtered_df.columns):
        country_risk = (
            filtered_df.assign(high_addiction=filtered_df["addiction_level"].astype(str).str.lower().eq("high").astype(int))
            .groupby("country")["high_addiction"]
            .mean()
            .mul(100)
            .sort_values(ascending=False)
            .reset_index()
        )
        fig = px.bar(
            country_risk.head(15),
            x="country",
            y="high_addiction",
            text="high_addiction",
            title="High Addiction Rate by Country (%)",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        c1.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("High addiction rate by country (%):\n" + country_risk.head(15).to_string(index=False))

    if {"purpose", "daily_usage_hours"}.issubset(filtered_df.columns):
        purpose_usage = (
            filtered_df.groupby("purpose")["daily_usage_hours"]
            .mean()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig = px.bar(
            purpose_usage,
            x="purpose",
            y="daily_usage_hours",
            text="daily_usage_hours",
            title="Average Daily Usage by Purpose",
        )
        fig.update_traces(texttemplate="%{text:.2f} hrs", textposition="outside")
        c2.plotly_chart(fig, use_container_width=True)
        chart_summaries.append("Average daily usage by purpose:\n" + purpose_usage.to_string(index=False))

with tab5:
    st.write("Use this section for any uploaded dataset, even if it is not the Gen Z social media dataset.")
    selected_num = st.selectbox("Choose a numeric metric", filtered_numeric_cols) if filtered_numeric_cols else None
    selected_cat = st.selectbox("Choose a segment/category", filtered_categorical_cols) if filtered_categorical_cols else None

    g1, g2 = st.columns(2)
    with g1:
        if selected_num:
            fig = px.histogram(
                filtered_df,
                x=selected_num,
                nbins=40,
                title=f"Distribution of {selected_num}",
            )
            st.plotly_chart(fig, use_container_width=True)
            desc = filtered_df[selected_num].describe().round(2).to_string()
            chart_summaries.append(f"Distribution summary for {selected_num}:\n{desc}")

    with g2:
        if selected_cat:
            top_counts = value_counts_summary(filtered_df, selected_cat, 12)
            fig = px.bar(
                top_counts,
                x=selected_cat,
                y="count",
                text="percentage",
                title=f"Top Values in {selected_cat}",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
            chart_summaries.append(f"Top values in {selected_cat}:\n" + top_counts.to_string(index=False))

    if selected_num and selected_cat:
        grouped = (
            filtered_df.groupby(selected_cat, dropna=False)[selected_num]
            .mean()
            .sort_values(ascending=False)
            .head(12)
            .reset_index()
        )
        fig = px.bar(
            grouped,
            x=selected_cat,
            y=selected_num,
            text=selected_num,
            title=f"Average {selected_num} by {selected_cat}",
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
        chart_summaries.append(f"Average {selected_num} by {selected_cat}:\n" + grouped.to_string(index=False))

    if len(filtered_numeric_cols) >= 2:
        st.write("### Relationship Explorer")
        x_axis = st.selectbox("X-axis", filtered_numeric_cols, index=0)
        y_axis = st.selectbox("Y-axis", filtered_numeric_cols, index=1)
        color_col = selected_cat if selected_cat else None
        sample_df = filtered_df.sample(min(len(filtered_df), 8000), random_state=42) if len(filtered_df) > 8000 else filtered_df
        fig = px.scatter(
            sample_df,
            x=x_axis,
            y=y_axis,
            color=color_col,
            opacity=0.55,
            title=f"{y_axis} vs {x_axis}",
        )
        st.plotly_chart(fig, use_container_width=True)
        corr = sample_df[[x_axis, y_axis]].corr().iloc[0, 1]
        chart_summaries.append(f"Correlation between {x_axis} and {y_axis}: {corr:.3f}")

# -----------------------------
# Anomaly scan
# -----------------------------
st.subheader("4. Anomaly & Risk Detection")
if anomaly_df.empty:
    st.success("No major z-score anomalies detected in numeric columns.")
else:
    st.dataframe(anomaly_df, use_container_width=True)

# -----------------------------
# AI grounded context
# -----------------------------
eda_context = make_eda_context(filtered_profile, kpi_summary, chart_summaries, anomaly_df, missing_table)

with st.expander("View AI Grounding Context"):
    st.caption("This is the exact analysis layer sent to Gemini. It uses KPIs, EDA tables, chart summaries, anomaly scans, and data quality checks — not raw dataset rows.")
    st.text(eda_context[:12000])

# -----------------------------
# AI report
# -----------------------------
st.subheader("5. AI-Generated Executive Insight Report")
if st.button("Generate AI Insights", type="primary"):
    with st.spinner("Generating AI business report from EDA outputs..."):
        report = generate_ai_text(make_report_prompt(eda_context))
        st.markdown(report)
        st.download_button("Download AI Report", report, file_name="ai_insight_report.md", mime="text/markdown")

# -----------------------------
# AI chatbot
# -----------------------------
st.subheader("6. Ask the AI Analyst")
st.caption("Ask questions about the dashboard. The chatbot is grounded in the generated KPIs, EDA summaries, charts, and anomaly scan.")

example_questions = [
    "Which platform appears highest risk?",
    "What segments should the business prioritize?",
    "What does the dashboard suggest about night usage?",
    "What are the biggest data quality issues?",
]
selected_example = st.selectbox("Example questions", [""] + example_questions)
user_question = st.text_input("Your question", value=selected_example)

if st.button("Ask AI Analyst"):
    if not user_question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Answering from the EDA context..."):
            answer = generate_ai_text(make_chat_prompt(eda_context, user_question))
            st.markdown(answer)

st.divider()
st.caption(
    "Built as a Data-to-Insight Agent: upload structured data → generate EDA → visualize trends → detect anomalies/risk → produce AI-grounded recommendations."
)

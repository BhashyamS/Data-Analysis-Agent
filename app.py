import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

st.set_page_config(page_title="AI Data-to-Insight Agent", page_icon="📊", layout="wide")

st.title("📊 AI Data-to-Insight Agent")
st.caption("Upload any CSV or Excel file to generate data profiling, visual insights, anomalies, and AI-powered business recommendations.")

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
    profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values_total": int(df.isna().sum().sum()),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "date_columns": date_cols,
    }
    return profile

def find_anomalies(df: pd.DataFrame, numeric_cols, threshold=3.0):
    results = []
    for col in numeric_cols[:8]:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 10 or series.std() == 0:
            continue
        z = ((series - series.mean()) / series.std()).abs()
        count = int((z > threshold).sum())
        if count > 0:
            results.append({"column": col, "anomaly_count": count, "max_value": float(series.max()), "min_value": float(series.min())})
    return pd.DataFrame(results)

def make_prompt(df, profile, numeric_cols, categorical_cols, anomaly_df):
    sample_rows = df.head(8).to_csv(index=False)
    missing = df.isna().sum().sort_values(ascending=False).head(10).to_string()
    summary = df[numeric_cols].describe().round(2).to_string() if numeric_cols else "No numeric columns detected."
    cat_summary_parts = []
    for col in categorical_cols[:5]:
        cat_summary_parts.append(f"\n{col}:\n{df[col].value_counts(dropna=False).head(8).to_string()}")
    cat_summary = "\n".join(cat_summary_parts) if cat_summary_parts else "No categorical columns detected."
    anomaly_summary = anomaly_df.to_string(index=False) if not anomaly_df.empty else "No major z-score anomalies detected."

    return f"""
You are an AI data analyst. Analyze this uploaded structured dataset for a business audience.

Return the answer in this exact format:
1. Executive Summary: 3-4 sentences.
2. Key Insights: 4 bullet points, each with business meaning.
3. Anomalies or Risks: 2-3 bullets. Mention if none are significant.
4. Recommended Actions: 2 practical next steps.
5. Data Quality Notes: missing values, duplicates, or limitations.

Dataset profile:
{profile}

Numeric summary:
{summary}

Top categorical distributions:
{cat_summary}

Missing values by column:
{missing}

Anomaly scan:
{anomaly_summary}

Sample rows:
{sample_rows}
"""

def generate_ai_report(prompt: str):
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        st.error("Gemini API key not found. Add GEMINI_API_KEY in Streamlit secrets.")
        st.stop()
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("How it works")
    st.write("1. Upload CSV or Excel")
    st.write("2. App profiles the data")
    st.write("3. App builds charts automatically")
    st.write("4. Gemini generates insights")
    st.divider()
    st.write("Best demo datasets: sales, marketing, customer behavior, product usage, social media, operations.")

uploaded_file = st.file_uploader("Upload a CSV or Excel dataset", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("Upload a dataset to begin.")
    st.stop()

try:
    df = clean_column_names(load_file(uploaded_file))
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

numeric_cols, categorical_cols, date_cols = detect_columns(df)
profile = build_profile(df, numeric_cols, categorical_cols, date_cols)
anomaly_df = find_anomalies(df, numeric_cols)

# -----------------------------
# Data preview and profile
# -----------------------------
st.subheader("1. Dataset Preview")
st.dataframe(df.head(50), use_container_width=True)

st.subheader("2. Data Profile")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{profile['rows']:,}")
c2.metric("Columns", f"{profile['columns']:,}")
c3.metric("Missing Values", f"{profile['missing_values_total']:,}")
c4.metric("Duplicate Rows", f"{profile['duplicate_rows']:,}")

with st.expander("Detected column types"):
    st.write("**Numeric:**", numeric_cols)
    st.write("**Categorical:**", categorical_cols)
    st.write("**Date-like:**", date_cols)

# -----------------------------
# Auto visualizations
# -----------------------------
st.subheader("3. Auto-Generated Visual Insights")

if numeric_cols:
    selected_num = st.selectbox("Choose a numeric metric", numeric_cols)
else:
    selected_num = None

if categorical_cols:
    selected_cat = st.selectbox("Choose a segment/category", categorical_cols)
else:
    selected_cat = None

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    if selected_num:
        fig = px.histogram(df, x=selected_num, nbins=30, title=f"Distribution of {selected_num}")
        st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    if selected_cat:
        top_counts = df[selected_cat].astype(str).value_counts().head(10).reset_index()
        top_counts.columns = [selected_cat, "count"]
        fig = px.bar(top_counts, x=selected_cat, y="count", text="count", title=f"Top Values in {selected_cat}")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

if selected_num and selected_cat:
    grouped = df.groupby(selected_cat, dropna=False)[selected_num].mean().sort_values(ascending=False).head(12).reset_index()
    fig = px.bar(grouped, x=selected_cat, y=selected_num, text=selected_num, title=f"Average {selected_num} by {selected_cat}")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

if len(numeric_cols) >= 2:
    st.write("### Relationship Explorer")
    x_axis = st.selectbox("X-axis", numeric_cols, index=0)
    y_axis = st.selectbox("Y-axis", numeric_cols, index=1)
    color_col = selected_cat if selected_cat else None
    sample_df = df.sample(min(len(df), 5000), random_state=42) if len(df) > 5000 else df
    fig = px.scatter(sample_df, x=x_axis, y=y_axis, color=color_col, opacity=0.6, title=f"{y_axis} vs {x_axis}")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("4. Anomaly Scan")
if anomaly_df.empty:
    st.success("No major z-score anomalies detected in numeric columns.")
else:
    st.dataframe(anomaly_df, use_container_width=True)

# -----------------------------
# AI report
# -----------------------------
st.subheader("5. AI-Generated Insight Report")
if st.button("Generate AI Insights", type="primary"):
    with st.spinner("Generating AI business report..."):
        prompt = make_prompt(df, profile, numeric_cols, categorical_cols, anomaly_df)
        report = generate_ai_report(prompt)
        st.markdown(report)
        st.download_button("Download AI Report", report, file_name="ai_insight_report.md", mime="text/markdown")

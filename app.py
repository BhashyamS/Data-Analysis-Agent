import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google import genai

st.set_page_config(page_title="AI Data-to-Insight Agent", page_icon="📊", layout="wide")

st.title("📊 AI Data-to-Insight Agent")


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



def add_persona_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create simple behavioral personas when the expected social-media columns exist."""
    df = df.copy()
    needed = {"daily_usage_hours", "num_platforms_used", "night_usage", "screen_time_before_sleep"}
    if not needed.issubset(df.columns):
        return df

    usage = pd.to_numeric(df["daily_usage_hours"], errors="coerce").fillna(0)
    platforms = pd.to_numeric(df["num_platforms_used"], errors="coerce").fillna(0)
    sleep = pd.to_numeric(df["screen_time_before_sleep"], errors="coerce").fillna(0)
    night = pd.to_numeric(df["night_usage"], errors="coerce").fillna(0)

    conditions = [
        (night == 1) & (sleep >= sleep.quantile(0.60)),
        (platforms >= platforms.quantile(0.75)),
        (usage >= usage.quantile(0.75)),
        (usage <= usage.quantile(0.25)) & (night == 0),
    ]
    choices = [
        "Night Scrollers",
        "Platform Switchers",
        "Heavy Engagement Users",
        "Balanced Low-Risk Users",
    ]
    df["behavior_persona"] = np.select(conditions, choices, default="Moderate Everyday Users")
    return df

def segment_metrics(df: pd.DataFrame) -> dict:
    """Reusable metrics for comparison cards and AI grounding."""
    metrics = {"records": len(df)}
    if len(df) == 0:
        return metrics
    if "daily_usage_hours" in df.columns:
        metrics["avg_daily_usage_hours"] = pd.to_numeric(df["daily_usage_hours"], errors="coerce").mean()
    if "mental_health_score" in df.columns:
        metrics["avg_mental_health_score"] = pd.to_numeric(df["mental_health_score"], errors="coerce").mean()
    if "screen_time_before_sleep" in df.columns:
        metrics["avg_screen_time_before_sleep"] = pd.to_numeric(df["screen_time_before_sleep"], errors="coerce").mean()
    if "night_usage" in df.columns:
        metrics["night_usage_rate_%"] = pd.to_numeric(df["night_usage"], errors="coerce").eq(1).mean() * 100
    if "addiction_level" in df.columns:
        metrics["high_addiction_rate_%"] = df["addiction_level"].astype(str).str.lower().eq("high").mean() * 100
    if "risk_category" in df.columns:
        metrics["high_risk_rate_%"] = df["risk_category"].astype(str).eq("High Risk").mean() * 100
    if "risk_score" in df.columns:
        metrics["avg_risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").mean()
    return metrics

def build_strategy_recommendations(df: pd.DataFrame) -> list:
    """Rule-based recommendations that make the dashboard feel more productized."""
    recs = []
    if "night_usage" in df.columns and pd.to_numeric(df["night_usage"], errors="coerce").eq(1).mean() > 0.45:
        recs.append(("Wellness Team", "Launch a night-usage awareness campaign and test bedtime reminder nudges."))
    if "risk_category" in df.columns and df["risk_category"].astype(str).eq("High Risk").mean() > 0.25:
        recs.append(("Product Team", "Add optional screen-time controls, daily recap notifications, or soft usage limits for high-risk segments."))
    if "primary_platform" in df.columns and "risk_category" in df.columns:
        top_platform = (
            df.assign(high_risk=df["risk_category"].astype(str).eq("High Risk").astype(int))
            .groupby("primary_platform")["high_risk"]
            .mean()
            .sort_values(ascending=False)
        )
        if not top_platform.empty:
            recs.append(("Marketing / Content Team", f"Prioritize deeper review of {top_platform.index[0]} users because they show the highest calculated high-risk share."))
    if not recs:
        recs.append(("Analytics Team", "Use the filters and segment comparison tool to identify the strongest behavioral differences before taking action."))
    return recs[:3]


def build_theoretical_use_cases(df: pd.DataFrame) -> list:
    """Create business-facing use case recommendations from observed dashboard trends."""
    use_cases = []

    night_rate = None
    high_risk_rate = None
    high_addiction_rate = None
    top_risk_platform = None
    top_persona = None
    avg_sleep_high = None
    avg_sleep_low = None

    if "night_usage" in df.columns:
        night_rate = pd.to_numeric(df["night_usage"], errors="coerce").eq(1).mean() * 100

    if "risk_category" in df.columns:
        high_risk_rate = df["risk_category"].astype(str).eq("High Risk").mean() * 100

    if "addiction_level" in df.columns:
        high_addiction_rate = df["addiction_level"].astype(str).str.lower().eq("high").mean() * 100

    if {"primary_platform", "risk_category"}.issubset(df.columns):
        risk_by_platform = (
            df.assign(high_risk=df["risk_category"].astype(str).eq("High Risk").astype(int))
            .groupby("primary_platform")["high_risk"]
            .mean()
            .mul(100)
            .sort_values(ascending=False)
        )
        if not risk_by_platform.empty:
            top_risk_platform = (str(risk_by_platform.index[0]), float(risk_by_platform.iloc[0]))

    if "behavior_persona" in df.columns:
        persona_counts = df["behavior_persona"].astype(str).value_counts(normalize=True).mul(100)
        if not persona_counts.empty:
            top_persona = (str(persona_counts.index[0]), float(persona_counts.iloc[0]))

    if {"addiction_level", "screen_time_before_sleep"}.issubset(df.columns):
        sleep_by_addiction = df.groupby("addiction_level")["screen_time_before_sleep"].mean()
        if "High" in sleep_by_addiction.index:
            avg_sleep_high = float(sleep_by_addiction.loc["High"])
        if "Low" in sleep_by_addiction.index:
            avg_sleep_low = float(sleep_by_addiction.loc["Low"])

    wellness_trends = []
    wellness_actions = []
    if night_rate is not None:
        wellness_trends.append(f"Night usage appears in {night_rate:.1f}% of the filtered records.")
        if night_rate >= 40:
            wellness_actions.append("Test bedtime nudges or quiet-hour reminders for users active at night.")
    if high_risk_rate is not None:
        wellness_trends.append(f"The calculated high-risk segment represents {high_risk_rate:.1f}% of the filtered population.")
        if high_risk_rate >= 20:
            wellness_actions.append("Create a targeted digital wellness flow for high-risk users, such as weekly usage summaries or optional screen-time limits.")
    if avg_sleep_high is not None and avg_sleep_low is not None:
        wellness_trends.append(f"High-addiction users average {avg_sleep_high:.1f} minutes before-sleep screen time compared with {avg_sleep_low:.1f} minutes for low-addiction users.")
        wellness_actions.append("Prioritize sleep-focused messaging where bedtime screen time is highest.")
    if not wellness_trends:
        wellness_trends.append("Use the risk radar, night usage chart, and screen-time charts to identify wellness-related behavior patterns.")
    if not wellness_actions:
        wellness_actions.append("Monitor night usage, screen time before sleep, and risk category movement before launching interventions.")

    marketing_trends = []
    marketing_actions = []
    if top_risk_platform:
        marketing_trends.append(f"{top_risk_platform[0]} shows the highest calculated high-risk share at {top_risk_platform[1]:.1f}% among platforms in the filtered data.")
        marketing_actions.append(f"Review {top_risk_platform[0]} campaigns carefully and avoid over-targeting users already flagged as high risk.")
    if top_persona:
        marketing_trends.append(f"The largest behavioral persona is {top_persona[0]}, representing {top_persona[1]:.1f}% of filtered records.")
        marketing_actions.append(f"Design content strategies around the {top_persona[0]} persona while keeping engagement goals balanced with user well-being.")
    if high_addiction_rate is not None:
        marketing_trends.append(f"High addiction level accounts for {high_addiction_rate:.1f}% of the filtered records.")
        marketing_actions.append("Prioritize moderate-risk, high-engagement segments for campaigns instead of pushing more engagement to high-risk users.")
    if not marketing_trends:
        marketing_trends.append("Use platform, purpose, and persona charts to identify audience segments with meaningful engagement differences.")
    if not marketing_actions:
        marketing_actions.append("Use segment comparison to pick audiences with strong engagement but lower risk signals.")

    product_trends = []
    product_actions = []
    if high_risk_rate is not None:
        product_trends.append(f"High-risk users make up {high_risk_rate:.1f}% of the selected segment.")
    if night_rate is not None:
        product_trends.append(f"Night usage rate is {night_rate:.1f}% in the selected segment.")
    product_actions.extend([
        "Add optional break reminders, cooldown prompts, or weekly usage recaps for users with high risk signals.",
        "A/B test intentional-use features, such as session goals or 'take a break' prompts, before rolling them out broadly."
    ])

    strategy_trends = []
    strategy_actions = []
    if top_risk_platform:
        strategy_trends.append(f"Platform-level risk analysis highlights {top_risk_platform[0]} as a priority segment.")
    if top_persona:
        strategy_trends.append(f"Persona segmentation shows {top_persona[0]} as the largest audience group.")
    strategy_actions.extend([
        "Use the Segment Comparison tool to compare two groups before deciding where to invest resources.",
        "Track these KPIs over time to move from descriptive analytics into forecasting and intervention measurement."
    ])

    use_cases.append(("Wellness & Digital Health", wellness_trends, wellness_actions))
    use_cases.append(("Marketing & Audience Strategy", marketing_trends, marketing_actions))
    use_cases.append(("Product / UX Design", product_trends or ["Risk, session, and night-usage charts highlight where product friction may help."], product_actions))
    use_cases.append(("Business Strategy", strategy_trends or ["Segment-level charts show where behavior differs across audiences."], strategy_actions))
    return use_cases

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
    st.write("1. Upload a CSV or Excel dataset")
    st.write("2. Apply filters to explore segments")
    st.write("3. App generates KPIs, charts, EDA summaries, and anomalies")
    st.write("4. Gemini answers only from those EDA outputs")
    st.divider()
    st.write("Use a structured dataset with numeric and categorical columns for the best dashboard experience.")

uploaded_file = st.file_uploader("Upload a CSV or Excel dataset", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("Upload a dataset to begin.")
    st.stop()

try:
    df = clean_column_names(load_file(uploaded_file))
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

df = add_persona_features(add_risk_features(df))
numeric_cols, categorical_cols, date_cols = detect_columns(df)
profile = build_profile(df, numeric_cols, categorical_cols, date_cols)

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Dashboard Filters")
filtered_df = df.copy()
filterable_cols = [
    c for c in ["country", "gender", "primary_platform", "purpose", "addiction_level", "risk_category", "behavior_persona"]
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


# Prepare shared EDA summary list before any charts are rendered.
chart_summaries = []

# -----------------------------
# Creative analytics layer
# -----------------------------
st.subheader("3. Creative Analytics Layer")
st.caption("This section turns the EDA into a decision-support product: risk radar, personas, segment comparison, and strategy recommendations.")

creative_tab1, creative_tab2, creative_tab3, creative_tab4 = st.tabs([
    "Digital Wellness Radar",
    "Behavior Personas",
    "Segment Comparison",
    "Strategy Cards",
])

with creative_tab1:
    radar_group = None
    if "primary_platform" in filtered_df.columns:
        radar_group = st.selectbox("Compare risk radar by", ["Overall"] + sorted(filtered_df["primary_platform"].dropna().astype(str).unique().tolist()))
    else:
        radar_group = "Overall"

    radar_df = filtered_df if radar_group == "Overall" else filtered_df[filtered_df["primary_platform"].astype(str) == radar_group]
    radar_metrics = segment_metrics(radar_df)

    radar_labels = []
    radar_values = []
    if "avg_daily_usage_hours" in radar_metrics:
        radar_labels.append("Usage Intensity")
        radar_values.append(min((radar_metrics["avg_daily_usage_hours"] / 10) * 100, 100))
    if "avg_screen_time_before_sleep" in radar_metrics:
        radar_labels.append("Bedtime Screen Time")
        radar_values.append(min((radar_metrics["avg_screen_time_before_sleep"] / 120) * 100, 100))
    if "night_usage_rate_%" in radar_metrics:
        radar_labels.append("Night Usage")
        radar_values.append(radar_metrics["night_usage_rate_%"])
    if "high_addiction_rate_%" in radar_metrics:
        radar_labels.append("High Addiction")
        radar_values.append(radar_metrics["high_addiction_rate_%"])
    if "high_risk_rate_%" in radar_metrics:
        radar_labels.append("High Risk")
        radar_values.append(radar_metrics["high_risk_rate_%"])

    if radar_labels:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=radar_values + [radar_values[0]],
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            name=str(radar_group),
        ))
        fig.update_layout(
            title=f"Digital Wellness Risk Radar: {radar_group}",
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("The radar normalizes key behavior signals to a 0-100 scale so risk patterns are easier to compare.")
        chart_summaries.append(f"Digital wellness risk radar for {radar_group}: " + str({k: round(v, 2) if isinstance(v, float) else v for k, v in radar_metrics.items()}))
    else:
        st.info("Risk radar appears when usage, night behavior, addiction, or risk columns are available.")

with creative_tab2:
    if "behavior_persona" in filtered_df.columns:
        persona_counts = value_counts_summary(filtered_df, "behavior_persona", 10)
        fig = px.bar(
            persona_counts,
            x="behavior_persona",
            y="percentage",
            text="percentage",
            title="Behavior Persona Distribution",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        persona_cols = st.columns(min(5, len(persona_counts)))
        for idx, row in persona_counts.head(5).iterrows():
            with persona_cols[idx % len(persona_cols)]:
                st.metric(row["behavior_persona"], f"{row['percentage']:.1f}%", f"{int(row['count']):,} users")

        st.markdown(
            """
            **Persona logic**  
            - **Night Scrollers:** high bedtime screen time + night usage  
            - **Platform Switchers:** uses many platforms  
            - **Heavy Engagement Users:** high daily usage  
            - **Balanced Low-Risk Users:** lower usage and no night usage  
            """
        )
        chart_summaries.append("Behavior persona distribution:\n" + persona_counts.to_string(index=False))
    else:
        st.info("Persona cards appear for datasets with daily usage, platform count, night usage, and bedtime screen-time columns.")

with creative_tab3:
    comparison_candidates = [c for c in ["primary_platform", "country", "gender", "purpose", "addiction_level", "behavior_persona"] if c in filtered_df.columns]
    if comparison_candidates:
        comp_col = st.selectbox("Choose segment to compare", comparison_candidates)
        comp_options = sorted(filtered_df[comp_col].dropna().astype(str).unique().tolist())
        if len(comp_options) >= 2:
            left_val = st.selectbox("Segment A", comp_options, index=0)
            right_val = st.selectbox("Segment B", comp_options, index=1)
            left_df = filtered_df[filtered_df[comp_col].astype(str) == left_val]
            right_df = filtered_df[filtered_df[comp_col].astype(str) == right_val]
            left_metrics = segment_metrics(left_df)
            right_metrics = segment_metrics(right_df)

            comparison_rows = []
            for metric in sorted(set(left_metrics) | set(right_metrics)):
                left_metric = left_metrics.get(metric, np.nan)
                right_metric = right_metrics.get(metric, np.nan)
                if pd.notna(left_metric) and pd.notna(right_metric):
                    comparison_rows.append({
                        "metric": metric,
                        str(left_val): left_metric,
                        str(right_val): right_metric,
                        "difference": left_metric - right_metric,
                    })
            comparison_df = pd.DataFrame(comparison_rows)
            st.dataframe(comparison_df.round(2), use_container_width=True)

            display_df = comparison_df[comparison_df["metric"].ne("records")].melt(
                id_vars="metric",
                value_vars=[str(left_val), str(right_val)],
                var_name="segment",
                value_name="value",
            )
            fig = px.bar(
                display_df,
                x="metric",
                y="value",
                color="segment",
                barmode="group",
                title=f"Segment Comparison: {left_val} vs {right_val}",
            )
            st.plotly_chart(fig, use_container_width=True)
            chart_summaries.append(f"Segment comparison on {comp_col}: {left_val} vs {right_val}\n" + comparison_df.round(2).to_string(index=False))
        else:
            st.info("Need at least two segment values to compare.")
    else:
        st.info("Segment comparison appears when categorical columns are available.")

with creative_tab4:
    strategy_recs = build_strategy_recommendations(filtered_df)
    rec_cols = st.columns(len(strategy_recs))
    strategy_summary_lines = []
    for idx, (audience, recommendation) in enumerate(strategy_recs):
        with rec_cols[idx]:
            st.markdown(f"### {audience}")
            st.write(recommendation)
        strategy_summary_lines.append(f"{audience}: {recommendation}")
    chart_summaries.append("Rule-based strategy recommendation cards:\n" + "\n".join(strategy_summary_lines))


# -----------------------------
# Theoretical use cases from observed trends
# -----------------------------
st.subheader("4. Theoretical Use Cases & Recommendations")
st.caption("These recommendations translate the dashboard's observed EDA trends into business actions for different teams.")

use_cases = build_theoretical_use_cases(filtered_df)
use_case_summary_lines = []
uc_cols = st.columns(2)
for idx, (team, observed_trends, recommended_actions) in enumerate(use_cases):
    with uc_cols[idx % 2]:
        with st.container(border=True):
            st.markdown(f"### {team}")
            st.markdown("**Observed dashboard trends**")
            for trend in observed_trends[:3]:
                st.write(f"• {trend}")
            st.markdown("**Recommended actions**")
            for action in recommended_actions[:3]:
                st.write(f"• {action}")
    use_case_summary_lines.append(
        f"{team} observed trends: " + " | ".join(observed_trends[:3]) +
        "\nRecommended actions: " + " | ".join(recommended_actions[:3])
    )

chart_summaries.append("Theoretical use case recommendations based on observed dashboard trends:\n" + "\n\n".join(use_case_summary_lines))

# -----------------------------
# EDA visual insights
# -----------------------------
st.subheader("5. Trend & Segment Dashboard")
st.caption("These charts generate the analysis layer that the AI report and chatbot use as context.")

# chart_summaries already includes creative analytics outputs.

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
st.subheader("6. Anomaly & Risk Detection")
if anomaly_df.empty:
    st.success("No major z-score anomalies detected in numeric columns.")
else:
    st.dataframe(anomaly_df, use_container_width=True)

# -----------------------------
# AI grounded context
# -----------------------------
eda_context = make_eda_context(filtered_profile, kpi_summary, chart_summaries, anomaly_df, missing_table)


executive_summary_md = f"""
# AI Data-to-Insight Executive Summary

## KPI Snapshot
{kpi_summary}

## Dashboard Grounding Notes
{chr(10).join(chart_summaries[:8])}

## Anomaly Summary
{anomaly_df.to_string(index=False) if not anomaly_df.empty else 'No major z-score anomalies detected.'}
"""

st.download_button(
    "Download Dashboard Summary (EDA Grounding)",
    executive_summary_md,
    file_name="dashboard_eda_summary.md",
    mime="text/markdown",
)

with st.expander("View AI Grounding Context"):
    st.caption("This is the exact analysis layer sent to Gemini. It uses KPIs, EDA tables, chart summaries, anomaly scans, and data quality checks — not raw dataset rows.")
    st.text(eda_context[:12000])

# -----------------------------
# AI report
# -----------------------------
st.subheader("7. AI-Generated Executive Insight Report")
if st.button("Generate AI Insights", type="primary"):
    with st.spinner("Generating AI business report from EDA outputs..."):
        report = generate_ai_text(make_report_prompt(eda_context))
        st.markdown(report)
        st.download_button("Download AI Report", report, file_name="ai_insight_report.md", mime="text/markdown")

# -----------------------------
# AI chatbot
# -----------------------------
st.subheader("8. Ask the AI Analyst")
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

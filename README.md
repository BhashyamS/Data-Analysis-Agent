# Analytics Copilot

Analytics Copilot is an end-to-end Streamlit analytics workspace that mirrors a real data analyst workflow. It transforms an uploaded CSV or Excel file into a documented cleaning process, exploratory analysis, target-driver investigation, executive dashboard, grounded AI report, and downloadable analysis package.

## Analyst workflow

1. **Prepare** — profile the schema, diagnose quality issues, apply a reproducible cleaning recipe, and compare raw versus cleaned data.
2. **Executive Brief** — review adaptive KPIs, automatic findings, and dataset-appropriate visual summaries.
3. **Explore** — inspect distributions, categories, trends, correlations, and build custom charts.
4. **Analyze** — select a numeric outcome and investigate potential numeric and categorical drivers. Results are explicitly presented as associations, not causal proof.
5. **Quality & Outliers** — review a data-health score, column-level quality, and row-level IQR outliers.
6. **AI Analyst** — generate a stakeholder-ready report or ask questions using grounded aggregate evidence.
7. **Export** — download cleaned data, filtered analysis data, outlier review rows, and a JSON evidence package.

## Universal dataset support

The app does not require predefined column names. It detects:

- Numeric variables
- Categorical variables
- Date and time variables
- Boolean variables
- Identifiers
- Long-text fields

This allows it to adapt to sales, finance, HR, marketing, operations, survey, inventory, healthcare, research, and other structured datasets.

## Cleaning capabilities

- Remove duplicate rows
- Drop completely empty columns
- Drop selected columns
- Trim text whitespace
- Standardize categorical text case
- Fill numeric missing values using median, mean, or zero
- Fill categorical missing values using mode or an `Unknown` label
- Record every applied transformation in a cleaning log
- Export the cleaned dataset

## Analysis capabilities

- Dataset and column profiling
- Missing-value and duplicate analysis
- Adaptive KPI cards
- Automatic narrative findings
- Histograms, box plots, bar charts, line charts, scatter plots, and correlation heatmaps
- Date-based aggregation
- Segment comparison
- Target-driver analysis
- IQR outlier detection with row-level review
- Data-health scoring
- Grounded Gemini reports and questions

## Installation

```bash
git clone https://github.com/BhashyamS/Data-Analysis-Agent.git
cd Data-Analysis-Agent
pip install -r requirements.txt
streamlit run app.py
```

## Gemini setup

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your_api_key_here"
```

The application still works without Gemini; only AI report and chat features are disabled.

## Important analytical guardrails

- Statistical outliers are review candidates, not automatically data errors.
- Correlations and group differences are associations, not proof of causation.
- AI output is instructed to separate evidence from hypotheses and avoid inventing unsupported business meaning.
- The exported analysis package preserves cleaning decisions and aggregated evidence for reproducibility.

## Tech stack

- Streamlit
- Pandas
- NumPy
- Plotly
- Statsmodels
- Google Gemini API

## Author

Srija Bhashyam

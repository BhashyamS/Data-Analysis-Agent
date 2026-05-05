# AI Data-to-Insight Agent

A Streamlit app that accepts any CSV or Excel dataset, profiles the data, generates automatic visualizations, scans for simple anomalies, and uses Gemini AI to produce business-friendly insights and recommendations.

## Features
- CSV / Excel upload
- Automatic column detection
- Data quality summary
- KPI cards
- Interactive Plotly charts
- Simple z-score anomaly scan
- AI-generated executive summary, insights, risks, recommendations, and data quality notes

## Local Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets
Add your Gemini API key in Streamlit secrets:
```toml
GEMINI_API_KEY = "your_key_here"
```

## Deployment
Push `app.py`, `requirements.txt`, and `README.md` to a GitHub repository. Then deploy through Streamlit Community Cloud and add the Gemini key in the app's Secrets settings.

import streamlit as st


def apply_app_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #0b1020; }
        [data-testid="stHeader"] { background: rgba(11,16,32,.75); }
        [data-testid="stSidebar"] { background: #0e1529; border-right: 1px solid #25304a; }
        .block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }
        h1, h2, h3 { letter-spacing: -0.03em; }
        .hero {
            padding: 3.2rem 2.2rem;
            border-radius: 24px;
            border: 1px solid #293653;
            background: radial-gradient(circle at top left, rgba(99,102,241,.25), transparent 45%),
                        linear-gradient(145deg, #121a31, #0e1428);
            box-shadow: 0 22px 60px rgba(0,0,0,.28);
            margin-bottom: 1.4rem;
        }
        .eyebrow { color: #a5b4fc; font-weight: 700; font-size: .82rem; letter-spacing: .12em; text-transform: uppercase; }
        .hero h1 { font-size: 3.2rem; margin: .45rem 0 .6rem; color: #f8fafc; }
        .hero p { max-width: 720px; color: #bdc7dc; font-size: 1.15rem; line-height: 1.7; }
        .workflow-card, .info-card {
            border: 1px solid #27334d;
            border-radius: 18px;
            padding: 1.15rem 1.2rem;
            background: #11192d;
            min-height: 132px;
        }
        .workflow-number { color:#818cf8; font-size:.8rem; font-weight:800; }
        .workflow-title { color:#f8fafc; font-weight:700; font-size:1.02rem; margin:.3rem 0; }
        .workflow-copy { color:#95a1ba; font-size:.9rem; line-height:1.45; }
        .status-ready { color:#86efac; font-weight:700; }
        div[data-testid="stMetric"] {
            border: 1px solid #27334d; background:#11192d; padding:1rem; border-radius:16px;
        }
        div[data-testid="stFileUploader"] section {
            border: 1px dashed #6676c8; background:#111a32; border-radius:18px; padding:1rem;
        }
        .small-muted { color:#91a0bb; font-size:.9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

from io import BytesIO

import pandas as pd
from pptx import Presentation
from pypdf import PdfReader

from src.report_exports import build_pdf_export, build_powerpoint_export
from src.reporting import build_report_data


def sample_data():
    df = pd.DataFrame(
        {
            "sales": [100, 200, 300, 400],
            "profit": [10, 20, 25, 50],
            "region": ["East", "East", "West", "West"],
        }
    )

    report_data = build_report_data(
        df,
        filename="sales.csv",
        title="Sales Report",
        audience="Executive",
        detail_level="Standard",
        selected_sections=[
            "Executive Summary",
            "Dataset Overview",
            "Dashboard",
            "Limitations",
        ],
        dashboard_title="Sales Dashboard",
        dashboard_widgets=[
            {
                "id": "kpi-1",
                "type": "kpi",
                "title": "Total Sales",
                "config": {
                    "column": "sales",
                    "aggregation": "sum",
                    "value": 1000,
                    "prefix": "$",
                    "suffix": "",
                },
            },
            {
                "id": "chart-1",
                "type": "chart",
                "title": "Sales by Region",
                "config": {
                    "chart_type": "Bar",
                    "x_column": "region",
                    "y_column": "sales",
                    "aggregation": "Sum",
                    "top_n": 10,
                },
            },
        ],
    )

    return df, report_data


def test_pdf_export_is_readable():
    df, report_data = sample_data()
    result = build_pdf_export(report_data, df, narrative="Sales increased.")

    reader = PdfReader(BytesIO(result))

    assert len(reader.pages) >= 1
    assert len(result) > 1000


def test_powerpoint_export_is_readable():
    df, report_data = sample_data()
    result = build_powerpoint_export(report_data, df, narrative="Sales increased.")

    presentation = Presentation(BytesIO(result))

    assert len(presentation.slides) >= 3
    assert len(result) > 1000

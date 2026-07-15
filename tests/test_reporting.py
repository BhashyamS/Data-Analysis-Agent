import json

import pandas as pd

from src.reporting import (
    build_markdown_report,
    build_report_data,
    markdown_to_html,
    report_to_json,
)


def sample_report_data():
    df = pd.DataFrame(
        {
            "sales": [100, 200, 300],
            "profit": [10, 20, 30],
            "region": ["East", "West", "West"],
        }
    )

    return build_report_data(
        df,
        filename="sales.csv",
        title="Sales Report",
        audience="Executive",
        detail_level="Standard",
        selected_sections=[
            "Executive Summary",
            "Dataset Overview",
            "Statistical Analysis",
            "Dashboard",
            "Limitations",
        ],
        cleaning_history=[{"description": "Removed duplicate rows."}],
        dashboard_title="Sales Dashboard",
        dashboard_widgets=[
            {
                "id": "1",
                "type": "kpi",
                "title": "Total Sales",
                "config": {"column": "sales", "value": 600},
            }
        ],
    )


def test_build_report_data():
    result = sample_report_data()

    assert result["metadata"]["title"] == "Sales Report"
    assert result["dataset"]["rows"] == 3
    assert result["dashboard"]["widgets"][0]["title"] == "Total Sales"


def test_markdown_report_contains_sections():
    report = build_markdown_report(sample_report_data())

    assert "# Sales Report" in report
    assert "## Dataset Overview" in report
    assert "## Dashboard" in report


def test_html_report_is_complete():
    html = markdown_to_html("# Report\n\n## Summary\nText", "Report")

    assert "<!doctype html>" in html
    assert "<h1>Report</h1>" in html


def test_json_report_is_valid():
    result = report_to_json(sample_report_data(), "Narrative")
    payload = json.loads(result)

    assert payload["generated_narrative"] == "Narrative"
    assert payload["dataset"]["rows"] == 3

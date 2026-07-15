import json

import pandas as pd

from src.dashboard import (
    create_widget,
    dashboard_from_json,
    duplicate_widget,
    refresh_kpi_widgets,
    update_widget,
)
from src.dashboard_recommendation import parse_dashboard_recommendation


def test_duplicate_widget_creates_new_id():
    widget = create_widget("text", title="Notes", text="Hello")
    result = duplicate_widget([widget], widget["id"])

    assert len(result) == 2
    assert result[0]["id"] != result[1]["id"]


def test_update_widget_changes_title_and_config():
    widget = create_widget("text", title="Old", text="Before")
    result = update_widget(
        [widget],
        widget["id"],
        title="New",
        config_updates={"text": "After"},
    )

    assert result[0]["title"] == "New"
    assert result[0]["config"]["text"] == "After"


def test_refresh_kpi_widgets():
    df = pd.DataFrame({"sales": [10, 20, 30]})
    widget = create_widget(
        "kpi",
        title="Sales",
        column="sales",
        aggregation="sum",
    )

    result = refresh_kpi_widgets(df, [widget])
    assert result[0]["config"]["value"] == 60.0


def test_dashboard_import():
    widget = create_widget("text", title="Notes", text="Hello")
    payload = json.dumps({"title": "Imported", "widgets": [widget]})

    title, widgets = dashboard_from_json(payload)

    assert title == "Imported"
    assert len(widgets) == 1


def test_parse_ai_dashboard_recommendation():
    response = json.dumps(
        {
            "title": "Sales Dashboard",
            "reason": "Focuses on performance.",
            "widgets": [
                {
                    "type": "kpi",
                    "title": "Total Sales",
                    "column": "sales",
                    "aggregation": "sum",
                },
                {
                    "type": "chart",
                    "title": "Sales by Region",
                    "chart_type": "Bar",
                    "x_column": "region",
                    "y_column": "sales",
                    "aggregation": "Sum",
                },
            ],
        }
    )

    result = parse_dashboard_recommendation(
        response,
        available_columns=["sales", "region"],
    )

    assert result["title"] == "Sales Dashboard"
    assert len(result["widgets"]) == 2

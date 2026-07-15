import pandas as pd
import pytest

from src.dashboard import (
    add_widget,
    calculate_kpi,
    create_widget,
    dashboard_to_json,
    move_widget,
    remove_widget,
)


def test_create_add_and_remove_widget():
    widget = create_widget("text", title="Notes", text="Hello")
    widgets = add_widget([], widget)

    assert len(widgets) == 1
    assert widgets[0]["title"] == "Notes"

    widgets = remove_widget(widgets, widget["id"])
    assert widgets == []


def test_move_widget():
    first = create_widget("text", title="First")
    second = create_widget("text", title="Second")
    widgets = [first, second]

    moved = move_widget(widgets, second["id"], "up")
    assert moved[0]["id"] == second["id"]


def test_calculate_kpi():
    df = pd.DataFrame({"sales": [10, 20, 30], "region": ["A", "A", "B"]})

    assert calculate_kpi(df, "sales", "sum") == 60.0
    assert calculate_kpi(df, "sales", "mean") == 20.0
    assert calculate_kpi(df, "region", "unique") == 2


def test_invalid_widget_type():
    with pytest.raises(ValueError):
        create_widget("video")


def test_dashboard_json():
    widget = create_widget("kpi", title="Sales", value=100)
    result = dashboard_to_json("Executive", [widget])

    assert '"title": "Executive"' in result
    assert '"widgets"' in result

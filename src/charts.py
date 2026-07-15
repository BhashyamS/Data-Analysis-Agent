
"""Plotly chart builders used by the Explore page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def histogram_chart(df: pd.DataFrame, column: str, bins: int = 30) -> go.Figure:
    values = pd.to_numeric(df[column], errors="coerce")
    figure = px.histogram(
        x=values,
        nbins=bins,
        labels={"x": column, "y": "Count"},
        title=f"Distribution of {column}",
    )
    figure.update_layout(bargap=0.04)
    return figure


def box_chart(df: pd.DataFrame, column: str) -> go.Figure:
    working = df.copy()
    working[column] = pd.to_numeric(working[column], errors="coerce")
    return px.box(working, y=column, points="outliers", title=f"Outliers in {column}")


def category_bar_chart(summary: pd.DataFrame, column: str) -> go.Figure:
    return px.bar(
        summary,
        x="count",
        y="value",
        orientation="h",
        title=f"Top values in {column}",
        labels={"count": "Count", "value": column},
    ).update_layout(yaxis={"categoryorder": "total ascending"})


def correlation_heatmap(correlation: pd.DataFrame) -> go.Figure:
    figure = go.Figure(
        data=go.Heatmap(
            z=correlation.values,
            x=correlation.columns,
            y=correlation.index,
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            reversescale=True,
            colorbar={"title": "Correlation"},
            text=correlation.round(2).values,
            texttemplate="%{text}",
        )
    )
    figure.update_layout(title="Correlation heatmap")
    return figure


def scatter_chart(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: str | None = None,
) -> go.Figure:
    working = df.copy()
    working[x_column] = pd.to_numeric(working[x_column], errors="coerce")
    working[y_column] = pd.to_numeric(working[y_column], errors="coerce")
    return px.scatter(
        working,
        x=x_column,
        y=y_column,
        color=color_column,
        trendline=None,
        title=f"{y_column} vs {x_column}",
        opacity=0.7,
    )


def grouped_bar_chart(
    summary: pd.DataFrame,
    category_column: str,
    numeric_column: str,
    aggregation: str,
) -> go.Figure:
    return px.bar(
        summary,
        x=category_column,
        y="value",
        title=f"{aggregation.title()} {numeric_column} by {category_column}",
        labels={"value": f"{aggregation.title()} {numeric_column}"},
    )


def time_series_chart(
    summary: pd.DataFrame,
    date_column: str,
    numeric_column: str,
    aggregation: str,
) -> go.Figure:
    return px.line(
        summary,
        x=date_column,
        y="value",
        markers=True,
        title=f"{aggregation.title()} {numeric_column} over time",
        labels={"value": f"{aggregation.title()} {numeric_column}"},
    )


def custom_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: str | None = None,
    color_column: str | None = None,
    aggregation: str = "None",
    top_n: int = 20,
) -> go.Figure:
    """Build a chart from user selections."""
    working = df.copy()

    if aggregation != "None" and y_column:
        aggregation_name = aggregation.lower()
        supported = {"mean", "median", "sum", "min", "max", "count"}

        if aggregation_name not in supported:
            aggregation_name = "mean"

        working[y_column] = pd.to_numeric(working[y_column], errors="coerce")
        if aggregation_name == "count":
            working = (
                working.groupby(x_column, dropna=False)[y_column]
                .count()
                .reset_index(name=y_column)
            )
        else:
            working = (
                working.groupby(x_column, dropna=False)[y_column]
                .agg(aggregation_name)
                .reset_index()
            )
        working = working.sort_values(y_column, ascending=False).head(top_n)

    if chart_type == "Bar":
        return px.bar(working, x=x_column, y=y_column, color=color_column)
    if chart_type == "Line":
        return px.line(working, x=x_column, y=y_column, color=color_column, markers=True)
    if chart_type == "Scatter":
        return px.scatter(working, x=x_column, y=y_column, color=color_column)
    if chart_type == "Box":
        return px.box(working, x=x_column if y_column else None, y=y_column or x_column, color=color_column)
    if chart_type == "Pie":
        if y_column:
            return px.pie(working, names=x_column, values=y_column)
        counts = working[x_column].fillna("Missing").astype(str).value_counts().head(top_n)
        pie_data = counts.rename_axis(x_column).reset_index(name="count")
        return px.pie(pie_data, names=x_column, values="count")

    return px.histogram(working, x=x_column, color=color_column)

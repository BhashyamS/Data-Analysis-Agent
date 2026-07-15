from __future__ import annotations

import streamlit as st


def render_workflow_navigation(active_step: int) -> None:
    steps = [
        "Import",
        "Prepare",
        "Explore",
        "Analyze",
        "AI Analyst",
        "Dashboard Studio",
        "Report Builder",
    ]
    labels = []

    for index, step in enumerate(steps, start=1):
        marker = "●" if index == active_step else "✓" if index < active_step else "○"
        labels.append(f"{marker} {step}")

    st.caption("   ·   ".join(labels))

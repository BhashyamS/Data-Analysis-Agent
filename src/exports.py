from __future__ import annotations

import json
from typing import Any

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def transformation_log_text(history: list[dict[str, Any]]) -> str:
    lines = ["Analytics Copilot · Transformation Log", "=" * 44, ""]
    for index, item in enumerate(history, start=1):
        lines.extend(
            [
                f"{index}. {item.get('action', 'Transformation')}",
                f"   Time: {item.get('timestamp', '')}",
                f"   Details: {item.get('details', '')}",
                "",
            ]
        )
    return "\n".join(lines)

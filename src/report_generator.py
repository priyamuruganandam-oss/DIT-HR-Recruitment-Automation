"""CSV report generation helpers."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

def write_csv_report(data: pd.DataFrame, output_path: str | Path) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(destination, index=False)
    return destination

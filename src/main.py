"""Command-line entry point for validating and screening a local CSV dataset.

The deployed web application is served by backend/main.py. This entry point is
provided for local project testing and follows the DIT src/ module structure.
"""
from pathlib import Path
import pandas as pd
from .data_reader import read_candidate_sheet
from .validator import validate_candidates
from .business_rules import screen_candidates
from .logger import get_logger

LOGGER = get_logger(__name__)

def run(input_file: str | Path, output_file: str | Path = "data/output/screening_results.csv") -> Path:
    input_path = Path(input_file)
    raw_data = read_candidate_sheet(input_path.name, input_path.read_bytes())
    valid, exceptions = validate_candidates(raw_data)
    screened = screen_candidates(valid, ["python", "sql"], 2, ["Bachelor", "Master", "Diploma"], 60, 60)
    destination = Path(output_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    screened.to_csv(destination, index=False)
    exceptions.to_csv(destination.with_name("data_exceptions.csv"), index=False)
    LOGGER.info("Processed %s rows: %s valid, %s exceptions", len(raw_data), len(screened), len(exceptions))
    return destination

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the DIT HR candidate screening sample workflow.")
    parser.add_argument("input_file", help="Path to a CSV or XLSX candidate dataset")
    parser.add_argument("--output", default="data/output/screening_results.csv")
    args = parser.parse_args()
    print(run(args.input_file, args.output))

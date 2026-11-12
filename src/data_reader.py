"""Readers for approved CSV, XLSX and text-based PDF input files."""
from __future__ import annotations
import io
import pandas as pd
from .business_rules import extract_resume_text, parse_resume_text

def read_candidate_sheet(filename: str, content: bytes) -> pd.DataFrame:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        return pd.read_csv(io.BytesIO(content))
    if suffix == "xlsx":
        return pd.read_excel(io.BytesIO(content))
    raise ValueError("Candidate file must be CSV or XLSX.")

def read_resume(filename: str, content: bytes) -> pd.DataFrame:
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Resume file must be PDF.")
    extracted_text = extract_resume_text(content)
    return pd.DataFrame([parse_resume_text(extracted_text, filename)])

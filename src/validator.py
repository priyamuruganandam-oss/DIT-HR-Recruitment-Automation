"""Input normalization and candidate data validation."""
from __future__ import annotations
import re
from typing import Any
import pandas as pd

REQUIRED_COLUMNS = [
    "candidate_id", "full_name", "email", "phone", "education",
    "experience_years", "skills", "location", "notice_period_days",
    "expected_salary", "applied_role",
]

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [str(column).strip().lower().replace(" ", "_") for column in normalized.columns]
    return normalized

def valid_email(value: Any) -> bool:
    email = str(value or "").strip()
    return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email))

def validate_candidates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = normalize_columns(df)
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    for column in ("full_name", "email", "phone"):
        data[column] = data[column].fillna("").astype(str).str.strip()

    data["email_valid"] = data["email"].apply(valid_email)
    data["validation_issues"] = ""
    data.loc[data["full_name"].eq(""), "validation_issues"] += "Missing name; "
    data.loc[~data["email_valid"], "validation_issues"] += "Invalid email; "
    phone_digits = data["phone"].str.replace(r"\D", "", regex=True)
    data.loc[phone_digits.str.len().lt(10), "validation_issues"] += "Invalid phone; "

    for column in ("experience_years", "notice_period_days", "expected_salary"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
        data.loc[data[column].isna(), "validation_issues"] += f"Invalid {column}; "

    duplicate_email = data["email"].str.lower().duplicated(keep=False) & data["email"].ne("")
    data.loc[duplicate_email, "validation_issues"] += "Duplicate email; "

    valid = data[data["validation_issues"].eq("")].copy()
    exceptions = data[~data["validation_issues"].eq("")].copy()
    return valid, exceptions

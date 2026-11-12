
"""Transparent, rule-based candidate screening helpers.
HR must make all final recruitment decisions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


# --------------------------------------------------
# REQUIRED CANDIDATE DATASET COLUMNS
# --------------------------------------------------

REQUIRED_COLUMNS = [
    "candidate_id",
    "full_name",
    "email",
    "phone",
    "education",
    "experience_years",
    "skills",
    "location",
    "notice_period_days",
    "expected_salary",
    "applied_role"
]


# --------------------------------------------------
# SUPPORTED SKILLS
# --------------------------------------------------

SKILL_BANK = [
    "python",
    "java",
    "sql",
    "excel",
    "power bi",
    "tableau",
    "javascript",
    "html",
    "css",
    "react",
    "django",
    "flask",
    "machine learning",
    "communication",
    "project management",
    "testing",
    "git",
    "aws"
]


# --------------------------------------------------
# EMAIL VALIDATION
# --------------------------------------------------

def valid_email(value: Any) -> bool:

    value = str(value or "").strip()

    pattern = (
        r"[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}"
    )

    return bool(re.fullmatch(pattern, value))


# --------------------------------------------------
# COLUMN NORMALIZATION
# --------------------------------------------------

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:

    out = df.copy()

    out.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in out.columns
    ]

    return out


# --------------------------------------------------
# CANDIDATE DATA VALIDATION
# --------------------------------------------------

def validate_candidates(
    df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:

    data = normalize_columns(df)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    # Clean text fields
    data["full_name"] = (
        data["full_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    data["email"] = (
        data["email"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    data["phone"] = (
        data["phone"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Email validation
    data["email_valid"] = data["email"].apply(valid_email)

    # Initialize validation issues
    data["validation_issues"] = ""

    # Name validation
    data.loc[
        data["full_name"].eq(""),
        "validation_issues"
    ] += "Missing name; "

    # Email validation
    data.loc[
        ~data["email_valid"],
        "validation_issues"
    ] += "Invalid email; "

    # Phone validation
    phone_digits = (
        data["phone"]
        .str.replace(r"\D", "", regex=True)
    )

    data.loc[
        phone_digits.str.len().lt(10),
        "validation_issues"
    ] += "Invalid phone; "

    # Numeric field validation
    numeric_columns = [
        "experience_years",
        "notice_period_days",
        "expected_salary"
    ]

    for column in numeric_columns:

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

        data.loc[
            data[column].isna(),
            "validation_issues"
        ] += f"Invalid {column}; "

    # Duplicate email validation
    duplicate_email = (
        data["email"]
        .str.lower()
        .duplicated(keep=False)
        &
        data["email"].ne("")
    )

    data.loc[
        duplicate_email,
        "validation_issues"
    ] += "Duplicate email; "

    # Separate valid candidates and exceptions
    valid = data[
        data["validation_issues"].eq("")
    ].copy()

    exceptions = data[
        ~data["validation_issues"].eq("")
    ].copy()

    return valid, exceptions


# --------------------------------------------------
# CANDIDATE SCREENING
# EXACT EXPERIENCE MATCHING
# --------------------------------------------------

def screen_candidates(
    valid: pd.DataFrame,
    required_skills: list[str],
    min_experience: float,
    education_keywords: list[str],
    max_notice_days: float,
    threshold: float = 60.0
) -> pd.DataFrame:

    out = valid.copy()

    # Normalize requirements
    skills = [
        skill.strip().lower()
        for skill in required_skills
        if skill.strip()
    ]

    education_terms = [
        term.strip().lower()
        for term in education_keywords
        if term.strip()
    ]

    # Convert experience to numeric values
    out["experience_years"] = pd.to_numeric(
        out["experience_years"],
        errors="coerce"
    )

    # --------------------------------------------------
    # EXACT EXPERIENCE MATCH
    # --------------------------------------------------

    if min_experience <= 0:

        out["experience_match"] = True

    else:

        out["experience_match"] = (
            out["experience_years"] == float(min_experience)
        )

    # --------------------------------------------------
    # SKILL SCORE - 40%
    # --------------------------------------------------

    def skill_score(value):

        candidate_skills = str(value).lower()

        if not skills:
            return 100.0

        matched_skills = sum(
            skill in candidate_skills
            for skill in skills
        )

        return (
            100.0 * matched_skills / len(skills)
        )

    # --------------------------------------------------
    # EXPERIENCE SCORE - 30%
    # --------------------------------------------------

    def experience_score(value):

        if min_experience <= 0:
            return 100.0

        if pd.isna(value):
            return 0.0

        return (
            100.0
            if float(value) == float(min_experience)
            else 0.0
        )

    # --------------------------------------------------
    # EDUCATION SCORE - 15%
    # --------------------------------------------------

    def education_score(value):

        if not education_terms:
            return 100.0

        education = str(value).lower()

        matched = any(
            term in education
            for term in education_terms
        )

        return 100.0 if matched else 0.0

    # --------------------------------------------------
    # NOTICE PERIOD SCORE - 15%
    # --------------------------------------------------

    def notice_score(value):

        if pd.isna(value):
            return 0.0

        if max_notice_days <= 0:

            return (
                100.0
                if float(value) <= 0
                else 0.0
            )

        return (
            100.0
            if float(value) <= max_notice_days
            else 0.0
        )

    # Calculate individual scores
    out["skill_score"] = (
        out["skills"].apply(skill_score)
    )

    out["experience_score"] = (
        out["experience_years"].apply(experience_score)
    )

    out["education_score"] = (
        out["education"].apply(education_score)
    )

    out["notice_score"] = (
        out["notice_period_days"].apply(notice_score)
    )

    # --------------------------------------------------
    # FINAL MATCH SCORE
    # --------------------------------------------------

    out["match_score"] = (
        out["skill_score"] * 0.40
        +
        out["experience_score"] * 0.30
        +
        out["education_score"] * 0.15
        +
        out["notice_score"] * 0.15
    ).round(1)

    # --------------------------------------------------
    # FINAL RECOMMENDATION
    # Exact experience AND threshold are compulsory
    # --------------------------------------------------

    out["screening_recommendation"] = out.apply(
        lambda row: (
            "Meets review threshold"
            if (
                row["experience_match"]
                and row["match_score"] >= threshold
            )
            else "Below review threshold"
        ),
        axis=1
    )

    # HR must review every recommendation
    out["hr_review_status"] = "Pending HR review"

    # Sort by score
    out = out.sort_values(
        ["match_score", "full_name"],
        ascending=[False, True]
    )

    return out


# --------------------------------------------------
# PDF TEXT EXTRACTION
# Retained for existing backend compatibility
# --------------------------------------------------

def extract_resume_text(pdf_bytes: bytes) -> str:

    """Extract selectable text from a PDF.
    Scanned PDFs require OCR, which is not included.
    """

    import fitz

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    return "\n".join(
        page.get_text("text")
        for page in doc
    )


# --------------------------------------------------
# RESUME TEXT PARSING
# Retained for existing backend compatibility
# --------------------------------------------------

def parse_resume_text(
    text: str,
    filename: str
) -> dict:

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    phones = re.findall(
        r"(?:\+?\d[\d\s().-]{8,}\d)",
        text
    )

    lower = text.lower()

    found_skills = [
        skill
        for skill in SKILL_BANK
        if skill in lower
    ]

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    name = ""

    for line in lines[:8]:

        if (
            "@" not in line
            and not re.search(r"\d", line)
            and 1 < len(line.split()) <= 4
        ):

            name = line[:100]
            break

    exp_match = re.search(
        r"(\d+(?:\.\d+)?)\s*\+?\s*"
        r"(?:years?|yrs?)\s+"
        r"(?:of\s+)?(?:experience|exp)",
        lower
    )

    exp = (
        float(exp_match.group(1))
        if exp_match
        else 0.0
    )

    education = next(
        (
            term
            for term in [
                "Bachelor of Engineering",
                "Bachelor of Technology",
                "Bachelor of Science",
                "Bachelor of Computer Applications",
                "Master of Business Administration",
                "Master of Science",
                "Master of Computer Applications",
                "Diploma"
            ]
            if term.lower() in lower
        ),
        "Not detected"
    )

    return {
        "candidate_id": (
            "PDF-"
            + re.sub(r"\W+", "", filename)[:18]
        ),
        "full_name": name or Path(filename).stem,
        "email": emails[0] if emails else "",
        "phone": (
            re.sub(r"\D", "", phones[0])
            if phones
            else ""
        ),
        "education": education,
        "experience_years": exp,
        "skills": ", ".join(found_skills),
        "location": "Not detected",
        "notice_period_days": 30,
        "expected_salary": 0,
        "applied_role": "Not specified",
        "resume_file": filename
    }

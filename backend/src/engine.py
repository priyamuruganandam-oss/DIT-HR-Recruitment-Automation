"""Transparent, rule-based candidate screening helpers. HR must make final decisions."""
from __future__ import annotations
import re
from typing import Any
import pandas as pd

REQUIRED_COLUMNS = [
    "candidate_id", "full_name", "email", "phone", "education",
    "experience_years", "skills", "location", "notice_period_days",
    "expected_salary", "applied_role"
]

SKILL_BANK = [
    "python", "java", "sql", "excel", "power bi", "tableau", "javascript",
    "html", "css", "react", "django", "flask", "machine learning",
    "communication", "project management", "testing", "git", "aws"
]

def valid_email(value: Any) -> bool:
    value = str(value or "").strip()
    return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value))

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out

def validate_candidates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = normalize_columns(df)
    missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    data["full_name"] = data["full_name"].fillna("").astype(str).str.strip()
    data["email"] = data["email"].fillna("").astype(str).str.strip()
    data["phone"] = data["phone"].fillna("").astype(str).str.strip()
    data["email_valid"] = data["email"].apply(valid_email)
    data["validation_issues"] = ""
    data.loc[data["full_name"].eq(""), "validation_issues"] += "Missing name; "
    data.loc[~data["email_valid"], "validation_issues"] += "Invalid email; "
    data.loc[data["phone"].str.replace(r"\D", "", regex=True).str.len().lt(10), "validation_issues"] += "Invalid phone; "
    for col in ["experience_years", "notice_period_days", "expected_salary"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
        data.loc[data[col].isna(), "validation_issues"] += f"Invalid {col}; "
    dup = data["email"].str.lower().duplicated(keep=False) & data["email"].ne("")
    data.loc[dup, "validation_issues"] += "Duplicate email; "
    valid = data[data["validation_issues"].eq("")].copy()
    exceptions = data[~data["validation_issues"].eq("")].copy()
    return valid, exceptions

def screen_candidates(valid: pd.DataFrame, required_skills: list[str],
                      min_experience: float, education_keywords: list[str],
                      max_notice_days: float, threshold: float = 60.0) -> pd.DataFrame:
    out = valid.copy()
    skills = [s.strip().lower() for s in required_skills if s.strip()]
    education_terms = [s.strip().lower() for s in education_keywords if s.strip()]
    def skill_score(value):
        candidate = str(value).lower()
        if not skills:
            return 100.0
        return 100.0 * sum(s in candidate for s in skills) / len(skills)
    def education_score(value):
        if not education_terms:
            return 100.0
        text = str(value).lower()
        return 100.0 if any(term in text for term in education_terms) else 0.0
    def experience_score(value):
        if min_experience <= 0:
            return 100.0
        return min(100.0, max(0.0, float(value) / min_experience * 100.0))
    def notice_score(value):
        if max_notice_days <= 0:
            return 100.0 if float(value) <= 0 else 0.0
        return 100.0 if float(value) <= max_notice_days else 0.0

    out["skill_score"] = out["skills"].apply(skill_score)
    out["experience_score"] = out["experience_years"].apply(experience_score)
    out["education_score"] = out["education"].apply(education_score)
    out["notice_score"] = out["notice_period_days"].apply(notice_score)
    out["match_score"] = (
        out["skill_score"] * 0.40 +
        out["experience_score"] * 0.30 +
        out["education_score"] * 0.15 +
        out["notice_score"] * 0.15
    ).round(1)
    out["screening_recommendation"] = out["match_score"].apply(
        lambda x: "Meets review threshold" if x >= threshold else "Below review threshold"
    )
    out["hr_review_status"] = "Pending HR review"
    return out.sort_values(["match_score", "full_name"], ascending=[False, True])

def extract_resume_text(pdf_bytes: bytes) -> str:
    """Extract selectable text from a PDF. Scanned PDFs need OCR, not included here."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_resume_text(text: str, filename: str) -> dict:
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?:\+?\d[\d\s().-]{8,}\d)", text)
    lower = text.lower()
    found_skills = [s for s in SKILL_BANK if s in lower]
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    name = ""
    for line in lines[:8]:
        if "@" not in line and not re.search(r"\d", line) and 1 < len(line.split()) <= 4:
            name = line[:100]
            break
    exp_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)", lower)
    exp = float(exp_match.group(1)) if exp_match else 0.0
    education = next((term for term in [
        "Bachelor of Engineering", "Bachelor of Technology", "Bachelor of Science",
        "Bachelor of Computer Applications", "Master of Business Administration",
        "Master of Science", "Master of Computer Applications", "Diploma"
    ] if term.lower() in lower), "Not detected")
    return {
        "candidate_id": "PDF-" + re.sub(r"\W+", "", filename)[:18],
        "full_name": name or Path(filename).stem,
        "email": emails[0] if emails else "",
        "phone": re.sub(r"\D", "", phones[0]) if phones else "",
        "education": education,
        "experience_years": exp,
        "skills": ", ".join(found_skills),
        "location": "Not detected",
        "notice_period_days": 30,
        "expected_salary": 0,
        "applied_role": "Not specified",
        "resume_file": filename
    }

"""Explainable, rule-based candidate matching. HR makes all final decisions."""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

SKILL_BANK = [
    "python", "java", "sql", "excel", "power bi", "tableau", "javascript",
    "html", "css", "react", "django", "flask", "machine learning",
    "communication", "project management", "testing", "git", "aws",
]

def screen_candidates(valid: pd.DataFrame, required_skills: list[str],
                      min_experience: float, education_keywords: list[str],
                      max_notice_days: float, threshold: float = 60.0) -> pd.DataFrame:
    output = valid.copy()
    skills = [skill.strip().lower() for skill in required_skills if skill.strip()]
    education_terms = [term.strip().lower() for term in education_keywords if term.strip()]

    def skill_score(value):
        candidate_skills = str(value).lower()
        if not skills:
            return 100.0
        return 100.0 * sum(skill in candidate_skills for skill in skills) / len(skills)

    def education_score(value):
        if not education_terms:
            return 100.0
        education = str(value).lower()
        return 100.0 if any(term in education for term in education_terms) else 0.0

    def experience_score(value):
        if min_experience <= 0:
            return 100.0
        return min(100.0, max(0.0, float(value) / min_experience * 100.0))

    def notice_score(value):
        if max_notice_days <= 0:
            return 100.0 if float(value) <= 0 else 0.0
        return 100.0 if float(value) <= max_notice_days else 0.0

    output["skill_score"] = output["skills"].apply(skill_score)
    output["experience_score"] = output["experience_years"].apply(experience_score)
    output["education_score"] = output["education"].apply(education_score)
    output["notice_score"] = output["notice_period_days"].apply(notice_score)
    output["match_score"] = (
        output["skill_score"] * 0.40
        + output["experience_score"] * 0.30
        + output["education_score"] * 0.15
        + output["notice_score"] * 0.15
    ).round(1)
    output["screening_recommendation"] = output["match_score"].apply(
        lambda score: "Meets review threshold" if score >= threshold else "Below review threshold"
    )
    output["hr_review_status"] = "Pending HR review"
    return output.sort_values(["match_score", "full_name"], ascending=[False, True])

def extract_resume_text(pdf_bytes: bytes) -> str:
    """Extract selectable PDF text. Scanned PDFs require OCR."""
    import fitz
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text("text") for page in document)

def parse_resume_text(text: str, filename: str) -> dict:
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?:\+?\d[\d\s().-]{8,}\d)", text)
    lowered = text.lower()
    found_skills = [skill for skill in SKILL_BANK if skill in lowered]
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    name = next((line[:100] for line in lines[:8]
                 if "@" not in line and not re.search(r"\d", line)
                 and 1 < len(line.split()) <= 4), "")
    experience_match = re.search(
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
        lowered,
    )
    experience = float(experience_match.group(1)) if experience_match else 0.0
    education = next((term for term in [
        "Bachelor of Engineering", "Bachelor of Technology", "Bachelor of Science",
        "Bachelor of Computer Applications", "Master of Business Administration",
        "Master of Science", "Master of Computer Applications", "Diploma",
    ] if term.lower() in lowered), "Not detected")
    return {
        "candidate_id": "PDF-" + re.sub(r"\W+", "", filename)[:18],
        "full_name": name or Path(filename).stem,
        "email": emails[0] if emails else "",
        "phone": re.sub(r"\D", "", phones[0]) if phones else "",
        "education": education,
        "experience_years": experience,
        "skills": ", ".join(found_skills),
        "location": "Not detected",
        "notice_period_days": 30,
        "expected_salary": 0,
        "applied_role": "Not specified",
        "resume_file": filename,
    }

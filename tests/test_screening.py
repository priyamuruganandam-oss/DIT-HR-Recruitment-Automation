import pandas as pd
import pytest
from src.validator import validate_candidates
from src.business_rules import screen_candidates

def valid_row(**overrides):
    row = {
        "candidate_id": "DIT-T001",
        "full_name": "Test Candidate",
        "email": "test.candidate@example.com",
        "phone": "9876543210",
        "education": "Bachelor of Engineering",
        "experience_years": 2,
        "skills": "Python, SQL",
        "location": "Chennai",
        "notice_period_days": 30,
        "expected_salary": 400000,
        "applied_role": "Python Developer",
    }
    row.update(overrides)
    return row

def test_valid_candidate_passes_validation():
    valid, exceptions = validate_candidates(pd.DataFrame([valid_row()]))
    assert len(valid) == 1
    assert len(exceptions) == 0

def test_invalid_email_is_flagged_as_exception():
    valid, exceptions = validate_candidates(pd.DataFrame([valid_row(email="not-an-email")]))
    assert len(valid) == 0
    assert "Invalid email" in exceptions.iloc[0]["validation_issues"]

def test_match_score_and_recommendation_are_created():
    valid, _ = validate_candidates(pd.DataFrame([valid_row()]))
    screened = screen_candidates(valid, ["python", "sql"], 2, ["Bachelor"], 60, 60)
    assert screened.iloc[0]["match_score"] == 100.0
    assert screened.iloc[0]["screening_recommendation"] == "Meets review threshold"

def test_missing_required_column_raises_error():
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_candidates(pd.DataFrame([{"candidate_id": "DIT-T001"}]))

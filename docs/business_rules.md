# HR Recruitment Automation System – Business Rules

## 1. Candidate Data Validation
- Candidate ID must be available.
- Candidate name must not be empty.
- Email must follow a valid email format.
- Phone number must contain at least 10 digits.
- Required candidate fields must be present.
- Duplicate email records must be identified.

## 2. Candidate Screening
- Candidates are evaluated based on required skills.
- Experience must exactly match the HR-defined minimum experience.
- Candidates with lower or higher experience than the specified value are not eligible.
- Education qualifications are checked against job requirements.
- Notice period is evaluated against the HR-defined maximum.
- A configurable match score threshold is used for screening recommendations.

## 3. Exact Experience Match Rule

The candidate's experience must be exactly equal to the experience value specified by HR.

Example: If HR sets Minimum Experience to 2 years:

| Candidate Experience | Eligibility |
|---|---|
| 1 year | Rejected |
| 2 years | Eligible |
| 2.5 years | Rejected |
| 3 years | Rejected |

Only candidates with exactly 2 years of experience can proceed to the remaining screening evaluation.

## 4. Match Score
- Skills: 40%
- Experience: 30%
- Education: 15%
- Notice Period: 15%

## 5. HR Review
- Screening results are recommendations only.
- Final candidate selection is made by the HR team.
- Candidate review status is maintained.

## 6. Reports
- Screening results can be exported as CSV and Excel files.
- Invalid candidate records are reported separately.
- Original input files must not be overwritten.

## 7. Data Privacy
- Use synthetic sample candidate data for demonstrations.
- Protect candidate personal information.
- Do not expose confidential candidate information.

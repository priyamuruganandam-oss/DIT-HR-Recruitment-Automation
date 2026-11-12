# DIT HR Recruitment Automation System

**DIT Internship 2026 | Project ID: DIT-P01**

## 1. Project Overview
The HR Recruitment Automation System is a browser-based application designed to help HR teams validate candidate information, process resumes, screen candidates using defined job requirements, and generate recruitment reports.

## 2. Objectives
- Automate candidate data validation.
- Identify missing, invalid, and duplicate records.
- Support resume PDF upload and text extraction.
- Match candidates against job requirements.
- Generate screening reports in CSV and Excel formats.
- Support transparent HR review and decision-making.

## 3. Key Features
- CSV and Excel candidate data upload.
- Candidate information validation.
- Duplicate and invalid record detection.
- Resume PDF processing.
- Skills and experience-based screening.
- Exact experience matching based on configured criteria.
- HR review and candidate reports.
- CSV and Excel report export.

## 4. Technologies Used
- Frontend: HTML, CSS, JavaScript
- Backend: Python, FastAPI
- Data Processing: Pandas
- Database: SQLite
- Deployment: Netlify and Render
- Version Control: GitHub

## 5. Project Structure
```text
DIT_HR_Recruitment_Automation/
├── frontend/
├── backend/
├── data/
│   ├── input/
│   ├── output/
│   └── sample/
├── src/
├── tests/
├── reports/
├── screenshots/
├── docs/
├── .gitignore
├── requirements.txt
└── README.md
```

## 6. Screening Rule
The system applies exact experience matching according to the configured minimum experience value. For example, if the required experience is 2 years, candidates with exactly 2 years pass this experience filter. Candidates with less or more experience do not pass this filter.

Other configured validation and screening rules are applied separately.

## 7. Human Review
The system provides decision-support results. Final recruitment and selection decisions must be made by authorized HR personnel.

## 8. Deployment
- Frontend: https://dit-hr-recruitment-automation.netlify.app
- Backend API: https://dit-hr-recruitment-automation.onrender.com
- API Documentation: https://dit-hr-recruitment-automation.onrender.com/docs

## 9. Documentation
Refer to the `docs/` folder for project structure, business rules, requirements, and test plan.

## 10. Team
DIT Internship 2026 – HR Recruitment Automation System.

**Institution:** Anjalai Ammal Mahalingam Engineering College, Kovilvenni, Thiruvarur.

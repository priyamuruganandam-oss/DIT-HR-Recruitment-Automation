# DIT HR Recruitment Automation — Netlify + Render

This package separates the browser website from its Python service:
- `frontend/` — responsive DIT-branded website hosted on Netlify.
- `backend/` — FastAPI service hosted on Render. It reuses the Python candidate validation and weighted screening engine from the supplied project.
- SQLite history is stored on a Render persistent disk, configured in `backend/render.yaml`.

## Deployment order

### A. Deploy the Python backend on Render
1. Push the complete extracted project folder to a GitHub repository. Keep both `frontend/` and `backend/`.
2. Open https://render.com and connect your GitHub account.
3. Create a **Blueprint** using this repository and choose `backend/render.yaml` if Render asks for the Blueprint file.
4. Deploy the `dit-hr-recruitment-api` service.
5. Copy the Render service URL, e.g. `https://dit-hr-recruitment-api.onrender.com`.
6. Test `https://YOUR-RENDER-URL/api/health`. It should return a JSON status of `ok`.

### B. Point the website to the backend
1. Open `frontend/app.js`.
2. At the top, replace `https://YOUR-BACKEND.onrender.com` with your actual Render service URL (no trailing slash).
3. Save and push this update to GitHub.

### C. Deploy the website on Netlify
1. Open https://app.netlify.com/ and choose **Add new site → Import an existing project**.
2. Select the GitHub repository.
3. Set **Base directory** blank, **Build command** blank, and **Publish directory** to `frontend`.
4. Deploy. Netlify will provide a public `*.netlify.app` link.

## Included features
- DIT logo and navy/blue professional responsive design
- Recruitment overview dashboard with KPI cards, match-score distribution chart and HR review pipeline
- Candidate CSV / XLSX upload
- Multiple text-based PDF resume upload and extraction
- Candidate validation and data-exception reporting
- Configurable role, skills, experience, education, notice period and score threshold
- Weighted match score: skills 40%, experience 30%, education 15%, notice 15%
- Candidate directory and search
- HR review status updates saved to backend SQLite
- CSV report exports

## Important limitations and safety
- This is an internship prototype and decision-support system, not a production hiring platform.
- Use synthetic or properly authorized candidate data only. Never commit real candidate resumes, personal information, database files, secrets or credentials to a public repository.
- HR must verify extracted details and make all interview/hiring decisions. Scores must not be used as automatic hiring decisions.
- PDF extraction is heuristic. Scanned PDFs need OCR.
- The included Render disk is intended to preserve SQLite data. Persistent-disk availability and pricing depend on the Render plan selected; confirm current plan details before deployment.
- Before handling real candidate information, add authentication, role-based access, privacy controls, backups, monitoring and rate limits.

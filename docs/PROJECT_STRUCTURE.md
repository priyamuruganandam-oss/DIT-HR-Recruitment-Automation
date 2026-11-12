# Project architecture

This project preserves the existing deployed website while aligning its source layout with the DIT Python coding standards.

- `data/input/`: approved input files for local runs.
- `data/output/`: locally generated processing results.
- `data/sample/`: synthetic demonstration CSV.
- `src/`: reusable Python modules for reading, validation, screening rules, logging, and reporting.
- `backend/`: FastAPI web API used by the existing website and deployed on Render.
- `frontend/`: existing DIT-branded dashboard deployed on Netlify.
- `tests/`: automated tests.
- `reports/`: reviewed reports.
- `screenshots/`: permitted test and demonstration evidence.
- `docs/`: technical documentation.

The API entry point remains `backend/main.py` so the current Render service can continue using `backend/` as its root directory. The frontend remains in `frontend/` so Netlify can continue publishing that directory. The reusable Python logic now lives in the top-level `src/` package and is imported by the API.

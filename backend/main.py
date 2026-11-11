import os, io, sqlite3, json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.engine import validate_candidates, screen_candidates, extract_resume_text, parse_resume_text

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "data" / "recruitment.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="DIT HR Recruitment API", version="1.1.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS screening_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT, full_name TEXT, email TEXT, phone TEXT,
            education TEXT, experience_years REAL, skills TEXT, location TEXT, notice_period_days REAL,
            expected_salary REAL, applied_role TEXT, email_valid INTEGER, validation_issues TEXT,
            skill_score REAL, experience_score REAL, education_score REAL, notice_score REAL,
            match_score REAL, screening_recommendation TEXT, hr_review_status TEXT, resume_file TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS current_dataset (
            id INTEGER PRIMARY KEY CHECK (id=1), rows_json TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS screening_exceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_json TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS screening_settings (
            id INTEGER PRIMARY KEY CHECK (id=1), settings_json TEXT NOT NULL)""")
init_db()

def clean(v):
    if pd.isna(v): return None
    if hasattr(v, "item"): v = v.item()
    return v

def records(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict(orient="records")]

def save_screening(screened, exceptions, raw_df, settings):
    now = datetime.now(timezone.utc).isoformat()
    if not screened.empty:
        screened = screened.copy()
        screened["created_at"] = now
    with connect() as c:
        # A new upload replaces the active dataset instead of appending to history.
        c.execute("DELETE FROM screening_results")
        c.execute("DELETE FROM screening_exceptions")
        if not screened.empty:
            for record in records(screened):
                keys = list(record.keys())
                c.execute("INSERT INTO screening_results (" + ",".join(keys) + ") VALUES (" +
                          ",".join(["?"] * len(keys)) + ")", [record[k] for k in keys])
        for record in records(exceptions):
            c.execute("INSERT INTO screening_exceptions (candidate_json) VALUES (?)",
                      (json.dumps(record, ensure_ascii=False),))
        raw_json = raw_df.to_json(orient="records", date_format="iso")
        c.execute("INSERT OR REPLACE INTO current_dataset (id, rows_json, updated_at) VALUES (1, ?, ?)",
                  (raw_json, now))
        c.execute("INSERT OR REPLACE INTO screening_settings (id, settings_json) VALUES (1, ?)",
                  (json.dumps(settings),))

def run_screening(raw_df, settings):
    valid, exceptions = validate_candidates(raw_df)
    screened = screen_candidates(
        valid,
        [x.strip() for x in settings["skills"].split(",") if x.strip()],
        float(settings["min_experience"]),
        [x.strip() for x in settings["education_keywords"].split(",") if x.strip()],
        float(settings["max_notice_days"]),
        float(settings["threshold"])
    )
    if not screened.empty:
        screened["applied_role"] = settings["role"]
    return screened, exceptions

def all_rows():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM screening_results ORDER BY match_score DESC, full_name ASC").fetchall()]

def all_exceptions():
    with connect() as c:
        rows = c.execute("SELECT candidate_json FROM screening_exceptions ORDER BY id ASC").fetchall()
    return [json.loads(r["candidate_json"]) for r in rows]

@app.get("/")
def root():
    return {"service":"DIT HR Recruitment API","status":"online"}

@app.get("/api/health")
def health():
    return {"status":"ok","service":"DIT HR Recruitment API"}

@app.post("/api/screen")
async def screen(candidate_file: Optional[UploadFile] = File(None), resumes: list[UploadFile] = File(default=[]),
                 role: str = Form("Python Developer"), skills: str = Form("Python, SQL"),
                 min_experience: float = Form(2), education_keywords: str = Form("Bachelor, Master, Diploma"),
                 max_notice_days: float = Form(60), threshold: float = Form(60)):
    frames = []
    if candidate_file:
        raw = await candidate_file.read()
        try:
            filename = (candidate_file.filename or "").lower()
            if filename.endswith(".csv"):
                frames.append(pd.read_csv(io.BytesIO(raw)))
            elif filename.endswith(".xlsx"):
                frames.append(pd.read_excel(io.BytesIO(raw)))
            else:
                raise HTTPException(400, "Candidate file must be CSV or XLSX.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Could not read candidate file: {e}")
    for f in resumes:
        if not (f.filename or "").lower().endswith(".pdf"): continue
        try:
            txt = extract_resume_text(await f.read())
            frames.append(pd.DataFrame([parse_resume_text(txt, f.filename)]))
        except Exception as e:
            raise HTTPException(400, f"Could not parse {f.filename}: {e}")
    if not frames:
        raise HTTPException(400, "Upload a candidate CSV/XLSX file or PDF resume.")
    combined = pd.concat(frames, ignore_index=True, sort=False)
    settings = {"role":role, "skills":skills, "min_experience":min_experience,
                "education_keywords":education_keywords, "max_notice_days":max_notice_days,
                "threshold":threshold}
    try:
        screened, exceptions = run_screening(combined, settings)
        save_screening(screened, exceptions, combined, settings)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"total_rows":len(combined), "candidates":records(screened),
            "exceptions":records(exceptions), "dataset_replaced":True, "settings":settings}

class RequirementsUpdate(BaseModel):
    role: str = "Python Developer"
    skills: str = "Python, SQL"
    min_experience: float = 2
    education_keywords: str = "Bachelor, Master, Diploma"
    max_notice_days: float = 60
    threshold: float = 60

@app.post("/api/requirements")
def update_requirements(data: RequirementsUpdate):
    with connect() as c:
        saved = c.execute("SELECT rows_json FROM current_dataset WHERE id=1").fetchone()
    if not saved:
        raise HTTPException(400, "Upload a candidate dataset before changing requirements.")
    try:
        raw_df = pd.read_json(io.StringIO(saved["rows_json"]), orient="records")
        settings = data.model_dump()
        screened, exceptions = run_screening(raw_df, settings)
        save_screening(screened, exceptions, raw_df, settings)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"total_rows":len(raw_df), "candidates":records(screened),
            "exceptions":records(exceptions), "settings":settings,
            "message":"Current dataset re-screened using the updated requirements."}

class ReviewUpdate(BaseModel):
    candidate_id: str
    hr_review_status: str

@app.post("/api/review")
def review(data: ReviewUpdate):
    allowed = {"Pending HR review","HR approved for interview","Hold","Not selected by HR"}
    if data.hr_review_status not in allowed:
        raise HTTPException(400, "Invalid HR review status.")
    with connect() as c:
        cur = c.execute("UPDATE screening_results SET hr_review_status=? WHERE candidate_id=?",
                        (data.hr_review_status, data.candidate_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Candidate not found.")
    return {"saved":True}

@app.get("/api/dashboard")
def dashboard():
    data = all_rows()
    exceptions = all_exceptions()
    df = pd.DataFrame(data)
    if df.empty:
        stats = {"total_candidates":len(exceptions),"valid_candidates":0,"average_match_score":0,
                 "pending_review":0,"status_counts":{},"matched_candidates":0,"rejected_candidates":0}
    else:
        status = df["hr_review_status"].fillna("Pending HR review").value_counts().to_dict()
        matched = int((df["screening_recommendation"] == "Meets review threshold").sum())
        rejected = int((df["screening_recommendation"] != "Meets review threshold").sum())
        stats = {"total_candidates":len(df)+len(exceptions),"valid_candidates":len(df),
                 "average_match_score":float(df["match_score"].mean()),
                 "pending_review":int((df["hr_review_status"].fillna("Pending HR review")=="Pending HR review").sum()),
                 "status_counts":{str(k):int(v) for k,v in status.items()},
                 "matched_candidates":matched,"rejected_candidates":rejected}
    with connect() as c:
        saved = c.execute("SELECT updated_at FROM current_dataset WHERE id=1").fetchone()
    return {"stats":stats,"candidates":data[:1000],"exceptions":exceptions[:1000],
            "updated_at":saved["updated_at"] if saved else None}

import os, io, sqlite3
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
app = FastAPI(title="DIT HR Recruitment API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS screening_results (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT, full_name TEXT, email TEXT, phone TEXT, education TEXT, experience_years REAL, skills TEXT, location TEXT, notice_period_days REAL, expected_salary REAL, applied_role TEXT, email_valid INTEGER, validation_issues TEXT, skill_score REAL, experience_score REAL, education_score REAL, notice_score REAL, match_score REAL, screening_recommendation TEXT, hr_review_status TEXT, resume_file TEXT, created_at TEXT)")
init_db()

def clean(v):
    if pd.isna(v): return None
    if hasattr(v, "item"): v = v.item()
    return v

def all_rows():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM screening_results ORDER BY id DESC").fetchall()]

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
            if candidate_file.filename.lower().endswith(".csv"):
                frames.append(pd.read_csv(io.BytesIO(raw)))
            elif candidate_file.filename.lower().endswith(".xlsx"):
                frames.append(pd.read_excel(io.BytesIO(raw)))
            else:
                raise HTTPException(400, "Candidate file must be CSV or XLSX.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Could not read candidate file: {e}")
    for f in resumes:
        if not f.filename.lower().endswith(".pdf"): continue
        try:
            txt = extract_resume_text(await f.read())
            frames.append(pd.DataFrame([parse_resume_text(txt, f.filename)]))
        except Exception as e:
            raise HTTPException(400, f"Could not parse {f.filename}: {e}")
    if not frames:
        raise HTTPException(400, "Upload a candidate CSV/XLSX file or PDF resume.")
    combined = pd.concat(frames, ignore_index=True, sort=False)
    try:
        valid, exceptions = validate_candidates(combined)
    except Exception as e:
        raise HTTPException(400, str(e))
    screened = screen_candidates(valid, [x.strip() for x in skills.split(",") if x.strip()],
                                 min_experience, [x.strip() for x in education_keywords.split(",") if x.strip()],
                                 max_notice_days, threshold)
    if not screened.empty:
        screened["applied_role"] = role
        screened["created_at"] = datetime.now(timezone.utc).isoformat()
        with connect() as c:
            for record in screened.to_dict(orient="records"):
                payload = {k: clean(v) for k, v in record.items()}
                keys = list(payload.keys())
                c.execute("INSERT INTO screening_results (" + ",".join(keys) + ") VALUES (" + ",".join(["?"]*len(keys)) + ")",
                          [payload[k] for k in keys])
    return {"total_rows":len(combined),
            "candidates":[{k:clean(v) for k,v in r.items()} for r in screened.to_dict(orient="records")],
            "exceptions":[{k:clean(v) for k,v in r.items()} for r in exceptions.to_dict(orient="records")]}

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
    df = pd.DataFrame(data)
    if df.empty:
        stats = {"total_candidates":0,"valid_candidates":0,"average_match_score":0,"pending_review":0,"status_counts":{}}
    else:
        status = df["hr_review_status"].fillna("Pending HR review").value_counts().to_dict()
        stats = {"total_candidates":len(df),"valid_candidates":len(df),
                 "average_match_score":float(df["match_score"].mean()),
                 "pending_review":int((df["hr_review_status"].fillna("Pending HR review")=="Pending HR review").sum()),
                 "status_counts":{str(k):int(v) for k,v in status.items()}}
    return {"stats":stats,"candidates":data[:500],"updated_at":data[0].get("created_at") if data else None}

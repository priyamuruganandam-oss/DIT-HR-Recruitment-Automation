from pathlib import Path
import io
import pandas as pd
import streamlit as st
import plotly.express as px
from src.engine import validate_candidates, screen_candidates, extract_resume_text, parse_resume_text
from src.database import save_screening, load_screening

st.set_page_config(page_title="DIT | HR Recruitment Automation", page_icon="👥", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
.hero {padding: 1.3rem 1.5rem; border-radius: 14px; background: linear-gradient(120deg,#14213d,#245b83); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0; font-size:2rem;}
.hero p {color:#e5edf5; margin:.4rem 0 0 0;}
.small-note {color:#667085; font-size:.88rem;}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>HR Recruitment Automation System</h1><p>Candidate data validation • Resume parsing • Transparent job matching • HR review</p></div>', unsafe_allow_html=True)
st.caption("DIT Internship 2026 | Python • Streamlit • Pandas • SQLite")

with st.sidebar:
    st.header("Job requirements")
    role = st.text_input("Job role", "Python Developer")
    skills_text = st.text_input("Required skills (comma-separated)", "Python, SQL")
    min_exp = st.number_input("Minimum experience (years)", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
    education_text = st.text_input("Accepted education keywords", "Bachelor, Master, Diploma")
    max_notice = st.number_input("Maximum notice period (days)", min_value=0, max_value=365, value=60)
    threshold = st.slider("Match score review threshold", 0, 100, 60)
    st.caption("Weights: Skills 40% • Experience 30% • Education 15% • Notice period 15%")

tab1, tab2, tab3 = st.tabs(["Candidate Screening", "HR Dashboard", "About & Guidance"])

with tab1:
    st.subheader("1. Upload candidate data")
    left, right = st.columns(2)
    with left:
        data_file = st.file_uploader("Upload CSV or Excel candidate sheet", type=["csv", "xlsx"], key="datafile")
    with right:
        resume_files = st.file_uploader("Upload PDF resumes (select multiple)", type=["pdf"], accept_multiple_files=True, key="resumes")
    st.info("Use synthetic or authorized candidate data only. PDF text extraction works with text-based PDFs; scanned PDFs need OCR.")
    if "screened" not in st.session_state:
        st.session_state.screened = pd.DataFrame()
    if st.button("Process Candidates", type="primary", use_container_width=True):
        frames = []
        if data_file:
            try:
                if data_file.name.lower().endswith(".csv"):
                    frames.append(pd.read_csv(data_file))
                else:
                    frames.append(pd.read_excel(data_file))
            except Exception as e:
                st.error(f"Could not read candidate file: {e}")
        if resume_files:
            parsed = []
            for f in resume_files:
                try:
                    txt = extract_resume_text(f.getvalue())
                    parsed.append(parse_resume_text(txt, f.name))
                except Exception as e:
                    st.warning(f"Could not parse {f.name}: {e}")
            if parsed:
                frames.append(pd.DataFrame(parsed))
        if not frames:
            st.warning("Please upload a CSV/Excel file or at least one PDF resume.")
        else:
            combined = pd.concat(frames, ignore_index=True, sort=False)
            try:
                valid, exceptions = validate_candidates(combined)
                screened = screen_candidates(
                    valid, skills_text.split(","), min_exp,
                    education_text.split(","), max_notice, threshold
                )
                if not screened.empty:
                    screened["applied_role"] = role
                    save_screening(screened)
                st.session_state.screened = screened
                st.session_state.exceptions = exceptions
                st.session_state.total_rows = len(combined)
                st.success("Processing completed. Recommendations are for HR review only.")
            except Exception as e:
                st.error(f"Validation issue: {e}")
                st.caption("Candidate spreadsheet must include: " + ", ".join([
                    "candidate_id","full_name","email","phone","education","experience_years",
                    "skills","location","notice_period_days","expected_salary","applied_role"
                ]))
    result = st.session_state.screened
    if not result.empty:
        exceptions = st.session_state.get("exceptions", pd.DataFrame())
        st.subheader("2. Screening results")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Uploaded records", st.session_state.get("total_rows", len(result)))
        c2.metric("Valid candidates", len(result))
        c3.metric("Data exceptions", len(exceptions))
        c4.metric("Meets review threshold", int((result.match_score >= threshold).sum()))
        st.dataframe(result, use_container_width=True, hide_index=True)
        st.subheader("HR review")
        choices = {}
        for idx, row in result.iterrows():
            choices[str(row["candidate_id"])] = st.selectbox(
                f'{row["full_name"]} — {row["match_score"]}%',
                ["Pending HR review", "HR approved for interview", "Hold", "Not selected by HR"],
                key=f"review_{idx}"
            )
        if st.button("Update HR review statuses"):
            result = result.copy()
            result["hr_review_status"] = result["candidate_id"].astype(str).map(choices)
            st.session_state.screened = result
            st.success("HR review statuses updated for this session.")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result.to_excel(writer, sheet_name="Screening Results", index=False)
            exceptions.to_excel(writer, sheet_name="Data Exceptions", index=False)
        st.download_button("Download Excel Screening Report", output.getvalue(),
                           file_name="HR_Screening_Report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        csv_bytes = result.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV Results", csv_bytes, "HR_Screening_Results.csv", "text/csv")

with tab2:
    st.subheader("Recruitment analytics")
    history = load_screening()
    if not history.empty:
        d1,d2,d3 = st.columns(3)
        d1.metric("Saved screening records", len(history))
        d2.metric("Average match score", f'{history["match_score"].mean():.1f}%')
        d3.metric("Unique candidates", history["candidate_id"].nunique())
        chart = px.histogram(history, x="match_score", nbins=10, title="Candidate match-score distribution")
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(history.tail(100), use_container_width=True, hide_index=True)
    else:
        st.info("Dashboard analytics will appear after you process candidate data.")

with tab3:
    st.subheader("System capabilities")
    st.markdown("""
- CSV / Excel candidate data upload
- Multiple text-based PDF resume extraction
- Required-field, email, phone and duplicate-email validation
- Configurable job criteria and weighted match score
- SQLite screening history
- HR review status tracking
- Excel and CSV report downloads
- Candidate analytics dashboard

**Important limitations:** PDF extraction is best-effort. Scanned image PDFs need OCR. Resume fields such as experience, education and skills may be missed or incorrectly extracted and must be checked by HR. Match scores are explainable screening support, not a hiring decision. Do not use protected characteristics or infer them from resumes.
""")
    st.subheader("Required spreadsheet columns")
    st.code("candidate_id, full_name, email, phone, education, experience_years, skills, location, notice_period_days, expected_salary, applied_role")
    st.caption("Sample data is synthetic and intended only for software testing.")

import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "recruitment.db"

def save_screening(df: pd.DataFrame, db_path=DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql("screening_results", conn, if_exists="append", index=False)

def load_screening(db_path=DB_PATH):
    if not Path(db_path).exists():
        return pd.DataFrame()
    with sqlite3.connect(db_path) as conn:
        try:
            return pd.read_sql_query("SELECT * FROM screening_results ORDER BY id DESC", conn)
        except Exception:
            return pd.DataFrame()

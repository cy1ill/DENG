import os
import logging
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

FILE_PATH = os.environ.get("CSV_PATH", "data/raw_credit_data.csv")
TABLE_NAME = os.environ.get("TABLE_NAME", "credit_risk_raw")

DB_URL = (
    f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
)

EXPECTED_COLUMNS = [
    "person_age",
    "person_income",
    "person_home_ownership",
    "person_emp_length",
    "loan_intent",
    "loan_grade",
    "loan_amnt",
    "loan_int_rate",
    "loan_status",
    "loan_percent_income",
    "cb_person_default_on_file",
    "cb_person_cred_hist_length",
]

def extract(path: str) -> pd.DataFrame:
    logging.info(f"Reading file: {path}")
    df = pd.read_csv(path)
    logging.info(f"Extracted {len(df):,} rows and {len(df.columns)} columns")
    return df

def validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    before = len(df)
    df = df.dropna(subset=["loan_status"])
    dropped = before - len(df)

    logging.info(f"Dropped {dropped:,} rows with null loan_status")
    logging.info(f"Validated {len(df):,} rows")
    return df

def load(df: pd.DataFrame, db_url: str, table_name: str) -> None:
    logging.info(f"Loading into table: {table_name}")
    engine = create_engine(db_url)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    logging.info(f"Loaded {len(df):,} rows into '{table_name}'")

def main() -> None:
    df = extract(FILE_PATH)
    df = validate(df)
    load(df, DB_URL, TABLE_NAME)
    logging.info("Ingestion complete.")

if __name__ == "__main__":
    main()
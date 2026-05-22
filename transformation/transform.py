"""Transformation: clean the raw credit risk data and load it into PostgreSQL."""
from pathlib import Path
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

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

RAW_FILE = DATA_DIR / "raw_credit_data.csv"
CLEAN_FILE = DATA_DIR / "cleaned_credit_data.csv"

TABLE_NAME = os.environ.get("CLEAN_TABLE_NAME", "credit_risk_cleaned")


def get_db_url() -> str:
    """Build the PostgreSQL connection URL from environment variables."""
    return (
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw data: impute missing employment length, drop null interest rates, remove age outliers."""
    df["emp_length_missing"] = df["person_emp_length"].isnull().astype(int)

    df["person_emp_length"] = df["person_emp_length"].fillna(
        df["person_emp_length"].median()
    )

    df = df.dropna(subset=["loan_int_rate"])

    df = df[df["person_age"] <= 85].copy()

    df.drop(columns=["emp_length_missing"], inplace=True)

    return df


def load_to_postgres(df: pd.DataFrame, db_url: str, table_name: str) -> None:
    """Write the cleaned DataFrame to a PostgreSQL table, replacing any existing table."""
    logging.info(f"Loading cleaned data into table: {table_name}")
    engine = create_engine(db_url)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    logging.info(f"Loaded {len(df):,} rows into '{table_name}'")


def main() -> None:
    """Run the transformation pipeline: read raw data, clean it, save a CSV, load to PostgreSQL."""
    logging.info(f"Reading raw data from: {RAW_FILE}")
    df = pd.read_csv(RAW_FILE)

    logging.info(f"Raw shape: {df.shape}")

    df_clean = transform_data(df)

    logging.info(f"Clean shape: {df_clean.shape}")
    logging.info(f"Saving cleaned data to: {CLEAN_FILE}")
    df_clean.to_csv(CLEAN_FILE, index=False)

    load_to_postgres(df_clean, get_db_url(), TABLE_NAME)

    logging.info("Transformation complete.")


if __name__ == "__main__":
    main()

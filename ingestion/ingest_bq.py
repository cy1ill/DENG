"""Data warehouse pipeline: read raw data from the GCS data lake, transform it,
and load it into a partitioned and clustered BigQuery table."""
import os
import sys
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transformation.transform import transform_data  # noqa: E402

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
BQ_DATASET = os.environ.get("BQ_DATASET", "credit_risk_dw")
BQ_TABLE = os.environ.get("BQ_TABLE", "credit_risk_clean")


def resolve_run_date() -> str:
    """Return the run date as YYYY-MM-DD (from RUN_DATE env, or today)."""
    raw = os.environ.get("RUN_DATE", "").strip()
    if not raw:
        return date.today().isoformat()
    # Kestra passes the trigger date; accept a plain date or an ISO datetime.
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()


def read_from_data_lake(bucket_name: str, run_date: str) -> pd.DataFrame:
    """Read the raw CSV for the given run date from the GCS data lake."""
    gcs_path = f"gs://{bucket_name}/raw/credit_risk_{run_date}.csv"
    logging.info(f"Reading from data lake: {gcs_path}")
    df = pd.read_csv(gcs_path)
    logging.info(f"Read {len(df):,} rows from data lake")
    return df


def load_to_bigquery(df: pd.DataFrame, table_id: str) -> None:
    """Load a DataFrame into a partitioned + clustered BigQuery table."""
    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY
        ),
        clustering_fields=["loan_grade", "loan_intent"],
    )

    logging.info(f"Loading {len(df):,} rows into {table_id}")
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    logging.info(f"Load complete: {table_id} now has {table.num_rows:,} rows")


def main() -> None:
    run_date = resolve_run_date()
    logging.info(f"Run date: {run_date}")

    df_raw = read_from_data_lake(BUCKET_NAME, run_date)
    df_clean = transform_data(df_raw)
    logging.info(
        f"Transformed {len(df_raw):,} raw rows into {len(df_clean):,} clean rows"
    )

    table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    load_to_bigquery(df_clean, table_id)
    logging.info("Data warehouse pipeline complete.")


if __name__ == "__main__":
    main()

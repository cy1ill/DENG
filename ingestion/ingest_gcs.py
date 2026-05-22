"""Data lake ingestion: upload the raw credit risk CSV to Google Cloud Storage."""
import os
import logging
from datetime import date, datetime

from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
LOCAL_FILE = os.environ.get("CSV_PATH", "data/raw_credit_data.csv")


def resolve_run_date() -> str:
    """Return the run date as YYYY-MM-DD (from RUN_DATE env, or today)."""
    raw = os.environ.get("RUN_DATE", "").strip()
    if not raw:
        return date.today().isoformat()
    # Kestra passes the trigger date; accept a plain date or an ISO datetime.
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()


def upload_to_gcs(local_path: str, bucket_name: str, run_date: str) -> str:
    """Upload a local file to gs://<bucket>/raw/credit_risk_<run_date>.csv."""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Source file not found: {local_path}")

    destination = f"raw/credit_risk_{run_date}.csv"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination)

    logging.info(f"Uploading {local_path} -> gs://{bucket_name}/{destination}")
    blob.upload_from_filename(local_path)
    logging.info(f"Upload complete: gs://{bucket_name}/{destination}")
    return f"gs://{bucket_name}/{destination}"


def main() -> None:
    run_date = resolve_run_date()
    logging.info(f"Run date: {run_date}")
    upload_to_gcs(LOCAL_FILE, BUCKET_NAME, run_date)
    logging.info("Data lake ingestion complete.")


if __name__ == "__main__":
    main()

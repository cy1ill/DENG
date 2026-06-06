# DENG

An end-to-end batch data engineering pipeline for a credit risk dataset. The local stack ingests, validates, transforms, and orchestrates the data with PostgreSQL, pgAdmin, Docker Compose, and Kestra. The cloud phase extends it to a Google Cloud Storage data lake and a BigQuery data warehouse, provisioned with Terraform.

Dataset source: Credit Risk Dataset (Kaggle)  
Source: https://www.kaggle.com/datasets/laotse/credit-risk-dataset/data
Source file used in this project: `data/raw_credit_data.csv`

---

## Project Goal

This project builds a reproducible local pipeline for a credit risk dataset.  
The pipeline:

1. reads a raw CSV file
2. validates the schema and required target column
3. loads raw data into PostgreSQL
4. applies cleaning transformations
5. writes cleaned data back to PostgreSQL
6. orchestrates the workflow with Kestra

---

## Use Case

**Persona — Maria, a Credit Risk Analyst at a mid-sized retail bank.**

**Why she needs a pipeline:** Maria currently pulls raw borrower CSVs by hand each reporting cycle and cleans them in a spreadsheet before passing them on. The process is slow, error-prone, and not reproducible — when the source format changes or an outlier slips through, the downstream default model trains on bad data.

**What problem it solves:** She needs an automated, repeatable pipeline that ingests raw credit-bureau data, applies consistent cleaning, and delivers a query-ready table, so every consumer works from the same trusted dataset.

**How she uses the processed data:** Maria queries the cleaned table to build risk segments — e.g. default rate by `loan_grade`, or high-risk borrowers by `loan_intent` — and hands the result to the data science team as training data for a loan-default prediction model. The cleaning decisions in this pipeline are driven directly by those queries.

---

## Dataset Overview

The dataset contains borrower demographics, financial information, loan characteristics, and the default target.

| Column | Description |
|---|---|
| `person_age` | Age of the borrower |
| `person_income` | Annual income |
| `person_home_ownership` | Home ownership status |
| `person_emp_length` | Employment length in years |
| `loan_intent` | Purpose of the loan |
| `loan_grade` | Risk grade of the loan |
| `loan_amnt` | Loan amount |
| `loan_int_rate` | Interest rate |
| `loan_status` | Target variable: 0 = no default, 1 = default |
| `loan_percent_income` | Loan amount as a share of income |
| `cb_person_default_on_file` | Historical default flag (`Y`/`N`) |
| `cb_person_cred_hist_length` | Credit history length |

### Known Data Quality Issues

This dataset contains several issues that are handled before analysis:

- `loan_status` (the target column) can be missing — such rows cannot be used for modelling
- `person_age` contains unrealistic outliers (e.g. ages of 144)
- `person_emp_length` contains missing values
- `loan_int_rate` contains missing values

`loan_status` is checked during ingestion; the remaining issues are handled in the transformation step.

---

## Pipeline Architecture

### Local pipeline flow

```text
raw_credit_data.csv
        |
        v
   ingestion/ingest.py
        |
        v
 PostgreSQL table:
   credit_risk_raw
        |
        v
transformation/transform.py
        |
        v
PostgreSQL table:
 credit_risk_cleaned
        |
        v
Kestra flow orchestrates the steps
````

### Components

* **Python** for ingestion and transformation
* **PostgreSQL** as local storage
* **pgAdmin** for database inspection
* **Docker Compose** to run the local stack
* **Kestra** to orchestrate and monitor the workflow

---

## Repository Structure

```text
DENG/
├── README.md
├── .env.example
├── .gitignore
├── data/
│   ├── raw_credit_data.csv
│   └── cleaned_credit_data.csv
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── kestra.Dockerfile
│   └── init/
│       └── 01-create-kestra-db.sql
├── docs/
│   └── screenshots/
├── ingestion/
│   ├── ingest.py              # local: CSV -> PostgreSQL
│   ├── ingest_gcs.py          # cloud: CSV -> GCS data lake
│   ├── ingest_bq.py           # cloud: GCS -> transform -> BigQuery
│   └── requirements.txt
├── transformation/
│   └── transform.py           # shared cleaning logic
├── orchestration/
│   └── flows/
│       ├── local_ingest.yaml
│       ├── credit_risk_pipeline.yaml
│       ├── gcs_ingestion.yaml
│       └── bq_pipeline.yaml
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── secrets/
│   └── README.md
└── notebooks/
    └── 01_data_loading_and_cleaning.ipynb
```

---

## Ingestion Step

The ingestion script is located at:

```text
ingestion/ingest.py
```

### What it does

* reads the raw CSV file
* checks that all expected columns are present
* drops rows with a null `loan_status` (the target column)
* loads the validated raw data into PostgreSQL

### Output table

```text
credit_risk_raw
```

### Validation logic

The ingestion step:

* verifies that every expected column is present, and fails fast if any are missing
* drops rows with a null `loan_status`, since the target column is required for modelling

This protects the pipeline from loading incomplete or invalid data into the raw table.

---

## Transformation Step

The transformation script is located at:

```text
transformation/transform.py
```

### What it does

The transformation step reads the raw data, applies cleaning logic, saves a cleaned CSV, and loads the result into PostgreSQL.

### Output table

```text
credit_risk_cleaned
```

### Transformations implemented

#### 1. Remove unrealistic ages

Rows with `person_age > 85` are removed.

**Why this helps:**
The raw data contains impossible ages (such as 144). These would distort age-based risk segments and bias model training. The same junk records also hold the dataset's other extreme outliers (e.g. `person_emp_length` of 123 years), so removing them cleans both fields at once.

#### 2. Impute missing employment length

Missing `person_emp_length` values are filled with the column median.

**Why this helps:**
Roughly 2.5% of rows have no employment length. Dropping them would discard otherwise-valid borrowers; imputing with the median keeps those rows usable and is robust to outliers.

#### 3. Remove rows with missing interest rate

Rows with a missing `loan_int_rate` are removed.

**Why this helps:**
Interest rate is a core risk signal needed for segmentation and model features. Unlike employment length it cannot be sensibly imputed, so incomplete rows are dropped.

---

## Docker Environment

The local stack is defined in:

```text
docker/docker-compose.yml
```

### Services

The Compose setup includes:

* `postgres`
* `pgadmin`
* `ingestion`
* `runner`
* `kestra`
* `kestra_importer`

### Purpose of each service

* **postgres**: stores raw and cleaned data
* **pgadmin**: UI to inspect PostgreSQL tables
* **ingestion**: runs the ingestion image
* **runner**: reusable container used to execute pipeline scripts manually and from Kestra
* **kestra**: orchestration and workflow monitoring
* **kestra_importer**: automatically imports the real pipeline flow into Kestra after startup

---

## Workflow Orchestration with Kestra

Kestra is used to orchestrate and monitor the local pipeline.

### Flow files
```text
orchestration/flows/local_ingest.yaml
orchestration/flows/credit_risk_pipeline.yaml
```

### Flow roles
* `credit_risk_local_ingest`: minimal bootstrap flow to ensure the `credit_risk` namespace is available
* `credit_risk_pipeline`: the real pipeline flow that validates the source file, runs ingestion, and runs transformation

### Automatic import behavior

* `local_ingest.yaml` is loaded automatically when Kestra starts
* `credit_risk_pipeline.yaml` is imported automatically by the `kestra_importer` service after Kestra becomes healthy

### Main pipeline tasks

The main pipeline flow contains these tasks:

1. `validate_source`
2. `ingest`
3. `transform`

### Scheduling and backfills

`credit_risk_pipeline` has a daily schedule trigger (`0 6 * * *`), so it runs on a regular basis without manual intervention. Past runs can be replayed from the Kestra UI via **Triggers → Backfill**, and a run can be triggered manually at any time from the flow page.

### Why Kestra is used

Kestra provides:

* workflow visibility
* task-level logging
* manual triggering
* reproducible orchestration
* easier pipeline demonstration for the project

---

## How to Run Locally

### Prerequisites

You need:

* Docker Desktop
* Docker Compose
* the dataset file in `data/raw_credit_data.csv`
* a `.env` file created from `.env.example`

### 1. Clone the repository

```bash
git clone https://github.com/cy1ill/DENG
cd DENG
```

### 2. Create your environment file

Create `.env` from `.env.example` and fill in your values.

Example:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=credit_risk
DB_USER=postgres
DB_PASSWORD=yourpassword
CSV_PATH=data/raw_credit_data.csv
TABLE_NAME=credit_risk_raw

KESTRA_DB_NAME=kestra
```

### 3. Place the dataset

Put the raw file here:

```text
data/raw_credit_data.csv
```

### 4. Start the local stack

Run from the repository root:

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

### 5. Open pgAdmin

Open:

```text
http://localhost:8080
```

pgAdmin login:

* Email: `admin@admin.com`
* Password: `admin`

Then add a PostgreSQL server with:

* Host: `postgres`
* Port: `5432`
* Username: value from `.env`
* Password: value from `.env`

### 6. Open Kestra

Open:

```text
http://localhost:8081/ui/
```

Kestra login:

* Username: `admin@kestra.io`
* Password: `Admin1234`

### 7. Verify Kestra flow import

In the Kestra UI, open namespace `credit_risk`.

You should see:

* `credit_risk_local_ingest`
* `credit_risk_pipeline`

### 8. Run the pipeline manually

In the Kestra UI:

* open namespace `credit_risk`
* select flow `credit_risk_pipeline`
* trigger an execution manually
* inspect the logs of each task

### 9. Verify outputs in PostgreSQL

Run these queries in pgAdmin:

```sql
SELECT COUNT(*) FROM credit_risk_raw;
SELECT COUNT(*) FROM credit_risk_cleaned;
SELECT * FROM credit_risk_cleaned LIMIT 20;
```

---

## Expected Outputs

After a successful run, you should have:

### In PostgreSQL

* `credit_risk_raw`
* `credit_risk_cleaned`

### In the local data folder

* `data/cleaned_credit_data.csv`

### In Kestra

* namespace `credit_risk`
* flow `credit_risk_local_ingest`
* flow `credit_risk_pipeline`
* a successful execution of `credit_risk_pipeline`
* green task states for:

  * `validate_source`
  * `ingest`
  * `transform`

---

## Verification Queries

### Check raw row count

```sql
SELECT COUNT(*) AS raw_count FROM credit_risk_raw;
```

### Check cleaned row count

```sql
SELECT COUNT(*) AS cleaned_count FROM credit_risk_cleaned;
```

### Check that age outliers are removed

```sql
SELECT MAX(person_age) AS max_age FROM credit_risk_cleaned;
```

### Check that employment length outliers are removed

```sql
SELECT MAX(person_emp_length) AS max_emp_length FROM credit_risk_cleaned;
```

### Preview cleaned rows

```sql
SELECT * FROM credit_risk_cleaned LIMIT 20;
```

---

## Cloud Pipeline (Final Phase)

The cloud phase extends the local pipeline to Google Cloud Platform:

* a **GCS data lake** that stores raw batch files
* a **BigQuery data warehouse** that holds the cleaned, query-ready table
* **Terraform** to provision both reproducibly
* two **Kestra cloud flows** that schedule and orchestrate the cloud pipelines

### Cloud Architecture

```text
                 raw_credit_data.csv
                         |
                         v
           ingestion/ingest_gcs.py          (data lake ingestion)
                         |
                         v
   GCS data lake:  gs://<bucket>/raw/credit_risk_<date>.csv
                         |
                         v
           ingestion/ingest_bq.py           (data warehouse pipeline)
                 |   reads raw file from GCS
                 |   applies transformation/transform.py
                 v
   BigQuery:  <project>.credit_risk_dw.credit_risk_clean
              partitioned by ingestion day
              clustered by loan_grade, loan_intent

   Terraform provisions the bucket and the dataset.
   Kestra schedules and orchestrates both pipelines.
```

### GCP Setup

You need a Google Cloud account (the free tier is sufficient).

1. Create a GCP project and note the **project ID**.
2. Enable the **Cloud Storage API** and the **BigQuery API**.
3. Create a **service account** with roles `Storage Admin` and `BigQuery Admin`.
4. Create a JSON key for that service account and download it.
5. Save the key as `secrets/gcp-key.json` (gitignored — never committed).
6. Set a billing alert (e.g. $5) so usage stays within the free tier.

Add the cloud values to your `.env` (template in `.env.example`):

```env
GCP_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_NAME=credit-risk-lake-yourname
BQ_DATASET=credit_risk_dw
BQ_TABLE=credit_risk_clean
```

### Provision Infrastructure with Terraform

The `terraform/` directory provisions the GCS bucket (data lake) and the
BigQuery dataset (data warehouse).

```bash
# authenticate with Application Default Credentials
gcloud auth application-default login

cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: set project_id and a globally unique bucket_name

terraform init       # downloads the Google provider
terraform plan       # previews the bucket + dataset
terraform apply      # creates the bucket + dataset
```

**Tear down when finished to avoid ongoing cloud costs:**

```bash
terraform destroy
```

| Variable | Description | Default |
|---|---|---|
| `project_id` | GCP project ID | (required) |
| `region` | Location for the bucket + dataset | `EU` |
| `bucket_name` | Globally unique data lake bucket name | (required) |
| `bq_dataset` | BigQuery dataset ID | `credit_risk_dw` |
| `credentials_file` | Optional path to a service account key | `""` (uses ADC) |

### Data Lake Ingestion Pipeline

Script: `ingestion/ingest_gcs.py`

It reads the raw CSV and uploads it to the GCS data lake under a dated path:

```text
gs://<bucket>/raw/credit_risk_<run_date>.csv
```

Every run — scheduled, backfilled, or manual — writes its own dated object, so
the data lake keeps an immutable history of each batch.

### Data Warehouse Transformation Pipeline

Script: `ingestion/ingest_bq.py`

It:

1. reads the dated raw file from the GCS data lake
2. applies the same cleaning logic as the local pipeline
   (`transformation/transform.py` — `transform_data()`)
3. loads the result into the BigQuery table `credit_risk_clean`

The local and cloud pipelines share one transformation function, so the
cleaned data is identical in PostgreSQL and in BigQuery.

### BigQuery Design Decisions

**Partitioning — ingestion-time, daily.**
The dataset has no natural event-time column (no application or loan-issue
date), so there is no field to time-partition on. The table uses
ingestion-time partitioning (`DAY`): BigQuery records each row's load time in
the `_PARTITIONTIME` pseudo-column. Each scheduled run lands in its own daily
partition, so an analyst can query only the latest load
(`WHERE DATE(_PARTITIONTIME) = CURRENT_DATE()`) instead of scanning every
historical load — fewer bytes scanned, lower cost.

**Clustering — `loan_grade`, then `loan_intent`.**
These are the two columns the credit risk analyst filters on most: building
risk segments by grade (e.g. high-risk D–G borrowers) and isolating loan
purposes (e.g. debt consolidation). Clustering co-locates rows with the same
grade and intent, so filtered queries scan only the relevant storage blocks.

*Note:* this dataset is small (~28k rows, far below 1 GB), so the real cost
saving is negligible. Partitioning and clustering are applied here to
demonstrate the production pattern the pipeline is designed around.

### Cloud Orchestration with Kestra

Two Kestra flows orchestrate the cloud pipelines:

| Flow | File | Schedule |
|---|---|---|
| `credit_risk_gcs_ingestion` | `orchestration/flows/gcs_ingestion.yaml` | monthly — `0 6 1 * *` |
| `credit_risk_bq_pipeline` | `orchestration/flows/bq_pipeline.yaml` | monthly — `0 7 1 * *` |

Both flows run their work inside the `credit_risk_runner` container, which
holds the GCP libraries and the mounted service account key. Kestra loads the
flows automatically from `orchestration/flows/`.

**Run a flow manually:** open the Kestra UI at `http://localhost:8081/ui/`,
namespace `credit_risk`, select the flow, and trigger an execution.

**Backfill:** open the flow, choose **Triggers → Backfill**, and select a date
range. Kestra replays the schedule for each past date; `ingest_gcs.py` writes
one dated file per backfilled date.

### BigQuery Verification Queries

Run these in the BigQuery console (replace `PROJECT` with your project ID):

```sql
-- 1. Row count
SELECT COUNT(*) AS total_rows
FROM `PROJECT.credit_risk_dw.credit_risk_clean`;

-- 2. Confirm cleaning: no ages above 85, no null interest rates
SELECT MAX(person_age) AS max_age,
       COUNTIF(loan_int_rate IS NULL) AS null_interest_rates
FROM `PROJECT.credit_risk_dw.credit_risk_clean`;

-- 3. Use case: default rate by loan grade
SELECT loan_grade,
       COUNT(*) AS loans,
       SUM(loan_status) AS defaults,
       ROUND(AVG(loan_status) * 100, 2) AS default_rate_pct
FROM `PROJECT.credit_risk_dw.credit_risk_clean`
GROUP BY loan_grade
ORDER BY loan_grade;

-- 4. Uses the clustered columns: high-risk debt-consolidation loans
SELECT loan_grade, loan_intent,
       COUNT(*) AS loans,
       ROUND(AVG(loan_int_rate), 2) AS avg_int_rate
FROM `PROJECT.credit_risk_dw.credit_risk_clean`
WHERE loan_grade IN ('D', 'E', 'F', 'G')
  AND loan_intent = 'DEBTCONSOLIDATION'
GROUP BY loan_grade, loan_intent
ORDER BY loan_grade;

-- 5. Query only the latest ingestion-time partition
SELECT COUNT(*) AS latest_partition_rows
FROM `PROJECT.credit_risk_dw.credit_risk_clean`
WHERE DATE(_PARTITIONTIME) = CURRENT_DATE();
```

---

## Screenshots / Evidence

Screenshots are stored in:

```text
docs/screenshots/
```

Examples of evidence to include:

* pgAdmin query result
* successful Kestra execution log
* running services / UI screenshots
* GCS bucket showing the dated raw file
* BigQuery table schema and a sample query result
* `terraform apply` output / GCP console showing the resources

---

## Troubleshooting

### Kestra fails with `Failed to initialize pool: The connection attempt failed`

Almost always one of three things:

1. **`.env` missing or incomplete.** Create it from `.env.example` and make sure
   `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `KESTRA_DB_NAME` are all set.
2. **Compose started without `--env-file`.** The compose file interpolates
   `${DB_USER}`, `${KESTRA_DB_NAME}` etc. at parse time. Without `--env-file .env`
   they become empty strings and Kestra tries to connect with no credentials and
   no database name. Always run from the repo root:
   ```bash
   docker compose --env-file .env -f docker/docker-compose.yml up --build
   ```
   The compose file now ships with sensible defaults
   (`${DB_USER:-postgres}` etc.) so a missing `.env` produces a working stack
   instead of silent failure, but you should still set your own `.env` for
   anything beyond a smoke test.
3. **Stale Postgres volume from a previous broken first start.** The init SQL
   in `docker/init/` runs only on a fresh data directory. The
   `kestra_db_init` one-shot service is a belt-and-braces guard that creates
   the Kestra metadata DB on every startup, so this failure mode is now
   prevented — but if you upgraded from an older version of this repo and
   are still seeing it, wipe the volumes and start fresh:
   ```bash
   docker compose -f docker/docker-compose.yml down -v
   docker compose --env-file .env -f docker/docker-compose.yml up --build
   ```

### Verifying that both databases exist

After the stack is up, you can confirm Postgres has both the data DB and the
Kestra metadata DB:

```bash
docker exec -it credit_risk_postgres psql -U postgres -l
```

You should see `credit_risk` **and** `kestra` in the list.

---

## Current Scope

### Completed — local phase

* dataset selection and use case
* ingestion pipeline
* Docker environment
* transformation logic
* local orchestration with Kestra
* automatic Kestra pipeline import

### Completed — cloud phase

* Terraform infrastructure (GCS bucket + BigQuery dataset)
* Cloud Storage data lake ingestion
* BigQuery transformation pipeline (partitioned + clustered)
* cloud orchestration with Kestra

---

## Tech Stack

* Python
* pandas
* SQLAlchemy
* PostgreSQL
* pgAdmin 4
* Docker
* Docker Compose
* Kestra
* Terraform
* Google Cloud Storage
* BigQuery

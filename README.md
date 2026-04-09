# DENG

A local data engineering pipeline for ingesting, validating, transforming, and orchestrating a credit risk dataset with PostgreSQL, pgAdmin, Docker Compose, and Kestra.

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
4. applies cleaning and feature engineering
5. writes cleaned data back to PostgreSQL
6. orchestrates the workflow with Kestra

---

## Use Case

A bank or lending company wants to decide whether a loan applicant is likely to default on a loan. Using historical borrower data such as income, employment length, loan amount, interest rate, and credit history, a machine learning model can predict the probability of default.

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

This dataset contains several issues that need to be handled before analysis:

- `person_age` contains unrealistic outliers above 85
- `person_emp_length` contains missing values
- `person_emp_length` contains unrealistic outliers above 60
- `loan_int_rate` contains missing values

These issues are handled in the transformation step.

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
│   ├── ingest.py
│   └── requirements.txt
├── orchestration/
│   └── flows/
│       ├── local_ingest.yaml
│       └── credit_risk_pipeline.yaml
├── transformation/
│   └── transform.py
├── notebooks/
│   └── 01_data_loading_and_cleaning.ipynb
└── terraform/
```

---

## Ingestion Step

The ingestion script is located at:

```text
ingestion/ingest.py
```

### What it does

* reads the raw CSV file
* checks that expected columns exist
* drops rows with null `person_emp_length`
* drops rows with null `loan_int_rate`
* loads the validated raw data into PostgreSQL

### Output table

```text
credit_risk_raw
```

### Validation logic

The ingestion step checks:

* expected schema is present

This protects the pipeline from loading incomplete or invalid data into the raw database table.

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

#### 1. Remove unrealistic ages above 85

Rows with `person_age > 85` are removed.

**Why this helps:**
Values above 85 are likely data entry errors and would distort borrower age analysis and downstream modeling.

#### 2. Remove unrealistic employment lengths above 60

Rows with `person_emp_length > 60` are removed.

**Why this helps:**
Employment lengths above 60 years are not realistic and would reduce trust in the cleaned dataset.

#### 3. Remove missing person_emp_length

Rows with missing `person_emp_length` are removed.

**Why this helps:**
This preserves more rows for analysis instead of dropping records unnecessarily.

#### 4. Remove rows with missing interest rate

Rows with missing `loan_int_rate` are removed.

**Why this helps:**
Interest rate is an important risk-related variable and is needed for segmentation and feature creation.

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

## Screenshots / Evidence

Screenshots are stored in:

```text
docs/screenshots/
```

Examples of evidence to include:

* pgAdmin query result
* successful Kestra execution log
* running services / UI screenshots

---

## Current Scope

### Completed local phases

* dataset selection and use case
* ingestion pipeline
* Docker environment
* transformation logic
* local orchestration with Kestra
* automatic Kestra pipeline import

### Planned next phases

* Terraform infrastructure
* Cloud Storage ingestion
* BigQuery loading and transformation
* final cloud architecture and presentation

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

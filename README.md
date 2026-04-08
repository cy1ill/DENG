# DENG

A local data engineering pipeline for ingesting, validating, transforming, and orchestrating a credit risk dataset with PostgreSQL, pgAdmin, Docker Compose, and Kestra.

Dataset source: Credit Risk Dataset (Kaggle)
Kaggle: https://www.kaggle.com/datasets/laotse/credit-risk-dataset
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

This is the local midterm part of the project. The later cloud phases will extend this pipeline to GCS, BigQuery, and Terraform. :contentReference[oaicite:1]{index=1}

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

This dataset has a few issues that need to be handled before analysis:

- `person_age` contains unrealistic outliers above 100
- `person_emp_length` contains missing values
- `person_emp_length` may contain unrealistic outliers above 60
- `loan_int_rate` may contain missing values
- `cb_person_default_on_file` is stored as `Y` / `N` instead of a numeric feature

These issues are explicitly addressed in the transformation step. :contentReference[oaicite:3]{index=3}

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
│       └── local_ingest.yaml
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
* drops rows with null `loan_status`
* loads the validated raw data into PostgreSQL

### Output table

```text
credit_risk_raw
```

### Validation logic

The ingestion step checks:

* expected schema is present
* `loan_status` is not null

This protects the pipeline from loading incomplete target data into the raw database table. 

---

## Transformation Step

The transformation script is located at:

```text
transformation/transform.py
```

### What it does

The transformation step reads the raw CSV, applies cleaning and feature engineering, saves a cleaned CSV, and loads the result into PostgreSQL.

### Output table

```text
credit_risk_cleaned
```

### Transformations implemented

#### 1. Remove unrealistic ages above 100

Rows with `person_age > 100` are removed.

**Why this helps:**
Values above 100 are likely data entry errors and would distort borrower age analysis and downstream modeling.

#### 2. Remove unrealistic employment lengths above 60

Rows with `person_emp_length > 60` are removed.

**Why this helps:**
Employment lengths above 60 years are not realistic and would reduce trust in the cleaned dataset.

#### 3. Impute missing employment length with the median

Missing `person_emp_length` values are filled with the median of the column.

**Why this helps:**
This preserves more rows for analysis instead of dropping records unnecessarily.

#### 4. Remove rows with missing interest rate

Rows with missing `loan_int_rate` are removed.

**Why this helps:**
Interest rate is an important risk-related variable and is needed for segmentation and feature creation.

#### 5. Create `debt_to_income`

A new feature is created:

```text
debt_to_income = loan_amnt / person_income
```

**Why this helps:**
Debt-to-income is a core credit risk indicator and supports both analysis and later ML use.

#### 6. Convert historical default flag into numeric form

`cb_person_default_on_file` is converted from `Y/N` into:

```text
has_historical_default
```

with values `1` or `0`.

**Why this helps:**
This makes filtering easier in SQL and prepares the feature for ML workflows.

#### 7. Create interest-rate bands

`loan_int_rate` is grouped into:

* Low
* Medium
* High

**Why this helps:**
This makes borrower segmentation easier for reporting and exploratory analysis. 

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

### Purpose of each service

* **postgres**: stores raw and cleaned data
* **pgadmin**: UI to inspect PostgreSQL tables
* **ingestion**: runs the ingestion image
* **runner**: reusable container used to execute pipeline scripts manually and from Kestra
* **kestra**: orchestration and workflow monitoring

This matches the project requirement to run the local pipeline in a reproducible Docker-based environment. 

---

## Workflow Orchestration with Kestra

The Kestra flow is defined in:

```text
orchestration/flows/local_ingest.yaml
```

### Flow ID

```text
credit_risk_local_ingest
```

### What the flow does

The flow has three main tasks:

1. **validate_source**
   checks that the raw CSV exists in the mounted workspace

2. **ingest**
   runs `ingestion/ingest.py` and loads raw data into PostgreSQL

3. **transform**
   runs `transformation/transform.py` and writes the cleaned table

### Scheduling

The flow includes a cron trigger:

```text
0 6 * * *
```

This means it is scheduled to run daily at 06:00.

### Why Kestra is used

Kestra provides:

* scheduled execution
* task-level logging
* workflow visibility
* manual triggering
* backfill support

This makes the local pipeline reproducible and monitorable. 

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
git clone <your-repo-url>
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

```bash
cd docker
docker compose up --build
```

### 5. Verify PostgreSQL and pgAdmin

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

### 6. Verify the raw table

Run this query in pgAdmin:

```sql
SELECT COUNT(*) FROM credit_risk_raw;
```

### 7. Verify the cleaned table

Run:

```sql
SELECT COUNT(*) FROM credit_risk_cleaned;
```

You can also preview rows:

```sql
SELECT * FROM credit_risk_cleaned LIMIT 20;
```

### 8. Open Kestra

Open:

```text
http://localhost:8081
```

### 9. Run the flow manually

In the Kestra UI:

* open namespace `credit_risk`
* select flow `credit_risk_local_ingest`
* trigger an execution manually
* inspect the logs of each task

### 10. Backfill

In Kestra, you can also create backfill runs for previous scheduled dates to demonstrate reproducibility and orchestration history. 

---

## Expected Outputs

After a successful run, you should have:

### In PostgreSQL

* `credit_risk_raw`
* `credit_risk_cleaned`

### In the local data folder

* `data/cleaned_credit_data.csv`

### In Kestra

* a successful execution of `credit_risk_local_ingest`
* green task states for:

  * `validate_source`
  * `ingest`
  * `transform`

---

## Verification Queries

### Check raw row count

```sql
SELECT COUNT(*) FROM credit_risk_raw;
```

### Check cleaned row count

```sql
SELECT COUNT(*) FROM credit_risk_cleaned;
```

### Check new engineered columns

```sql
SELECT
    debt_to_income,
    has_historical_default,
    rate_band
FROM credit_risk_cleaned
LIMIT 20;
```

### Check that age outliers are removed

```sql
SELECT MAX(person_age) FROM credit_risk_cleaned;
```

### Check that employment length outliers are removed

```sql
SELECT MAX(person_emp_length) FROM credit_risk_cleaned;
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

This supports reproducibility and peer review. 

---

## Reproducibility Notes

To make this project reproducible for another reviewer:

* all services are started via Docker Compose
* environment variables are documented in `.env.example`
* pipeline logic is separated into ingestion and transformation scripts
* orchestration is defined declaratively in a Kestra flow
* verification can be done through pgAdmin and Kestra UI

---

## Current Scope

### Completed local phases

* dataset selection and use case
* ingestion pipeline
* Docker environment
* transformation logic
* local orchestration with Kestra

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

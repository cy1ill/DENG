terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = var.credentials_file != "" ? file(var.credentials_file) : null
}

# Data Lake — Cloud Storage bucket holding the raw batch files.
resource "google_storage_bucket" "data_lake" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Drop superseded (non-current) object versions after 30 days.
  lifecycle_rule {
    condition {
      age        = 30
      with_state = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }
}

# Data Warehouse — BigQuery dataset holding the cleaned, query-ready table.
resource "google_bigquery_dataset" "data_warehouse" {
  dataset_id                 = var.bq_dataset
  location                   = var.region
  description                = "Credit risk data warehouse — cleaned table for default-risk analysis."
  delete_contents_on_destroy = true

  labels = {
    project = "credit-risk-pipeline"
    managed = "terraform"
  }
}

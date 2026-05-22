variable "project_id" {
  description = "GCP project ID where the data lake and warehouse are created."
  type        = string
}

variable "region" {
  description = "Location for the GCS bucket and BigQuery dataset (e.g. EU, US, europe-west6)."
  type        = string
  default     = "EU"
}

variable "bucket_name" {
  description = "Globally unique name for the GCS data lake bucket."
  type        = string
}

variable "bq_dataset" {
  description = "BigQuery dataset ID for the data warehouse."
  type        = string
  default     = "credit_risk_dw"
}

variable "credentials_file" {
  description = "Path to a GCP service account JSON key. Leave empty to use Application Default Credentials."
  type        = string
  default     = ""
}

output "data_lake_bucket" {
  description = "Name of the GCS data lake bucket."
  value       = google_storage_bucket.data_lake.name
}

output "data_lake_url" {
  description = "gs:// URL of the data lake bucket."
  value       = "gs://${google_storage_bucket.data_lake.name}"
}

output "bigquery_dataset" {
  description = "Fully qualified BigQuery dataset ID."
  value       = "${var.project_id}.${google_bigquery_dataset.data_warehouse.dataset_id}"
}

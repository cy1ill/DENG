# secrets/

Place your GCP service account key here as **`gcp-key.json`**.

The cloud pipeline (GCS ingestion and BigQuery load) reads it through the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable, which the `runner`
container sets to `/secrets/gcp-key.json`.

`*.json` is gitignored, so the key is never committed. See the project README
section "Cloud Setup (Final Phase)" for how to create the service account and
download the key.

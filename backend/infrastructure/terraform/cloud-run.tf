provider "google" {
  project = "infinitum-agent"
  region  = "europe-central1"  # Replace with your chosen region
}

resource "google_cloud_run_service" "default" {
  name     = "infinitum-agent"
  location = "europe-central1"  # Replace with your chosen region

  template {
    spec {
      containers {
        image = "gcr.io/infinitum-agent/backend:latest"  # Placeholder for now
      }
    }
  }
}
#!/bin/bash
# Deploy PSF Cloud Compute to Google Cloud Run.
# Prerequisites: gcloud CLI authenticated, Docker installed.
# Usage: ./cloud/deploy.sh <GCP_PROJECT_ID>

set -euo pipefail

PROJECT_ID="${1:?Usage: $0 <GCP_PROJECT_ID>}"
REGION="${2:-us-central1}"
SERVICE_NAME="psf-cloud-compute"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== Enable required APIs ==="
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com --project="${PROJECT_ID}"

echo "=== Build & push Docker image ==="
cd "$(dirname "$0")"
docker build -t "${IMAGE}" .
docker push "${IMAGE}"

echo "=== Deploy to Cloud Run ==="
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --platform=managed \
  --region="${REGION}" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --max-instances=5 \
  --allow-unauthenticated \
  --project="${PROJECT_ID}"

CLOUD_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")
echo ""
echo "=== Deployed ==="
echo "Cloud URL: ${CLOUD_URL}"
echo ""
echo "Set in your local environment:"
echo "  export PSF_CLOUD_URL=${CLOUD_URL}"

#!/bin/bash
# Deploy PSF Cloud Compute to Google Cloud Run.
# Prerequisites: gcloud CLI authenticated, Docker installed.
# Usage: PSF_CLOUD_SECRET=<random-token> ./cloud/deploy.sh <GCP_PROJECT_ID> [REGION]
#
# PSF_CLOUD_SECRET is REQUIRED: the service refuses all compute requests
# without it, so deploying without one would produce a broken service.
# Generate one with: openssl rand -hex 32
#
# The service is reachable unauthenticated so /health stays publicly
# probeable, but every /compute/* request must present X-API-Key
# matching PSF_CLOUD_SECRET (see server.py and SECURITY.md).  For a
# stricter posture, drop --allow-unauthenticated and grant
# roles/run.invoker to the caller identity instead.

set -euo pipefail

PROJECT_ID="${1:?Usage: PSF_CLOUD_SECRET=<token> $0 <GCP_PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"
SERVICE_NAME="psf-cloud-compute"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

PSF_CLOUD_SECRET="${PSF_CLOUD_SECRET:?Set PSF_CLOUD_SECRET to a random token (e.g. openssl rand -hex 32). Compute endpoints refuse requests without it.}"

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
  --set-env-vars="PSF_CLOUD_SECRET=${PSF_CLOUD_SECRET},PSF_RATE_LIMIT_BURST=30,PSF_RATE_LIMIT_RPS=5" \
  --project="${PROJECT_ID}"

CLOUD_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")
echo ""
echo "=== Deployed ==="
echo "Cloud URL: ${CLOUD_URL}"
echo ""
echo "Set in your local environment (the same secret value you deployed with):"
echo "  export PSF_CLOUD_URL=${CLOUD_URL}"
echo "  export PSF_CLOUD_SECRET=<your-secret>"

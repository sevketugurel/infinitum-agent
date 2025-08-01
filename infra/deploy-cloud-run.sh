#!/bin/bash

# Deployment script for Infinitum AI Agent to Google Cloud Run
# This script builds and deploys the application to Cloud Run

set -e

# Configuration
PROJECT_ID="infinitum-agent"
SERVICE_NAME="infinitum-ai-agent"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment of Infinitum AI Agent to Cloud Run${NC}"

# Check if required tools are installed
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud CLI is not installed${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}🔧 Setting up project: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔌 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Build the Docker image using Cloud Build
echo -e "${YELLOW}🏗️  Building Docker image...${NC}"
cd ../backend
gcloud builds submit --tag ${IMAGE_NAME} .

# Create secrets if they don't exist
echo -e "${YELLOW}🔐 Setting up secrets...${NC}"

# Check if secrets exist, create if they don't
if ! gcloud secrets describe serpapi-key &> /dev/null; then
    echo "Creating SERPAPI_KEY secret..."
    echo -n "Please enter your SerpAPI key: "
    read -s SERPAPI_KEY
    echo
    echo -n "${SERPAPI_KEY}" | gcloud secrets create serpapi-key --data-file=-
fi

if ! gcloud secrets describe gemini-key &> /dev/null; then
    echo "Creating GEMINI_API_KEY secret..."
    echo -n "Please enter your Gemini API key: "
    read -s GEMINI_KEY
    echo
    echo -n "${GEMINI_KEY}" | gcloud secrets create gemini-key --data-file=-
fi

# Create service account if it doesn't exist
echo -e "${YELLOW}👤 Setting up service account...${NC}"
SERVICE_ACCOUNT_EMAIL="infinitum-agent@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} &> /dev/null; then
    gcloud iam service-accounts create infinitum-agent \
        --display-name="Infinitum AI Agent Service Account" \
        --description="Service account for Infinitum AI Agent"
fi

# Grant necessary permissions
echo -e "${YELLOW}🔑 Granting permissions...${NC}"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/logging.logWriter"

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT_EMAIL} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --timeout 300 \
    --concurrency 10 \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "FIREBASE_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GEMINI_MODEL=gemini-2.5-pro" \
    --set-secrets "SERPAPI_API_KEY=serpapi-key:latest" \
    --set-secrets "GEMINI_API_KEY=gemini-key:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}🩺 Health check: ${SERVICE_URL}/healthz${NC}"
echo -e "${GREEN}📚 API documentation: ${SERVICE_URL}/docs${NC}"

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
if curl -f "${SERVICE_URL}/healthz" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${RED}❌ Health check failed. Check the logs:${NC}"
    echo "gcloud logs read --service=${SERVICE_NAME} --region=${REGION}"
fi

echo -e "${GREEN}🎉 Deployment complete! Your AI shopping assistant is now live.${NC}"
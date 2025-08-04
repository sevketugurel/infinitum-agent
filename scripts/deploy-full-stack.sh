#!/bin/bash

# Full-Stack Deployment Script for Infinitum AI Agent
# Deploys both frontend and backend to Google Cloud Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="infinitum-agent"
REGION="us-central1"
BACKEND_SERVICE_NAME="infinitum-ai-agent"
FRONTEND_BUCKET_NAME="infinitum-agent-frontend"

echo -e "${BLUE}🚀 Starting Full-Stack Deployment for Infinitum AI Agent${NC}"
echo "=================================================="

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}📋 Setting GCP project to ${PROJECT_ID}${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required Google Cloud APIs${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    firebase.googleapis.com \
    firestore.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com

# Deploy Backend
echo -e "${BLUE}🔧 Deploying Backend to Cloud Run${NC}"
echo "=================================="

cd backend

# Build and deploy backend
echo -e "${YELLOW}📦 Building backend Docker image${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE_NAME

echo -e "${YELLOW}🚀 Deploying backend to Cloud Run${NC}"
gcloud run deploy $BACKEND_SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=$PROJECT_ID" \
    --service-account infinitum-agent@$PROJECT_ID.iam.gserviceaccount.com

# Get backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE_NAME --region=$REGION --format="value(status.url)")
echo -e "${GREEN}✅ Backend deployed successfully at: $BACKEND_URL${NC}"

cd ..

# Deploy Frontend
echo -e "${BLUE}🎨 Deploying Frontend to Firebase Hosting${NC}"
echo "=========================================="

cd InfinitiumX

# Install dependencies
echo -e "${YELLOW}📦 Installing frontend dependencies${NC}"
npm install

# Create production environment file
echo -e "${YELLOW}⚙️ Creating production environment configuration${NC}"
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
VITE_WS_BASE_URL=${BACKEND_URL/https:/wss:}
VITE_FIREBASE_PROJECT_ID=$PROJECT_ID
VITE_FIREBASE_AUTH_DOMAIN=$PROJECT_ID.firebaseapp.com
VITE_FIREBASE_STORAGE_BUCKET=$PROJECT_ID.appspot.com
VITE_NODE_ENV=production
EOF

# Build frontend
echo -e "${YELLOW}🏗️ Building frontend for production${NC}"
npm run build

# Deploy to Firebase Hosting
echo -e "${YELLOW}🚀 Deploying frontend to Firebase Hosting${NC}"
if ! command -v firebase &> /dev/null; then
    echo -e "${YELLOW}Installing Firebase CLI${NC}"
    npm install -g firebase-tools
fi

# Initialize Firebase if not already done
if [ ! -f "firebase.json" ]; then
    echo -e "${YELLOW}🔧 Initializing Firebase project${NC}"
    firebase init hosting --project $PROJECT_ID
fi

firebase deploy --project $PROJECT_ID

# Get frontend URL
FRONTEND_URL="https://$PROJECT_ID.web.app"
echo -e "${GREEN}✅ Frontend deployed successfully at: $FRONTEND_URL${NC}"

cd ..

# Setup Vector Search (if not already done)
echo -e "${BLUE}🔍 Setting up Vector Search Infrastructure${NC}"
echo "============================================="

cd backend

if [ -f "infra/deploy-vector-search.sh" ]; then
    echo -e "${YELLOW}🚀 Deploying vector search infrastructure${NC}"
    chmod +x infra/deploy-vector-search.sh
    ./infra/deploy-vector-search.sh
else
    echo -e "${YELLOW}⚠️ Vector search deployment script not found, skipping${NC}"
fi

cd ..

# Create secrets in Secret Manager
echo -e "${BLUE}🔐 Setting up secrets in Secret Manager${NC}"
echo "======================================="

# Check if secrets exist, create if they don't
secrets_to_create=(
    "serpapi-key"
    "gemini-api-key"
    "openai-api-key"
    "firebase-web-api-key"
)

for secret in "${secrets_to_create[@]}"; do
    if ! gcloud secrets describe $secret &> /dev/null; then
        echo -e "${YELLOW}Creating secret: $secret${NC}"
        echo "REPLACE_WITH_ACTUAL_VALUE" | gcloud secrets create $secret --data-file=-
        echo -e "${RED}⚠️ Please update the secret '$secret' with the actual value:${NC}"
        echo "gcloud secrets versions add $secret --data-file=<path-to-secret-file>"
    else
        echo -e "${GREEN}✅ Secret '$secret' already exists${NC}"
    fi
done

# Final health check
echo -e "${BLUE}🏥 Performing health checks${NC}"
echo "============================"

echo -e "${YELLOW}Checking backend health...${NC}"
if curl -f "$BACKEND_URL/healthz" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
fi

echo -e "${YELLOW}Checking frontend accessibility...${NC}"
if curl -f "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${RED}❌ Frontend accessibility check failed${NC}"
fi

# Summary
echo -e "${GREEN}"
echo "=================================================="
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "=================================================="
echo -e "${NC}"
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo "• Backend URL: $BACKEND_URL"
echo "• Frontend URL: $FRONTEND_URL"
echo "• Project ID: $PROJECT_ID"
echo "• Region: $REGION"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Update secrets in Secret Manager with actual values"
echo "2. Configure Firebase Authentication providers"
echo "3. Set up monitoring and alerting"
echo "4. Configure custom domain (optional)"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "• View backend logs: gcloud run services logs tail $BACKEND_SERVICE_NAME --region=$REGION"
echo "• Update backend: gcloud run services update $BACKEND_SERVICE_NAME --region=$REGION"
echo "• View frontend: firebase hosting:channel:open live --project $PROJECT_ID"
echo ""
echo -e "${GREEN}✅ Full-stack deployment completed!${NC}"
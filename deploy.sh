#!/bin/bash

# Quick Deployment Script for Bakery Inventory Management System
# Assumes all secrets are already configured in Google Secret Manager

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deploying Bakery Inventory System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
SERVICE_NAME="bakery-inventory"
REGION="us-central1"

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}No project configured. Please enter your GCP Project ID:${NC}"
    read -p "Project ID: " PROJECT_ID
    gcloud config set project $PROJECT_ID
fi

echo -e "${GREEN}✓${NC} Using Project: ${PROJECT_ID}"

# Optional: Allow user to change region
echo -e "${YELLOW}Using region: ${REGION}${NC}"
read -p "Press Enter to use this region, or type a different region: " INPUT_REGION
if [ ! -z "$INPUT_REGION" ]; then
    REGION=$INPUT_REGION
fi

echo -e "${GREEN}✓${NC} Deploying to region: ${REGION}"
echo ""

# Check if Cloud SQL instance exists and get connection name
echo -e "${BLUE}Checking for Cloud SQL instance...${NC}"
DB_INSTANCE_NAME="bakery-db"

if gcloud sql instances describe $DB_INSTANCE_NAME --format="value(name)" 2>/dev/null; then
    INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")
    echo -e "${GREEN}✓${NC} Found Cloud SQL: ${INSTANCE_CONNECTION_NAME}"
    CLOUDSQL_FLAG="--add-cloudsql-instances $INSTANCE_CONNECTION_NAME"
else
    echo -e "${YELLOW}⚠${NC} No Cloud SQL instance found. Deploying without database connection."
    CLOUDSQL_FLAG=""
fi

echo ""
echo -e "${BLUE}Starting deployment...${NC}"
echo ""

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars FLASK_ENV=production \
    --set-secrets SECRET_KEY=flask-secret-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,DATABASE_URL=database-url:latest \
    $CLOUDSQL_FLAG \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")

echo -e "${GREEN}✓${NC} Service URL: ${SERVICE_URL}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Visit your application: ${SERVICE_URL}"
echo "2. Check health endpoint: ${SERVICE_URL}/health"
echo "3. View logs: gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
echo -e "${YELLOW}Note: Make sure your Google OAuth redirect URI includes:${NC}"
echo "   ${SERVICE_URL}/login/callback"
echo ""

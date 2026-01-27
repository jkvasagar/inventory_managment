#!/bin/bash

# Optimized Deployment Script for Bakery Inventory Management System
# Uses cached builds and only rebuilds when necessary

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Bakery Inventory - Fast Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
SERVICE_NAME="bakery-inventory"
REGION="asia-south1"
ARTIFACT_REPO="bakery-app"

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}No project configured. Please enter your GCP Project ID:${NC}"
    read -p "Project ID: " PROJECT_ID
    gcloud config set project $PROJECT_ID
fi

echo -e "${GREEN}✓${NC} Using Project: ${PROJECT_ID}"
echo -e "${GREEN}✓${NC} Region: ${REGION}"
echo ""

# Check if Cloud SQL instance exists
echo -e "${BLUE}Checking Cloud SQL instance...${NC}"
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

# Check if Artifact Registry repository exists
echo -e "${BLUE}Checking Artifact Registry...${NC}"
if ! gcloud artifacts repositories describe $ARTIFACT_REPO --location=$REGION &>/dev/null; then
    echo -e "${YELLOW}⚠${NC} Artifact Registry repository not found. Creating..."
    gcloud artifacts repositories create $ARTIFACT_REPO \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for Bakery Inventory app"
    echo -e "${GREEN}✓${NC} Created Artifact Registry repository"
else
    echo -e "${GREEN}✓${NC} Artifact Registry repository exists"
fi

IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/bakery-inventory"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Options${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Quick deploy (reuse latest image - no rebuild)"
echo "2. Build and deploy (rebuild Docker image)"
echo "3. Force rebuild (clear cache and rebuild)"
echo ""
read -p "Choose option [1-3] (default: 1): " DEPLOY_OPTION
DEPLOY_OPTION=${DEPLOY_OPTION:-1}

case $DEPLOY_OPTION in
    1)
        echo ""
        echo -e "${BLUE}Quick deploying with latest image...${NC}"
        echo -e "${YELLOW}Note: This reuses the existing Docker image${NC}"
        echo ""

        # Check if latest image exists
        if gcloud artifacts docker images list $IMAGE_NAME --filter="tags:latest" --format="value(package)" 2>/dev/null | grep -q "bakery-inventory"; then
            echo -e "${GREEN}✓${NC} Found latest image"

            # Deploy directly with existing image
            gcloud run deploy $SERVICE_NAME \
                --image ${IMAGE_NAME}:latest \
                --platform managed \
                --region $REGION \
                --allow-unauthenticated \
                --set-env-vars FLASK_ENV=production,GCP_PROJECT_ID=$PROJECT_ID \
                --set-secrets SECRET_KEY=flask-secret-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,DATABASE_URL=database-url:latest \
                $CLOUDSQL_FLAG \
                --memory 512Mi \
                --cpu 1 \
                --timeout 300 \
                --max-instances 10 \
                --min-instances 0
        else
            echo -e "${RED}✗${NC} No existing image found. Building..."
            DEPLOY_OPTION=2
        fi
        ;;

    2)
        echo ""
        echo -e "${BLUE}Building with cache and deploying...${NC}"
        echo ""

        # Build with Cloud Build using cache
        gcloud builds submit --tag ${IMAGE_NAME}:latest \
            --timeout=10m \
            --machine-type=e2-highcpu-8

        echo ""
        echo -e "${GREEN}✓${NC} Image built successfully"
        echo ""
        echo -e "${BLUE}Deploying to Cloud Run...${NC}"

        # Deploy with the new image
        gcloud run deploy $SERVICE_NAME \
            --image ${IMAGE_NAME}:latest \
            --platform managed \
            --region $REGION \
            --allow-unauthenticated \
            --set-env-vars FLASK_ENV=production,GCP_PROJECT_ID=$PROJECT_ID \
            --set-secrets SECRET_KEY=flask-secret-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,DATABASE_URL=database-url:latest \
            $CLOUDSQL_FLAG \
            --memory 512Mi \
            --cpu 1 \
            --timeout 300 \
            --max-instances 10 \
            --min-instances 0
        ;;

    3)
        echo ""
        echo -e "${BLUE}Force rebuilding (no cache)...${NC}"
        echo ""

        # Build without cache
        gcloud builds submit --tag ${IMAGE_NAME}:latest \
            --timeout=10m \
            --machine-type=e2-highcpu-8 \
            --no-cache

        echo ""
        echo -e "${GREEN}✓${NC} Image rebuilt successfully"
        echo ""
        echo -e "${BLUE}Deploying to Cloud Run...${NC}"

        # Deploy with the new image
        gcloud run deploy $SERVICE_NAME \
            --image ${IMAGE_NAME}:latest \
            --platform managed \
            --region $REGION \
            --allow-unauthenticated \
            --set-env-vars FLASK_ENV=production,GCP_PROJECT_ID=$PROJECT_ID \
            --set-secrets SECRET_KEY=flask-secret-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,DATABASE_URL=database-url:latest \
            $CLOUDSQL_FLAG \
            --memory 512Mi \
            --cpu 1 \
            --timeout 300 \
            --max-instances 10 \
            --min-instances 0
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")

echo -e "${GREEN}✓${NC} Service URL: ${SERVICE_URL}"
echo -e "${GREEN}✓${NC} Login page: ${SERVICE_URL}/login"
echo ""
echo -e "${BLUE}Important - OAuth Configuration:${NC}"
echo -e "${YELLOW}Add this redirect URI to Google Cloud Console:${NC}"
echo "   ${SERVICE_URL}/login/callback"
echo ""
echo "Go to: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "• View logs: gcloud run services logs read $SERVICE_NAME --region $REGION --limit=50"
echo "• Check status: ./check-oauth-setup.sh"
echo "• Stream logs: gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""

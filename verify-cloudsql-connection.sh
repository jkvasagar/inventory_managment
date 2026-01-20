#!/bin/bash

# Cloud Run and Cloud SQL Connection Verifier

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="bakery-inventory"
REGION="asia-south1"
PROJECT_ID="inventory-app-484515"
INSTANCE_CONNECTION="inventory-app-484515:asia-south1:bakery-db"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud Run & Cloud SQL Connection Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${BLUE}Checking Cloud Run configuration...${NC}"
echo ""

# Get Cloud SQL instances connected to Cloud Run
CLOUDSQL_INSTANCES=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(spec.template.metadata.annotations.'run.googleapis.com/cloudsql-instances')" 2>/dev/null)

if [ -z "$CLOUDSQL_INSTANCES" ]; then
    echo -e "${RED}✗${NC} No Cloud SQL instances connected to Cloud Run!"
    echo ""
    echo -e "${YELLOW}This is the problem!${NC} Cloud Run needs to be configured to connect to Cloud SQL."
    echo ""
    NEEDS_REDEPLOY=true
else
    echo -e "${GREEN}✓${NC} Cloud SQL instances connected: $CLOUDSQL_INSTANCES"

    if [[ "$CLOUDSQL_INSTANCES" == *"$INSTANCE_CONNECTION"* ]]; then
        echo -e "${GREEN}✓${NC} Correct instance is connected"
    else
        echo -e "${RED}✗${NC} Wrong instance connected!"
        echo -e "${YELLOW}Expected:${NC} $INSTANCE_CONNECTION"
        echo -e "${YELLOW}Got:${NC} $CLOUDSQL_INSTANCES"
        NEEDS_REDEPLOY=true
    fi
fi

echo ""

# Check if database-url secret is configured
echo -e "${BLUE}Checking secrets configuration...${NC}"
SECRETS=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(spec.template.spec.containers[0].env)" 2>/dev/null | grep -i database)

if [[ "$SECRETS" == *"DATABASE_URL"* ]]; then
    echo -e "${GREEN}✓${NC} DATABASE_URL secret is configured"
else
    echo -e "${RED}✗${NC} DATABASE_URL secret is NOT configured"
    NEEDS_REDEPLOY=true
fi

echo ""
echo -e "${BLUE}========================================${NC}"

if [ "$NEEDS_REDEPLOY" = true ]; then
    echo -e "${RED}  Action Required: Redeploy with Cloud SQL${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Your Cloud Run service is not configured to connect to Cloud SQL.${NC}"
    echo ""
    echo "Run this command to fix it:"
    echo ""
    echo "./deploy-gcp.sh"
    echo ""
    echo "Choose option 1 (Quick deploy)"
    echo ""
    echo "This will:"
    echo "  1. Connect Cloud Run to Cloud SQL instance"
    echo "  2. Configure DATABASE_URL secret"
    echo "  3. Enable the app to access the database"
else
    echo -e "${GREEN}  Configuration Looks Good${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Cloud Run is properly configured to connect to Cloud SQL."
    echo ""
    echo "If you're still seeing connection errors, check:"
    echo ""
    echo "1. Database and user exist:"
    echo "   ./check-cloudsql.sh"
    echo ""
    echo "2. Database password in secret is correct:"
    echo "   gcloud secrets versions access latest --secret=database-url --project=$PROJECT_ID"
    echo ""
    echo "3. Cloud SQL instance is running:"
    echo "   gcloud sql instances describe bakery-db --project=$PROJECT_ID --format='value(state)'"
fi

echo ""

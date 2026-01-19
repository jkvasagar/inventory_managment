#!/bin/bash

# Debug Cloud Run Deployment Script
# Use this when deployment is stuck in "initializing" state

set +e  # Don't exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="bakery-inventory"
REGION="asia-south1"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud Run Deployment Debugger${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check current deployment status
echo -e "${YELLOW}1. Checking current deployment status...${NC}"
gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.conditions[0].message)" 2>/dev/null || echo "Service not found or error"
echo ""

# Get latest revision
echo -e "${YELLOW}2. Getting latest revision...${NC}"
LATEST_REVISION=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.latestCreatedRevisionName)" 2>/dev/null)
echo "Latest revision: $LATEST_REVISION"
echo ""

# Check revision status
echo -e "${YELLOW}3. Checking revision status...${NC}"
if [ ! -z "$LATEST_REVISION" ]; then
    gcloud run revisions describe $LATEST_REVISION --region $REGION --format="table(status.conditions[0].type,status.conditions[0].status,status.conditions[0].message)"
fi
echo ""

# Show recent logs (last 2 minutes)
echo -e "${YELLOW}4. Checking recent logs for errors...${NC}"
echo -e "${BLUE}Looking for startup errors, tracebacks, and failures:${NC}"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND (severity>=ERROR OR textPayload=~\"Traceback\" OR textPayload=~\"Error\" OR textPayload=~\"Failed\")" \
    --limit=20 \
    --format="table(timestamp,severity,textPayload)" \
    --freshness=5m
echo ""

# Check if container is crashing
echo -e "${YELLOW}5. Checking for container crashes...${NC}"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND textPayload=~\"Container (crashed|failed|terminated)\"" \
    --limit=10 \
    --freshness=10m
echo ""

# Check health check status
echo -e "${YELLOW}6. Checking health check logs...${NC}"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND (textPayload=~\"/health\" OR httpRequest.requestUrl=~\"/health\")" \
    --limit=5 \
    --freshness=5m
echo ""

# Show all recent logs
echo -e "${YELLOW}7. Showing last 30 log entries...${NC}"
gcloud run services logs read $SERVICE_NAME --region $REGION --limit=30
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Troubleshooting Suggestions${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Common issues when stuck in 'initializing':${NC}"
echo ""
echo "1. DATABASE CONNECTION ISSUE"
echo "   - Cloud SQL instance might not be accessible"
echo "   - Database credentials in secrets might be wrong"
echo "   - Fix: Check DATABASE_URL secret"
echo ""
echo "2. MISSING SECRETS"
echo "   - Required secrets not found in Secret Manager"
echo "   - Fix: Verify all secrets exist:"
echo "   gcloud secrets list"
echo ""
echo "3. HEALTH CHECK FAILING"
echo "   - /health endpoint not responding"
echo "   - Fix: Check if /health endpoint works locally"
echo ""
echo "4. IMPORT ERRORS"
echo "   - Missing Python packages"
echo "   - Fix: Check requirements.txt includes all dependencies"
echo ""
echo "5. MEMORY/TIMEOUT ISSUES"
echo "   - Container taking too long to start"
echo "   - Fix: Increase memory or startup timeout"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review the logs above for specific errors"
echo "2. If you see database errors, check Cloud SQL connection"
echo "3. If stuck for >15 minutes, cancel and redeploy:"
echo "   gcloud run services delete $SERVICE_NAME --region $REGION"
echo "   ./deploy.sh"
echo ""

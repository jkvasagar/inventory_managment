#!/bin/bash

# Quick Cloud Run Logs Viewer
# Shows recent logs and useful diagnostic info

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="bakery-inventory"
REGION="asia-south1"
PROJECT_ID="inventory-app-484515"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud Run Logs - Recent Activity${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${BLUE}Fetching last 30 log entries...${NC}"
echo ""

gcloud run services logs read $SERVICE_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --limit=30 \
    --format="table(timestamp.datetime('%Y-%m-%d %H:%M:%S'),severity,textPayload)"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Useful Log Commands${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Stream logs in real-time:${NC}"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION --project $PROJECT_ID"
echo ""
echo -e "${YELLOW}View errors only:${NC}"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION --limit=50 --filter='severity>=ERROR' --project $PROJECT_ID"
echo ""
echo -e "${YELLOW}Search for OAuth logs:${NC}"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION --limit=100 --project $PROJECT_ID | grep -i oauth"
echo ""
echo -e "${YELLOW}Web console:${NC}"
echo "  https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID"
echo ""

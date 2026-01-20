#!/bin/bash

# OAuth Configuration Verification Script
# This helps debug OAuth configuration issues

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  OAuth Configuration Debugger${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

PROJECT_ID="inventory-app-484515"
SERVICE_NAME="bakery-inventory"
REGION="asia-south1"

# Get Cloud Run URL
echo -e "${BLUE}1. Checking Cloud Run service...${NC}"
if ! gcloud run services describe $SERVICE_NAME --region $REGION &>/dev/null; then
    echo -e "${RED}✗${NC} Service not deployed"
    exit 1
fi

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
REDIRECT_URI="${SERVICE_URL}/login/callback"

echo -e "${GREEN}✓${NC} Service URL: ${SERVICE_URL}"
echo -e "${GREEN}✓${NC} Expected redirect URI: ${REDIRECT_URI}"
echo ""

# Check Secret Manager
echo -e "${BLUE}2. Checking Secret Manager credentials...${NC}"

CLIENT_ID=$(gcloud secrets versions access latest --secret="google-client-id" --project=$PROJECT_ID 2>/dev/null)
if [ -z "$CLIENT_ID" ]; then
    echo -e "${RED}✗${NC} Cannot read google-client-id from Secret Manager"
    exit 1
fi

echo -e "${GREEN}✓${NC} Client ID in Secret Manager: ${CLIENT_ID}"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ACTION REQUIRED${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Go to Google Cloud Console and verify:${NC}"
echo ""
echo "1. Open: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
echo ""
echo "2. Find the OAuth 2.0 Client with this Client ID:"
echo -e "   ${GREEN}${CLIENT_ID}${NC}"
echo ""
echo "3. Click on it to edit"
echo ""
echo "4. Scroll to 'Authorized redirect URIs' and verify it has EXACTLY:"
echo -e "   ${GREEN}${REDIRECT_URI}${NC}"
echo ""
echo "5. Check for common issues:"
echo "   - No trailing slash: ${REDIRECT_URI%/} ✓ (correct)"
echo "   - Not: ${REDIRECT_URI}/ ✗ (wrong - has trailing slash)"
echo "   - Not: http://${SERVICE_URL#https://}/login/callback ✗ (wrong - uses http)"
echo ""
echo "6. If the redirect URI is correct, make sure you clicked 'SAVE'"
echo ""
echo "7. If you have multiple OAuth clients, make sure you're editing the one with Client ID:"
echo "   ${CLIENT_ID}"
echo ""
echo -e "${YELLOW}After verifying, wait 1-2 minutes and try again.${NC}"
echo ""

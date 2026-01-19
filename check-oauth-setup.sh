#!/bin/bash

# OAuth Setup Checker for Cloud Run
# This script helps you configure OAuth redirect URIs correctly

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="bakery-inventory"
REGION="asia-south1"
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  OAuth Configuration Checker${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if service is deployed
echo -e "${BLUE}Checking Cloud Run service...${NC}"
if ! gcloud run services describe $SERVICE_NAME --region $REGION &>/dev/null; then
    echo -e "${RED}✗${NC} Service '$SERVICE_NAME' not found in region '$REGION'"
    echo ""
    echo "Deploy your service first:"
    echo "  ./deploy.sh"
    exit 1
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
echo -e "${GREEN}✓${NC} Service is deployed at: ${SERVICE_URL}"
echo ""

# Calculate redirect URI
REDIRECT_URI="${SERVICE_URL}/login/callback"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Required OAuth Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Add this redirect URI to Google Cloud Console:${NC}"
echo ""
echo -e "  ${GREEN}${REDIRECT_URI}${NC}"
echo ""

echo -e "${BLUE}Steps:${NC}"
echo "1. Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo "2. Click on your OAuth 2.0 Client ID"
echo "3. Under 'Authorized redirect URIs', click '+ ADD URI'"
echo "4. Paste: ${REDIRECT_URI}"
echo "5. Click SAVE"
echo ""

# Check if secrets exist
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Checking Secret Manager${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

for secret in google-client-id google-client-secret flask-secret-key database-url; do
    if gcloud secrets describe $secret &>/dev/null; then
        echo -e "${GREEN}✓${NC} $secret exists"
    else
        echo -e "${RED}✗${NC} $secret is missing"
        MISSING_SECRETS=true
    fi
done

if [ "$MISSING_SECRETS" = true ]; then
    echo ""
    echo -e "${YELLOW}Some secrets are missing. Run:${NC}"
    echo "  ./setup-secrets.sh"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Testing Endpoints${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test health endpoint
echo -e "${BLUE}Testing health endpoint...${NC}"
if curl -s "${SERVICE_URL}/health" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Health endpoint is responding"
else
    echo -e "${YELLOW}⚠${NC} Health endpoint not responding (service might still be starting)"
fi

# Test login page
echo -e "${BLUE}Testing login page...${NC}"
if curl -s "${SERVICE_URL}/login" | grep -q "Sign in"; then
    echo -e "${GREEN}✓${NC} Login page is accessible"
else
    echo -e "${YELLOW}⚠${NC} Login page check inconclusive"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service URL: ${SERVICE_URL}"
echo "Login page: ${SERVICE_URL}/login"
echo "Required redirect URI: ${REDIRECT_URI}"
echo ""
echo -e "${YELLOW}After adding the redirect URI to Google Cloud Console,${NC}"
echo -e "${YELLOW}test the OAuth login at: ${SERVICE_URL}/login${NC}"
echo ""

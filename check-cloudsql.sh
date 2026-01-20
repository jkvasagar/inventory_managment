#!/bin/bash

# Cloud SQL Database Configuration Checker

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ID="inventory-app-484515"
INSTANCE_NAME="bakery-db"
DB_NAME="bakery_inventory"
DB_USER="bakery_user"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud SQL Configuration Checker${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check instance status
echo -e "${BLUE}1. Checking Cloud SQL instance...${NC}"
STATE=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(state)")
echo -e "${GREEN}✓${NC} Instance: $INSTANCE_NAME"
echo -e "${GREEN}✓${NC} State: $STATE"
echo ""

# Check if database exists
echo -e "${BLUE}2. Checking if database exists...${NC}"
if gcloud sql databases describe $DB_NAME --instance=$INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    echo -e "${GREEN}✓${NC} Database '$DB_NAME' exists"
else
    echo -e "${RED}✗${NC} Database '$DB_NAME' does NOT exist"
    echo ""
    echo -e "${YELLOW}Create it with:${NC}"
    echo "  gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME --project=$PROJECT_ID"
    DB_MISSING=true
fi
echo ""

# Check if user exists
echo -e "${BLUE}3. Checking if database user exists...${NC}"
if gcloud sql users list --instance=$INSTANCE_NAME --project=$PROJECT_ID --format="value(name)" | grep -q "^$DB_USER$"; then
    echo -e "${GREEN}✓${NC} User '$DB_USER' exists"
else
    echo -e "${RED}✗${NC} User '$DB_USER' does NOT exist"
    echo ""
    echo -e "${YELLOW}Create it with:${NC}"
    echo "  gcloud sql users create $DB_USER --instance=$INSTANCE_NAME --password=YOUR_PASSWORD --project=$PROJECT_ID"
    USER_MISSING=true
fi
echo ""

# Check database-url secret
echo -e "${BLUE}4. Checking database-url secret...${NC}"
if gcloud secrets describe database-url --project=$PROJECT_ID &>/dev/null; then
    echo -e "${GREEN}✓${NC} Secret 'database-url' exists"
    echo ""
    echo -e "${YELLOW}Database URL format should be:${NC}"
    echo "  postgresql://bakery_user:PASSWORD@/bakery_inventory?host=/cloudsql/inventory-app-484515:asia-south1:bakery-db"
else
    echo -e "${RED}✗${NC} Secret 'database-url' does NOT exist"
    SECRET_MISSING=true
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$DB_MISSING" = true ] || [ "$USER_MISSING" = true ] || [ "$SECRET_MISSING" = true ]; then
    echo -e "${YELLOW}Action required:${NC}"
    echo ""

    if [ "$DB_MISSING" = true ]; then
        echo "1. Create database:"
        echo "   gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME --project=$PROJECT_ID"
        echo ""
    fi

    if [ "$USER_MISSING" = true ]; then
        echo "2. Create database user (choose a strong password):"
        echo "   gcloud sql users create $DB_USER --instance=$INSTANCE_NAME --password=YOUR_STRONG_PASSWORD --project=$PROJECT_ID"
        echo ""
    fi

    if [ "$SECRET_MISSING" = true ] || [ "$DB_MISSING" = true ] || [ "$USER_MISSING" = true ]; then
        echo "3. Update database-url secret:"
        echo "   After creating database and user, run:"
        echo "   echo -n 'postgresql://bakery_user:YOUR_PASSWORD@/bakery_inventory?host=/cloudsql/inventory-app-484515:asia-south1:bakery-db' | \\"
        echo "     gcloud secrets versions add database-url --data-file=- --project=$PROJECT_ID"
        echo ""
    fi

    echo "4. Redeploy Cloud Run:"
    echo "   ./deploy-gcp.sh"
    echo "   Choose option 1 (Quick deploy)"
else
    echo -e "${GREEN}✓ All Cloud SQL components are configured!${NC}"
    echo ""
    echo "If still having connection issues, verify:"
    echo "1. Cloud Run has Cloud SQL connection configured"
    echo "2. Database password in secret matches the user password"
fi
echo ""

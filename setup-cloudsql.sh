#!/bin/bash

# =============================================================
# Script: setup-cloudsql.sh
# Description: Create Cloud Storage bucket and Cloud SQL instance
# Cost: ~₹580/month (~$7/month)
# =============================================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud SQL Setup Script${NC}"
echo -e "${BLUE}  Instance: db-f1-micro (~₹580/mo)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project configured${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✓${NC} Project: ${PROJECT_ID}"

# Configuration
REGION="asia-south1"
INSTANCE_NAME="bakery-db-new"
DATABASE_NAME="bakery"
DB_USER="bakery_user"
BUCKET_NAME="${PROJECT_ID}-db-backup"

echo -e "${GREEN}✓${NC} Region: ${REGION}"
echo -e "${GREEN}✓${NC} Instance: ${INSTANCE_NAME}"
echo -e "${GREEN}✓${NC} Database: ${DATABASE_NAME}"
echo ""

# Prompt for database password
echo -e "${YELLOW}Enter password for database user (${DB_USER}):${NC}"
read -s DB_PASSWORD
echo ""

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Error: Password cannot be empty${NC}"
    exit 1
fi

echo -e "${YELLOW}Confirm password:${NC}"
read -s DB_PASSWORD_CONFIRM
echo ""

if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}Error: Passwords do not match${NC}"
    exit 1
fi

# =============================================================
# Step 1: Create backup bucket
# =============================================================
echo ""
echo -e "${BLUE}Step 1: Creating backup bucket...${NC}"

if gcloud storage buckets describe gs://${BUCKET_NAME} &>/dev/null; then
    echo -e "${GREEN}✓${NC} Bucket already exists: ${BUCKET_NAME}"
else
    gcloud storage buckets create gs://${BUCKET_NAME} \
        --location=${REGION} \
        --uniform-bucket-level-access
    echo -e "${GREEN}✓${NC} Created bucket: ${BUCKET_NAME}"
fi

# =============================================================
# Step 2: Create Cloud SQL instance
# =============================================================
echo ""
echo -e "${BLUE}Step 2: Creating Cloud SQL instance (db-f1-micro)...${NC}"
echo -e "${YELLOW}This will take 5-10 minutes...${NC}"

if gcloud sql instances describe ${INSTANCE_NAME} &>/dev/null; then
    echo -e "${GREEN}✓${NC} Instance ${INSTANCE_NAME} already exists"
else
    gcloud sql instances create ${INSTANCE_NAME} \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=${REGION} \
        --edition=ENTERPRISE \
        --storage-type=HDD \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --availability-type=ZONAL \
        --root-password="${DB_PASSWORD}"

    echo -e "${GREEN}✓${NC} Created instance: ${INSTANCE_NAME}"
fi

# =============================================================
# Step 3: Create database
# =============================================================
echo ""
echo -e "${BLUE}Step 3: Creating database...${NC}"

if gcloud sql databases describe ${DATABASE_NAME} --instance=${INSTANCE_NAME} &>/dev/null; then
    echo -e "${GREEN}✓${NC} Database ${DATABASE_NAME} already exists"
else
    gcloud sql databases create ${DATABASE_NAME} --instance=${INSTANCE_NAME}
    echo -e "${GREEN}✓${NC} Created database: ${DATABASE_NAME}"
fi

# =============================================================
# Step 4: Create user
# =============================================================
echo ""
echo -e "${BLUE}Step 4: Creating database user...${NC}"

if gcloud sql users list --instance=${INSTANCE_NAME} --format="value(name)" | grep -q "^${DB_USER}$"; then
    echo -e "${GREEN}✓${NC} User ${DB_USER} already exists"
else
    gcloud sql users create ${DB_USER} \
        --instance=${INSTANCE_NAME} \
        --password="${DB_PASSWORD}"
    echo -e "${GREEN}✓${NC} Created user: ${DB_USER}"
fi

# =============================================================
# Step 5: Update Secret Manager
# =============================================================
echo ""
echo -e "${BLUE}Step 5: Setting up DATABASE_URL secret...${NC}"

CONNECTION_NAME="${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${DATABASE_NAME}?host=/cloudsql/${CONNECTION_NAME}"

# Check if secret exists
if gcloud secrets describe database-url &>/dev/null; then
    echo "${DATABASE_URL}" | gcloud secrets versions add database-url --data-file=-
    echo -e "${GREEN}✓${NC} Updated secret: database-url"
else
    echo "${DATABASE_URL}" | gcloud secrets create database-url --data-file=-
    echo -e "${GREEN}✓${NC} Created secret: database-url"
fi

# =============================================================
# Step 6: Grant Cloud Run access to secret
# =============================================================
echo ""
echo -e "${BLUE}Step 6: Granting Cloud Run access to secrets...${NC}"

# Get the compute service account
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"
COMPUTE_SA="$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

# Grant access to database-url secret
gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || true

echo -e "${GREEN}✓${NC} Granted secret access to Cloud Run"

# =============================================================
# Summary
# =============================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Instance Details:${NC}"
echo "  Name:            ${INSTANCE_NAME}"
echo "  Connection:      ${CONNECTION_NAME}"
echo "  Database:        ${DATABASE_NAME}"
echo "  User:            ${DB_USER}"
echo "  Tier:            db-f1-micro"
echo "  Storage:         10GB HDD"
echo "  Region:          ${REGION}"
echo ""
echo -e "${BLUE}Bucket Details:${NC}"
echo "  Name:            ${BUCKET_NAME}"
echo "  Location:        ${REGION}"
echo ""
echo -e "${BLUE}Estimated Monthly Cost:${NC}"
echo "  Cloud SQL:       ~₹580 (~\$7)"
echo "  Storage Bucket:  ~₹10 (~\$0.12)"
echo "  Total:           ~₹590/month"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Deploy your application:"
echo "   ./deploy-gcp.sh"
echo ""
echo "2. Or manually update Cloud Run:"
echo "   gcloud run services update bakery-inventory \\"
echo "     --add-cloudsql-instances ${CONNECTION_NAME} \\"
echo "     --region ${REGION}"
echo ""
echo -e "${GREEN}Setup complete!${NC}"

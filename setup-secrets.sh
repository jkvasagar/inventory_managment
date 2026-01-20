#!/bin/bash

# Quick Secret Setup Script for Bakery Inventory
# This creates all required secrets for GCP deployment

set -e

PROJECT_ID="inventory-app-484515"
REGION="asia-south1"

echo "=========================================="
echo "  Bakery Inventory - Secret Setup"
echo "=========================================="
echo ""
echo "This script will create all required secrets for deployment."
echo "You'll need:"
echo "1. Google OAuth Client ID and Secret"
echo "2. Database password (you set this when creating bakery-db)"
echo ""
read -p "Press Enter to continue..."

# 1. Create flask-secret-key
echo ""
echo "Step 1/4: Creating Flask secret key..."
python3 -c "import secrets; print(secrets.token_hex(32))" | \
  gcloud secrets create flask-secret-key --data-file=- --project=$PROJECT_ID
echo "✓ Flask secret key created"

# 2. Create google-client-id
echo ""
echo "Step 2/4: Google OAuth Client ID"
echo "Get this from: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo ""
echo "If you haven't created OAuth credentials yet:"
echo "1. Click 'Create Credentials' > 'OAuth client ID'"
echo "2. Configure consent screen if prompted"
echo "3. Select 'Web application'"
echo "4. Add redirect URIs (you'll need BOTH for local dev and Cloud Run):"
echo "   - http://localhost:5000/login/callback (for local development)"
echo "   - https://your-cloud-run-url.run.app/login/callback (for production)"
echo "   Note: You can add the Cloud Run URL after deployment"
echo "5. Click Create and copy the Client ID"
echo ""
echo "IMPORTANT: After deploying, run ./check-oauth-setup.sh to get your Cloud Run URL"
echo ""
read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID

if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo "Error: Client ID cannot be empty"
    exit 1
fi

echo -n "$GOOGLE_CLIENT_ID" | \
  gcloud secrets create google-client-id --data-file=- --project=$PROJECT_ID
echo "✓ Google Client ID saved"

# 3. Create google-client-secret
echo ""
echo "Step 3/4: Google OAuth Client Secret"
read -sp "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
echo

if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "Error: Client Secret cannot be empty"
    exit 1
fi

echo -n "$GOOGLE_CLIENT_SECRET" | \
  gcloud secrets create google-client-secret --data-file=- --project=$PROJECT_ID
echo "✓ Google Client Secret saved"

# 4. Create database-url
echo ""
echo "Step 4/4: Database Configuration"
echo "Getting Cloud SQL connection name..."

INSTANCE_CONNECTION=$(gcloud sql instances describe bakery-db \
  --project=$PROJECT_ID \
  --format="value(connectionName)")

echo "Connection name: $INSTANCE_CONNECTION"
echo ""
echo "Enter the password for database user 'bakery_user'"
echo "(This is the password you set when creating the database)"
echo ""
echo "If you don't remember it, reset it with:"
echo "  gcloud sql users set-password bakery_user --instance=bakery-db --password=NEW_PASSWORD --project=$PROJECT_ID"
echo ""
read -sp "Database password: " DB_PASSWORD
echo

if [ -z "$DB_PASSWORD" ]; then
    echo "Error: Database password cannot be empty"
    exit 1
fi

DB_URL="postgresql://bakery_user:$DB_PASSWORD@/bakery_inventory?host=/cloudsql/$INSTANCE_CONNECTION"
echo -n "$DB_URL" | \
  gcloud secrets create database-url --data-file=- --project=$PROJECT_ID
echo "✓ Database URL saved"

# Grant permissions
echo ""
echo "Granting Cloud Run access to secrets..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

for secret in flask-secret-key google-client-id google-client-secret database-url; do
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID > /dev/null
    echo "✓ Granted access to $secret"
done

echo ""
echo "=========================================="
echo "  ✓ All secrets created successfully!"
echo "=========================================="
echo ""
echo "Created secrets:"
gcloud secrets list --project=$PROJECT_ID
echo ""
echo "You can now run the deployment script:"
echo "  ./deploy-gcp.sh"
echo ""

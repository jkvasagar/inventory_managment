#!/bin/bash

# Bakery Inventory Management System - GCP Deployment Script
# This script automates the deployment to Google Cloud Run with Cloud SQL

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_info "Checking prerequisites..."

if ! command_exists gcloud; then
    print_error "gcloud CLI is not installed. Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command_exists python3; then
    print_error "python3 is not installed."
    exit 1
fi

print_success "Prerequisites check passed!"

# Get project configuration
print_info "Setting up project configuration..."

# Get current project or ask for it
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
    gcloud config set project $PROJECT_ID
fi

print_info "Using Project ID: $PROJECT_ID"

# Get region or use default
REGION=$(gcloud config get-value run/region 2>/dev/null)
if [ -z "$REGION" ]; then
    REGION="asia-south1"
    read -p "Enter your preferred region (default: asia-south1): " INPUT_REGION
    if [ ! -z "$INPUT_REGION" ]; then
        REGION=$INPUT_REGION
    fi
    gcloud config set run/region $REGION
fi

print_info "Using Region: $REGION"

# Service configuration
SERVICE_NAME="bakery-inventory"
DB_INSTANCE_NAME="bakery-db"

# Check if Cloud SQL instance exists
print_info "Checking for Cloud SQL instance..."
if gcloud sql instances describe $DB_INSTANCE_NAME --format="value(name)" 2>/dev/null; then
    print_success "Cloud SQL instance '$DB_INSTANCE_NAME' found!"
    INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")
else
    print_warning "Cloud SQL instance '$DB_INSTANCE_NAME' not found."
    read -p "Do you want to create it? (y/n): " CREATE_DB

    if [ "$CREATE_DB" = "y" ] || [ "$CREATE_DB" = "Y" ]; then
        print_info "Creating Cloud SQL instance (this takes 5-10 minutes)..."

        read -sp "Enter a password for the database root user: " ROOT_PASSWORD
        echo

        gcloud sql instances create $DB_INSTANCE_NAME \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region=$REGION \
            --root-password=$ROOT_PASSWORD \
            --database-flags=max_connections=100

        print_info "Creating database..."
        gcloud sql databases create bakery_inventory --instance=$DB_INSTANCE_NAME

        print_info "Creating database user..."
        read -sp "Enter a password for bakery_user: " USER_PASSWORD
        echo

        gcloud sql users create bakery_user \
            --instance=$DB_INSTANCE_NAME \
            --password=$USER_PASSWORD

        INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")

        print_success "Cloud SQL instance created!"
        print_info "Connection name: $INSTANCE_CONNECTION_NAME"

        # Create database URL secret
        DB_URL="postgresql://bakery_user:$USER_PASSWORD@/bakery_inventory?host=/cloudsql/$INSTANCE_CONNECTION_NAME"
        print_info "Creating database URL secret..."
        echo -n "$DB_URL" | gcloud secrets create database-url --data-file=- 2>/dev/null || \
            (echo -n "$DB_URL" | gcloud secrets versions add database-url --data-file=-)

        # Grant access to secret
        PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
        gcloud secrets add-iam-policy-binding database-url \
            --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor" 2>/dev/null || true
    else
        print_error "Cloud SQL instance is required for deployment."
        exit 1
    fi
fi

# Check for required secrets
print_info "Checking for required secrets..."

REQUIRED_SECRETS=("flask-secret-key" "google-client-id" "google-client-secret" "database-url")
MISSING_SECRETS=()

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe $secret --format="value(name)" 2>/dev/null; then
        MISSING_SECRETS+=($secret)
    fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    print_warning "Missing secrets: ${MISSING_SECRETS[*]}"
    print_info "Please create these secrets before deploying."
    print_info "Run the following commands:"
    echo ""

    for secret in "${MISSING_SECRETS[@]}"; do
        if [ "$secret" = "flask-secret-key" ]; then
            echo "python3 -c \"import secrets; print(secrets.token_hex(32))\" | gcloud secrets create flask-secret-key --data-file=-"
        elif [ "$secret" = "google-client-id" ]; then
            echo "echo -n \"YOUR_GOOGLE_CLIENT_ID\" | gcloud secrets create google-client-id --data-file=-"
        elif [ "$secret" = "google-client-secret" ]; then
            echo "echo -n \"YOUR_GOOGLE_CLIENT_SECRET\" | gcloud secrets create google-client-secret --data-file=-"
        fi
    done

    echo ""
    read -p "Do you want to create the secrets now? (y/n): " CREATE_SECRETS

    if [ "$CREATE_SECRETS" = "y" ] || [ "$CREATE_SECRETS" = "Y" ]; then
        for secret in "${MISSING_SECRETS[@]}"; do
            if [ "$secret" = "flask-secret-key" ]; then
                print_info "Generating flask-secret-key..."
                python3 -c "import secrets; print(secrets.token_hex(32))" | gcloud secrets create flask-secret-key --data-file=-
            elif [ "$secret" = "google-client-id" ]; then
                read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID
                echo -n "$GOOGLE_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-
            elif [ "$secret" = "google-client-secret" ]; then
                read -sp "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
                echo
                echo -n "$GOOGLE_CLIENT_SECRET" | gcloud secrets create google-client-secret --data-file=-
            fi
        done

        # Grant access to secrets
        PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
        for secret in "${MISSING_SECRETS[@]}"; do
            gcloud secrets add-iam-policy-binding $secret \
                --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
                --role="roles/secretmanager.secretAccessor" 2>/dev/null || true
        done

        print_success "Secrets created!"
    else
        print_error "Cannot proceed without required secrets."
        exit 1
    fi
fi

print_success "All required secrets are configured!"

# Deploy to Cloud Run
print_info "Deploying to Cloud Run..."
print_info "Service: $SERVICE_NAME"
print_info "Region: $REGION"
print_info "Cloud SQL: $INSTANCE_CONNECTION_NAME"

gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars FLASK_ENV=production \
    --set-secrets SECRET_KEY=flask-secret-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,DATABASE_URL=database-url:latest \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0

print_success "Deployment complete!"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")

echo ""
print_success "===================================================="
print_success "  Bakery Inventory System Deployed Successfully!"
print_success "===================================================="
echo ""
print_info "Service URL: $SERVICE_URL"
echo ""
print_warning "IMPORTANT NEXT STEPS:"
echo "1. Update your Google OAuth redirect URIs:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials"
echo "   - Add authorized redirect URI: ${SERVICE_URL}/login/callback"
echo ""
echo "2. Test your application:"
echo "   - Visit: $SERVICE_URL"
echo "   - Sign in with your Google account"
echo ""
echo "3. View logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
echo "4. Monitor your service:"
echo "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"
echo ""
print_success "===================================================="

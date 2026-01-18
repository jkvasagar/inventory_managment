# Google Cloud Platform Deployment Guide

This guide will walk you through deploying the Bakery Inventory Management System to Google Cloud Platform using Cloud Run and Cloud SQL.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Cost Estimation](#cost-estimation)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- Google Cloud Platform account with billing enabled
- [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) installed
- Project with billing enabled
- Domain name (optional, but recommended for production)

## Architecture Overview

The deployment uses:

- **Cloud Run**: Serverless container platform for the Flask application
- **Cloud SQL (PostgreSQL)**: Managed PostgreSQL database
- **Secret Manager**: Secure storage for sensitive credentials
- **Cloud Build**: Automated container builds (optional)
- **Artifact Registry**: Container image storage

## Step-by-Step Deployment

### 1. Initial Setup

```bash
# Install gcloud CLI (if not already installed)
# Visit: https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Set your project ID (replace with your actual project ID)
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Set default region (choose one close to your users)
export REGION="us-central1"
gcloud config set run/region $REGION
```

### 2. Create Cloud SQL Database

```bash
# Create PostgreSQL instance (this takes 5-10 minutes)
gcloud sql instances create bakery-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password=CHANGE_THIS_PASSWORD \
    --database-flags=max_connections=100

# Create database
gcloud sql databases create bakery_inventory --instance=bakery-db

# Create database user
gcloud sql users create bakery_user \
    --instance=bakery-db \
    --password=CHANGE_THIS_USER_PASSWORD

# Get the instance connection name (you'll need this later)
gcloud sql instances describe bakery-db --format="value(connectionName)"
# Example output: your-project-id:us-central1:bakery-db
```

### 3. Set Up Secrets in Secret Manager

```bash
# Generate a secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Create secrets
echo -n "$SECRET_KEY" | gcloud secrets create flask-secret-key --data-file=-
echo -n "YOUR_GOOGLE_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-
echo -n "YOUR_GOOGLE_CLIENT_SECRET" | gcloud secrets create google-client-secret --data-file=-

# Create database URL secret
# Replace the connection name with your actual instance connection name
DB_URL="postgresql://bakery_user:CHANGE_THIS_USER_PASSWORD@/bakery_inventory?host=/cloudsql/your-project-id:us-central1:bakery-db"
echo -n "$DB_URL" | gcloud secrets create database-url --data-file=-

# Grant Cloud Run access to secrets
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding flask-secret-key \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-client-id \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-client-secret \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 4. Configure Google OAuth

1. Go to [Google Cloud Console - APIs & Credentials](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (if you haven't already)
3. Add authorized redirect URIs:
   - For testing: `https://YOUR-SERVICE-NAME-PROJECT-HASH.a.run.app/login/callback`
   - For custom domain: `https://yourdomain.com/login/callback`

   (You'll get the Cloud Run URL after first deployment)

### 5. Deploy to Cloud Run

You can deploy using either the automated script or manual commands:

#### Option A: Using the Deployment Script (Recommended)

```bash
# Make the script executable
chmod +x deploy-gcp.sh

# Run the deployment script
./deploy-gcp.sh
```

#### Option B: Manual Deployment

```bash
# Get your Cloud SQL instance connection name
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe bakery-db --format="value(connectionName)")

# Deploy to Cloud Run
gcloud run deploy bakery-inventory \
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

# Get the service URL
gcloud run services describe bakery-inventory --region $REGION --format="value(status.url)"
```

### 6. Update Google OAuth Redirect URIs

After deployment, you'll receive a Cloud Run URL like:
`https://bakery-inventory-xxxxxxxxxx-uc.a.run.app`

1. Go back to [Google Cloud Console - APIs & Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 Client ID
3. Add the authorized redirect URI:
   - `https://bakery-inventory-xxxxxxxxxx-uc.a.run.app/login/callback`
4. Save changes

### 7. Initialize the Database

The database tables are created automatically when the application starts. However, you can verify by accessing your application and checking the logs:

```bash
# View logs
gcloud run services logs read bakery-inventory --region $REGION
```

## Post-Deployment Configuration

### Set Up Custom Domain (Optional)

```bash
# Map your domain to Cloud Run
gcloud run domain-mappings create \
    --service bakery-inventory \
    --domain yourdomain.com \
    --region $REGION

# Follow the instructions to verify domain ownership and update DNS records
```

### Enable Cloud Build for CI/CD (Optional)

The included `cloudbuild.yaml` enables automatic deployments:

```bash
# Create a Cloud Build trigger (from GitHub)
gcloud builds triggers create github \
    --repo-name=inventory_managment \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml

# Or deploy manually using Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

### Monitor Your Application

```bash
# View service details
gcloud run services describe bakery-inventory --region $REGION

# Stream logs
gcloud run services logs tail bakery-inventory --region $REGION

# View metrics in Cloud Console
echo "https://console.cloud.google.com/run/detail/$REGION/bakery-inventory/metrics?project=$PROJECT_ID"
```

### Set Up Backups

```bash
# Enable automated backups for Cloud SQL
gcloud sql instances patch bakery-db \
    --backup-start-time=03:00 \
    --enable-bin-log

# Create on-demand backup
gcloud sql backups create --instance=bakery-db
```

## Cost Estimation

### Development/Testing (Low Traffic)

- **Cloud Run**: ~$0-5/month (generous free tier)
- **Cloud SQL (db-f1-micro)**: ~$7-10/month
- **Cloud Storage/Networking**: ~$1-2/month
- **Total**: ~$8-17/month

### Production (Moderate Traffic)

- **Cloud Run**: ~$10-30/month
- **Cloud SQL (db-g1-small)**: ~$25-35/month
- **Cloud Storage/Networking**: ~$5-10/month
- **Total**: ~$40-75/month

Note: Costs vary based on usage. Use [GCP Pricing Calculator](https://cloud.google.com/products/calculator) for accurate estimates.

## Scaling Configuration

### For Higher Traffic

```bash
# Update Cloud Run service with more resources
gcloud run services update bakery-inventory \
    --region $REGION \
    --memory 1Gi \
    --cpu 2 \
    --max-instances 100 \
    --min-instances 1 \
    --concurrency 80

# Upgrade Cloud SQL instance
gcloud sql instances patch bakery-db \
    --tier=db-g1-small
```

## Environment Variables Reference

The application uses these environment variables:

| Variable | Source | Description |
|----------|--------|-------------|
| `SECRET_KEY` | Secret Manager | Flask session secret key |
| `GOOGLE_CLIENT_ID` | Secret Manager | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Secret Manager | Google OAuth client secret |
| `DATABASE_URL` | Secret Manager | PostgreSQL connection string |
| `FLASK_ENV` | Set directly | Environment (production/development) |
| `PORT` | Cloud Run | Port to run on (8080) |

## Troubleshooting

### Application Won't Start

```bash
# Check logs for errors
gcloud run services logs read bakery-inventory --region $REGION --limit 50

# Common issues:
# 1. Database connection - verify Cloud SQL instance is running
# 2. Secrets not accessible - check IAM permissions
# 3. OAuth misconfiguration - verify redirect URIs
```

### Database Connection Issues

```bash
# Test Cloud SQL connection
gcloud sql connect bakery-db --user=bakery_user

# Check if Cloud SQL instance is running
gcloud sql instances describe bakery-db --format="value(state)"

# Verify Cloud Run has Cloud SQL access
gcloud run services describe bakery-inventory --region $REGION --format="value(spec.template.spec.containers[0].resources.limits)"
```

### OAuth Redirect URI Mismatch

1. Get your exact Cloud Run URL:
   ```bash
   gcloud run services describe bakery-inventory --region $REGION --format="value(status.url)"
   ```

2. Ensure the redirect URI in Google Cloud Console matches exactly:
   - Format: `https://YOUR-EXACT-URL/login/callback`
   - No trailing slashes
   - Must be HTTPS

### 502 Bad Gateway / Timeout Errors

```bash
# Increase timeout and memory
gcloud run services update bakery-inventory \
    --region $REGION \
    --timeout 300 \
    --memory 1Gi
```

### View All Secrets

```bash
# List secrets
gcloud secrets list

# View secret value (for debugging)
gcloud secrets versions access latest --secret="flask-secret-key"
```

## Security Best Practices

1. **Use Secret Manager**: Never hardcode credentials
2. **Enable HTTPS**: Cloud Run provides this by default
3. **Restrict Access**: Use Cloud IAM for service-to-service communication
4. **Regular Updates**: Keep dependencies updated
5. **Monitor Logs**: Set up Cloud Logging alerts
6. **Database Security**:
   - Use strong passwords
   - Enable SSL for database connections
   - Regular backups

## Updating the Application

### Deploy New Version

```bash
# Deploy new version (zero-downtime)
gcloud run deploy bakery-inventory \
    --source . \
    --region $REGION

# Rollback if needed
gcloud run services update-traffic bakery-inventory \
    --region $REGION \
    --to-revisions=PREVIOUS_REVISION=100
```

### Update Secrets

```bash
# Update a secret
echo -n "NEW_SECRET_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-

# Cloud Run will automatically use the latest version
```

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/tips/general)

## Support

For issues:
1. Check Cloud Run logs: `gcloud run services logs read bakery-inventory`
2. Review this troubleshooting guide
3. Consult [GCP documentation](https://cloud.google.com/docs)
4. Check [Stack Overflow](https://stackoverflow.com/questions/tagged/google-cloud-run)

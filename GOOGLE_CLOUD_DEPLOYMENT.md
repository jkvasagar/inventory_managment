# Google Cloud Run + Cloud SQL Deployment Guide

This guide walks you through deploying the Bakery Inventory Management System to Google Cloud Run with Cloud SQL PostgreSQL.

## Why This Setup?

✅ **Perfect for 4-5 daily users**
✅ **Cost-effective: $7-12/month**
✅ **Automatic HTTPS**
✅ **Auto-scaling (including to zero)**
✅ **Managed database with automatic backups**
✅ **No data loss with concurrent users**

---

## Prerequisites

1. **Google Cloud account** (free tier available)
2. **Google Cloud SDK** installed on your machine
3. **Docker** installed (for local testing)
4. **Git** (for version control)

---

## Part 1: Local Testing (Optional but Recommended)

Before deploying to cloud, test locally with Docker:

```bash
# Start all services (app + PostgreSQL + pgAdmin)
docker-compose up -d

# Check if everything is running
docker-compose ps

# View logs
docker-compose logs -f web

# Access the application
open http://localhost:5000

# Access pgAdmin (database management)
open http://localhost:5050
# Login: admin@bakery.com / admin

# Stop services when done
docker-compose down
```

---

## Part 2: Google Cloud Setup

### Step 1: Install Google Cloud SDK

**macOS:**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

### Step 2: Authenticate and Initialize

```bash
# Login to Google Cloud
gcloud auth login

# Set your project (replace PROJECT_ID with your desired project name)
export PROJECT_ID="bakery-inventory-$(whoami)"

# Create a new project
gcloud projects create $PROJECT_ID --name="Bakery Inventory"

# Set as current project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable compute.googleapis.com
```

### Step 3: Set Up Billing

Google Cloud requires a billing account (even for free tier):

```bash
# Open billing page
gcloud alpha billing accounts list

# Link billing account to project
gcloud beta billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
```

---

## Part 3: Deploy Cloud SQL PostgreSQL Database

### Step 1: Create PostgreSQL Instance

```bash
# Set variables
export DB_INSTANCE="bakery-db"
export DB_NAME="bakery"
export DB_USER="bakery_user"
export DB_PASSWORD="$(openssl rand -base64 32)"  # Generate secure password

echo "Database Password: $DB_PASSWORD"
echo "SAVE THIS PASSWORD - you'll need it later!"

# Create Cloud SQL instance (db-f1-micro = $7/month)
gcloud sql instances create $DB_INSTANCE \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password="$DB_PASSWORD" \
  --storage-type=HDD \
  --storage-size=10GB \
  --backup \
  --backup-start-time=03:00

# This takes 5-10 minutes to complete
```

### Step 2: Create Database and User

```bash
# Create database
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE

# Create user
gcloud sql users create $DB_USER \
  --instance=$DB_INSTANCE \
  --password="$DB_PASSWORD"

# Get instance connection name
export DB_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --format="value(connectionName)")

echo "Connection Name: $DB_CONNECTION_NAME"
```

---

## Part 4: Deploy Application to Cloud Run

### Step 1: Build and Deploy

```bash
# Generate secret key
export SECRET_KEY=$(openssl rand -hex 32)

echo "Secret Key: $SECRET_KEY"
echo "SAVE THIS SECRET KEY!"

# Deploy to Cloud Run (deploys directly from source code)
gcloud run deploy bakery-inventory \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=$SECRET_KEY \
  --set-env-vars FLASK_ENV=production \
  --add-cloudsql-instances $DB_CONNECTION_NAME \
  --set-env-vars DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@/bakery?host=/cloudsql/$DB_CONNECTION_NAME" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --port 8080

# This will:
# 1. Build your Docker container
# 2. Push to Google Container Registry
# 3. Deploy to Cloud Run
# 4. Connect to Cloud SQL
# Takes about 3-5 minutes
```

### Step 2: Get Your Application URL

```bash
# Get the URL
export APP_URL=$(gcloud run services describe bakery-inventory \
  --region us-central1 \
  --format="value(status.url)")

echo "Your application is live at: $APP_URL"

# Open in browser
open $APP_URL
```

---

## Part 5: Verify Deployment

### Test the Application

```bash
# Check if app is running
curl $APP_URL

# View recent logs
gcloud run services logs read bakery-inventory \
  --region us-central1 \
  --limit 50

# Follow logs in real-time
gcloud run services logs tail bakery-inventory --region us-central1
```

### Test Database Connection

1. Open your application URL
2. Navigate to **Materials** → **Add Material**
3. Add a test material (e.g., "Flour", unit "kg", min quantity 10)
4. If it saves successfully, database is working!

---

## Part 6: Configure Custom Domain (Optional)

If you have your own domain:

```bash
# Add domain mapping
gcloud run domain-mappings create \
  --service bakery-inventory \
  --domain yourdomain.com \
  --region us-central1

# Follow the instructions to update your DNS records
```

---

## Cost Breakdown

### Monthly Costs (for 4-5 daily users)

| Service | Tier | Cost |
|---------|------|------|
| Cloud Run | 512MB, 1 CPU | $0-5/month* |
| Cloud SQL | db-f1-micro | ~$7/month |
| Outbound Traffic | ~1GB | $0.12/month |
| **TOTAL** | | **~$7-12/month** |

*Cloud Run scales to zero when not in use, so you only pay for active time.

### Free Tier Inclusions

- Cloud Run: 2 million requests/month free
- Cloud Run: 360,000 GB-seconds/month free
- Cloud SQL: First 30 days free trial

---

## Maintenance and Operations

### View Application Logs

```bash
# Recent logs
gcloud run services logs read bakery-inventory --region us-central1

# Live tail
gcloud run services logs tail bakery-inventory --region us-central1
```

### Database Backups

Backups are automatic (daily at 3 AM). To manually create a backup:

```bash
# Create on-demand backup
gcloud sql backups create --instance=$DB_INSTANCE

# List backups
gcloud sql backups list --instance=$DB_INSTANCE

# Restore from backup
gcloud sql backups restore BACKUP_ID --backup-instance=$DB_INSTANCE
```

### Scale the Application

```bash
# Increase max instances for more traffic
gcloud run services update bakery-inventory \
  --region us-central1 \
  --max-instances 20

# Increase memory
gcloud run services update bakery-inventory \
  --region us-central1 \
  --memory 1Gi

# Keep minimum instances running (reduces cold starts)
gcloud run services update bakery-inventory \
  --region us-central1 \
  --min-instances 1
```

### Update the Application

When you make changes to your code:

```bash
# Make your code changes, then redeploy
gcloud run deploy bakery-inventory \
  --source . \
  --region us-central1

# That's it! Cloud Run will rebuild and deploy automatically
```

---

## Monitoring and Alerts

### Set Up Monitoring Dashboard

```bash
# Open Cloud Console monitoring
open "https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
```

### Set Up Alerts (via Cloud Console)

1. Go to **Monitoring** → **Alerting**
2. Create alerts for:
   - High error rates
   - High latency
   - Database CPU usage
   - Database disk usage

---

## Security Best Practices

### 1. Restrict Database Access

```bash
# Database is already restricted to Cloud Run only
# Verify with:
gcloud sql instances describe $DB_INSTANCE --format="value(settings.ipConfiguration)"
```

### 2. Enable IAM Authentication (Optional)

```bash
# Require IAM authentication for Cloud Run
gcloud run services update bakery-inventory \
  --region us-central1 \
  --no-allow-unauthenticated

# Add specific users
gcloud run services add-iam-policy-binding bakery-inventory \
  --region us-central1 \
  --member="user:employee@example.com" \
  --role="roles/run.invoker"
```

### 3. Environment Variables Management

Store secrets in Secret Manager (more secure):

```bash
# Enable Secret Manager
gcloud services enable secretmanager.googleapis.com

# Store secret key
echo -n "$SECRET_KEY" | gcloud secrets create bakery-secret-key --data-file=-

# Update Cloud Run to use secret
gcloud run services update bakery-inventory \
  --region us-central1 \
  --update-secrets=SECRET_KEY=bakery-secret-key:latest
```

---

## Troubleshooting

### Application Not Starting

```bash
# Check logs
gcloud run services logs read bakery-inventory --region us-central1 --limit 100

# Common issues:
# 1. Port mismatch - ensure Dockerfile uses $PORT
# 2. Database connection - verify DATABASE_URL
# 3. Missing dependencies - check requirements.txt
```

### Database Connection Errors

```bash
# Verify Cloud SQL connection
gcloud run services describe bakery-inventory \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"

# Test database connectivity
gcloud sql connect $DB_INSTANCE --user=$DB_USER
```

### Slow Performance

```bash
# Check Cloud Run metrics
gcloud run services describe bakery-inventory --region us-central1

# Increase resources if needed
gcloud run services update bakery-inventory \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2
```

---

## Clean Up (Delete Everything)

⚠️ **WARNING: This will delete all your data!**

```bash
# Delete Cloud Run service
gcloud run services delete bakery-inventory --region us-central1

# Delete Cloud SQL instance (and all data)
gcloud sql instances delete $DB_INSTANCE

# Delete project (removes everything)
gcloud projects delete $PROJECT_ID
```

---

## Next Steps

1. ✅ **Set up monitoring alerts**
2. ✅ **Configure automated backups** (already enabled)
3. ✅ **Add custom domain** (optional)
4. ✅ **Set up CI/CD** with GitHub Actions
5. ✅ **Enable authentication** if needed
6. ✅ **Set up staging environment** for testing

---

## Support

- **Google Cloud Documentation**: https://cloud.google.com/run/docs
- **Cloud SQL Documentation**: https://cloud.google.com/sql/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator

---

## Summary Command Sheet

```bash
# Quick reference for common commands

# View logs
gcloud run services logs tail bakery-inventory --region us-central1

# Redeploy after changes
gcloud run deploy bakery-inventory --source . --region us-central1

# Check status
gcloud run services describe bakery-inventory --region us-central1

# Create backup
gcloud sql backups create --instance=bakery-db

# Scale up
gcloud run services update bakery-inventory --region us-central1 --max-instances 20

# View costs
gcloud billing accounts list
open "https://console.cloud.google.com/billing"
```

---

**Congratulations!** 🎉 Your bakery inventory system is now running on Google Cloud with a production-grade PostgreSQL database!

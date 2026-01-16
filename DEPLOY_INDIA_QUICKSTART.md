# Quick Start: Deploy to Google Cloud (India)

This is a condensed deployment guide for India region (Mumbai).

## 📍 Region Configuration

- **Region**: `asia-south1` (Mumbai)
- **Latency**: Low latency for Indian users
- **Backup Time**: 1:30 AM IST (20:00 UTC)
- **Cost**: ₹600-1000/month (~$7-12/month)

---

## 🚀 Complete Deployment (Copy & Paste)

**Prerequisites**: Install Google Cloud SDK from https://cloud.google.com/sdk/docs/install

### 1. Authenticate and Setup Project

```bash
# Login
gcloud auth login

# Create project
export PROJECT_ID="bakery-inventory-$(whoami)"
gcloud projects create $PROJECT_ID --name="Bakery Inventory"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com sqladmin.googleapis.com compute.googleapis.com

# Setup billing (get your billing account ID from console)
gcloud beta billing projects link $PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### 2. Create PostgreSQL Database (Mumbai Region)

```bash
# Set variables
export DB_INSTANCE="bakery-db"
export DB_NAME="bakery"
export DB_USER="bakery_user"
export DB_PASSWORD="$(openssl rand -base64 32)"

# SAVE THESE CREDENTIALS!
echo "DB Password: $DB_PASSWORD" | tee ~/bakery-db-credentials.txt

# Create database instance in Mumbai (takes 5-10 min)
gcloud sql instances create $DB_INSTANCE \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-south1 \
  --root-password="$DB_PASSWORD" \
  --storage-type=HDD \
  --storage-size=10GB \
  --backup \
  --backup-start-time=20:00

# Create database and user
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE
gcloud sql users create $DB_USER --instance=$DB_INSTANCE --password="$DB_PASSWORD"

# Get connection name
export DB_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --format="value(connectionName)")
echo "Connection: $DB_CONNECTION_NAME"
```

### 3. Deploy Application to Cloud Run (Mumbai)

```bash
# Navigate to your project directory
cd inventory_managment
git checkout claude/deployment-strategy-JyVcX

# Generate secret key
export SECRET_KEY=$(openssl rand -hex 32)
echo "Secret Key: $SECRET_KEY" | tee -a ~/bakery-db-credentials.txt

# Deploy to Mumbai region (takes 3-5 min)
gcloud run deploy bakery-inventory \
  --source . \
  --platform managed \
  --region asia-south1 \
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

# Get your URL
export APP_URL=$(gcloud run services describe bakery-inventory --region asia-south1 --format="value(status.url)")
echo "🎉 App is live at: $APP_URL"
```

---

## 💰 Pricing (India)

| Service | Cost (INR/month) | Cost (USD/month) |
|---------|------------------|------------------|
| Cloud Run (512MB) | ₹0-400 | $0-5 |
| Cloud SQL (db-f1-micro) | ₹600 | $7 |
| Network | ₹10 | $0.12 |
| **TOTAL** | **₹600-1000** | **$7-12** |

**Free credits**: New accounts get ₹25,000 (~$300) free credit

---

## 📊 Daily Operations

```bash
# View live logs
gcloud run services logs tail bakery-inventory --region asia-south1

# Redeploy after changes
gcloud run deploy bakery-inventory --source . --region asia-south1

# Check status
gcloud run services describe bakery-inventory --region asia-south1

# Create manual backup
gcloud sql backups create --instance=bakery-db

# View costs
open "https://console.cloud.google.com/billing"
```

---

## 🔧 Common Issues

**Issue: Build fails**
```bash
# Check build logs
gcloud builds log $(gcloud builds list --limit=1 --format="value(id)")
```

**Issue: Can't connect to database**
```bash
# Verify connection
gcloud run services describe bakery-inventory --region asia-south1 \
  --format="value(spec.template.spec.containers[0].env)"
```

**Issue: Application not responding**
```bash
# Check logs for errors
gcloud run services logs read bakery-inventory --region asia-south1 --limit 100
```

---

## 🌐 Performance for India

- **Mumbai Region**: ~5-20ms latency for users in India
- **Backup Time**: 1:30 AM IST (minimal disruption)
- **Data Location**: All data stays in India (asia-south1)

---

## 📞 Support

- **Google Cloud India Support**: https://cloud.google.com/contact
- **Pricing Calculator**: https://cloud.google.com/products/calculator
- **Status Dashboard**: https://status.cloud.google.com

---

## ✅ Checklist

- [ ] Install Google Cloud SDK
- [ ] Enable billing (add payment method)
- [ ] Create project and enable APIs
- [ ] Deploy Cloud SQL database (Mumbai)
- [ ] Deploy Cloud Run application (Mumbai)
- [ ] Test application URL
- [ ] Save credentials securely
- [ ] Set up monitoring alerts

---

**Total Setup Time**: ~20 minutes (including wait times)
**Region**: Mumbai (asia-south1)
**Expected Cost**: ₹600-1000/month for 4-5 users

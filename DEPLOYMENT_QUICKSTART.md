# Quick Start Deployment Guide

This guide provides step-by-step instructions for the most common deployment scenarios.

## Prerequisites

Before deploying, ensure you have:
- [ ] Migrated from JSON to a proper database (PostgreSQL recommended)
- [ ] Updated `SECRET_KEY` to use environment variables
- [ ] Tested the application locally with Docker
- [ ] Created necessary cloud provider accounts

---

## Option 1: Deploy to Google Cloud Run (Recommended for Beginners)

**Cost:** ~$7-12/month | **Difficulty:** Easy | **Time:** 15 minutes

### Step 1: Install Google Cloud CLI
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

### Step 2: Authenticate and Setup
```bash
# Login to Google Cloud
gcloud auth login

# Create or select project
gcloud projects create bakery-inventory-PROJECT_ID
gcloud config set project bakery-inventory-PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### Step 3: Deploy Application
```bash
# Generate secret key
export SECRET_KEY=$(openssl rand -hex 32)

# Deploy to Cloud Run
gcloud run deploy bakery-inventory \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=$SECRET_KEY \
  --port 8080

# Get your application URL
gcloud run services describe bakery-inventory \
  --region us-central1 \
  --format="value(status.url)"
```

### Step 4: Add Database (Optional but Recommended)
```bash
# Create PostgreSQL instance
gcloud sql instances create bakery-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=CHOOSE_SECURE_PASSWORD

# Create database
gcloud sql databases create bakery --instance=bakery-db

# Create user
gcloud sql users create bakery_user \
  --instance=bakery-db \
  --password=CHOOSE_SECURE_PASSWORD

# Connect Cloud Run to Cloud SQL
gcloud run services update bakery-inventory \
  --region us-central1 \
  --add-cloudsql-instances PROJECT_ID:us-central1:bakery-db \
  --set-env-vars DATABASE_URL="postgresql://bakery_user:PASSWORD@/bakery?host=/cloudsql/PROJECT_ID:us-central1:bakery-db"
```

**Done!** Your app is now live at the URL provided.

---

## Option 2: Deploy to Heroku

**Cost:** ~$12/month | **Difficulty:** Very Easy | **Time:** 10 minutes

### Step 1: Install Heroku CLI
```bash
# macOS
brew install heroku/brew/heroku

# Linux/WSL
curl https://cli-assets.heroku.com/install.sh | sh

# Windows
# Download from: https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Create and Deploy
```bash
# Login to Heroku
heroku login

# Create app
heroku create bakery-inventory-YOUR-NAME

# Add PostgreSQL database
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set SECRET_KEY=$(openssl rand -hex 32)

# Deploy
git push heroku main

# Open your app
heroku open
```

### Step 3: View Logs
```bash
# Stream logs
heroku logs --tail

# Check dyno status
heroku ps
```

**Done!** Your app is deployed and running.

---

## Option 3: Deploy with Docker Locally or on VPS

**Cost:** VPS from $5/month | **Difficulty:** Medium | **Time:** 30 minutes

### Step 1: Test Locally with Docker Compose
```bash
# Build and run
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f web

# Access at http://localhost:5000

# Stop
docker-compose down
```

### Step 2: Deploy to VPS (Digital Ocean, Linode, etc.)

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install docker-compose-plugin

# Clone your repository
git clone https://github.com/your-username/inventory_managment.git
cd inventory_managment

# Create .env file
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://bakery_user:bakery_password@db:5432/bakery_db
FLASK_ENV=production
EOF

# Start services
docker-compose up -d

# Setup Nginx reverse proxy (optional but recommended)
apt-get install nginx

cat > /etc/nginx/sites-available/bakery << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/bakery /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Setup SSL with Let's Encrypt
apt-get install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

**Done!** Your app is running on your VPS.

---

## Option 4: Deploy to AWS (Using Elastic Beanstalk)

**Cost:** ~$25/month | **Difficulty:** Medium | **Time:** 20 minutes

### Step 1: Install AWS CLI and EB CLI
```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Install Elastic Beanstalk CLI
pip install awsebcli
```

### Step 2: Initialize and Deploy
```bash
# Initialize EB application
eb init -p python-3.11 bakery-inventory --region us-east-1

# Create environment with PostgreSQL
eb create bakery-env \
  --database.engine postgres \
  --database.username bakeryuser \
  --database.password CHOOSE_SECURE_PASSWORD \
  --envvars SECRET_KEY=$(openssl rand -hex 32)

# Open application
eb open

# View logs
eb logs

# SSH into instance (if needed)
eb ssh
```

### Step 3: Update Application
```bash
# After making changes
git add .
git commit -m "Update application"
eb deploy
```

**Done!** Your app is running on AWS Elastic Beanstalk.

---

## Testing Your Deployment

After deployment, test these endpoints:

1. **Homepage**: `https://your-app-url/`
2. **Materials**: `https://your-app-url/materials`
3. **Recipes**: `https://your-app-url/recipes`
4. **Products**: `https://your-app-url/products`
5. **Sales**: `https://your-app-url/sales`

---

## Common Issues and Solutions

### Issue: Port binding error
**Solution:** Ensure your app uses the `PORT` environment variable:
```python
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
```

### Issue: Static files not loading
**Solution:** Check that `static/` and `templates/` directories are included in your deployment.

### Issue: Database connection fails
**Solution:**
- Verify `DATABASE_URL` environment variable is set correctly
- Check database credentials
- Ensure database accepts connections from your app's IP

### Issue: Application crashes on startup
**Solution:**
```bash
# Check logs
# For Cloud Run:
gcloud run services logs read bakery-inventory --region us-central1

# For Heroku:
heroku logs --tail

# For Docker:
docker-compose logs web
```

---

## Monitoring Your Deployment

### Cloud Run (Google Cloud)
```bash
# View logs
gcloud run services logs read bakery-inventory --region us-central1

# View metrics
gcloud run services describe bakery-inventory --region us-central1
```

### Heroku
```bash
# View logs
heroku logs --tail

# Check metrics
heroku ps
heroku pg:info
```

### Docker
```bash
# View logs
docker-compose logs -f

# Check resource usage
docker stats
```

---

## Setting Up Custom Domain

### Cloud Run
```bash
gcloud run domain-mappings create \
  --service bakery-inventory \
  --domain your-domain.com \
  --region us-central1
```

### Heroku
```bash
heroku domains:add your-domain.com
```

Then update your DNS:
- Add CNAME record pointing to the provided hostname

---

## Backup and Restore

### Backup PostgreSQL Database

**Cloud SQL (Google Cloud):**
```bash
gcloud sql backups create --instance=bakery-db
```

**Heroku:**
```bash
heroku pg:backups:capture
heroku pg:backups:download
```

**Docker/Self-hosted:**
```bash
docker-compose exec db pg_dump -U bakery_user bakery_db > backup.sql
```

### Restore Database
```bash
# Cloud SQL
gcloud sql import sql bakery-db gs://your-bucket/backup.sql --database=bakery

# Heroku
heroku pg:backups:restore 'https://your-backup-url' DATABASE_URL

# Docker
docker-compose exec -T db psql -U bakery_user bakery_db < backup.sql
```

---

## Scaling Your Application

### Cloud Run
```bash
# Increase max instances
gcloud run services update bakery-inventory \
  --region us-central1 \
  --max-instances 20

# Increase memory
gcloud run services update bakery-inventory \
  --region us-central1 \
  --memory 1Gi
```

### Heroku
```bash
# Scale dynos
heroku ps:scale web=2

# Upgrade dyno type
heroku ps:type standard-1x
```

---

## Next Steps

1. **Set up monitoring**: Configure error tracking (Sentry) and performance monitoring
2. **Enable backups**: Schedule regular database backups
3. **Add CI/CD**: Set up GitHub Actions or GitLab CI for automated deployments
4. **Configure alerts**: Set up alerts for errors and performance issues
5. **Optimize**: Add caching, CDN for static files
6. **Security audit**: Review security settings, enable 2FA on cloud accounts

---

## Getting Help

- **Google Cloud Run**: https://cloud.google.com/run/docs
- **Heroku**: https://devcenter.heroku.com
- **AWS**: https://docs.aws.amazon.com/elastic-beanstalk
- **Docker**: https://docs.docker.com

---

## Cost Optimization Tips

1. **Use spot/preemptible instances** for non-critical workloads
2. **Set up auto-scaling** to scale down during low traffic
3. **Use smaller database tiers** initially, scale up as needed
4. **Enable database connection pooling** to reduce connection overhead
5. **Set up CloudFlare** for free CDN and DDoS protection
6. **Monitor costs** using cloud provider billing alerts

---

**Congratulations!** Your bakery inventory system is now deployed to the cloud.

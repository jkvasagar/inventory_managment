# Cloud Deployment Strategies for Bakery Inventory Management System

## Table of Contents
1. [Application Overview](#application-overview)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Pre-Deployment Considerations](#pre-deployment-considerations)
4. [Deployment Strategies](#deployment-strategies)
5. [Recommended Approach](#recommended-approach)
6. [Security Hardening](#security-hardening)
7. [Cost Comparison](#cost-comparison)
8. [Implementation Guides](#implementation-guides)

---

## Application Overview

### Technology Stack
- **Framework**: Flask 3.0.0
- **Runtime**: Python 3.7+
- **Data Storage**: JSON file (`bakery_data.json`)
- **Port**: 5000
- **Dependencies**: Minimal (only Flask)

### Key Features
- Material inventory management (FIFO)
- Recipe management
- Production tracking
- Point of sale system
- Sales analytics
- Low stock alerts

---

## Current Architecture Analysis

### Strengths
- Simple, lightweight application
- Minimal dependencies
- Easy to containerize
- Low resource requirements

### Limitations & Risks
1. **File-based storage**: JSON file not suitable for production
2. **No database**: Data loss risk, no concurrent access support
3. **Hardcoded secret key**: Security vulnerability
4. **Debug mode**: Should be disabled in production
5. **No HTTPS**: Data transmitted in plaintext
6. **Single file persistence**: No backup or redundancy
7. **No authentication**: Open access to all features
8. **No horizontal scaling**: File storage prevents multi-instance deployment

---

## Pre-Deployment Considerations

### Critical Changes Required

#### 1. Database Migration (REQUIRED)
Replace JSON file storage with a proper database:

**Options:**
- **PostgreSQL** (Recommended for production)
- **MySQL/MariaDB** (Alternative relational DB)
- **MongoDB** (If document structure is preferred)
- **SQLite** (Only for very small deployments)

**Why:** JSON files don't support concurrent access, lack ACID properties, and can't scale horizontally.

#### 2. Security Enhancements (REQUIRED)
```python
# Changes needed in app.py:

# 1. Use environment variables for secrets
import os
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-for-dev-only')

# 2. Disable debug mode in production
app.run(debug=False, host='0.0.0.0', port=5000)

# 3. Add environment-based configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_URL = os.environ.get('DATABASE_URL')
    ENV = os.environ.get('FLASK_ENV', 'production')
```

#### 3. Static Files & Templates
- Verify all templates exist in `/templates/` directory
- Verify static assets exist in `/static/` directory
- Consider CDN for static assets in production

#### 4. Production WSGI Server
Replace Flask's development server with a production-grade WSGI server:
- **Gunicorn** (Recommended for Linux)
- **uWSGI** (Alternative)
- **Waitress** (Cross-platform)

Update `requirements.txt`:
```
Flask==3.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.9  # For PostgreSQL
python-dotenv==1.0.0     # For environment variables
```

---

## Deployment Strategies

### Strategy 1: Platform as a Service (PaaS) - Easiest

#### 1.1 Heroku
**Best for**: Quick deployment, small to medium scale

**Pros:**
- Extremely simple deployment
- Built-in PostgreSQL addon
- Free tier available (with limitations)
- Automatic HTTPS
- Easy scaling

**Cons:**
- More expensive at scale
- Dyno sleeps on free tier
- Limited customization

**Deployment Steps:**
```bash
# 1. Install Heroku CLI
# 2. Create Procfile
echo "web: gunicorn app:app" > Procfile

# 3. Create runtime.txt
echo "python-3.11" > runtime.txt

# 4. Initialize git and deploy
heroku create bakery-inventory
heroku addons:create heroku-postgresql:mini
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
git push heroku main

# 5. Open application
heroku open
```

**Cost Estimate:**
- Hobby tier: $7/month (dyno) + $5/month (PostgreSQL)
- **Total: ~$12/month**

---

#### 1.2 Google App Engine (Standard)
**Best for**: Google Cloud ecosystem, auto-scaling

**Pros:**
- Auto-scaling to zero
- Pay-per-use pricing
- Integrated with Google Cloud services
- Good free tier

**Cons:**
- Vendor lock-in
- Learning curve for GCP
- Cold start delays

**Deployment Steps:**
```bash
# 1. Create app.yaml
cat > app.yaml << EOF
runtime: python311
entrypoint: gunicorn -b :\$PORT app:app

env_variables:
  SECRET_KEY: "your-secret-key-here"

automatic_scaling:
  target_cpu_utilization: 0.65
  min_instances: 1
  max_instances: 10
EOF

# 2. Deploy
gcloud app deploy
gcloud app browse
```

**Cost Estimate:**
- ~$7-15/month for low traffic
- Scales up based on usage

---

#### 1.3 Azure App Service
**Best for**: Microsoft/Azure ecosystem

**Pros:**
- Easy deployment
- Integrated CI/CD
- Good Windows support
- Enterprise features

**Cons:**
- More expensive than alternatives
- Azure complexity

**Deployment Steps:**
```bash
# 1. Create App Service
az webapp up --name bakery-inventory \
  --resource-group myResourceGroup \
  --runtime "PYTHON:3.11" \
  --sku B1

# 2. Configure environment variables
az webapp config appsettings set \
  --name bakery-inventory \
  --resource-group myResourceGroup \
  --settings SECRET_KEY="your-secret"

# 3. Enable PostgreSQL
az postgres server create --name bakery-db \
  --resource-group myResourceGroup \
  --location eastus \
  --sku-name B_Gen5_1
```

**Cost Estimate:**
- Basic tier: ~$13/month (App Service) + $5/month (Database)
- **Total: ~$18/month**

---

### Strategy 2: Containerized Deployment - Recommended

#### 2.1 Docker + AWS ECS (Fargate)
**Best for**: Production-grade, scalable deployment

**Pros:**
- Full container orchestration
- Serverless containers (Fargate)
- Highly scalable
- Integration with AWS services

**Cons:**
- More complex setup
- Requires AWS knowledge
- Higher cost than PaaS

**Implementation:**

**Create Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

**Create docker-compose.yml (for local testing):**
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/bakery
      - SECRET_KEY=dev-secret-key
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=bakery
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**ECS Deployment Steps:**
```bash
# 1. Build and push to ECR
aws ecr create-repository --repository-name bakery-inventory
docker build -t bakery-inventory .
docker tag bakery-inventory:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/bakery-inventory:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/bakery-inventory:latest

# 2. Create ECS cluster
aws ecs create-cluster --cluster-name bakery-cluster

# 3. Create task definition (JSON config)
# 4. Create service with load balancer
# 5. Set up RDS PostgreSQL instance
```

**Cost Estimate:**
- Fargate: ~$15/month (0.25 vCPU, 0.5GB RAM)
- RDS PostgreSQL (t3.micro): ~$15/month
- Application Load Balancer: ~$20/month
- **Total: ~$50/month**

---

#### 2.2 Google Cloud Run
**Best for**: Serverless containers, pay-per-use

**Pros:**
- Fully managed serverless containers
- Auto-scaling to zero
- Very cost-effective for low traffic
- Simple deployment

**Cons:**
- Stateless (requires external database)
- Cold starts possible
- Request timeout limits

**Deployment Steps:**
```bash
# 1. Build and deploy
gcloud run deploy bakery-inventory \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=your-secret

# 2. Connect to Cloud SQL (PostgreSQL)
gcloud sql instances create bakery-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud run services update bakery-inventory \
  --add-cloudsql-instances bakery-db
```

**Cost Estimate:**
- Cloud Run: ~$0-5/month (for low traffic, pay-per-use)
- Cloud SQL (db-f1-micro): ~$7/month
- **Total: ~$7-12/month**

---

#### 2.3 Azure Container Instances + Container Apps
**Best for**: Simple container deployment on Azure

**Deployment Steps:**
```bash
# 1. Build and push to ACR
az acr create --resource-group myResourceGroup --name bakeryregistry --sku Basic
docker build -t bakeryregistry.azurecr.io/bakery-inventory:latest .
docker push bakeryregistry.azurecr.io/bakery-inventory:latest

# 2. Deploy container
az container create \
  --resource-group myResourceGroup \
  --name bakery-inventory \
  --image bakeryregistry.azurecr.io/bakery-inventory:latest \
  --dns-name-label bakery-inventory \
  --ports 5000
```

**Cost Estimate:**
- Container Instances: ~$10-20/month
- Azure Database for PostgreSQL: ~$5-20/month
- **Total: ~$15-40/month**

---

### Strategy 3: Kubernetes (For Large Scale)

#### 3.1 AWS EKS / GKE / AKS
**Best for**: Large scale, microservices, DevOps teams

**Pros:**
- Maximum scalability
- Industry standard
- Multi-cloud portable
- Advanced features (service mesh, auto-scaling)

**Cons:**
- Significant complexity
- Higher cost
- Requires Kubernetes expertise
- Overkill for simple applications

**Basic Kubernetes Manifests:**

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bakery-inventory
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bakery-inventory
  template:
    metadata:
      labels:
        app: bakery-inventory
    spec:
      containers:
      - name: app
        image: bakery-inventory:latest
        ports:
        - containerPort: 5000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: bakery-secrets
              key: secret-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: bakery-secrets
              key: database-url
---
apiVersion: v1
kind: Service
metadata:
  name: bakery-inventory
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5000
  selector:
    app: bakery-inventory
```

**Cost Estimate:**
- EKS Control Plane: $75/month
- Worker Nodes (t3.medium x 2): ~$60/month
- RDS Database: ~$30/month
- Load Balancer: ~$20/month
- **Total: ~$185/month minimum**

**Recommendation:** Only use Kubernetes if you have multiple services or need advanced orchestration. For this single application, it's overkill.

---

### Strategy 4: Traditional VMs

#### 4.1 AWS EC2 / GCP Compute Engine / Azure VMs
**Best for**: Full control, custom requirements

**Pros:**
- Complete control
- Can run anything
- Cost-effective for steady workloads

**Cons:**
- Manual management required
- OS updates, security patches
- No auto-scaling (without additional setup)

**Deployment Steps:**
```bash
# 1. Launch EC2 instance (Ubuntu)
# 2. SSH into instance
ssh ubuntu@<instance-ip>

# 3. Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql

# 4. Clone repository and setup
git clone <your-repo>
cd inventory_managment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configure Nginx as reverse proxy
sudo nano /etc/nginx/sites-available/bakery

# Nginx config:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# 6. Setup systemd service
sudo nano /etc/systemd/system/bakery.service

[Unit]
Description=Bakery Inventory Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/inventory_managment
Environment="PATH=/home/ubuntu/inventory_managment/venv/bin"
ExecStart=/home/ubuntu/inventory_managment/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target

# 7. Start service
sudo systemctl enable bakery
sudo systemctl start bakery
```

**Cost Estimate:**
- t3.micro EC2: ~$8/month
- RDS db.t3.micro: ~$15/month
- **Total: ~$23/month**

---

### Strategy 5: Serverless (Advanced)

#### 5.1 AWS Lambda + API Gateway
**Best for**: Event-driven, sporadic traffic

**Pros:**
- True pay-per-use
- Auto-scaling
- Very cost-effective for low traffic

**Cons:**
- Requires significant refactoring
- Cold start latency
- 15-minute execution limit
- Complexity

**Note:** Flask can run on Lambda using frameworks like **Zappa** or **AWS SAM**, but requires refactoring for stateless operation.

**Not recommended** for this application due to the complexity vs. benefit ratio.

---

## Recommended Approach

### For Small Deployments (1-100 users)
**Winner: Google Cloud Run + Cloud SQL**

**Why:**
- Best cost-effectiveness ($7-12/month)
- Scales to zero when not in use
- Managed container service
- Easy deployment
- Built-in HTTPS and custom domains

**Implementation Steps:**
1. Migrate JSON storage to PostgreSQL
2. Create Dockerfile
3. Deploy to Cloud Run
4. Connect Cloud SQL database
5. Configure custom domain

---

### For Medium Deployments (100-1000 users)
**Winner: AWS ECS Fargate + RDS**

**Why:**
- Better performance guarantees
- More control over scaling
- Integrated AWS ecosystem
- Better for business applications

**Implementation Steps:**
1. Migrate to PostgreSQL/RDS
2. Containerize with Docker
3. Deploy to ECS with Fargate
4. Setup Application Load Balancer
5. Configure auto-scaling policies

---

### For Large Deployments (1000+ users)
**Winner: Kubernetes (EKS/GKE/AKS) + Managed Database**

**Why:**
- Advanced orchestration
- High availability
- Multi-region deployment
- Service mesh capabilities

---

## Security Hardening

### 1. Environment Variables
Create `.env` file (DO NOT commit to git):
```
SECRET_KEY=<generate-with-openssl-rand-hex-32>
DATABASE_URL=postgresql://user:password@host:5432/dbname
FLASK_ENV=production
```

Add to `.gitignore`:
```
.env
bakery_data.json
*.pyc
__pycache__/
venv/
```

### 2. HTTPS/TLS
- Use cloud provider's load balancer for TLS termination
- Or use Let's Encrypt with Certbot for VMs

### 3. Authentication
Consider adding:
- Flask-Login for user authentication
- Flask-Security for role-based access
- OAuth2 for SSO

### 4. Database Security
- Use connection pooling
- Encrypt connections (SSL/TLS)
- Use parameter binding (prevent SQL injection)
- Regular backups

### 5. CORS Configuration
```python
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "https://yourdomain.com"}})
```

### 6. Rate Limiting
```python
from flask_limiter import Limiter
limiter = Limiter(app, default_limits=["200 per day", "50 per hour"])
```

---

## Cost Comparison

| Strategy | Monthly Cost | Best For | Complexity |
|----------|-------------|----------|------------|
| Google Cloud Run | $7-12 | Small apps, variable traffic | Low |
| Heroku | $12+ | Quick prototypes | Very Low |
| Azure App Service | $18+ | Microsoft ecosystem | Low |
| AWS EC2 + RDS | $23+ | Full control | Medium |
| AWS ECS Fargate | $50+ | Production, scalable | Medium |
| Kubernetes (EKS) | $185+ | Large scale, multiple services | High |

---

## Implementation Guides

### Quick Start: Deploy to Google Cloud Run

**1. Prepare Application:**
```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
EOF

# Update requirements.txt
cat > requirements.txt << 'EOF'
Flask==3.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
EOF
```

**2. Update app.py for production:**
```python
# At the end of app.py, replace:
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# With:
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
```

**3. Deploy:**
```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy
gcloud run deploy bakery-inventory \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=$(openssl rand -hex 32)

# Get URL
gcloud run services describe bakery-inventory --region us-central1 --format="value(status.url)"
```

**4. Add Database (Optional but recommended):**
```bash
# Create Cloud SQL instance
gcloud sql instances create bakery-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create bakery --instance=bakery-db

# Connect to Cloud Run
gcloud run services update bakery-inventory \
  --add-cloudsql-instances YOUR_PROJECT:us-central1:bakery-db \
  --set-env-vars DATABASE_URL="postgresql://user:password@/bakery?host=/cloudsql/YOUR_PROJECT:us-central1:bakery-db"
```

---

## Migration Path from JSON to PostgreSQL

### Step 1: Install Dependencies
```bash
pip install psycopg2-binary SQLAlchemy Flask-SQLAlchemy
```

### Step 2: Create Database Models
```python
# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    min_quantity = db.Column(db.Float, nullable=False)
    batches = db.relationship('MaterialBatch', backref='material', lazy=True, cascade='all, delete-orphan')

class MaterialBatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    cost_per_unit = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    batch_size = db.Column(db.Integer, nullable=False)
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True, cascade='all, delete-orphan')

class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
```

### Step 3: Migration Script
```python
# migrate_to_db.py
import json
from app import app, db
from models import Material, MaterialBatch, Recipe, Product, Sale

def migrate_json_to_db():
    with app.app_context():
        # Create all tables
        db.create_all()

        # Load JSON data
        with open('bakery_data.json', 'r') as f:
            data = json.load(f)

        # Migrate materials
        for name, material_data in data['materials'].items():
            material = Material(
                name=name,
                unit=material_data['unit'],
                min_quantity=material_data['min_quantity']
            )
            db.session.add(material)
            db.session.flush()

            for batch in material_data['batches']:
                batch_obj = MaterialBatch(
                    material_id=material.id,
                    quantity=batch['quantity'],
                    cost_per_unit=batch['cost_per_unit'],
                    purchase_date=datetime.strptime(batch['purchase_date'], '%Y-%m-%d')
                )
                db.session.add(batch_obj)

        # ... continue for recipes, products, sales

        db.session.commit()
        print("Migration completed successfully!")

if __name__ == '__main__':
    migrate_json_to_db()
```

---

## Next Steps

1. **Choose deployment strategy** based on your scale and budget
2. **Migrate to database** (critical for production)
3. **Implement security changes** (environment variables, HTTPS)
4. **Set up CI/CD pipeline** (GitHub Actions, GitLab CI, etc.)
5. **Configure monitoring** (CloudWatch, Stackdriver, Application Insights)
6. **Set up backups** (automated database backups)
7. **Implement logging** (centralized logging solution)
8. **Load testing** (before production launch)

---

## Conclusion

For most use cases, **Google Cloud Run with Cloud SQL** provides the best balance of:
- Cost-effectiveness
- Simplicity
- Scalability
- Maintenance burden

However, if you're already invested in AWS or Azure ecosystems, containerized deployment on those platforms is equally viable.

**Avoid Kubernetes** unless you have specific needs for container orchestration or are deploying multiple interconnected services.

**Critical Next Step**: Migrate from JSON file storage to PostgreSQL before any production deployment.

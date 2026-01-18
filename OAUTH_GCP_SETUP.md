# OAuth Configuration for Google Cloud Platform Deployment

This guide shows you how to configure Google OAuth when deploying to Google Cloud Run.

## Quick Overview

When deploying to GCP, OAuth credentials are stored in **Secret Manager** (not in `.env` files) and automatically injected into your Cloud Run service as environment variables.

## Step-by-Step Setup

### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console - APIs & Credentials](https://console.cloud.google.com/apis/credentials)

2. **Enable Required APIs** (if not already enabled):
   - Navigate to "APIs & Services" > "Library"
   - Search for and enable: **"Google+ API"** or **"Google Identity"**

3. **Configure OAuth Consent Screen**:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Select "External" (unless you have Google Workspace)
   - Fill in required fields:
     - App name: "Bakery Inventory Management"
     - User support email: Your email
     - Developer contact email: Your email
   - Click "Save and Continue" through all steps
   - Add test users (your email address)

4. **Create OAuth Client ID**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Name: "Bakery Inventory Web Client"

5. **Add Authorized Redirect URIs**:

   **IMPORTANT**: You'll need to do this in TWO stages:

   **Stage 1 - Initial Setup** (for first deployment):
   ```
   http://localhost:5000/login/callback
   ```

   **Stage 2 - After First Deployment** (we'll update this later):
   ```
   https://your-cloud-run-url.run.app/login/callback
   ```

6. Click "Create" and **SAVE** your:
   - Client ID (looks like: `xxxxx.apps.googleusercontent.com`)
   - Client Secret (random string)

### Step 2: Store Credentials in GCP Secret Manager

You have two options:

#### Option A: Use the Automated Script (Recommended)

```bash
# Make the script executable
chmod +x setup-secrets.sh

# Run the script - it will prompt you for all credentials
./setup-secrets.sh
```

The script will ask for:
1. Google Client ID
2. Google Client Secret
3. Database password
4. Automatically generates Flask secret key

#### Option B: Manual Setup

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# 1. Create Flask secret key
python3 -c "import secrets; print(secrets.token_hex(32))" | \
  gcloud secrets create flask-secret-key --data-file=-

# 2. Create Google OAuth secrets
echo -n "YOUR_GOOGLE_CLIENT_ID" | \
  gcloud secrets create google-client-id --data-file=-

echo -n "YOUR_GOOGLE_CLIENT_SECRET" | \
  gcloud secrets create google-client-secret --data-file=-

# 3. Grant Cloud Run access to secrets
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

for secret in flask-secret-key google-client-id google-client-secret; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Step 3: Verify Secrets Are Created

```bash
# List all secrets
gcloud secrets list

# You should see:
# - flask-secret-key
# - google-client-id
# - google-client-secret
# - database-url
```

### Step 4: Deploy to Cloud Run

```bash
# Use the automated deployment script
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

Or manually:

```bash
# Get your Cloud SQL instance connection name
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe bakery-db --format="value(connectionName)")

# Deploy
gcloud run deploy bakery-inventory \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars FLASK_ENV=production \
    --set-secrets SECRET_KEY=flask-secret-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,DATABASE_URL=database-url:latest \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0
```

### Step 5: Update OAuth Redirect URIs (CRITICAL!)

After deployment, you'll get a Cloud Run URL like:
```
https://bakery-inventory-abc123xyz-uc.a.run.app
```

**You MUST update your OAuth redirect URIs now:**

1. Copy your Cloud Run URL:
   ```bash
   gcloud run services describe bakery-inventory --region us-central1 --format="value(status.url)"
   ```

2. Go back to [Google Cloud Console - APIs & Credentials](https://console.cloud.google.com/apis/credentials)

3. Click on your OAuth 2.0 Client ID

4. Under "Authorized redirect URIs", **ADD** (keep existing ones):
   ```
   https://bakery-inventory-abc123xyz-uc.a.run.app/login/callback
   ```

   **Important**:
   - Replace with YOUR actual Cloud Run URL
   - Must be HTTPS (not HTTP)
   - Must end with `/login/callback`
   - No trailing slash after "callback"

5. Click "Save"

### Step 6: Test Your Application

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe bakery-inventory --region us-central1 --format="value(status.url)")
echo "Visit: $SERVICE_URL"

# Open in browser and test Google login
```

## How It Works

### Local Development vs Production

| Aspect | Local Development | GCP Production |
|--------|------------------|----------------|
| **Credentials Storage** | `.env` file | Secret Manager |
| **How App Reads Them** | `python-dotenv` | Cloud Run injects as env vars |
| **Redirect URI** | `http://localhost:5000/login/callback` | `https://your-app.run.app/login/callback` |
| **Security** | `.env` in `.gitignore` | IAM-controlled secrets |

### Secret Manager Flow

```
1. You store credentials in Secret Manager
2. You grant Cloud Run service account access
3. You reference secrets in deployment: --set-secrets
4. Cloud Run automatically injects them as environment variables
5. Your Flask app reads them from os.environ (no code changes needed!)
```

## Troubleshooting

### Error: "OAuth client was not found. Error 401: invalid_client"

**Causes:**
1. Secrets not created in Secret Manager
2. Cloud Run doesn't have access to secrets
3. Wrong Client ID or Secret

**Fix:**
```bash
# Check if secrets exist
gcloud secrets list

# Verify secret values (for debugging only - don't share these!)
gcloud secrets versions access latest --secret=google-client-id
gcloud secrets versions access latest --secret=google-client-secret

# Re-grant permissions if needed
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding google-client-id \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding google-client-secret \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Error: "redirect_uri_mismatch"

**Cause:** The redirect URI in your OAuth client doesn't match your Cloud Run URL

**Fix:**
1. Get exact URL: `gcloud run services describe bakery-inventory --format="value(status.url)"`
2. Add to OAuth client: `https://YOUR-EXACT-URL/login/callback`
3. Make sure there are no typos, trailing slashes, or http vs https mismatches

### Error: "Access to Secret Denied"

**Fix:**
```bash
# Grant Cloud Run service account access
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding google-client-id \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-client-secret \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Users Can't Sign In (Even Though OAuth Works)

**Cause:** Not added as test users in OAuth consent screen

**Fix:**
1. Go to [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
2. Click "Edit App"
3. Under "Test users", add email addresses
4. Save

**Production Fix:** Publish your OAuth app or use Internal user type with Google Workspace

## Updating OAuth Credentials

If you need to rotate your OAuth credentials:

```bash
# Update the secret (creates a new version)
echo -n "NEW_CLIENT_ID" | gcloud secrets versions add google-client-id --data-file=-
echo -n "NEW_CLIENT_SECRET" | gcloud secrets versions add google-client-secret --data-file=-

# Cloud Run automatically uses the latest version
# Force a new deployment to pick up changes immediately
gcloud run services update bakery-inventory --region us-central1
```

## Security Best Practices

1. **Never commit secrets to Git** - Always use Secret Manager in production
2. **Use different OAuth clients** - Separate credentials for dev/staging/prod
3. **Restrict redirect URIs** - Only add URIs you actually use
4. **Monitor secret access** - Use Cloud Audit Logs to see who accessed secrets
5. **Rotate credentials regularly** - Change secrets periodically
6. **Use least privilege** - Only grant Secret Accessor role, not Admin

## Complete Deployment Checklist

- [ ] Created Google OAuth Client ID
- [ ] Configured OAuth consent screen
- [ ] Added test users
- [ ] Created secrets in Secret Manager
- [ ] Granted Cloud Run access to secrets
- [ ] Deployed to Cloud Run
- [ ] Updated OAuth redirect URIs with Cloud Run URL
- [ ] Tested login functionality
- [ ] Verified users can sign in successfully

## Additional Resources

- [Full Deployment Guide](GCP_DEPLOYMENT.md)
- [Local OAuth Setup](OAUTH_SETUP.md)
- [GCP Secret Manager Docs](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)

## Quick Reference Commands

```bash
# View service URL
gcloud run services describe bakery-inventory --format="value(status.url)"

# View logs
gcloud run services logs read bakery-inventory --region us-central1

# List secrets
gcloud secrets list

# View secret value (for debugging)
gcloud secrets versions access latest --secret=google-client-id

# Update deployment
gcloud run deploy bakery-inventory --source . --region us-central1

# Force redeployment (pick up new secrets)
gcloud run services update bakery-inventory --region us-central1
```

## Need Help?

1. Check Cloud Run logs: `gcloud run services logs read bakery-inventory`
2. Verify secrets exist: `gcloud secrets list`
3. Check OAuth redirect URIs match exactly
4. Review this troubleshooting guide
5. See [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md) for more details

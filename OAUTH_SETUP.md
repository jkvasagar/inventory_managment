# Google OAuth Setup Guide

This application uses Google OAuth 2.0 for authentication. Follow these steps to set up Google login.

## Prerequisites

- A Google account
- Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "Bakery Inventory")
5. Click "Create"

## Step 2: Enable Google+ API

1. In your project, go to "APIs & Services" > "Library"
2. Search for "Google+ API"
3. Click on it and press "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type (unless you have a Google Workspace)
3. Click "Create"
4. Fill in the required fields:
   - App name: "Bakery Inventory Management"
   - User support email: Your email
   - Developer contact email: Your email
5. Click "Save and Continue"
6. On the Scopes page, click "Save and Continue"
7. On Test users page, add your email address
8. Click "Save and Continue"

## Step 4: Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as the application type
4. Enter a name (e.g., "Bakery Inventory Web Client")
5. Under "Authorized redirect URIs", add:
   - For local development: `http://localhost:5000/login/callback`
   - For Cloud Run: `https://your-service-name-hash.a.run.app/login/callback`
   - For custom domain: `https://yourdomain.com/login/callback`
   - For production: `https://yourdomain.com/login/callback`
6. Click "Create"
7. Copy the "Client ID" and "Client Secret"

## Step 5: Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your credentials:
   ```
   GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret-here
   ```

3. Generate a secure SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Add it to `.env`:
   ```
   SECRET_KEY=your-generated-secret-key
   ```

## Step 6: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 7: Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Important Notes

### For Production Deployment

1. Update the authorized redirect URIs in Google Cloud Console to match your production domain
2. Set `FLASK_ENV=production` in your `.env` file
3. Use a strong, random `SECRET_KEY`
4. Enable HTTPS for your application
5. Consider moving from "External" to "Internal" user type if using Google Workspace

### Security Considerations

- Never commit the `.env` file to version control
- Keep your `GOOGLE_CLIENT_SECRET` confidential
- Regularly rotate your `SECRET_KEY`
- Use HTTPS in production

### Troubleshooting

**Error: redirect_uri_mismatch**
- Make sure the redirect URI in Google Cloud Console exactly matches your application URL + `/login/callback`
- Check for trailing slashes and http vs https

**Error: invalid_client**
- Verify your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
- Make sure there are no extra spaces in your `.env` file

**Users can't sign in**
- Check that you've added them as test users in the OAuth consent screen
- Verify the Google+ API is enabled

## Testing the Login

1. Navigate to `http://localhost:5000`
2. You should be redirected to the login page
3. Click "Sign in with Google"
4. Authorize the application
5. You should be redirected back and logged in

## User Management

- First-time users are automatically created in the database
- User information (name, email, profile picture) is stored
- Users can only access the application after authenticating

## Production Deployment (GCP Cloud Run)

When deploying to Google Cloud Platform:

### 1. Use Secret Manager for Credentials

Instead of `.env` files, use Secret Manager:

```bash
# Store credentials in Secret Manager
echo -n "YOUR_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create google-client-secret --data-file=-

# Grant Cloud Run access
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding google-client-id \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-client-secret \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 2. Update Redirect URIs After Deployment

After deploying to Cloud Run:

```bash
# Get your Cloud Run URL
gcloud run services describe bakery-inventory --region REGION --format="value(status.url)"
```

Then add the redirect URI to Google Cloud Console:
- URL format: `https://bakery-inventory-xxxxxxxxxx-uc.a.run.app/login/callback`

### 3. Production Security Checklist

- [ ] OAuth consent screen is configured
- [ ] Redirect URIs use HTTPS only
- [ ] Credentials are in Secret Manager (not in code)
- [ ] Test users are added (if using external user type)
- [ ] Application is using production SECRET_KEY
- [ ] Database uses strong passwords
- [ ] Consider moving to "Internal" user type if using Google Workspace

For complete deployment instructions, see [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md)

## Support

For issues related to Google OAuth setup, refer to:
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Authlib Flask Documentation](https://docs.authlib.org/en/latest/client/flask.html)

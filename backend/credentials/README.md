# Credentials

This directory contains secure credential files for the application.

## Security Notice

⚠️ **IMPORTANT**: This directory contains sensitive information and should never be committed to version control.

## Files

- `infinitum-agent-a9f15079e3e6.json` - Google Cloud service account key
- `infinitum-agent-a9f15079e3e6.json.backup` - Backup of service account key

## Setup

1. **Download Service Account Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to IAM & Admin > Service Accounts
   - Create or select your service account
   - Create and download a JSON key file

2. **Place Credentials**:
   ```bash
   # Copy your downloaded key to this directory
   cp ~/Downloads/your-service-account-key.json backend/credentials/
   ```

3. **Set Environment Variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="backend/credentials/your-service-account-key.json"
   ```

## Required Permissions

Your service account should have these roles:
- **Vertex AI User** - For AI/ML operations
- **Cloud Run Developer** - For deployment
- **Storage Admin** - For vector search data
- **Firestore User** - For database operations

## Security Best Practices

1. **Never commit credentials** - They're in `.gitignore`
2. **Rotate keys regularly** - Especially for production
3. **Use least privilege** - Only grant necessary permissions
4. **Monitor usage** - Check GCP audit logs
5. **Use different keys** - For different environments

## Environment Variables

Set these in your [`../config/.env`](../config/.env):
```bash
GOOGLE_APPLICATION_CREDENTIALS="backend/credentials/your-key.json"
GCP_PROJECT_ID="your-project-id"
```

## Troubleshooting

### Authentication Errors
- Verify the key file exists and is readable
- Check the `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Ensure the service account has required permissions

### Permission Errors
- Review IAM roles in Google Cloud Console
- Check if APIs are enabled (Vertex AI, Cloud Run, etc.)
- Verify project ID matches your configuration

## Backup

Keep secure backups of your credentials:
- Store in a secure password manager
- Keep offline copies in a safe location
- Document recovery procedures
# AWS Credentials Expired

## Issue

The AWS credentials in `.env` have expired:

```
An error occurred (ExpiredTokenException) when calling the ListFunctions operation: 
The security token included in the request is expired
```

## Solution

You need to refresh your AWS credentials. The credentials in `.env` are temporary session tokens that expire.

### Steps to Fix:

1. **Get new AWS credentials** from your AWS account/SSO
   - If using AWS SSO: Run `aws sso login`
   - If using IAM user: Get new session token
   - If using temporary credentials: Refresh them

2. **Update .env file** with new credentials:
   ```bash
   AWS_ACCESS_KEY_ID="<new_key>"
   AWS_SECRET_ACCESS_KEY="<new_secret>"
   AWS_SESSION_TOKEN="<new_token>"
   ```

3. **Reload environment**:
   ```bash
   source .venv/bin/activate
   export $(grep -v '^#' .env | xargs)
   ```

4. **Test credentials**:
   ```bash
   aws sts get-caller-identity
   ```

## Why This Happened

The credentials in your `.env` file are temporary session tokens (notice the `AWS_SESSION_TOKEN`). These typically expire after:
- 1 hour (default)
- 12 hours (extended)
- 36 hours (maximum)

## After Refreshing Credentials

Once you have valid credentials, you can:

1. **Test the upload**:
   ```bash
   ./test-fresh-upload.sh
   ```

2. **Run end-to-end test**:
   ```bash
   ./test-e2e-gssr.sh
   ```

3. **Check S3 buckets**:
   ```bash
   ./s3-inspector.sh
   ```

## Note

All the code changes are complete and deployed. The only issue is expired AWS credentials preventing API calls and S3 operations.

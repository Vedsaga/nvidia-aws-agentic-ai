import json
import os
import uuid
import boto3
import time
from botocore.exceptions import ClientError

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
JOBS_TABLE_NAME = os.environ["JOBS_TABLE"]
RAW_BUCKET_NAME = os.environ["RAW_BUCKET"]
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


def lambda_handler(event, context):
    """
    Handles the initial API request to upload a file.
    Generates a job_id and a pre-signed URL for the client to upload to S3.
    """
    try:
        # 1. Parse request body
        body = json.loads(event.get("body", "{}"))
        filename = body.get("filename")
        if not filename:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'filename' in request body"}),
            }

        # 2. Generate a unique job_id
        job_id = str(uuid.uuid4())
        # S3 object key will be job_id/filename to keep it organized
        object_key = f"{job_id}/{filename}"
        
        # 3. Create pre-signed URL
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": RAW_BUCKET_NAME, "Key": object_key},
            ExpiresIn=3600,  # URL expires in 1 hour
        )
        
        # 4. Create an entry in DocumentJobs table
        timestamp = int(time.time())
        jobs_table.put_item(
            Item={
                "job_id": job_id,
                "filename": filename,
                "status": "PENDING_UPLOAD", # Client has URL, waiting for file
                "s3_raw_key": object_key,
                "received_at": timestamp,
            }
        )

        # 5. Return the URL and job_id to the client
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Pre-signed URL generated successfully.",
                    "job_id": job_id,
                    "pre_signed_url": presigned_url,
                    "s3_key": object_key
                }
            ),
        }

    except ClientError as e:
        print(f"Boto3 error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "AWS service error"})}
    except Exception as e:
        print(f"Handler error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
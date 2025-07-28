# src/infra_review_cli/adapters/aws/s3_adapter.py

import boto3
from botocore.exceptions import ClientError
from src.infra_review_cli.core.checks.s3_public_access import check_s3_public_access

def fetch_s3_public_info(region: str) -> list:
    s3 = boto3.client("s3", region_name=region)
    control = boto3.client("s3control", region_name=region)

    findings_input = []

    try:
        response = s3.list_buckets()
        buckets = response.get("Buckets", [])

        for bucket in buckets:
            name = bucket["Name"]
            public = False
            reason = None

            # 1. Try bucket policy
            try:
                policy = s3.get_bucket_policy(Bucket=name)
                if '"Principal":"*"' in policy["Policy"]:
                    public = True
                    reason = "Bucket policy allows public '*' access"
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchBucketPolicy':
                    print(f"⚠️ Error fetching policy for {name}: {e}")

            # 2. Try public access block
            # try:
            #     pab = s3.get_bucket_policy_status(Bucket=name)
            #     if pab["PolicyStatus"]["IsPublic"]:
            #         public = True
            #         reason = "PolicyStatus indicates public bucket"
            # except ClientError as e:
            #     print(f"⚠️ Error checking PolicyStatus for {name}: {e}")

            findings_input.append({
                "Name": name,
                "Public": public,
                "Reason": reason or "Could not verify policy clearly"
            })

    except ClientError as e:
        print(f"❌ Error listing buckets: {e}")
        return []

    return check_s3_public_access(findings_input, region)

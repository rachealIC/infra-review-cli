# src/infra_review_cli/adapters/aws/s3_adapter.py
"""
AWS S3 adapter — fetches public access and versioning data.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.s3 import check_s3_public_access, check_s3_versioning


def fetch_s3_public_info(region: str) -> tuple[list, list[str]]:
    """
    Checks all S3 buckets for public access.

    Returns:
        Tuple of (findings: list[Finding], public_bucket_names: list[str])
        Public bucket names are returned so the CloudFront adapter can reuse them.
    """
    s3 = boto3.client("s3", region_name=region)
    findings_input = []

    try:
        response = s3.list_buckets()
        buckets = response.get("Buckets", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  S3 check skipped — missing permission: s3:ListAllMyBuckets")
        else:
            print(f"⚠️  S3: {e}")
        return [], []

    for bucket in buckets:
        name = bucket["Name"]
        is_public = False
        reason = None

        # 1. Check bucket policy for wildcard principal
        try:
            policy = s3.get_bucket_policy(Bucket=name)
            if '"Principal":"*"' in policy["Policy"] or '"Principal": "*"' in policy["Policy"]:
                is_public = True
                reason = "Bucket policy allows public '*' access"
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchBucketPolicy":
                pass  # ignore other errors — bucket might still be public via ACL

        # 2. Check GetBucketPolicyStatus
        if not is_public:
            try:
                status = s3.get_bucket_policy_status(Bucket=name)
                if status.get("PolicyStatus", {}).get("IsPublic"):
                    is_public = True
                    reason = "PolicyStatus indicates public bucket"
            except ClientError:
                pass

        findings_input.append({
            "Name": name,
            "Public": is_public,
            "Reason": reason or "No public access detected",
        })

    findings = check_s3_public_access(findings_input, region)
    public_names = [b["Name"] for b in findings_input if b["Public"]]
    return findings, public_names


def fetch_s3_versioning_findings(region: str) -> list:
    """Checks all S3 buckets for versioning status."""
    s3 = boto3.client("s3", region_name=region)
    buckets_with_versioning = []

    try:
        all_buckets = s3.list_buckets().get("Buckets", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  S3 versioning check skipped — missing: s3:ListAllMyBuckets")
        return []

    for bucket in all_buckets:
        name = bucket["Name"]
        try:
            versioning = s3.get_bucket_versioning(Bucket=name)
            status = versioning.get("Status", "")
        except ClientError:
            status = ""

        buckets_with_versioning.append({"Name": name, "VersioningStatus": status})

    return check_s3_versioning(buckets_with_versioning, region)

# src/infra_review_cli/adapters/aws/cloudtrail_adapter.py
"""
AWS CloudTrail adapter — fetches data for Operational Excellence checks.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.operational_excellence import check_cloudtrail_enabled


def fetch_cloudtrail_findings(region: str) -> list:
    """
    Describes all trails and their logging status, then runs check_cloudtrail_enabled().
    """
    cloudtrail = boto3.client("cloudtrail", region_name=region)
    findings = []

    try:
        trails_resp = cloudtrail.describe_trails(includeShadowTrails=False)
        trails = trails_resp.get("trailList", [])

        # Enrich each trail with its logging status
        for trail in trails:
            try:
                status = cloudtrail.get_trail_status(Name=trail["TrailARN"])
                trail["IsLogging"] = status.get("IsLogging", False)
            except ClientError:
                trail["IsLogging"] = False

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print(
                "⚠️  CloudTrail check skipped — missing permission: cloudtrail:DescribeTrails"
            )
        else:
            print(f"⚠️  CloudTrail: {e}")
        return []

    return check_cloudtrail_enabled(trails, region)

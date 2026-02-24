# src/infra_review_cli/adapters/aws/ebs_adapter.py
"""
AWS EBS adapter — fetches unattached volume data.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.ec2 import check_unattached_ebs
from infra_review_cli.config import EBS_MIN_AGE_DAYS


def fetch_ebs_findings(region: str) -> list:
    """Fetches unattached EBS volumes and runs check_unattached_ebs()."""
    ec2 = boto3.client("ec2", region_name=region)
    volumes = []

    try:
        paginator = ec2.get_paginator("describe_volumes")
        for page in paginator.paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        ):
            volumes.extend(page.get("Volumes", []))
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  EBS check skipped — missing permission: ec2:DescribeVolumes")
        else:
            print(f"⚠️  EBS: {e}")
        return []

    return check_unattached_ebs(volumes, region, min_age_days=EBS_MIN_AGE_DAYS)

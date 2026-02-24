# src/infra_review_cli/adapters/aws/cloudwatch_adapter.py
"""
AWS CloudWatch adapter — fetches alarm data for Operational Excellence checks.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.operational_excellence import check_cloudwatch_alarms


def fetch_cloudwatch_alarm_findings(region: str) -> list:
    """Fetches CloudWatch alarms and checks whether any are configured."""
    cw = boto3.client("cloudwatch", region_name=region)

    try:
        paginator = cw.get_paginator("describe_alarms")
        alarms = []
        for page in paginator.paginate():
            alarms.extend(page.get("MetricAlarms", []))
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print("⚠️  CloudWatch alarm check skipped — missing permission: cloudwatch:DescribeAlarms")
        else:
            print(f"⚠️  CloudWatch: {e}")
        return []

    return check_cloudwatch_alarms(alarms, region)

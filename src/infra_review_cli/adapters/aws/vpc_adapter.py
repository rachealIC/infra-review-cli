# src/infra_review_cli/adapters/aws/vpc_adapter.py
"""
AWS VPC adapter — fetches security group rules.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.vpc import check_insecure_sg_rules


def fetch_vpc_findings(region: str) -> list:
    """Fetches all Security Groups and checks for insecure rules."""
    ec2 = boto3.client("ec2", region_name=region)
    findings = []

    try:
        paginator = ec2.get_paginator("describe_security_groups")
        for page in paginator.paginate():
            for sg in page.get("SecurityGroups", []):
                findings.extend(check_insecure_sg_rules(sg, region))
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  VPC check skipped — missing permission: ec2:DescribeSecurityGroups")
        else:
            print(f"⚠️  VPC: {e}")
        return []

    return findings

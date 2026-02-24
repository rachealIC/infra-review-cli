# src/infra_review_cli/adapters/aws/rds_adapter.py
"""
AWS RDS adapter — fetches data for RDS reliability checks.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.rds import check_rds_multi_az, check_rds_backup_policy


def fetch_rds_findings(region: str) -> list:
    """
    Fetches all RDS DB instances and runs:
      - check_rds_multi_az
      - check_rds_backup_policy
    """
    rds = boto3.client("rds", region_name=region)
    findings = []

    try:
        paginator = rds.get_paginator("describe_db_instances")
        instances = []
        for page in paginator.paginate():
            instances.extend(page.get("DBInstances", []))
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print(
                "⚠️  RDS check skipped — missing permission: rds:DescribeDBInstances "
                "(Add it to your IAM policy to enable this check)"
            )
        else:
            print(f"⚠️  RDS: {e}")
        return []

    findings.extend(check_rds_multi_az(instances, region))
    findings.extend(check_rds_backup_policy(instances, region))
    return findings

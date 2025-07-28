# src/infra_review_cli/adapters/aws/ebs_adapter.py

import boto3
from src.infra_review_cli.core.checks.ec2 import check_unattached_ebs

def fetch_unattached_ebs(region: str, min_age_days: int = 30) -> list:
    ec2 = boto3.client("ec2", region_name=region)

    response = ec2.describe_volumes(
        Filters=[
            {"Name": "status", "Values": ["available"]}  # Only unattached volumes
        ]
    )

    volumes = response.get("Volumes", [])

    return check_unattached_ebs(volumes, region=region, min_age_days=min_age_days)

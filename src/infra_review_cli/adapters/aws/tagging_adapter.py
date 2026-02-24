# src/infra_review_cli/adapters/aws/tagging_adapter.py
"""
AWS Resource Groups Tagging API adapter — checks for missing required tags.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.operational_excellence import check_resource_tagging
from infra_review_cli.config import REQUIRED_TAGS


def fetch_tagging_findings(region: str) -> list:
    """
    Uses the Resource Groups Tagging API to list resources missing required tags.
    """
    tagging = boto3.client("resourcegroupstaggingapi", region_name=region)
    resources = []

    try:
        paginator = tagging.get_paginator("get_resources")
        for page in paginator.paginate(
            TagFilters=[],  # No filter — get all resources
            ResourcesPerPage=100,
        ):
            for resource in page.get("ResourceTagMappingList", []):
                resources.append({
                    "ResourceARN": resource["ResourceARN"],
                    "Tags": resource.get("Tags", []),
                })
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print("⚠️  Tagging check skipped — missing permission: tag:GetResources")
        else:
            print(f"⚠️  Tagging API: {e}")
        return []

    return check_resource_tagging(resources, REQUIRED_TAGS, region)

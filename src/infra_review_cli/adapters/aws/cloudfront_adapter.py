# src/infra_review_cli/adapters/aws/cloudfront_adapter.py
"""
AWS CloudFront adapter — checks whether CDN is in use for public assets.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.performance import check_cloudfront_usage


def fetch_cloudfront_findings(
    region: str,
    public_bucket_names: list[str],
    alb_dns_names: list[str],
) -> list:
    """
    Lists CloudFront distributions and checks coverage for public buckets and ALBs.
    CloudFront is a global service — the region param is used in Finding.region.
    """
    cf = boto3.client("cloudfront")  # CloudFront is global, no region needed
    distributions = []

    try:
        paginator = cf.get_paginator("list_distributions")
        for page in paginator.paginate():
            dist_list = page.get("DistributionList", {})
            for item in dist_list.get("Items", []):
                distributions.append({
                    "DomainName": item.get("DomainName", ""),
                    "Origins": item.get("Origins", {}),
                })
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print("⚠️  CloudFront check skipped — missing permission: cloudfront:ListDistributions")
        else:
            print(f"⚠️  CloudFront: {e}")
        return []

    return check_cloudfront_usage(distributions, public_bucket_names, alb_dns_names, region)

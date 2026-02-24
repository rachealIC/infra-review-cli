# src/infra_review_cli/adapters/aws/elb_adapter.py
"""
AWS ELB adapter — fetches data for unused load balancer check.
"""

import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.elb import check_unused_elb


def fetch_elb_findings(region: str) -> list:
    """
    Fetches all ELBs (ALB/NLB), gets their request counts and healthy target counts,
    and returns findings.
    """
    elbv2 = boto3.client("elbv2", region_name=region)
    cw = boto3.client("cloudwatch", region_name=region)
    elbs_data = []

    try:
        paginator = elbv2.get_paginator("describe_load_balancers")
        for page in paginator.paginate():
            for lb in page["LoadBalancers"]:
                lb_arn = lb["LoadBalancerArn"]
                lb_name = lb["LoadBalancerName"]
                lb_type = lb["Type"]

                # 1. Get Healthy Target Count
                healthy_count = 0
                try:
                    target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)["TargetGroups"]
                    for tg in target_groups:
                        health = elbv2.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
                        healthy_count += sum(
                            1 for h in health["TargetHealthDescriptions"]
                            if h["TargetHealth"]["State"] == "healthy"
                        )
                except ClientError:
                    pass

                # 2. Get Request Count from CloudWatch (Last 7 days)
                request_count = 0
                try:
                    metric_name = "RequestCount" if lb_type == "application" else "ProcessedBytes"
                    namespace = "AWS/ApplicationELB" if lb_type == "application" else "AWS/NetworkELB"
                    dimension_name = "LoadBalancer"
                    
                    # ALB/NLB dimensions in Cloudwatch use the suffix of the ARN
                    short_arn = lb_arn.split("/", 1)[1] if "/" in lb_arn else lb_arn

                    stats = cw.get_metric_statistics(
                        Namespace=namespace,
                        MetricName=metric_name,
                        Dimensions=[{"Name": dimension_name, "Value": short_arn}],
                        StartTime=datetime.now(timezone.utc) - timedelta(days=7),
                        EndTime=datetime.now(timezone.utc),
                        Period=604800,  # 7 days
                        Statistics=["Sum"],
                    )
                    datapoints = stats.get("Datapoints", [])
                    request_count = sum(dp.get("Sum", 0) for dp in datapoints)
                except ClientError:
                    pass

                elbs_data.append({
                    "LoadBalancerArn": lb_arn,
                    "Name": lb_name,
                    "Type": lb_type,
                    "RequestCount": request_count,
                    "HealthyTargetCount": healthy_count,
                })

    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  ELB check skipped — missing permission: elasticloadbalancing:DescribeLoadBalancers")
        else:
            print(f"⚠️  ELB: {e}")
        return []

    return check_unused_elb(elbs_data, region)


def fetch_alb_dns_names(region: str) -> list[str]:
    """Returns DNS names of all Application Load Balancers (used for CloudFront check)."""
    elbv2 = boto3.client("elbv2", region_name=region)
    try:
        lbs = elbv2.describe_load_balancers()["LoadBalancers"]
        return [lb["DNSName"] for lb in lbs if lb["Type"] == "application"]
    except ClientError:
        return []

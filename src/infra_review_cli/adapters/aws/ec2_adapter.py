# src/infra_review_cli/adapters/aws/ec2_adapter.py
"""
AWS EC2 adapter — fetches CPU metrics, EBS volumes, and Elastic IP data.
"""

import json
import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.ec2 import (
    check_ec2_rightsizing,
    check_unattached_ebs,
    check_unassociated_elastic_ips,
    check_ec2_autoscaling_groups,
)
from infra_review_cli.config import (
    CPU_UNDERUTIL_THRESHOLD,
    CLOUDWATCH_LOOKBACK_DAYS,
    REGION_LOCATION_MAP,
)


# ---------------------------------------------------------------------------
# Pricing cache (module-level, cleared per process)
# ---------------------------------------------------------------------------
_pricing_cache: dict[tuple[str, str], float] = {}


def fetch_price_from_aws(instance_type: str, region: str) -> float:
    """Fetches On-Demand Linux price for an EC2 instance type from the AWS Pricing API."""
    cache_key = (instance_type, region)
    if cache_key in _pricing_cache:
        return _pricing_cache[cache_key]

    location = REGION_LOCATION_MAP.get(region)
    if not location:
        return 0.0

    pricing = boto3.client("pricing", region_name="us-east-1")
    try:
        response = pricing.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType",    "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "location",        "Value": location},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw",  "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "tenancy",         "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus",  "Value": "Used"},
            ],
            MaxResults=1,
        )
        price_list = response.get("PriceList", [])
        if not price_list:
            return 0.0

        data = json.loads(price_list[0])
        on_demand = list(data["terms"]["OnDemand"].values())[0]
        price_dimension = list(on_demand["priceDimensions"].values())[0]
        price = float(price_dimension["pricePerUnit"]["USD"])
        _pricing_cache[cache_key] = price
        return price

    except Exception:
        return 0.0


def fetch_cpu_data(region: str, threshold: float = CPU_UNDERUTIL_THRESHOLD) -> list:
    """
    Fetches running EC2 instances + 14-day CPU metrics and returns check findings.
    Gracefully handles AccessDenied per-call.
    """
    ec2 = boto3.client("ec2", region_name=region)
    cloudwatch = boto3.client("cloudwatch", region_name=region)
    instances = []

    try:
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    if instance["State"]["Name"] != "running":
                        continue

                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]
                    architecture = instance.get("Architecture", "x86_64")

                    now = datetime.now(timezone.utc)
                    start = now - timedelta(days=CLOUDWATCH_LOOKBACK_DAYS)

                    try:
                        stats = cloudwatch.get_metric_statistics(
                            Namespace="AWS/EC2",
                            MetricName="CPUUtilization",
                            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                            StartTime=start,
                            EndTime=now,
                            Period=3600,
                            Statistics=["Average", "Maximum"],
                        )
                        datapoints = stats.get("Datapoints", [])
                        cpu_avg = (
                            sum(dp["Average"] for dp in datapoints if "Average" in dp) / len(datapoints)
                            if datapoints else 0.0
                        )
                        cpu_max = max(
                            (dp["Maximum"] for dp in datapoints if "Maximum" in dp), default=0.0
                        )
                    except ClientError:
                        cpu_avg = cpu_max = 0.0

                    price = fetch_price_from_aws(instance_type, region)

                    instances.append({
                        "instance_id": instance_id,
                        "instance_type": instance_type,
                        "architecture": architecture,
                        "region": region,
                        "cpu_avg": cpu_avg,
                        "cpu_max": cpu_max,
                        "network_gb_total": 0.0,
                        "current_price": price,
                    })

    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  EC2 check skipped — missing permission: ec2:DescribeInstances")
        else:
            print(f"⚠️  EC2: {e}")
        return []

    return check_ec2_rightsizing(instances, threshold=threshold)


def fetch_unassociated_eips(region: str) -> list:
    """Fetches all Elastic IPs and returns findings for unassociated ones."""
    ec2 = boto3.client("ec2", region_name=region)
    try:
        addresses = ec2.describe_addresses()["Addresses"]
        return check_unassociated_elastic_ips(addresses, region)
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  Elastic IP check skipped — missing permission: ec2:DescribeAddresses")
        else:
            print(f"⚠️  Elastic IPs: {e}")
        return []


def fetch_asg_instance_ids(region: str) -> set[str]:
    """Returns the set of instance IDs that are part of an Auto Scaling Group."""
    asg = boto3.client("autoscaling", region_name=region)
    instance_ids: set[str] = set()
    try:
        paginator = asg.get_paginator("describe_auto_scaling_instances")
        for page in paginator.paginate():
            for item in page.get("AutoScalingInstances", []):
                instance_ids.add(item["InstanceId"])
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  ASG check skipped — missing permission: autoscaling:DescribeAutoScalingInstances")
        else:
            print(f"⚠️  ASG: {e}")
    return instance_ids


def fetch_asg_findings(region: str) -> list:
    """Orchestrates the ASG coverage check."""
    ec2 = boto3.client("ec2", region_name=region)
    try:
        # Get all running instance IDs
        instances = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        all_ids = []
        for res in instances["Reservations"]:
            for inst in res["Instances"]:
                all_ids.append(inst["InstanceId"])

        if not all_ids:
            return []

        asg_ids = fetch_asg_instance_ids(region)
        return check_ec2_autoscaling_groups(asg_ids, all_ids, region)
    except ClientError:
        return []

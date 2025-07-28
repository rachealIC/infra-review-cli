# src/infra_review_cli/adapters/aws/ec2_adapter.py

import boto3
from datetime import datetime, timedelta
from src.infra_review_cli.core.checks.ec2 import check_ec2_rightsizing, check_unassociated_elastic_ips


def fetch_cpu_data(region: str, threshold: float = 20.0) -> list:
    cloudwatch = boto3.client("cloudwatch", region_name=region)
    ec2 = boto3.client("ec2", region_name=region)

    response = ec2.describe_instances()
    instance_ids = []
    for r in response["Reservations"]:
        for i in r["Instances"]:
            instance_ids.append(i["InstanceId"])

    cpu_data = {}

    for instance_id in instance_ids:
        metrics = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=datetime.utcnow() - timedelta(days=18),
            EndTime=datetime.utcnow(),
            Period=3600,  # hourly datapoints
            Statistics=["Maximum"]
        )

        cpu_values = [dp["Maximum"] for dp in metrics["Datapoints"]]
        cpu_data[instance_id] = cpu_values

    # print("fetched CPU data for instances:", cpu_data, )

    # Run check with this data
    return check_ec2_rightsizing(cpu_data, region, threshold)


def fetch_unassociated_eips(region: str):
    ec2 = boto3.client("ec2", region_name=region)

    addresses = ec2.describe_addresses()["Addresses"]
    findings = check_unassociated_elastic_ips(addresses, region)
    return findings

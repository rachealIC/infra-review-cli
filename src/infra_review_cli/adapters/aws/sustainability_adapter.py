"""
AWS Sustainability adapter.

Each fetch_* function returns a tuple:
    (findings: list[Finding], scanned_ok: bool)

scanned_ok=False means the check could not run (for example, due to missing
permissions/API failures) and should not increment pillar check count.
"""

from datetime import datetime, timedelta, timezone
import time

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.adapters.aws.ec2_adapter import fetch_price_from_aws
from infra_review_cli.config import CLOUDWATCH_LOOKBACK_DAYS
from infra_review_cli.core.checks.sustainability import (
    check_graviton_instance_usage,
    check_idle_always_on_instances,
    check_lambda_overprovisioned_memory,
    check_s3_lifecycle_policies,
    check_unencrypted_ebs_volumes,
)

_LAMBDA_MEMORY_QUERY = """
fields @message
| filter @message like /REPORT RequestId/
| parse @message /Max Memory Used: (?<max_memory_used>[0-9]+) MB/
| stats max(max_memory_used) as maxMemoryUsed
"""


def _is_access_denied(error: ClientError) -> bool:
    code = error.response.get("Error", {}).get("Code", "")
    return code in {
        "AccessDenied",
        "AccessDeniedException",
        "UnauthorizedOperation",
        "Client.UnauthorizedOperation",
        "UnrecognizedClientException",
    }


def _query_lambda_max_memory_used(logs, function_name: str, start: datetime, end: datetime) -> tuple[float, bool]:
    """
    Returns (max_memory_used_mb, query_ok).
    query_ok=False means missing permissions for Logs Insights.
    """
    log_group = f"/aws/lambda/{function_name}"
    start_epoch = int(start.timestamp())
    end_epoch = int(end.timestamp())

    try:
        query = logs.start_query(
            logGroupName=log_group,
            startTime=start_epoch,
            endTime=end_epoch,
            queryString=_LAMBDA_MEMORY_QUERY,
            limit=1,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            return 0.0, True
        if _is_access_denied(e):
            return 0.0, False
        return 0.0, True

    query_id = query.get("queryId")
    if not query_id:
        return 0.0, True

    for _ in range(24):
        time.sleep(0.25)
        try:
            result = logs.get_query_results(queryId=query_id)
        except ClientError as e:
            if _is_access_denied(e):
                return 0.0, False
            return 0.0, True

        status = result.get("status")
        if status == "Complete":
            rows = result.get("results", [])
            if not rows:
                return 0.0, True
            for field in rows[0]:
                if field.get("field") == "maxMemoryUsed":
                    value = field.get("value")
                    try:
                        return float(value), True
                    except (TypeError, ValueError):
                        return 0.0, True
            return 0.0, True
        if status in {"Failed", "Cancelled", "Timeout"}:
            return 0.0, True

    return 0.0, True


def fetch_graviton_usage_findings(region: str) -> tuple[list, bool]:
    ec2 = boto3.client("ec2", region_name=region)
    instances: list[dict] = []

    try:
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    if instance.get("State", {}).get("Name") != "running":
                        continue
                    instance_type = instance.get("InstanceType", "")
                    instances.append({
                        "instance_id": instance.get("InstanceId", "unknown"),
                        "instance_type": instance_type,
                        "current_price": fetch_price_from_aws(instance_type, region),
                    })
    except ClientError as e:
        if _is_access_denied(e):
            print("⚠️  Sustainability Graviton check skipped — missing: ec2:DescribeInstances")
        else:
            print(f"⚠️  Sustainability Graviton check failed: {e}")
        return [], False

    return check_graviton_instance_usage(instances, region), True


def fetch_s3_lifecycle_findings(region: str) -> tuple[list, bool]:
    s3 = boto3.client("s3", region_name=region)
    buckets_input: list[dict] = []
    checked_any_bucket = False
    access_denied_buckets = 0

    try:
        buckets = s3.list_buckets().get("Buckets", [])
    except ClientError as e:
        if _is_access_denied(e):
            print("⚠️  Sustainability S3 lifecycle check skipped — missing: s3:ListAllMyBuckets")
        else:
            print(f"⚠️  Sustainability S3 lifecycle check failed: {e}")
        return [], False

    for bucket in buckets:
        name = bucket.get("Name", "unknown")
        has_rules = False
        try:
            response = s3.get_bucket_lifecycle_configuration(Bucket=name)
            has_rules = bool(response.get("Rules"))
            checked_any_bucket = True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"NoSuchLifecycleConfiguration", "NoSuchBucket"}:
                has_rules = False
                checked_any_bucket = True
            elif _is_access_denied(e):
                # Per-bucket permission issue; still continue account scan.
                access_denied_buckets += 1
                continue
            else:
                continue

        buckets_input.append({"Name": name, "HasLifecycleRules": has_rules})

    if buckets and not checked_any_bucket and access_denied_buckets == len(buckets):
        print("⚠️  Sustainability S3 lifecycle check skipped — missing: s3:GetLifecycleConfiguration")
        return [], False

    return check_s3_lifecycle_policies(buckets_input, region), True


def fetch_idle_always_on_findings(region: str) -> tuple[list, bool]:
    ec2 = boto3.client("ec2", region_name=region)
    cloudwatch = boto3.client("cloudwatch", region_name=region)

    try:
        paginator = ec2.get_paginator("describe_instances")
        running: list[dict] = []
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    if instance.get("State", {}).get("Name") != "running":
                        continue
                    running.append(instance)
    except ClientError as e:
        if _is_access_denied(e):
            print("⚠️  Sustainability idle EC2 check skipped — missing: ec2:DescribeInstances")
        else:
            print(f"⚠️  Sustainability idle EC2 check failed: {e}")
        return [], False

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=CLOUDWATCH_LOOKBACK_DAYS)
    instances_input: list[dict] = []

    for instance in running:
        instance_id = instance.get("InstanceId", "unknown")
        instance_type = instance.get("InstanceType", "unknown")

        try:
            stats = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=now,
                Period=3600,
                Statistics=["Average"],
            )
            datapoints = stats.get("Datapoints", [])
            cpu_avg = (
                sum(dp.get("Average", 0.0) for dp in datapoints) / len(datapoints)
                if datapoints else 0.0
            )
        except ClientError as e:
            if _is_access_denied(e):
                print("⚠️  Sustainability idle EC2 check skipped — missing: cloudwatch:GetMetricStatistics")
                return [], False
            # Skip instances where CPU telemetry is unavailable due to transient API issues.
            continue

        instances_input.append({
            "instance_id": instance_id,
            "instance_type": instance_type,
            "cpu_avg": cpu_avg,
            "current_price": fetch_price_from_aws(instance_type, region),
        })

    return check_idle_always_on_instances(instances_input, region), True


def fetch_lambda_memory_findings(region: str) -> tuple[list, bool]:
    lambda_client = boto3.client("lambda", region_name=region)
    logs = boto3.client("logs", region_name=region)

    try:
        paginator = lambda_client.get_paginator("list_functions")
        functions = []
        for page in paginator.paginate():
            functions.extend(page.get("Functions", []))
    except ClientError as e:
        if _is_access_denied(e):
            print("⚠️  Sustainability Lambda memory check skipped — missing: lambda:ListFunctions")
        else:
            print(f"⚠️  Sustainability Lambda memory check failed: {e}")
        return [], False

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=CLOUDWATCH_LOOKBACK_DAYS)
    functions_input: list[dict] = []

    for function in functions:
        fn_name = function.get("FunctionName", "unknown")
        configured_memory = int(function.get("MemorySize", 0) or 0)

        max_used, query_ok = _query_lambda_max_memory_used(logs, fn_name, start, now)
        if not query_ok:
            print("⚠️  Sustainability Lambda memory check skipped — missing: logs:StartQuery/logs:GetQueryResults")
            return [], False

        functions_input.append({
            "FunctionName": fn_name,
            "ConfiguredMemoryMB": configured_memory,
            "MaxMemoryUsedMB": max_used,
        })

    return check_lambda_overprovisioned_memory(functions_input, region), True


def fetch_unencrypted_ebs_findings(region: str) -> tuple[list, bool]:
    ec2 = boto3.client("ec2", region_name=region)
    volumes: list[dict] = []

    try:
        paginator = ec2.get_paginator("describe_volumes")
        for page in paginator.paginate():
            volumes.extend(page.get("Volumes", []))
    except ClientError as e:
        if _is_access_denied(e):
            print("⚠️  Sustainability EBS encryption check skipped — missing: ec2:DescribeVolumes")
        else:
            print(f"⚠️  Sustainability EBS encryption check failed: {e}")
        return [], False

    return check_unencrypted_ebs_volumes(volumes, region), True

# src/infra_review_cli/adapters/aws/elb_adapter.py

import boto3
from datetime import datetime, timedelta
from src.infra_review_cli.core.checks.check_unused_elb import check_unused_elb


def fetch_elb_usage(region: str) -> list:
    elbv2 = boto3.client("elbv2", region_name=region)
    cw = boto3.client("cloudwatch", region_name=region)

    findings_input = []

    try:
        # 1. Get all load balancers
        response = elbv2.describe_load_balancers()
        load_balancers = response["LoadBalancers"]



        for lb in load_balancers:
            name = lb["LoadBalancerName"]
            arn = lb["LoadBalancerArn"]
            lb_type = lb["Type"]

            # 2. Get healthy targets count
            target_health_count = 0
            try:
                target_groups = elbv2.describe_target_groups(LoadBalancerArn=arn)["TargetGroups"]
                for tg in target_groups:
                    health = elbv2.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
                    target_health_count += sum(1 for t in health["TargetHealthDescriptions"]
                                               if t["TargetHealth"]["State"] == "healthy")
            except Exception as e:
                print(f"⚠️ Error checking target health for {name}: {e}")

            # 3. Get request count from CloudWatch (7 days)
            end = datetime.utcnow()
            start = end - timedelta(days=7)
            try:
                metrics = cw.get_metric_statistics(
                    Namespace="AWS/ApplicationELB",
                    MetricName="RequestCount",
                    Dimensions=[{"Name": "LoadBalancer", "Value": arn.split(":loadbalancer/")[1]}],
                    StartTime=start,
                    EndTime=end,
                    Period=86400,
                    Statistics=["Sum"]
                )

                # Sum the request counts from the datapoints

                datapoints = metrics.get("Datapoints", [])
                request_count = int(sum(dp["Sum"] for dp in datapoints)) if datapoints else 0

            except Exception as e:
                print(f"⚠️ Error fetching RequestCount for {name}: {e}")
                request_count = 0

            findings_input.append({
                "Name": name,
                "Type": lb_type,
                "LoadBalancerArn": arn,
                "RequestCount": request_count,
                "HealthyTargetCount": target_health_count
            })

    except Exception as e:
        print(f"❌ Error listing load balancers: {e}")
        return []

    return check_unused_elb(findings_input, region)

import boto3
from src.infra_review_cli.core.checks.ecs import check_ecs_task_definition_drift


def fetch_ecs_task_def_drift(region: str):
    ecs = boto3.client("ecs", region_name=region)

    findings = []

    clusters = ecs.list_clusters()["clusterArns"]
    for cluster_arn in clusters:
        service_arns = ecs.list_services(cluster=cluster_arn)["serviceArns"]

        if not service_arns:
            continue

        described_services = ecs.describe_services(
            cluster=cluster_arn,
            services=service_arns
        )["services"]

        for svc in described_services:
            current_td = svc["taskDefinition"]
            family = current_td.split("/")[-1].split(":")[0]  # e.g. "my-service"
            current_revision = int(current_td.split(":")[-1])

            # Get latest revision for this family
            td_list = ecs.list_task_definitions(
                familyPrefix=family,
                sort="DESC",
                maxResults=1
            )["taskDefinitionArns"]

            if td_list:
                latest_td = td_list[0]
                latest_revision = int(latest_td.split(":")[-1])

                if current_revision < latest_revision:
                    findings.extend(check_ecs_task_definition_drift(
                        service_name=svc["serviceName"],
                        current_rev=current_revision,
                        latest_rev=latest_revision,
                        region=region
                    ))

    return findings

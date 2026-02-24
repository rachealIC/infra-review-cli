"""
ECS checks — consolidated security, scaling, drift, and performance.
"""

from infra_review_cli.core.ai.fargate import suggest_cpu_memory
from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.core.ai.remediation import generate_ai_remediation
from infra_review_cli.utils.utility import generate_finding_id


def check_ecs_task_definition_drift(service_name, current_rev, latest_rev, region):
    headline = f"ECS service '{service_name}' is not using latest task definition"
    description = (
        f"The service is using revision {current_rev}, "
        f"but the latest available is {latest_rev}."
    )

    remediation = generate_ai_remediation(headline, description)

    return [Finding(
        finding_id=generate_finding_id("perf-ecs-001", service_name, region),
        resource_id=service_name,
        region=region,
        pillar=Pillar.PERFORMANCE,
        severity=Severity.MEDIUM,
        effort=Effort.MEDIUM,
        headline=headline,
        detailed_description=description,
        remediation_steps=remediation
    )]


def check_unused_services(service: dict, cluster_arn: str, region: str) -> list[Finding]:
    service_name = service["serviceName"]
    desired = service.get("desiredCount", 0)
    running = service.get("runningCount", 0)

    if desired == 0 and running == 0:
        headline = f"ECS service '{service_name}' in cluster '{cluster_arn}' is unused"
        description = (
            f"The service is not running any tasks and has a desired count of 0. "
            f"It may be inactive, leftover from testing, or no longer needed."
        )

        return [Finding(
            finding_id=generate_finding_id("cost-ecs-001", service_name, region),
            resource_id=service_name,
            region=region,
            pillar=Pillar.COST,
            severity=Severity.LOW,
            effort=Effort.LOW,
            headline=headline,
            detailed_description=description,
            remediation_steps="Consider deleting the service if it is no longer needed."
        )]

    return []


def check_overprovisioned_task(task_id, service_name, region,
                                requested_cpu, requested_mem,
                                cpu_used_pct, mem_used_pct,
                                cpu_threshold, mem_threshold) -> list[Finding]:

    findings = []

    cpu_under_threshold = cpu_used_pct < cpu_threshold
    mem_under_threshold = mem_used_pct < mem_threshold

    if cpu_under_threshold or mem_under_threshold:
        suggestion = suggest_cpu_memory(
            cpu=requested_cpu,
            mem=requested_mem,
            avg_cpu=cpu_used_pct,
            avg_mem=mem_used_pct
        )

        if suggestion and isinstance(suggestion, dict):
            suggested_cpu = suggestion.get("cpu", requested_cpu)
            suggested_mem = suggestion.get("memory", requested_mem)
            est_savings = suggestion.get("estimated_savings", 0.0)

            if suggested_cpu == requested_cpu and suggested_mem == requested_mem:
                return findings

            headline = f"ECS task '{task_id}' is overprovisioned"
            description = (
                f"Provisioned: {requested_cpu} CPU, {requested_mem}MB memory. "
                f"Used: {cpu_used_pct:.1f}% CPU, {mem_used_pct:.1f}% memory. "
                f"Suggested: {suggested_cpu} CPU, {suggested_mem}MB."
            )

            findings.append(Finding(
                finding_id=generate_finding_id("cost-ecs-005", task_id, region),
                resource_id=task_id,
                region=region,
                pillar=Pillar.COST,
                severity=Severity.MEDIUM,
                effort=Effort.MEDIUM,
                estimated_savings=est_savings,
                headline=headline,
                detailed_description=description,
                remediation_steps="Resize to suggested CPU and memory to optimize cost.",
                suggested_cpu_units=suggested_cpu,
                suggested_mem_mb=suggested_mem
            ))
    return findings


def check_missing_autoscaling(
    service_name: str,
    cluster_name: str,
    region: str,
) -> list[Finding]:
    """Returns a finding if the ECS service has no auto-scaling policy."""
    headline = f"ECS service '{service_name}' has no auto scaling policy"
    description = (
        f"The ECS service '{service_name}' in cluster '{cluster_name}' is not attached to any "
        "Application Auto Scaling policy. This could lead to performance bottlenecks under "
        "increased load, or wasted costs when load is low."
    )

    return [Finding(
        finding_id=generate_finding_id("perf-ecs-003", service_name, region),
        resource_id=service_name,
        region=region,
        pillar=Pillar.PERFORMANCE,
        severity=Severity.MEDIUM,
        effort=Effort.MEDIUM,
        headline=headline,
        detailed_description=description,
        remediation_steps=(
            "- Attach a target tracking scaling policy to this ECS service.\n"
            "- Use ECSServiceAverageCPUUtilization as the target metric "
            "(target value: 60–70% is a good starting point)."
        ),
        required_iam_permission="application-autoscaling:DescribeScalableTargets",
    )]


def check_task_running_as_root(
    task_arn: str,
    region: str,
    container_def: dict,
    task_family: str,
) -> list[Finding]:
    """Returns a finding if the container user is root or unset."""
    container_name = container_def.get("name", "unknown")
    user = container_def.get("user", "").strip().lower()

    if user and user not in ["root", "0"]:
        return []

    headline = f"ECS container '{container_name}' runs as root"
    description = (
        f"The container in task definition '{task_family}' is either not specifying a user "
        "or is explicitly set to run as root. Running containers as root increases risk "
        "of privilege escalation attacks."
    )

    return [Finding(
        finding_id=generate_finding_id("sec-ecs-001", task_arn, region),
        resource_id=task_arn,
        region=region,
        pillar=Pillar.SECURITY,
        severity=Severity.HIGH,
        effort=Effort.MEDIUM,
        headline=headline,
        detailed_description=description,
        remediation_steps=(
            "- Specify a non-root user in the container definition, e.g.: "
            "\"user\": \"1000:1000\".\n"
            "- Enable ECS Exec audit logging to detect any privilege escalation attempts."
        ),
        required_iam_permission="ecs:DescribeTaskDefinition",
    )]

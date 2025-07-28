# core/checks/ecs.py

from src.infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from src.infra_review_cli.core.ai.remediation import generate_ai_remediation
from src.infra_review_cli.core.utility import generate_finding_id


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
        estimated_savings=0.0,  # Not a cost issue
        headline=headline,
        detailed_description=description,
        remediation_steps=remediation
    )]

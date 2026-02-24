from infra_review_cli.core.ai.cost import estimate_savings
from infra_review_cli.core.ai.remediation import generate_ai_remediation
from infra_review_cli.core.models import Finding, Severity, Effort, Pillar
from infra_review_cli.utils.utility import generate_finding_id


def check_unused_elb(elbs: list[dict], region: str) -> list[Finding]:
    """
    Flags load balancers that have no traffic and no healthy targets.

    Each ELB input must include:
      - LoadBalancerArn
      - Name
      - Type
      - RequestCount (last 7 days)
      - HealthyTargetCount
    """
    findings = []



    for elb in elbs:

        headline = "Unused Load Balancer detected"
        detailed_description = (
            f"Load Balancer '{elb.get("Name")}' of type '{elb.get("Type")}' has had no traffic and "
            f"no healthy targets in the past 7 days. It may be unused."
        )

        # remediation_steps = generate_ai_remediation(headline, detailed_description)

        name = elb.get("Name")
        lb_type = elb.get("Type")
        arn = elb.get("LoadBalancerArn", name)
        request_count = elb.get("RequestCount", 0)
        healthy_targets = elb.get("HealthyTargetCount", 0)

        if request_count == 0 and healthy_targets == 0:
            findings.append(Finding(
                finding_id=generate_finding_id("cost-elb-001", name, region),
                resource_id=name,
                region=region,
                pillar=Pillar.COST,
                severity=Severity.MEDIUM,
                effort=Effort.MEDIUM,
                headline=headline,
                estimated_savings=estimate_savings(
                    resource_type="elb",
                    usage="unused_elb",
                    region=region,
                    instance_id=name
                ),
                detailed_description=detailed_description,
                remediation_steps="Deregister the ELB or update target group health checks."
            ))

    return findings

# core/checks/ec2.py
from src.infra_review_cli.core.ai.cost import estimate_savings
from src.infra_review_cli.core.ai.remediation import generate_ai_remediation
from src.infra_review_cli.core.models import Finding, Severity, Effort, Pillar
from datetime import datetime, timezone

from src.infra_review_cli.core.utility import generate_finding_id


def check_ec2_rightsizing(cpu_data: dict, region: str, threshold: float = 20.0) -> list[Finding]:
    findings = []
    for instance_id, cpu_values in cpu_data.items():

        if not cpu_values:
            continue

        peak = max(cpu_values)
        headline = "Underutilized EC2 instance"
        detailed_description = f"Instance '{instance_id}' has low CPU usage (max {peak:.1f}%)."

        remediation_steps = generate_ai_remediation(headline, detailed_description)


        if peak < threshold:
            findings.append(Finding(
                finding_id=generate_finding_id("cost-ec2-001", instance_id, region),
                resource_id=instance_id,
                region=region,
                pillar=Pillar.COST,
                severity=Severity.MEDIUM,
                effort=Effort.MEDIUM,
                estimated_savings=estimate_savings(
                    resource_type="ec2",
                    usage="low_cpu",
                    region=region,
                    instance_id=instance_id
                ),
                headline=headline,
                detailed_description=detailed_description,
                remediation_steps=remediation_steps
            ))
    return findings


def check_unattached_ebs(volumes: list[dict], region: str, min_age_days: int = 30) -> list[Finding]:
    now = datetime.now(timezone.utc)
    findings = []

    for vol in volumes:
        if vol["State"] != "available":
            continue

        age_days = (now - vol["CreateTime"]).days
        if age_days < min_age_days:
            continue

        headline = "Unattached EBS volume"
        detailed_description = f"Volume has been unattached for {age_days} days."

        remediation_steps = generate_ai_remediation(headline, detailed_description)
        resource_id = vol["VolumeId"]

        findings.append(Finding(
            finding_id=generate_finding_id("cost-ebs-001", resource_id, region),
            resource_id=resource_id,
            region=region,
            pillar=Pillar.COST,
            severity=Severity.MEDIUM,
            effort=Effort.LOW,
            estimated_savings=estimate_savings(
                                resource_type="ec2",
                                usage="unattached_ebs",
                                region=region,
                                instance_id=resource_id
),
            headline=headline,
            detailed_description=detailed_description,
            remediation_steps=remediation_steps
        ))

        print(f"Unattached EBS volume found: {resource_id} in {region}, age: {age_days} days")
    return findings



def check_unassociated_elastic_ips(addresses: list[dict], region: str) -> list[Finding]:
    findings = []

    for ip in addresses:
        if "AssociationId" not in ip:
            allocation_id = ip.get("AllocationId", "unknown")
            public_ip = ip.get("PublicIp", "unknown")

            headline = f"Unassociated Elastic IP: {public_ip}"
            description = (
                f"Elastic IP '{public_ip}' (Allocation ID: {allocation_id}) is not associated "
                f"with any EC2 instance, NAT gateway, or network interface."
            )

            remediation = generate_ai_remediation(headline, description)

            findings.append(Finding(
                finding_id=generate_finding_id("cost-elip-003", allocation_id, region),
                resource_id=public_ip,
                region=region,
                pillar=Pillar.COST,
                severity=Severity.LOW,
                effort=Effort.LOW,
                estimated_savings=3.60,  # Based on AWS pricing
                headline=headline,
                detailed_description=description,
                remediation_steps=remediation
            ))

    return findings

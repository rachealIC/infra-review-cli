"""
EC2 checks — consolidated rightsizing, unattached EBS, unassociated EIPs, and ASG coverage.
"""

from datetime import datetime, timezone
from infra_review_cli.core.ai.ec2 import suggest_ec2_rightsizing
from infra_review_cli.core.models import Finding, Severity, Effort, Pillar
from infra_review_cli.utils.pricing import get_ebs_price_per_gb, get_elastic_ip_price
from infra_review_cli.utils.utility import generate_finding_id
from infra_review_cli.config import CPU_OVERUTIL_THRESHOLD, CPU_PEAK_SPIKE_THRESHOLD


def check_ec2_rightsizing(instance_data: list, threshold: float = 20.0) -> list[Finding]:
    findings = []
    for inst in instance_data:
        instance_id = inst["instance_id"]
        cpu_avg = inst["cpu_avg"]
        cpu_max = inst["cpu_max"]
        instance_type = inst["instance_type"]
        region = inst["region"]
        arch = inst.get("architecture", "x86_64")
        network = inst.get("network_gb_total", 0.0)
        price = inst.get("current_price", 0.0)

        if cpu_avg < threshold:
            suggestion = suggest_ec2_rightsizing(
                instance_id=instance_id,
                instance_type=instance_type,
                architecture=arch,
                region=region,
                current_price=price,
                cpu_avg=cpu_avg,
                cpu_max=cpu_max,
                network_gb_total=network
            )

            if suggestion and suggestion.get("suggested_instance_type"):
                est_savings = suggestion.get("estimated_monthly_savings")
                if est_savings is None:
                    est_savings = price * 730 * 0.5 if price > 0 else 0.0

                findings.append(Finding(
                    finding_id=generate_finding_id("cost-ec2-001", instance_id, region),
                    resource_id=instance_id,
                    region=region,
                    pillar=Pillar.COST,
                    severity=Severity.MEDIUM,
                    effort=Effort.MEDIUM,
                    estimated_savings=est_savings,
                    headline=f"EC2 instance '{instance_id}' is underutilized",
                    detailed_description=(
                        f"Average CPU: {cpu_avg:.1f}%, Peak: {cpu_max:.1f}%. "
                        f"Suggested: {suggestion['suggested_instance_type']}. "
                        f"Reason: {suggestion['reasoning']}"
                    ),
                    remediation_steps=suggestion.get("notes", "Review before resizing.")
                ))

        elif cpu_avg > CPU_OVERUTIL_THRESHOLD or (cpu_max > CPU_PEAK_SPIKE_THRESHOLD and cpu_avg > (CPU_OVERUTIL_THRESHOLD * 0.7)):
            findings.append(Finding(
                finding_id=generate_finding_id("perf-ec2-highcpu", instance_id, region),
                resource_id=instance_id,
                region=region,
                pillar=Pillar.PERFORMANCE,
                severity=Severity.HIGH,
                effort=Effort.HIGH,
                headline=f"EC2 instance '{instance_id}' is consistently overutilized",
                detailed_description=(
                    f"This instance has averaged {cpu_avg:.1f}% CPU usage over 14 days. "
                    "This may cause latency or degraded performance."
                ),
                remediation_steps="Consider upgrading instance type or using Auto Scaling."
            ))

    return findings


def check_unattached_ebs(volumes: list[dict], region: str, min_age_days: int = 30) -> list[Finding]:
    now = datetime.now(timezone.utc)
    findings = []
    for vol in volumes:
        size_gb = vol["Size"]
        if vol["State"] != "available":
            continue

        age_days = (now - vol["CreateTime"]).days
        if age_days < min_age_days:
            continue

        volume_type = vol.get("VolumeType", "gp2")
        price_per_gb = get_ebs_price_per_gb(volume_type, region)
        estimated_savings = size_gb * price_per_gb

        resource_id = vol["VolumeId"]
        findings.append(Finding(
            finding_id=generate_finding_id("cost-ebs-001", resource_id, region),
            resource_id=resource_id,
            region=region,
            pillar=Pillar.COST,
            severity=Severity.MEDIUM,
            effort=Effort.LOW,
            estimated_savings=estimated_savings,
            headline=f"Unattached {volume_type.upper()} EBS volume of {size_gb} GB",
            detailed_description=(
                f"EBS volume '{resource_id}' is currently unattached. "
                f"Estimated monthly cost: ${estimated_savings:.2f}"
            ),
            remediation_steps="Delete or snapshot the volume to save costs."
        ))
    return findings


def check_unassociated_elastic_ips(addresses: list[dict], region: str) -> list[Finding]:
    findings = []
    for ip in addresses:
        if "AssociationId" not in ip:
            allocation_id = ip.get("AllocationId", "unknown")
            public_ip = ip.get("PublicIp", "unknown")

            findings.append(Finding(
                finding_id=generate_finding_id("cost-elip-003", allocation_id, region),
                resource_id=public_ip,
                region=region,
                pillar=Pillar.COST,
                severity=Severity.LOW,
                effort=Effort.LOW,
                estimated_savings=get_elastic_ip_price(region),
                headline=f"Unassociated Elastic IP: {public_ip}",
                detailed_description=(
                    f"Elastic IP '{public_ip}' is not associated with any resource."
                ),
                remediation_steps="Release the unused Elastic IP to avoid charges."
            ))
    return findings


def check_ec2_autoscaling_groups(
    instance_ids_in_asgs: set[str],
    all_instance_ids: list[str],
    region: str,
) -> list[Finding]:
    """Flags running EC2 instances that are NOT part of any Auto Scaling Group."""
    findings = []
    for instance_id in all_instance_ids:
        if instance_id in instance_ids_in_asgs:
            continue

        findings.append(Finding(
            finding_id=generate_finding_id("rel-asg-001", instance_id, region),
            resource_id=instance_id,
            region=region,
            pillar=Pillar.RELIABILITY,
            severity=Severity.MEDIUM,
            effort=Effort.MEDIUM,
            headline=f"EC2 instance '{instance_id}' is not in an Auto Scaling Group",
            detailed_description=(
                f"Instance '{instance_id}' is not managed by an Auto Scaling Group. "
                "Failed instances will not be automatically replaced."
            ),
            remediation_steps="Move the instance into an Auto Scaling Group for better resilience.",
            required_iam_permission="autoscaling:DescribeAutoScalingInstances",
        ))
    return findings

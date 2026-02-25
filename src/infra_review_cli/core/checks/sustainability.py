"""
Sustainability pillar checks.
"""

import math
import re
from infra_review_cli.core.models import Effort, Finding, Pillar, Severity
from infra_review_cli.utils.utility import generate_finding_id


_GRAVITON_SUPPORTED_PREFIXES = {"t", "m", "c", "r"}


def suggest_graviton_equivalent(instance_type: str) -> str | None:
    """
    Returns a likely Graviton equivalent instance type for common families,
    or None when no straightforward mapping is available.
    """
    if not instance_type or "." not in instance_type:
        return None

    family, size = instance_type.split(".", 1)
    family = family.lower()

    if family.endswith("g"):
        return None

    match = re.match(r"^([a-z]+)(\d+)([a-z0-9-]*)$", family)
    if not match:
        return None

    prefix, generation_raw, _suffix = match.groups()
    if prefix not in _GRAVITON_SUPPORTED_PREFIXES:
        return None

    generation = int(generation_raw)

    if prefix == "t":
        target_family = "t4g"
    else:
        # m/c/r gained Graviton in gen 6. For higher gens, keep same generation.
        target_family = f"{prefix}{max(generation, 6)}g"

    return f"{target_family}.{size}"


def check_graviton_instance_usage(instances: list[dict], region: str) -> list[Finding]:
    """Flags x86 instance families with practical Graviton equivalents."""
    findings: list[Finding] = []

    for inst in instances:
        instance_id = inst.get("instance_id", "unknown")
        instance_type = inst.get("instance_type", "")
        suggested = suggest_graviton_equivalent(instance_type)

        if not suggested:
            continue

        price = float(inst.get("current_price", 0.0) or 0.0)
        monthly_cost = price * 730 if price > 0 else 0.0
        est_savings = monthly_cost * 0.2 if monthly_cost > 0 else 0.0

        findings.append(Finding(
            finding_id=generate_finding_id("sus-ec2-graviton-001", instance_id, region),
            resource_id=instance_id,
            region=region,
            pillar=Pillar.SUSTAINABILITY,
            severity=Severity.LOW,
            effort=Effort.MEDIUM,
            estimated_savings=est_savings,
            headline=f"EC2 instance '{instance_id}' is not using Graviton",
            detailed_description=(
                f"Instance type '{instance_type}' can often be migrated to '{suggested}'. "
                "Graviton-based instances typically provide better price-performance and "
                "lower energy consumption."
            ),
            remediation_steps=(
                f"Validate workload compatibility, then migrate from '{instance_type}' to '{suggested}' "
                "in a staged rollout."
            ),
            required_iam_permission="ec2:DescribeInstances",
        ))

    return findings


def check_s3_lifecycle_policies(buckets: list[dict], region: str) -> list[Finding]:
    """Flags buckets without lifecycle policies."""
    findings: list[Finding] = []

    for bucket in buckets:
        name = bucket.get("Name", "unknown")
        has_rules = bucket.get("HasLifecycleRules", False)
        if has_rules:
            continue

        findings.append(Finding(
            finding_id=generate_finding_id("sus-s3-lifecycle-001", name, region),
            resource_id=name,
            region=region,
            pillar=Pillar.SUSTAINABILITY,
            severity=Severity.LOW,
            effort=Effort.LOW,
            headline=f"S3 bucket '{name}' has no lifecycle policy",
            detailed_description=(
                f"Bucket '{name}' has no lifecycle rules. Keeping all objects in standard storage "
                "indefinitely increases storage cost and environmental footprint."
            ),
            remediation_steps=(
                "Add lifecycle rules to transition objects to S3 Standard-IA after 90 days, "
                "Glacier after 180 days, and expire/delete after 365 days (or your policy baseline)."
            ),
            required_iam_permission="s3:GetLifecycleConfiguration",
        ))

    return findings


def check_idle_always_on_instances(instances: list[dict], region: str, threshold: float = 5.0) -> list[Finding]:
    """Flags EC2 instances that run continuously with very low average CPU."""
    findings: list[Finding] = []

    for inst in instances:
        instance_id = inst.get("instance_id", "unknown")
        cpu_avg = float(inst.get("cpu_avg", 0.0) or 0.0)
        instance_type = inst.get("instance_type", "unknown")

        if cpu_avg >= threshold:
            continue

        price = float(inst.get("current_price", 0.0) or 0.0)
        monthly_cost = price * 730 if price > 0 else 0.0
        est_savings = monthly_cost * 0.5 if monthly_cost > 0 else 0.0

        findings.append(Finding(
            finding_id=generate_finding_id("sus-ec2-idle-001", instance_id, region),
            resource_id=instance_id,
            region=region,
            pillar=Pillar.SUSTAINABILITY,
            severity=Severity.MEDIUM,
            effort=Effort.MEDIUM,
            estimated_savings=est_savings,
            headline=f"EC2 instance '{instance_id}' appears always-on and idle",
            detailed_description=(
                f"Instance '{instance_id}' ({instance_type}) averaged {cpu_avg:.2f}% CPU over 14 days. "
                "This suggests the workload can likely be scheduled or decommissioned."
            ),
            remediation_steps=(
                "Use AWS Instance Scheduler (or Lambda/EventBridge) to stop non-production instances "
                "during off-hours, or terminate if no longer needed."
            ),
            required_iam_permission="cloudwatch:GetMetricStatistics",
        ))

    return findings


def _recommended_lambda_memory(max_used_mb: float) -> int:
    """Returns memory recommendation with 20% headroom and sane floor."""
    target = max(128.0, max_used_mb * 1.2)
    return int(math.ceil(target / 64.0) * 64)


def check_lambda_overprovisioned_memory(functions: list[dict], region: str) -> list[Finding]:
    """Flags Lambda functions configured with >2x max observed memory usage."""
    findings: list[Finding] = []

    for fn in functions:
        name = fn.get("FunctionName", "unknown")
        configured = int(fn.get("ConfiguredMemoryMB", 0) or 0)
        max_used = float(fn.get("MaxMemoryUsedMB", 0.0) or 0.0)

        if configured <= 0 or max_used <= 0:
            continue

        if configured <= (max_used * 2):
            continue

        suggested = _recommended_lambda_memory(max_used)

        findings.append(Finding(
            finding_id=generate_finding_id("sus-lambda-memory-001", name, region),
            resource_id=name,
            region=region,
            pillar=Pillar.SUSTAINABILITY,
            severity=Severity.LOW,
            effort=Effort.LOW,
            headline=f"Lambda '{name}' may be over-provisioned on memory",
            detailed_description=(
                f"Function memory is set to {configured} MB, while max observed usage is {max_used:.1f} MB. "
                "Over-provisioned memory increases cost and energy usage."
            ),
            remediation_steps=(
                f"Reduce configured memory to around {suggested} MB (max usage + 20% headroom), "
                "then validate latency and error rate after deployment."
            ),
            required_iam_permission="logs:StartQuery, logs:GetQueryResults",
        ))

    return findings


def check_unencrypted_ebs_volumes(volumes: list[dict], region: str) -> list[Finding]:
    """Flags EBS volumes that are not encrypted."""
    findings: list[Finding] = []

    for volume in volumes:
        volume_id = volume.get("VolumeId", "unknown")
        if volume.get("Encrypted", False):
            continue

        findings.append(Finding(
            finding_id=generate_finding_id("sus-ebs-encryption-001", volume_id, region),
            resource_id=volume_id,
            region=region,
            pillar=Pillar.SUSTAINABILITY,
            severity=Severity.MEDIUM,
            effort=Effort.MEDIUM,
            headline=f"EBS volume '{volume_id}' is not encrypted",
            detailed_description=(
                f"Volume '{volume_id}' is unencrypted. Encryption supports data protection and "
                "aligns with sustainable, secure infrastructure practices."
            ),
            remediation_steps=(
                "Create an encrypted snapshot and restore to an encrypted volume, then replace the old volume. "
                "Also enable default EBS encryption for new volumes in account settings."
            ),
            required_iam_permission="ec2:DescribeVolumes",
        ))

    return findings

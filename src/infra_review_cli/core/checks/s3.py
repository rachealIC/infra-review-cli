"""
S3 checks — consolidated public access and versioning.
"""

from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.utils.utility import generate_finding_id


def check_s3_public_access(s3_buckets: list[dict], region: str) -> list[Finding]:
    """Flags S3 buckets that are publicly accessible."""
    findings = []
    for bucket in s3_buckets:
        if bucket.get("Public", False):
            name = bucket["Name"]
            headline = "S3 bucket is publicly accessible"
            description = f"Bucket '{name}' is publicly accessible. Reason: {bucket.get('Reason', 'Unknown')}"

            findings.append(Finding(
                finding_id=generate_finding_id("sec-s3-001", name, region),
                resource_id=name,
                region=region,
                pillar=Pillar.SECURITY,
                severity=Severity.HIGH,
                effort=Effort.LOW,
                headline=headline,
                detailed_description=description,
                remediation_steps="Make the bucket private or apply a restrictive bucket policy.",
                required_iam_permission="s3:GetBucketPolicy"
            ))
    return findings


def check_s3_versioning(buckets: list[dict], region: str) -> list[Finding]:
    """Flags S3 buckets that do not have versioning enabled."""
    findings = []
    for bucket in buckets:
        name = bucket.get("Name", "unknown")
        status = bucket.get("VersioningStatus", "")

        if status == "Enabled":
            continue

        suspended = status == "Suspended"
        headline = f"S3 bucket '{name}' has versioning {'suspended' if suspended else 'disabled'}"
        description = (
            f"Bucket '{name}' {'had versioning suspended' if suspended else 'has never had versioning enabled'}. "
            "Without versioning, accidental deletions or overwrites are permanent."
        )
        sev = Severity.MEDIUM if not suspended else Severity.HIGH

        findings.append(Finding(
            finding_id=generate_finding_id("rel-s3-001", name, region),
            resource_id=name,
            region=region,
            pillar=Pillar.RELIABILITY,
            severity=sev,
            effort=Effort.LOW,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"Enable versioning: aws s3api put-bucket-versioning "
                f"--bucket {name} --versioning-configuration Status=Enabled"
            ),
            required_iam_permission="s3:GetBucketVersioning",
        ))
    return findings

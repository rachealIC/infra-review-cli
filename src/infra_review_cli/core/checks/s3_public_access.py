# src/infra_review_cli/core/checks/s3_public_access.py
from src.infra_review_cli.core.ai.remediation import generate_ai_remediation
from src.infra_review_cli.core.models import Finding, Severity, Effort, Pillar
from src.infra_review_cli.core.utility import generate_finding_id


def check_s3_public_access(s3_buckets: list[dict], region: str) -> list[Finding]:
    findings = []

    for bucket in s3_buckets:
        name = bucket["Name"]
        is_public = bucket.get("Public", False)
        reason = bucket.get("Reason", "Unknown")

        if is_public:
            headline = "S3 bucket is publicly accessible"
            detailed_description = f"Bucket '{name}' is publicly accessible. Reason: {reason}"


            # Call the AI to generate remediation steps dynamically
            remediation_steps = generate_ai_remediation(headline, detailed_description)

            findings.append(Finding(
                finding_id=generate_finding_id("sec-s3-001", name, region),
                resource_id=name,
                region=region,
                pillar=Pillar.SECURITY,
                severity=Severity.HIGH,
                effort=Effort.LOW,
                detailed_description=detailed_description,
                headline=headline,
                remediation_steps=remediation_steps
            ))

    return findings

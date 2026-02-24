# src/infra_review_cli/core/checks/performance.py
"""
Performance Efficiency pillar checks (supplementing ecs.py).

Checks in this module:
  - check_cloudfront_usage      (perf-cf-001): Static content without CloudFront
  - check_ec2_rightsizing_extended (perf-ec2-002): High-CPU instances without ASG
"""

from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.utils.utility import generate_finding_id


# ---------------------------------------------------------------------------
# 1. CloudFront Distribution Usage
# ---------------------------------------------------------------------------

def check_cloudfront_usage(
    distributions: list[dict],
    public_buckets: list[str],
    alb_dns_names: list[str],
    region: str,
) -> list[Finding]:
    """
    Flags public S3 buckets and ALBs that aren't fronted by a CloudFront distribution.

    Args:
        distributions: CloudFront distribution origin domains (from cloudfront.list_distributions()).
        public_buckets: Names of public S3 buckets (from s3 adapter).
        alb_dns_names:  DNS names of Application Load Balancers.
        region: AWS region.

    IAM required: cloudfront:ListDistributions
    """
    findings = []

    # Build set of origins already in CloudFront
    cf_origins: set[str] = set()
    for dist in distributions:
        for origin in dist.get("Origins", {}).get("Items", []):
            cf_origins.add(origin.get("DomainName", "").lower())

    for bucket_name in public_buckets:
        bucket_domain = f"{bucket_name}.s3.amazonaws.com"
        if any(bucket_name in o or bucket_domain in o for o in cf_origins):
            continue

        headline = f"Public S3 bucket '{bucket_name}' is not served via CloudFront"
        description = (
            f"The publicly accessible S3 bucket '{bucket_name}' does not have a "
            "CloudFront distribution pointing to it. Without CloudFront, content is "
            "served directly from S3 with higher latency, no edge caching, no WAF "
            "integration, and no custom SSL certificate support."
        )
        findings.append(Finding(
            finding_id=generate_finding_id("perf-cf-001", bucket_name, region),
            resource_id=bucket_name,
            region=region,
            pillar=Pillar.PERFORMANCE,
            severity=Severity.LOW,
            effort=Effort.MEDIUM,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"- Create a CloudFront distribution with origin: {bucket_name}.s3.amazonaws.com\n"
                "- Enable Origin Access Control (OAC) so S3 only serves content via CloudFront."
            ),
            required_iam_permission="cloudfront:ListDistributions",
        ))

    for alb_dns in alb_dns_names:
        if any(alb_dns.lower() in o for o in cf_origins):
            continue

        headline = f"ALB '{alb_dns}' is not behind a CloudFront distribution"
        description = (
            f"Application Load Balancer '{alb_dns}' does not have a CloudFront distribution "
            "in front of it. CloudFront would reduce latency for global users via edge "
            "caching of static assets and enable AWS WAF for additional security."
        )
        findings.append(Finding(
            finding_id=generate_finding_id("perf-cf-002", alb_dns, region),
            resource_id=alb_dns,
            region=region,
            pillar=Pillar.PERFORMANCE,
            severity=Severity.LOW,
            effort=Effort.MEDIUM,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"- Create a CloudFront distribution with ALB '{alb_dns}' as the origin.\n"
                "- Configure caching behaviors for static assets (images, CSS, JS) "
                "and pass dynamic requests to the origin."
            ),
            required_iam_permission="cloudfront:ListDistributions",
        ))

    return findings

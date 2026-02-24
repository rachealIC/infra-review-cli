# src/infra_review_cli/core/checks/operational_excellence.py
"""
Operational Excellence pillar checks.

Each check function is a standalone function that implements the BaseCheck contract
semantically (returns list[Finding], never None).

Checks in this module:
  - check_cloudtrail_enabled     (sec-ct-001) : Is CloudTrail logging enabled?
  - check_cloudwatch_alarms      (ops-cw-001) : Are any CloudWatch alarms configured?
  - check_resource_tagging       (ops-tag-001): Do resources have required tags?
  - check_secrets_in_lambda_env  (ops-ssm-001): Are secrets stored in Lambda env vars?
"""

from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.utils.utility import generate_finding_id


# ---------------------------------------------------------------------------
# 1. CloudTrail Enabled
# ---------------------------------------------------------------------------

def check_cloudtrail_enabled(trails: list[dict], region: str) -> list[Finding]:
    """
    Checks whether CloudTrail is enabled and logging in the given region.

    Args:
        trails: Output of cloudtrail.describe_trails(includeShadowTrails=False)["trailList"]
                Each trail dict should include:
                  - TrailARN, Name, IsLogging (bool), IsMultiRegionTrail (bool)
        region: AWS region of the scan.

    Returns:
        A finding if no active trail is found, otherwise an empty list.

    IAM required: cloudtrail:DescribeTrails, cloudtrail:GetTrailStatus
    """
    active_trails = [t for t in trails if t.get("IsLogging", False)]

    if active_trails:
        return []

    headline = "CloudTrail is not enabled or logging is paused"
    description = (
        f"No active CloudTrail trail was found in region '{region}'. "
        "Without CloudTrail, API activity and changes to your AWS environment are not audited, "
        "making incident investigation and compliance reporting impossible."
    )

    return [Finding(
        finding_id=generate_finding_id("ops-ct-001", region, region),
        resource_id=region,
        region=region,
        pillar=Pillar.OPERATIONAL,
        severity=Severity.CRITICAL,
        effort=Effort.LOW,
        headline=headline,
        detailed_description=description,
        remediation_steps=(
            "- Enable CloudTrail in the AWS Console under CloudTrail > Create trail.\n"
            "- Enable multi-region logging and log to an S3 bucket with versioning enabled."
        ),
        required_iam_permission="cloudtrail:DescribeTrails",
    )]


# ---------------------------------------------------------------------------
# 2. CloudWatch Alarms Configured
# ---------------------------------------------------------------------------

def check_cloudwatch_alarms(alarms: list[dict], region: str) -> list[Finding]:
    """
    Checks whether any CloudWatch alarms are configured in the region.

    A region with zero alarms almost certainly has no operational monitoring
    in place, which is a significant Operational Excellence gap.

    Args:
        alarms: Output of cloudwatch.describe_alarms()["MetricAlarms"]
        region: AWS region of the scan.

    IAM required: cloudwatch:DescribeAlarms
    """
    if alarms:
        return []

    headline = "No CloudWatch alarms are configured in this region"
    description = (
        f"Region '{region}' has no CloudWatch metric alarms. "
        "Without alarms, operational issues (e.g. high CPU, failed health checks, "
        "billing spikes) will not be automatically detected or escalated."
    )

    return [Finding(
        finding_id=generate_finding_id("ops-cw-001", region, region),
        resource_id=region,
        region=region,
        pillar=Pillar.OPERATIONAL,
        severity=Severity.HIGH,
        effort=Effort.MEDIUM,
        headline=headline,
        detailed_description=description,
        remediation_steps=(
            "- Create CloudWatch alarms for key metrics: CPUUtilization, EstimatedCharges, "
            "HealthyHostCount, and 5xxError.\n"
            "- Attach alarms to an SNS topic that notifies your on-call team."
        ),
        required_iam_permission="cloudwatch:DescribeAlarms",
    )]


# ---------------------------------------------------------------------------
# 3. Resource Tagging
# ---------------------------------------------------------------------------

def check_resource_tagging(
    resources: list[dict],
    required_tags: list[str],
    region: str,
) -> list[Finding]:
    """
    Checks whether AWS resources have the required tags.

    Args:
        resources: List of resource dicts. Each dict must have:
                   - ResourceARN (str)
                   - Tags (list of {"Key": str, "Value": str})
        required_tags: List of tag keys that must be present (e.g. ["Name","Environment","Owner"]).
        region: AWS region of the scan.

    IAM required: tag:GetResources
    """
    findings = []

    for resource in resources:
        arn = resource.get("ResourceARN", "unknown")
        existing_keys = {tag["Key"] for tag in resource.get("Tags", [])}
        missing = [t for t in required_tags if t not in existing_keys]

        if not missing:
            continue

        headline = f"Resource is missing required tags: {', '.join(missing)}"
        description = (
            f"Resource '{arn}' is missing the following required tags: {', '.join(missing)}. "
            "Untagged resources cannot be attributed to a team, environment, or cost center, "
            "making cost allocation and incident response much harder."
        )

        findings.append(Finding(
            finding_id=generate_finding_id("ops-tag-001", arn, region),
            resource_id=arn,
            region=region,
            pillar=Pillar.OPERATIONAL,
            severity=Severity.MEDIUM,
            effort=Effort.LOW,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"- Add the missing tags ({', '.join(missing)}) to resource '{arn}'.\n"
                "- Enforce tagging via AWS Config rule 'required-tags' or a Service Control Policy."
            ),
            required_iam_permission="tag:GetResources",
        ))

    return findings


# ---------------------------------------------------------------------------
# 4. Secrets in Lambda Environment Variables
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    "password", "passwd", "secret", "api_key", "apikey",
    "token", "access_key", "private_key", "credentials",
    "db_pass", "database_password", "auth_token",
]


def check_secrets_in_lambda_env(functions: list[dict], region: str) -> list[Finding]:
    """
    Checks Lambda function environment variables for keys that suggest
    hardcoded secrets (vs. using AWS Secrets Manager or SSM Parameter Store).

    Args:
        functions: List of function dicts from lambda.list_functions()["Functions"].
                   Each dict should include:
                   - FunctionName (str)
                   - Environment.Variables (dict, optional)
        region: AWS region of the scan.

    IAM required: lambda:ListFunctions, lambda:GetFunctionConfiguration
    """
    findings = []

    for fn in functions:
        fn_name = fn.get("FunctionName", "unknown")
        env_vars = fn.get("Environment", {}).get("Variables", {})
        if not env_vars:
            continue

        suspicious = [
            key for key in env_vars
            if any(pattern in key.lower() for pattern in _SECRET_PATTERNS)
        ]

        if not suspicious:
            continue

        headline = f"Lambda '{fn_name}' may have secrets in environment variables"
        description = (
            f"Lambda function '{fn_name}' has environment variable keys that suggest "
            f"hardcoded secrets: {', '.join(suspicious)}. "
            "Storing secrets in plain environment variables risks exposure in CloudWatch Logs, "
            "IAM policies, and AWS Console sessions."
        )

        findings.append(Finding(
            finding_id=generate_finding_id("ops-ssm-001", fn_name, region),
            resource_id=fn_name,
            region=region,
            pillar=Pillar.OPERATIONAL,
            severity=Severity.HIGH,
            effort=Effort.MEDIUM,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                "- Migrate secret values to AWS Secrets Manager or SSM Parameter Store.\n"
                "- Reference them in Lambda using the /aws/reference/secretsmanager/ "
                "environment variable syntax or fetch programmatically at runtime."
            ),
            required_iam_permission="lambda:ListFunctions",
        ))

    return findings

# src/infra_review_cli/adapters/aws/aws_provider.py
"""
AWS implementation of the CloudProvider interface.
"""

from datetime import datetime, timezone
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from infra_review_cli.core.base_provider import BaseCloudProvider
from infra_review_cli.core.models import ScanResult, Pillar
from infra_review_cli.core.scoring import build_scan_result
from infra_review_cli.core.ai.remediation import generate_executive_summary

# Adapter imports
from infra_review_cli.adapters.aws.ec2_adapter import fetch_cpu_data, fetch_unassociated_eips, fetch_asg_findings
from infra_review_cli.adapters.aws.ebs_adapter import fetch_ebs_findings
from infra_review_cli.adapters.aws.s3_adapter import fetch_s3_public_info, fetch_s3_versioning_findings
from infra_review_cli.adapters.aws.elb_adapter import fetch_elb_findings, fetch_alb_dns_names
from infra_review_cli.adapters.aws.ecs_adapter import fetch_ecs_findings
from infra_review_cli.adapters.aws.vpc_adapter import fetch_vpc_findings
from infra_review_cli.adapters.aws.iam_adapter import fetch_iam_mfa_findings, fetch_root_activity_findings
from infra_review_cli.adapters.aws.rds_adapter import fetch_rds_findings
from infra_review_cli.adapters.aws.cloudtrail_adapter import fetch_cloudtrail_findings
from infra_review_cli.adapters.aws.cloudwatch_adapter import fetch_cloudwatch_alarm_findings
from infra_review_cli.adapters.aws.tagging_adapter import fetch_tagging_findings
from infra_review_cli.adapters.aws.lambda_adapter import fetch_lambda_findings
from infra_review_cli.adapters.aws.cloudfront_adapter import fetch_cloudfront_findings
from infra_review_cli.adapters.aws.sustainability_adapter import (
    fetch_graviton_usage_findings,
    fetch_idle_always_on_findings,
    fetch_lambda_memory_findings,
    fetch_s3_lifecycle_findings,
    fetch_unencrypted_ebs_findings,
)


class AWSProvider(BaseCloudProvider):
    """
    Main entry point for scanning an AWS account.
    """
    provider_name = "aws"

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._account_id: Optional[str] = None

    def validate_credentials(self) -> bool:
        """Checks if the user has valid AWS credentials."""
        try:
            sts = boto3.client("sts", region_name=self.region)
            identity = sts.get_caller_identity()
            self._account_id = identity["Account"]
            return True
        except (NoCredentialsError, ClientError):
            return False

    def get_account_id(self) -> str:
        if not self._account_id:
            self.validate_credentials()
        return self._account_id or "unknown"

    def get_checks(self, pillars=None, services=None) -> list:
        # Not used in the current orchestration flow which calls adapters directly.
        # But required by the BaseCloudProvider interface.
        return []

    def run_scan(
        self,
        pillars: Optional[list[str]] = None,
        services: Optional[list[str]] = None,
        severity_filter: Optional[list[str]] = None,
        dry_run: bool = False,
        progress_callback=None,
    ) -> ScanResult:
        """
        Runs the full scan orchestrating all adapters.
        """
        if dry_run:
            return ScanResult(provider="aws", region=self.region)

        scan_start = datetime.now(timezone.utc)
        findings = []
        # Track which pillars were actually checked for scoring
        checks_run_per_pillar = {p: 0 for p in Pillar}

        # List of scan steps to execute
        # Each step: (label, function, pillar_to_increment)
        steps = [
            ("IAM MFA", fetch_iam_mfa_findings, Pillar.SECURITY),
            ("Root Activity", fetch_root_activity_findings, Pillar.SECURITY),
            ("CloudTrail", fetch_cloudtrail_findings, Pillar.OPERATIONAL),
            ("CloudWatch Alarms", fetch_cloudwatch_alarm_findings, Pillar.OPERATIONAL),
            ("Resource Tagging", fetch_tagging_findings, Pillar.OPERATIONAL),
            ("Lambda Secrets", fetch_lambda_findings, Pillar.OPERATIONAL),
            ("RDS Health", fetch_rds_findings, Pillar.RELIABILITY),
            ("S3 Versioning", fetch_s3_versioning_findings, Pillar.RELIABILITY),
            ("ASG Coverage", fetch_asg_findings, Pillar.RELIABILITY),
            ("VPC Security", fetch_vpc_findings, Pillar.SECURITY),
            ("ECS Services", fetch_ecs_findings, Pillar.PERFORMANCE),
            ("EC2 Rightsizing", fetch_cpu_data, Pillar.COST),
            ("Elastic IPs", fetch_unassociated_eips, Pillar.COST),
            ("EBS Volumes", fetch_ebs_findings, Pillar.COST),
            ("Load Balancers", fetch_elb_findings, Pillar.COST),
            ("Graviton Adoption", fetch_graviton_usage_findings, Pillar.SUSTAINABILITY),
            ("S3 Lifecycle Policies", fetch_s3_lifecycle_findings, Pillar.SUSTAINABILITY),
            ("Idle Always-On Resources", fetch_idle_always_on_findings, Pillar.SUSTAINABILITY),
            ("Lambda Memory Tuning", fetch_lambda_memory_findings, Pillar.SUSTAINABILITY),
            ("Unencrypted EBS Volumes", fetch_unencrypted_ebs_findings, Pillar.SUSTAINABILITY),
        ]

        total_steps = len(steps) + 2  # +2 for S3 Public and CloudFront (special handling)

        # -------------------------------------------------------------------
        # Standard Scan Steps
        # -------------------------------------------------------------------
        for i, (label, func, pillar) in enumerate(steps):
            if progress_callback:
                progress_callback(label, i + 1, total_steps)
            
            # Simple filtering logic based on strings
            if pillars and pillar.value not in pillars:
                continue
                
            res = func(self.region)
            scan_ok = True
            findings_out = res

            # Sustainability adapter functions return (findings, scanned_ok)
            # so we can avoid marking pillars as scanned when calls fail.
            if (
                isinstance(res, tuple)
                and len(res) == 2
                and isinstance(res[1], bool)
            ):
                findings_out, scan_ok = res

            findings.extend(findings_out)
            if scan_ok:
                checks_run_per_pillar[pillar] += 1

        # -------------------------------------------------------------------
        # Specialized Steps (sharing data)
        # -------------------------------------------------------------------
        current_step = len(steps)
        
        # S3 Public Info (returns findings + names for next step)
        if progress_callback:
            progress_callback("S3 Public Access", current_step + 1, total_steps)
        
        s3_findings, public_bucket_names = fetch_s3_public_info(self.region)
        if not pillars or Pillar.SECURITY.value in pillars:
            findings.extend(s3_findings)
            checks_run_per_pillar[Pillar.SECURITY] += 1
        
        # CloudFront (uses public bucket names and alb dns)
        current_step += 1
        if progress_callback:
            progress_callback("CloudFront Coverage", current_step + 1, total_steps)
            
        alb_dns_names = fetch_alb_dns_names(self.region)
        cf_findings = fetch_cloudfront_findings(self.region, public_bucket_names, alb_dns_names)
        if not pillars or Pillar.PERFORMANCE.value in pillars:
            findings.extend(cf_findings)
            checks_run_per_pillar[Pillar.PERFORMANCE] += 1

        # -------------------------------------------------------------------
        # Build Result & Finalize
        # -------------------------------------------------------------------
        result = build_scan_result(
            findings=findings,
            checks_run_per_pillar=checks_run_per_pillar,
            account_id=self.get_account_id(),
            region=self.region,
            provider="aws",
            scan_timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        
        # Generate AI Executive Summary if enough findings
        if findings:
            result.executive_summary = generate_executive_summary(
                findings=findings,
                pillar_scores=result.pillar_scores,
                overall_score=result.overall_score,
                account_id=result.account_id,
                region=result.region
            )

        result.scan_duration_seconds = round(
            (datetime.now(timezone.utc) - scan_start).total_seconds(), 2
        )
        return result

"""
RDS checks — consolidated multi-AZ and backup retention.
"""

from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.utils.utility import generate_finding_id
from infra_review_cli.config import RDS_MIN_BACKUP_RETENTION_DAYS


def check_rds_multi_az(instances: list[dict], region: str) -> list[Finding]:
    """Flags RDS DB instances not running in Multi-AZ mode."""
    findings = []
    for inst in instances:
        if inst.get("MultiAZ", False):
            continue

        db_id = inst.get("DBInstanceIdentifier", "unknown")
        engine = inst.get("Engine", "unknown")
        instance_class = inst.get("DBInstanceClass", "unknown")

        headline = f"RDS instance '{db_id}' is not running in Multi-AZ"
        description = (
            f"RDS instance '{db_id}' ({engine}, {instance_class}) is configured as a single-AZ deployment. "
            "A failure in the underlying hardware or AZ will cause downtime."
        )

        findings.append(Finding(
            finding_id=generate_finding_id("rel-rds-001", db_id, region),
            resource_id=db_id,
            region=region,
            pillar=Pillar.RELIABILITY,
            severity=Severity.HIGH,
            effort=Effort.LOW,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"Modify the DB instance and enable Multi-AZ: "
                f"aws rds modify-db-instance --db-instance-identifier {db_id} --multi-az --apply-immediately"
            ),
            required_iam_permission="rds:DescribeDBInstances",
        ))
    return findings


def check_rds_backup_policy(instances: list[dict], region: str) -> list[Finding]:
    """Flags RDS instances with insufficient automated backup retention."""
    findings = []
    for inst in instances:
        db_id = inst.get("DBInstanceIdentifier", "unknown")
        retention = inst.get("BackupRetentionPeriod", 0)

        if retention >= RDS_MIN_BACKUP_RETENTION_DAYS:
            continue

        headline = f"RDS instance '{db_id}' has insufficient backup retention ({retention} day(s))"
        description = (
            f"Automated backups are configured for only {retention} day(s). "
            f"Minimum recommended is {RDS_MIN_BACKUP_RETENTION_DAYS} days."
        )
        sev = Severity.CRITICAL if retention == 0 else Severity.HIGH

        findings.append(Finding(
            finding_id=generate_finding_id("rel-rds-002", db_id, region),
            resource_id=db_id,
            region=region,
            pillar=Pillar.RELIABILITY,
            severity=sev,
            effort=Effort.LOW,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"Set backup retention to {RDS_MIN_BACKUP_RETENTION_DAYS} days: "
                f"aws rds modify-db-instance --db-instance-identifier {db_id} --backup-retention-period {RDS_MIN_BACKUP_RETENTION_DAYS}"
            ),
            required_iam_permission="rds:DescribeDBInstances",
        ))
    return findings

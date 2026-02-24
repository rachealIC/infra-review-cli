import os
from datetime import datetime
from infra_review_cli.core.models import ScanResult, Finding, PillarScore, Pillar, Severity, Effort
from infra_review_cli.utils.formatters import format_as_html

def generate_demo():
    # 1. Create a mock ScanResult
    result = ScanResult(
        account_id="123456789012",
        region="us-east-1",
        scan_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        overall_score=72,
        executive_summary="""
            Your AWS environment is in a **stable** state but requires optimization in **Cost** and **Security**. 
            We found several **unencrypted S3 buckets** and **idle EC2 instances** that are driving up costs. 
            Addressing these will improve your health score to **90+** and save approximately **$1,200/month**.
        """
    )
    
    # 2. Add Pillar Scores
    result.pillar_scores = {
        Pillar.SECURITY.value: PillarScore(Pillar.SECURITY, 45, 12, 5, critical_count=2, high_count=1, medium_count=2),
        Pillar.COST.value: PillarScore(Pillar.COST, 62, 8, 3, critical_count=0, high_count=2, medium_count=1),
        Pillar.RELIABILITY.value: PillarScore(Pillar.RELIABILITY, 88, 15, 1, critical_count=0, high_count=0, medium_count=1),
        Pillar.PERFORMANCE.value: PillarScore(Pillar.PERFORMANCE, 95, 10, 0),
        Pillar.OPERATIONAL.value: PillarScore(Pillar.OPERATIONAL, 78, 10, 2, high_count=1, low_count=1)
    }
    
    # 3. Add Mock Findings
    result.findings = [
        Finding(
            finding_id="f-1",
            resource_id="prod-data-bucket-01",
            region="us-east-1",
            pillar=Pillar.SECURITY,
            severity=Severity.CRITICAL,
            headline="Public Read/Write Access on S3 Bucket",
            detailed_description="This bucket contains sensitive customer PII and currently has `AllUsers` read/write permissions via ACL.",
            remediation_steps="""
1. Go to S3 Console
2. Select `prod-data-bucket-01`
3. Click **Permissions** tab
4. Enable **Block all public access**
5. Verify bucket policy doesn't explicitly allow `*` access.
            """,
            effort=Effort.LOW
        ),
        Finding(
            finding_id="f-2",
            resource_id="i-0abcdef123456789",
            region="us-east-1",
            pillar=Pillar.COST,
            severity=Severity.HIGH,
            headline="Severely Underutilized EC2 Instance",
            detailed_description="This `m5.2xlarge` instance has had < 2% CPU usage for the last 14 days.",
            remediation_steps="""
- **Downsize** to `t3.medium` to save 85% on costs.
- Use `aws ec2 modify-instance-attribute --instance-id i-0abcdef123456789 --instance-type t3.medium`
            """,
            effort=Effort.LOW,
            estimated_savings=420.50
        ),
        Finding(
            finding_id="f-3",
            resource_id="vpc-987654321",
            region="us-east-1",
            pillar=Pillar.RELIABILITY,
            severity=Severity.MEDIUM,
            headline="Single AZ Deployment for VPC Subnets",
            detailed_description="Critical workloads are currently running in only one Availability Zone (us-east-1a).",
            remediation_steps="Provision subnets in `us-east-1b` and `us-east-1c` to ensure high availability.",
            effort=Effort.MEDIUM
        ),
        Finding(
            finding_id="f-4",
            resource_id="root-account",
            region="global",
            pillar=Pillar.SECURITY,
            severity=Severity.CRITICAL,
            headline="MFA Not Enabled on Root User",
            detailed_description="The root user of this AWS account does not have Multi-Factor Authentication enabled.",
            remediation_steps="Immediately enable hardware or virtual MFA for the root user in the IAM console.",
            effort=Effort.LOW
        ),
        Finding(
            finding_id="f-5",
            resource_id="db-master-prod",
            region="us-east-1",
            pillar=Pillar.OPERATIONAL,
            severity=Severity.HIGH,
            headline="RDS DB Instance Missing Backup Plan",
            detailed_description="Automated backups are disabled for this production database.",
            remediation_steps="Modify the RDS instance to enable daily automated backups with a retention period of at least 7 days.",
            effort=Effort.MEDIUM
        )
    ]
    
    # 4. Generate HTML
    html_content = format_as_html(result)
    
    # 5. Save to file
    output_file = "/Users/rachealkuranchie/Documents/infra_review_cli/premium_infra_report_demo.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ Demo report generated at: {output_file}")

if __name__ == "__main__":
    generate_demo()

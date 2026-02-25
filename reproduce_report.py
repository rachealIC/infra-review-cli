import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
src_path = Path("/Users/rachealkuranchie/Documents/infra_review_cli/src")
sys.path.append(str(src_path))

# Mock markdown_it if not available for rendering test
try:
    from markdown_it import MarkdownIt
except ImportError:
    print("WARNING: markdown_it not found, using mock")
    class MarkdownIt:
        def render(self, content):
            return content

from infra_review_cli.core.models import ScanResult, Finding, Pillar, Severity, Effort, PillarScore
from infra_review_cli.utils.formatters import format_as_html
from infra_review_cli.reports.html_report import render_html_report

def test_rendering():
    # Mock data
    findings = [
        Finding(
            finding_id="f1",
            resource_id="i-1234567890abcdef0",
            region="us-east-1",
            pillar=Pillar.SECURITY,
            severity=Severity.CRITICAL,
            headline="S3 Bucket Publicly Accessible",
            detailed_description="The S3 bucket `my-public-bucket` is publicly accessible.",
            remediation_steps="Restrict access to the bucket.",
            effort=Effort.LOW,
            estimated_savings=0.0
        )
    ]

    pillar_scores = {
        Pillar.SECURITY.value: PillarScore(
            pillar=Pillar.SECURITY,
            score=45.0,
            total_checks_run=1,
            findings_count=1,
            critical_count=1
        )
    }

    result = ScanResult(
        findings=findings,
        pillar_scores=pillar_scores,
        overall_score=45.0,
        account_id="123456789012",
        region="us-east-1",
        scan_timestamp=datetime.now().isoformat(),
        executive_summary="Security issues found."
    )

    print("Rendering HTML report...")
    try:
        html_content = format_as_html(result)
        print(f"Report rendered, size: {len(html_content)} bytes")
        
        output_path = "test_verification_report.html"
        Path(output_path).write_text(html_content, encoding="utf-8")
        print(f"Report saved to: {output_path}")
        
        if len(html_content) < 500:
            print("FAILED: Report file is too small.")
            print("Content preview:")
            print(html_content[:200])
        else:
            print("SUCCESS: Report file generated with content.")
            print("Content preview:")
            print(html_content[:500])
            
    except Exception as e:
        print(f"ERROR during rendering: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rendering()

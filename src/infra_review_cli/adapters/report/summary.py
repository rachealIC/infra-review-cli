# src/infra_review_cli/reports/summary.py
"""
Summary and reporting utilities for infrastructure review
"""

from datetime import datetime
from typing import List
from src.infra_review_cli.core.models import Finding, Pillar, Severity

SEVERITY_EMOJIS = {
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "LOW": "🟢"
}


def display_summary(findings: List[Finding]) -> None:
    """Display a summary of findings by pillar and severity."""

    if not findings:
        print("✅ No issues found!")
        return

    # Group findings by pillar → severity
    summary = {}

    for finding in findings:
        pillar = finding.pillar.name if finding.pillar else "UNKNOWN"
        severity = finding.severity.name if finding.severity else "LOW"

        if pillar not in summary:
            summary[pillar] = {}
        if severity not in summary[pillar]:
            summary[pillar][severity] = 0
        summary[pillar][severity] += 1

    # Print summary
    print(f"\n📊 Summary: {len(findings)} total findings")
    total = sum(getattr(f, "estimated_savings", 0.0) for f in findings)
    print(f"\n💰 Estimated Total Monthly Savings: ${total:.2f}")

    for pillar, severities in summary.items():
        print(f"   🧱 {pillar.replace('_', ' ').title()}: {sum(severities.values())} issue(s)")
        for severity, count in severities.items():
            emoji = SEVERITY_EMOJIS.get(severity.upper(), "⚪")
            print(f"     {emoji} {severity.title()}: {count}")


def generate_filename(fmt: str) -> str:
    """Generate a timestamped filename like 'infra_report_20240723.html'"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"infra_report_{timestamp}.{fmt.lower()}"

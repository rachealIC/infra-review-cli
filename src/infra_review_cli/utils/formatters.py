import os
import json
from datetime import datetime
from markdown_it import MarkdownIt
from jinja2 import Template
from infra_review_cli.core.models import ScanResult, Pillar


def format_as_text(findings) -> str:
    """Basic text output for console (fallback)."""
    if not findings:
        return "✅ No findings discovered."

    output = [f"🔎 Found {len(findings)} finding(s):\n"]
    for f in findings:
        output.append(
            f"[{f.severity.value}] {f.headline}\n"
            f"  Resource: {f.resource_id} ({f.region})\n"
            f"  Pillar:   {f.pillar.value}\n"
            f"  Remediation: {f.remediation_steps}\n"
        )
        if f.estimated_savings > 0:
            output.append(f"  💰 Savings: ${f.estimated_savings:,.2f}/mo\n")
        output.append("-" * 40)
    return "\n".join(output)


def format_as_json(findings) -> str:
    """Standard JSON output."""
    def serialize(obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if hasattr(obj, "value"):  # Enums
            return obj.value
        return str(obj)

    return json.dumps(findings, default=serialize, indent=2)


def format_as_html(result: ScanResult) -> str:
    """
    Generates a premium, stakeholder-ready HTML report using Jinja2.
    """
    # 1. Load Template
    template_path = os.path.join(os.path.dirname(__file__), "report_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()
    
    template = Template(template_str)
    md = MarkdownIt()

    # 2. Prepare Pillar Data
    pillar_colors = {
        Pillar.SECURITY.value: "#8b5cf6",
        Pillar.COST.value: "#10b981",
        Pillar.RELIABILITY.value: "#3b82f6",
        Pillar.PERFORMANCE.value: "#06b6d4",
        Pillar.OPERATIONAL.value: "#f59e0b",
        Pillar.SUSTAINABILITY.value: "#84cc16"
    }
    
    # slugs for CSS variables
    pillar_slugs = {
        Pillar.SECURITY.value: "security",
        Pillar.COST.value: "cost",
        Pillar.RELIABILITY.value: "reliability",
        Pillar.PERFORMANCE.value: "performance",
        Pillar.OPERATIONAL.value: "operational",
        Pillar.SUSTAINABILITY.value: "sustainability"
    }

    pillars_list = []
    for name, ps in result.pillar_scores.items():
        pillars_list.append({
            "name": name,
            "score": int(ps.score),
            "status": ps.label.upper(),
            "emoji": ps.emoji,
            "findings_count": ps.findings_count,
            "critical_count": ps.critical_count,
            "color": pillar_colors.get(name, "#6366f1"),
            "slug": pillar_slugs.get(name, "security")
        })

    # 3. Prepare Findings Data
    findings_list = []
    for f in result.findings:
        findings_list.append({
            "finding_id": f.finding_id,
            "resource_id": f.resource_id,
            "region": f.region,
            "pillar": f.pillar.value,
            "pillar_slug": pillar_slugs.get(f.pillar.value, "security"),
            "severity": f.severity.value,
            "title": f.headline,
            "description": md.render(f.detailed_description or ""),
            "remediation": md.render(f.remediation_steps or ""),
            "estimated_savings": f.estimated_savings,
            "effort": f.effort.value
        })

    # Sort by severity
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    findings_list.sort(key=lambda x: severity_order.get(x["severity"], 4))

    # 4. Render
    return template.render(
        account_id=result.account_id,
        region=result.region.upper(),
        generated_at=result.scan_timestamp,
        overall_score=int(result.overall_score),
        monthly_savings=result.total_savings,
        ai_summary=result.executive_summary or "No summary available.",
        pillars=pillars_list,
        findings=findings_list
    )
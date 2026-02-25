import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
try:
    from markdown_it import MarkdownIt
except ImportError:
    # Fallback to a mock/noop if markdown-it-py is not available in the environment
    class MarkdownIt:
        def render(self, text):
            return text

from infra_review_cli.core.models import ScanResult, Pillar
from infra_review_cli.reports.html_report import render_html_report


def _parse_scan_timestamp(value: str) -> datetime | None:
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        cleaned = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _build_report_id(account_id: str, generated_at: str) -> str:
    timestamp = _parse_scan_timestamp(generated_at) or datetime.now(timezone.utc)
    account_token = "".join(ch for ch in str(account_id) if ch.isdigit()) or "UNKNOWN"
    return f"IR-{account_token}-{timestamp.strftime('%Y%m%d-%H%M%S')}"


def _resolve_app_version() -> str:
    try:
        return version("infra-review-cli")
    except PackageNotFoundError:
        return "0.2.0"


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
    Generates a premium, stakeholder-ready HTML report using a modular template system.
    """
    md = MarkdownIt()

    # 1. Prepare Pillar Data
    pillar_colors = {
        Pillar.SECURITY.value: "#2f9e8f",
        Pillar.COST.value: "#14b87f",
        Pillar.RELIABILITY.value: "#2a88c9",
        Pillar.PERFORMANCE.value: "#2aa7a0",
        Pillar.OPERATIONAL.value: "#d38a36",
        Pillar.SUSTAINABILITY.value: "#7ba93e"
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
        scanned = ps.total_checks_run > 0
        score_display = int(ps.score) if scanned else "N/A"
        status = ps.label.upper() if scanned else "NOT SCANNED"
        if not scanned:
            status_tone = "neutral"
        elif ps.score >= 75:
            status_tone = "good"
        elif ps.score >= 50:
            status_tone = "attention"
        else:
            status_tone = "risk"
        score_explainer = (
            "Score from checks run. Starts at 100 and deducts by severity; not a resource count."
            if scanned
            else "No checks were executed for this pillar in this scan."
        )
        pillars_list.append({
            "name": name,
            "score": int(ps.score),
            "status": status,
            "scanned": scanned,
            "score_display": score_display,
            "score_explainer": score_explainer,
            "status_tone": status_tone,
            "total_checks_run": ps.total_checks_run,
            "emoji": ps.emoji,
            "findings_count": ps.findings_count,
            "critical_count": ps.critical_count,
            "high_count": ps.high_count,
            "medium_count": ps.medium_count,
            "low_count": ps.low_count,
            "color": pillar_colors.get(name, "#6366f1"),
            "slug": pillar_slugs.get(name, "security")
        })

    # 2. Prepare Findings Data
    findings_list = []
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    prefix_by_pillar = {
        Pillar.SECURITY.value: "SEC",
        Pillar.COST.value: "COST",
        Pillar.RELIABILITY.value: "REL",
        Pillar.PERFORMANCE.value: "PERF",
        Pillar.OPERATIONAL.value: "OPS",
        Pillar.SUSTAINABILITY.value: "SUS",
    }
    finding_prefix_counters: dict[str, int] = {}

    findings_sorted = sorted(
        result.findings,
        key=lambda finding: severity_order.get(finding.severity.value, 4),
    )

    for f in findings_sorted:
        prefix = prefix_by_pillar.get(f.pillar.value, "GEN")
        finding_prefix_counters[prefix] = finding_prefix_counters.get(prefix, 0) + 1
        finding_ref_id = f"{prefix}-{finding_prefix_counters[prefix]:03d}"

        findings_list.append({
            "finding_id": f.finding_id,
            "finding_ref_id": finding_ref_id,
            "resource_id": f.resource_id,
            "region": f.region,
            "pillar": f.pillar.value,
            "pillar_slug": pillar_slugs.get(f.pillar.value, "security"),
            "severity": f.severity.value,
            "severity_rank": severity_order.get(f.severity.value, 4),
            "title": f.headline,
            "description": md.render(f.detailed_description or ""),
            "remediation": md.render(f.remediation_steps or ""),
            "estimated_savings": f.estimated_savings,
            "effort": f.effort.value,
            "status": "OPEN",
        })

    findings_json = json.dumps(findings_list).replace("</script>", "<\\/script>")
    pillars_json = json.dumps(pillars_list).replace("</script>", "<\\/script>")

    report_id = _build_report_id(result.account_id, result.scan_timestamp)
    duration_seconds = getattr(result, "scan_duration_seconds", None)
    if isinstance(duration_seconds, (int, float)):
        scan_duration = f"{duration_seconds:.2f}s"
    else:
        scan_duration = "N/A"

    # 3. Prepare Render Data
    data = {
        "account_id": result.account_id,
        "region": result.region.upper(),
        "generated_at": result.scan_timestamp,
        "report_id": report_id,
        "scan_duration": scan_duration,
        "app_version": _resolve_app_version(),
        "overall_score": int(result.overall_score),
        "monthly_savings": result.total_savings,
        "ai_summary": result.executive_summary or "No summary available.",
        "pillars": pillars_list,
        "findings": findings_list,
        "pillars_json": pillars_json,
        "findings_json": findings_json
    }

    # 4. Render and return HTML string
    return render_html_report(data)

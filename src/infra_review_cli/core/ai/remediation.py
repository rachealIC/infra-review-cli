# src/infra_review_cli/core/ai/remediation.py
"""
AI-powered remediation step generator and executive summary generator.
All functions return None gracefully if no AI provider is available.
"""

from .llm_client import call_ai


def generate_ai_remediation(headline: str, description: str) -> str | None:
    """
    Generate 1-2 concise remediation steps for a finding.
    Returns None if no AI is available (callers should use fallback hardcoded steps).
    """
    prompt = f"""
You are an AWS Well-Architected Framework expert.

A cloud infrastructure scan found the following issue:
- Headline: "{headline}"
- Description: {description}

Provide exactly 1–2 short, actionable remediation steps as bullet points.
Rules:
- Each step must be one line only
- Actionable — start with a verb (Enable, Delete, Restrict, Configure, etc.)
- No explanations or justifications
- Format: "- <step>"

Output only the bullet points. Nothing else.
""".strip()

    return call_ai(prompt)


def generate_executive_summary(
    findings: list,
    pillar_scores: dict,
    overall_score: float,
    account_id: str,
    region: str,
) -> str:
    """
    Generate a plain-English executive summary of the full scan.
    Suitable for a non-technical CTO/VP audience.
    Returns a fallback string if no AI is available.
    """
    finding_count = len(findings)
    total_savings = sum(getattr(f, "estimated_savings", 0.0) for f in findings)

    score_lines = "\n".join(
        f"  - {name}: {ps.score}/100 ({ps.label})"
        for name, ps in pillar_scores.items()
    )

    critical_count = sum(1 for f in findings if f.severity.value == "Critical")
    high_count = sum(1 for f in findings if f.severity.value == "High")

    prompt = f"""
You are a senior cloud architect writing an executive summary for a CTO.

Infrastructure scan results for AWS account {account_id} in {region}:
- Overall health score: {overall_score}/100
- Total findings: {finding_count}
- Critical findings: {critical_count}
- High-severity findings: {high_count}
- Estimated monthly savings if fixed: ${total_savings:,.2f}

Pillar scores:
{score_lines}

Write a 3-4 sentence executive summary:
1. Overall health assessment (use the score and key pillar concerns)
2. Most urgent action items (focus on critical/high findings)
3. Estimated financial impact

Use plain English. No bullet points. No technical jargon. Maximum 120 words.
""".strip()

    result = call_ai(prompt)
    if result:
        return result

    # Meaningful fallback if no AI is available
    return (
        f"This infrastructure scan of AWS account {account_id} ({region}) returned "
        f"{finding_count} finding(s) with an overall health score of {overall_score}/100. "
        f"There are {critical_count} critical and {high_count} high-severity issues that require "
        f"immediate attention. Addressing identified findings could save an estimated "
        f"${total_savings:,.2f}/month."
    )

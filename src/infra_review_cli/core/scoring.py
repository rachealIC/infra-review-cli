# src/infra_review_cli/core/scoring.py
"""
Pillar scoring engine for the Well-Architected health score.

Scoring model:
  - Each pillar starts at 100 points.
  - Each finding deducts points based on severity:
      Critical: -25  |  High: -15  |  Medium: -8  |  Low: -3
  - Score is clamped to [0, 100].
  - If a pillar has no checks run (not in scope), it is excluded from the overall average.

Overall health score = weighted average across all scored pillars.
"""

from infra_review_cli.core.models import Finding, Pillar, PillarScore, ScanResult
from infra_review_cli.config import PILLAR_DISPLAY_ORDER


def score_pillar(
    pillar: Pillar,
    findings: list[Finding],
    total_checks_run: int,
) -> PillarScore:
    """
    Compute a health score for a single pillar.

    Args:
        pillar:           The pillar being scored.
        findings:         All findings for this pillar.
        total_checks_run: How many distinct checks were executed for this pillar.
                          Used so a clean scan (zero findings) gives 100, not an error.

    Returns:
        A PillarScore with a 0–100 score and severity breakdown.
    """
    score = 100.0
    critical = high = medium = low = 0

    for f in findings:
        if f.pillar != pillar:
            continue
        deduction = f.severity.score_weight
        score = max(0.0, score - deduction)

        sev = f.severity.value
        if sev == "Critical":
            critical += 1
        elif sev == "High":
            high += 1
        elif sev == "Medium":
            medium += 1
        else:
            low += 1

    return PillarScore(
        pillar=pillar,
        score=round(score, 1),
        total_checks_run=total_checks_run,
        findings_count=len(findings),
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
    )


def score_all_pillars(
    findings: list[Finding],
    checks_run_per_pillar: dict[Pillar, int],
) -> dict[str, PillarScore]:
    """
    Compute scores for every pillar that had at least one check run.

    Args:
        findings:               All findings from the scan.
        checks_run_per_pillar:  Mapping of Pillar → number of checks executed.
                                Only pillars present in this mapping are scored.

    Returns:
        Dict mapping pillar name (str) → PillarScore.
    """
    pillar_findings: dict[Pillar, list[Finding]] = {}
    for f in findings:
        pillar_findings.setdefault(f.pillar, []).append(f)

    scores: dict[str, PillarScore] = {}
    for pillar, total_checks in checks_run_per_pillar.items():
        relevant_findings = pillar_findings.get(pillar, [])
        scores[pillar.value] = score_pillar(pillar, relevant_findings, total_checks)

    return scores


def overall_health_score(pillar_scores: dict[str, PillarScore]) -> float:
    """
    Compute the overall infrastructure health score as a weighted average.

    Weights are based on how critical each pillar is:
      Security × 2, Reliability × 2, Operational Excellence × 1.5,
      Performance × 1, Cost × 1.

    Args:
        pillar_scores: Output of score_all_pillars().

    Returns:
        A float between 0 and 100, or 0.0 if no pillars were scored.
    """
    pillar_weights = {
        "Security": 2.0,
        "Reliability": 2.0,
        "Operational Excellence": 1.5,
        "Performance Efficiency": 1.0,
        "Cost Optimization": 1.0,
        "Sustainability": 1.0,
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for pillar_name, ps in pillar_scores.items():
        # Pillars with zero checks were not scanned for this run; keep them visible
        # in reporting but exclude them from overall score math.
        if ps.total_checks_run == 0:
            continue
        weight = pillar_weights.get(pillar_name, 1.0)
        weighted_sum += ps.score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 1)


def build_scan_result(
    findings: list[Finding],
    checks_run_per_pillar: dict[Pillar, int],
    account_id: str,
    region: str,
    provider: str = "aws",
    scan_timestamp: str = "",
    executive_summary: str = "",
) -> ScanResult:
    """
    Combine findings, run scoring, and build the final ScanResult.

    This is the single function the CLI calls after all checks complete.
    """
    pillar_scores = score_all_pillars(findings, checks_run_per_pillar)
    health = overall_health_score(pillar_scores)

    return ScanResult(
        findings=findings,
        pillar_scores=pillar_scores,
        overall_score=health,
        account_id=account_id,
        region=region,
        provider=provider,
        scan_timestamp=scan_timestamp,
        executive_summary=executive_summary,
    )

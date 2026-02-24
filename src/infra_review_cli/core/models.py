# src/infra_review_cli/core/models.py
"""
Core domain models for Infra Review CLI.
These models are cloud-provider agnostic.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    @property
    def score_weight(self) -> int:
        """Points deducted from a pillar score per finding of this severity."""
        return {
            "Critical": 25,
            "High": 15,
            "Medium": 8,
            "Low": 3,
        }[self.value]

    @property
    def order(self) -> int:
        """Sort order: lower = more severe."""
        return {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}[self.value]


class Effort(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Pillar(str, Enum):
    SECURITY = "Security"
    COST = "Cost Optimization"
    RELIABILITY = "Reliability"
    PERFORMANCE = "Performance Efficiency"
    OPERATIONAL = "Operational Excellence"
    SUSTAINABILITY = "Sustainability"


@dataclass
class Finding:
    """
    A single infrastructure finding produced by a check.
    Cloud-provider agnostic — any provider's check should produce this.
    """
    finding_id: str
    resource_id: str
    region: str
    pillar: Pillar
    severity: Severity
    headline: str
    detailed_description: str = ""
    remediation_steps: str = ""
    effort: Effort = Effort.LOW
    estimated_savings: float = 0.0
    suggested_cpu_units: Optional[int] = None
    suggested_mem_mb: Optional[int] = None
    # IAM permission needed to run this check (for permission-error guidance)
    required_iam_permission: Optional[str] = None
    # Cloud provider tag (e.g. "aws", "gcp", "azure")
    provider: str = "aws"


@dataclass
class PillarScore:
    """
    Aggregated health score for a single Well-Architected pillar.
    """
    pillar: Pillar
    score: float              # 0–100
    total_checks_run: int
    findings_count: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    @property
    def label(self) -> str:
        if self.score >= 75:
            return "Good"
        elif self.score >= 50:
            return "Needs Attention"
        return "At Risk"

    @property
    def emoji(self) -> str:
        if self.score >= 75:
            return "🟢"
        elif self.score >= 50:
            return "🟡"
        return "🔴"


@dataclass
class ScanResult:
    """
    The complete result of a full infrastructure scan.
    Wraps all findings + per-pillar scores + metadata.
    """
    findings: list[Finding] = field(default_factory=list)
    pillar_scores: dict[str, PillarScore] = field(default_factory=dict)
    overall_score: float = 0.0
    account_id: str = "unknown"
    region: str = "unknown"
    scan_timestamp: str = ""
    provider: str = "aws"
    executive_summary: str = ""

    @property
    def total_savings(self) -> float:
        return sum(f.estimated_savings for f in self.findings)

    @property
    def findings_by_pillar(self) -> dict[str, list[Finding]]:
        result: dict[str, list[Finding]] = {}
        for f in self.findings:
            key = f.pillar.value
            result.setdefault(key, []).append(f)
        return result

    @property
    def findings_by_severity(self) -> dict[str, list[Finding]]:
        result: dict[str, list[Finding]] = {}
        for f in self.findings:
            key = f.severity.value
            result.setdefault(key, []).append(f)
        return result

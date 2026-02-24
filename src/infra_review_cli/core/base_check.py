# src/infra_review_cli/core/base_check.py
"""
Abstract base class for all infrastructure checks.

Design principles:
  - Cloud-provider agnostic: a check works with whatever data its run() method receives.
  - Each concrete check declares its pillar, default_severity, and required_iam_permission
    so the CLI can display the correct IAM guidance if the check fails.
  - Checks return list[Finding] — always a list, never a single Finding or None.
  - AI remediation is injected, not called directly inside checks. This keeps checks
    fast, testable, and usable with or without an AI key.

Adding a new check:
  1. Subclass BaseCheck in the relevant module (e.g. core/checks/reliability.py).
  2. Declare `pillar`, `default_severity`, and optionally `required_iam_permission`.
  3. Implement `run(**kwargs) -> list[Finding]`.
  4. Register the check in the provider's `get_checks()` method.

Adding a new cloud provider:
  1. Create an adapter package (e.g. adapters/gcp/).
  2. Subclass BaseCloudProvider (see base_provider.py).
  3. Implement `get_checks()`, `validate_credentials()`, and `get_account_id()`.
  4. Map each check to the appropriate BaseCheck subclass.
"""

from abc import ABC, abstractmethod
from typing import Optional

from  .models import Finding, Pillar, Severity


class BaseCheck(ABC):
    """
    Abstract base for a single infrastructure check.

    Subclasses must set class-level attributes:
        pillar               — the Well-Architected pillar this check covers.
        default_severity     — the default Severity if no finding-specific override.
        required_iam_permission — the exact IAM action string (e.g. "ec2:DescribeInstances")
                               that the caller needs. Used to surface helpful error messages.

    Class-level attributes can be overridden per-instance if a check spans multiple severities
    (e.g. HIGH for SSH open to 0.0.0.0/0 vs LOW for HTTP). In that case, the per-Finding
    severity takes precedence; `default_severity` is only for display/filtering purposes.
    """

    # ------------------------------------------------------------------
    # Class-level attributes — MUST be declared by every subclass
    # ------------------------------------------------------------------
    pillar: Pillar
    default_severity: Severity
    check_id: str = ""                        # Unique short identifier, e.g. "sec-s3-001"
    required_iam_permission: str = ""         # e.g. "s3:GetBucketPolicy"
    description: str = ""                     # One-line human description of what this check does

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------
    @abstractmethod
    def run(self, **kwargs) -> list[Finding]:
        """
        Execute this check and return a list of findings.

        Args:
            **kwargs: Check-specific input parameters (raw data fetched by the adapter).

        Returns:
            A list of Finding objects. Empty list means the check passed (no issues found).
            Must NEVER return None.
        """
        ...

    # ------------------------------------------------------------------
    # Optional hook — estimated savings for the whole check category.
    # Override in checks that can compute a global savings figure.
    # Individual findings carry their own estimated_savings field.
    # ------------------------------------------------------------------
    @property
    def estimated_savings(self) -> float:
        """Override to provide a check-level savings estimate."""
        return 0.0

    # ------------------------------------------------------------------
    # Convenience helpers available to all checks
    # ------------------------------------------------------------------
    def _no_findings(self) -> list[Finding]:
        """Explicitly return an empty findings list (for readability in run())."""
        return []

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} pillar={self.pillar.value!r} "
            f"id={self.check_id!r}>"
        )

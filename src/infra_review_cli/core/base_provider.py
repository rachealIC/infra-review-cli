# src/infra_review_cli/core/base_provider.py
"""
Abstract base class for cloud provider adapters.

This is the top-level integration point in the provider-agnostic architecture.

┌─────────────────────────────────────────────────────────────┐
│                     CLI / Orchestrator                      │
│   (adapters/cli/cli.py — provider-agnostic scan runner)     │
└────────────────────────┬────────────────────────────────────┘
                         │  uses
                         ▼
             ┌──────────────────────┐
             │   BaseCloudProvider  │  ◄── You implement this
             │   (this module)      │       for each new provider
             └──────────────────────┘
                    ▲         ▲
         implements │         │ implements
                    │         │
      ┌─────────────┐       ┌─────────────┐
      │ AWSProvider │       │ GCPProvider │  (future)
      │ (adapters/  │       │ (adapters/  │
      │  aws/…)     │       │  gcp/…)     │
      └─────────────┘       └─────────────┘

Each provider owns:
  - Credential validation
  - Fetching raw cloud data (boto3 / google-cloud-sdk / azure-sdk etc.)
  - Instantiating and running the relevant BaseCheck subclasses
  - Returning a ScanResult

Adding a new cloud provider (e.g. GCP):
  1. Create `src/infra_review_cli/adapters/gcp/` package.
  2. Create `gcp_provider.py` that subclasses BaseCloudProvider.
  3. Implement all abstract methods.
  4. Register the provider in `adapters/provider_registry.py`.
  5. The CLI will discover and offer it automatically.

No changes to the core models, scoring engine, or formatters are needed.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .models import ScanResult
from .base_check import BaseCheck


class BaseCloudProvider(ABC):
    """
    Abstract base for a cloud provider integration.

    A provider is responsible for:
        1. Validating that the user has credentials for this provider.
        2. Discovering and instantiating the set of checks relevant to the user's
           chosen pillar/service filter.
        3. Fetching the raw data each check needs and calling check.run().
        4. Returning a fully-populated ScanResult.

    The orchestrator (CLI) calls providers like this:
        provider = AWSProvider(region="us-east-1")
        if not provider.validate_credentials():
            raise PermissionError(...)
        result = provider.run_scan(pillars=["security"], dry_run=False)
    """

    # Subclasses must set this to a short identifier like "aws", "gcp", "azure"
    provider_name: str = ""

    # ------------------------------------------------------------------
    # Credential & identity
    # ------------------------------------------------------------------
    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Return True if valid credentials are available for this provider.
        Should NOT raise — return False and let the CLI handle messaging.
        """
        ...

    @abstractmethod
    def get_account_id(self) -> str:
        """
        Return the unique account/project identifier for this provider.
        E.g. AWS account ID, GCP project ID, Azure subscription ID.
        Used in reports and audit trails.
        """
        ...

    # ------------------------------------------------------------------
    # Check discovery
    # ------------------------------------------------------------------
    @abstractmethod
    def get_checks(
        self,
        pillars: Optional[list[str]] = None,
        services: Optional[list[str]] = None,
    ) -> list[BaseCheck]:
        """
        Return the list of check instances applicable to the requested scope.

        Args:
            pillars:  Optional filter — only return checks for these pillars.
                      Pillar names match the Pillar enum values (e.g. "Security").
            services: Optional filter — only return checks for these services.
                      Service names are provider-specific (e.g. "ec2", "s3").

        Returns:
            A list of instantiated BaseCheck objects, ready to call .run() on.
        """
        ...

    # ------------------------------------------------------------------
    # Scan execution
    # ------------------------------------------------------------------
    @abstractmethod
    def run_scan(
        self,
        pillars: Optional[list[str]] = None,
        services: Optional[list[str]] = None,
        severity_filter: Optional[list[str]] = None,
        dry_run: bool = False,
        progress_callback=None,
    ) -> ScanResult:
        """
        Execute all applicable checks and return a ScanResult.

        Args:
            pillars:           Filter to specific pillars.
            services:          Filter to specific services.
            severity_filter:   Only include findings at these severity levels.
            dry_run:           If True, return what *would* be scanned without
                               making any API calls.
            progress_callback: Optional callable(check_name: str, done: int, total: int)
                               invoked before each check runs. Used by the CLI to
                               render a progress bar.

        Returns:
            A ScanResult with all findings, pillar scores, account metadata, etc.
        """
        ...

    # ------------------------------------------------------------------
    # Optional: IAM / permission guidance
    # ------------------------------------------------------------------
    def get_required_permissions(self) -> list[dict]:
        """
        Return a list of IAM/permission descriptors for all checks this provider supports.
        Each item is a dict with keys: check_id, permission, description.

        Providers may override this to generate a least-privilege policy document.
        The default implementation returns an empty list.

        Example return value for AWS:
            [
                {
                    "check_id": "sec-s3-001",
                    "permission": "s3:GetBucketPolicy",
                    "description": "Needed to read S3 bucket policies for public access check"
                },
                ...
            ]
        """
        return []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider_name!r}>"

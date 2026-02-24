# src/infra_review_cli/adapters/provider_registry.py
"""
Registry for cloud providers. 
The CLI uses this to discover available providers without hardcoding them.
"""

from typing import Type
from infra_review_cli.core.base_provider import BaseCloudProvider
from infra_review_cli.adapters.aws.aws_provider import AWSProvider

# Map of provider_id (str) -> Provider Class
PROVIDERS: dict[str, Type[BaseCloudProvider]] = {
    "aws": AWSProvider,
}

def get_provider(provider_id: str) -> Type[BaseCloudProvider]:
    """Returns the provider class for the given ID."""
    provider_cls = PROVIDERS.get(provider_id.lower())
    if not provider_cls:
        raise ValueError(f"Unknown cloud provider: {provider_id}. Available: {list(PROVIDERS.keys())}")
    return provider_cls

def list_providers() -> list[str]:
    """Returns the list of registered provider IDs."""
    return list(PROVIDERS.keys())

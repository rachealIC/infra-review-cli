# src/infra_review_cli/adapters/aws/lambda_adapter.py
"""
AWS Lambda adapter — fetches function data for secrets check.
"""

import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.operational_excellence import check_secrets_in_lambda_env


def fetch_lambda_findings(region: str) -> list:
    """Fetches Lambda functions and checks for secrets in env vars."""
    client = boto3.client("lambda", region_name=region)
    functions = []

    try:
        paginator = client.get_paginator("list_functions")
        for page in paginator.paginate():
            functions.extend(page.get("Functions", []))
    except ClientError as e:
        if e.response["Error"]["Code"] == "AccessDenied":
            print("⚠️  Lambda check skipped — missing permission: lambda:ListFunctions")
        else:
            print(f"⚠️  Lambda: {e}")
        return []

    return check_secrets_in_lambda_env(functions, region)

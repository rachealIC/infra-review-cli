# src/infra_review_cli/adapters/aws/iam_adapter.py
"""
AWS IAM adapter — fetches data for IAM-related checks.
"""

import csv
import io
import time
import boto3
from botocore.exceptions import ClientError

from infra_review_cli.core.checks.iam import check_iam_mfa, check_root_account_activity


def fetch_iam_mfa_findings(region: str = "global") -> list:
    """
    Lists all IAM users and their MFA devices, then runs check_iam_mfa().

    IAM is a global service — region is only used for the Finding region field.
    """
    iam = boto3.client("iam")
    users_with_mfa = []

    try:
        paginator = iam.get_paginator("list_users")
        for page in paginator.paginate():
            for user in page.get("Users", []):
                username = user["UserName"]
                # Check if they have a console password (PasswordLastUsed is set if they do)
                try:
                    mfa_resp = iam.list_mfa_devices(UserName=username)
                    mfa_devices = mfa_resp.get("MFADevices", [])
                except ClientError:
                    mfa_devices = []

                users_with_mfa.append({
                    "UserName": username,
                    "UserId": user["UserId"],
                    "PasswordLastUsed": user.get("PasswordLastUsed"),
                    "MFADevices": mfa_devices,
                    "ConsoleAccess": user.get("PasswordLastUsed") is not None,
                })
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print(
                f"⚠️  IAM MFA check skipped — missing permission: iam:ListUsers "
                f"(Add it to your IAM policy to enable this check)"
            )
        else:
            print(f"⚠️  IAM: {e}")
        return []

    return check_iam_mfa(users_with_mfa, region)


def fetch_root_activity_findings(region: str = "global") -> list:
    """
    Generates and retrieves the IAM credential report, then checks root account activity.
    """
    iam = boto3.client("iam")

    try:
        # Trigger report generation
        iam.generate_credential_report()
        # Wait for it to be ready (usually <5s)
        for _ in range(10):
            result = iam.get_credential_report()
            if result.get("State") == "COMPLETE" or "Content" in result:
                break
            time.sleep(1)

        content = result["Content"].decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AccessDenied":
            print(
                "⚠️  Root activity check skipped — missing permission: iam:GenerateCredentialReport"
            )
        else:
            print(f"⚠️  IAM credential report: {e}")
        return []

    return check_root_account_activity(rows, region)

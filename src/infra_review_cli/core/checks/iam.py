# src/infra_review_cli/core/checks/security.py
"""
Additional Security pillar checks (supplementing vpc.py and s3_public_access.py).

Checks in this module:
  - check_iam_mfa_enabled   (sec-iam-001): IAM users without MFA
  - check_root_account_activity (sec-iam-002): Root account used recently
  - check_public_s3_acl     (sec-s3-002): S3 public ACLs (supplemental)
"""

from datetime import datetime, timezone, timedelta
from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.utils.utility import generate_finding_id


# ---------------------------------------------------------------------------
# 1. IAM MFA Enabled
# ---------------------------------------------------------------------------

def check_iam_mfa(users: list[dict], region: str = "global") -> list[Finding]:
    """
    Flags IAM users that do not have MFA enabled.

    Args:
        users: List of user dicts. Each should include:
               - UserName (str)
               - UserId (str)
               - MFADevices (list) — empty = no MFA
               - PasswordLastUsed (datetime, optional)
        region: Use "global" for IAM (it's a global service).

    IAM required: iam:ListUsers, iam:ListMFADevices
    """
    findings = []

    for user in users:
        username = user.get("UserName", "unknown")
        mfa_devices = user.get("MFADevices", [])
        has_console_password = user.get("PasswordLastUsed") is not None

        # Only flag users with console access (no point flagging service accounts
        # that never log in — they use access keys not passwords)
        if not has_console_password and not user.get("ConsoleAccess", True):
            continue

        if mfa_devices:
            continue

        headline = f"IAM user '{username}' does not have MFA enabled"
        description = (
            f"IAM user '{username}' has console access but no MFA device configured. "
            "If this account's password is compromised, an attacker has unrestricted "
            "console access to your AWS environment without a second factor."
        )

        findings.append(Finding(
            finding_id=generate_finding_id("sec-iam-001", username, region),
            resource_id=username,
            region=region,
            pillar=Pillar.SECURITY,
            severity=Severity.CRITICAL,
            effort=Effort.LOW,
            headline=headline,
            detailed_description=description,
            remediation_steps=(
                f"- Require the user to set up an MFA device: "
                f"AWS Console > IAM > Users > {username} > Security credentials > MFA.\n"
                "- Enforce MFA via an IAM policy condition: "
                "aws:MultiFactorAuthPresent: 'true'."
            ),
            required_iam_permission="iam:ListMFADevices",
        ))

    return findings


# ---------------------------------------------------------------------------
# 2. Root Account Activity
# ---------------------------------------------------------------------------

def check_root_account_activity(
    credential_report_rows: list[dict],
    region: str = "global",
    lookback_days: int = 30,
) -> list[Finding]:
    """
    Checks whether the AWS root account has been used recently.

    Args:
        credential_report_rows: Parsed rows from iam.generate_credential_report()
                                then iam.get_credential_report(). Filter for
                                the row where user == "<root_account>".
                                Keys: password_last_used (str or "N/A"), etc.
        region: "global" (IAM is global).
        lookback_days: Flag if root was used within this many days.

    IAM required: iam:GenerateCredentialReport, iam:GetCredentialReport
    """
    findings = []

    for row in credential_report_rows:
        if row.get("user") != "<root_account>":
            continue

        last_used_str = row.get("password_last_used", "N/A")
        if last_used_str in ("N/A", "no_information", "not_supported", ""):
            continue

        try:
            last_used = datetime.fromisoformat(last_used_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        days_ago = (datetime.now(timezone.utc) - last_used).days

        if days_ago <= lookback_days:
            headline = f"Root account was used {days_ago} day(s) ago"
            description = (
                f"The AWS root account was last used {days_ago} day(s) ago "
                f"(on {last_used.strftime('%Y-%m-%d')}). "
                "Root account usage bypasses IAM policies and provides unrestricted access. "
                "AWS strongly recommends not using the root account for routine operations."
            )

            findings.append(Finding(
                finding_id=generate_finding_id("sec-iam-002", "root", region),
                resource_id="<root_account>",
                region=region,
                pillar=Pillar.SECURITY,
                severity=Severity.CRITICAL,
                effort=Effort.LOW,
                headline=headline,
                detailed_description=description,
                remediation_steps=(
                    "- Create a dedicated IAM administrator user with least-privilege permissions "
                    "and use that for daily operations.\n"
                    "- Enable MFA on the root account and delete root access keys: "
                    "AWS Console > My Account > Security Credentials > Delete access keys."
                ),
                required_iam_permission="iam:GetCredentialReport",
            ))

    return findings

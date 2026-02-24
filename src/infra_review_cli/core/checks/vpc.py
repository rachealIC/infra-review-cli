from infra_review_cli.core.models import Finding, Pillar, Severity, Effort
from infra_review_cli.core.ai.remediation import generate_ai_remediation
from infra_review_cli.utils.utility import generate_finding_id


def check_insecure_sg_rules(sg: dict, region: str) -> list[Finding]:
    findings = []

    # Ports we consider critical if exposed publicly
    high_risk_ports = {22, 3389, 3306, 5432}  # SSH, RDP, MySQL, Postgres
    low_risk_ports = {80, 443}  # HTTP, HTTPS

    for rule in sg.get("IpPermissions", []):
        protocol = rule.get("IpProtocol", "any")
        from_port = rule.get("FromPort", -1)  # -1 means all ports
        to_port = rule.get("ToPort", -1)

        # Each rule can have multiple CIDR ranges
        for ip_range in rule.get("IpRanges", []):
            cidr = ip_range.get("CidrIp")

            # Only flag public access
            if cidr == "0.0.0.0/0":
                # Determine severity
                if from_port == -1:
                    severity = Severity.HIGH
                    port_desc = "all ports"
                elif from_port in high_risk_ports:
                    severity = Severity.HIGH
                    port_desc = f"port {from_port}"
                elif from_port in low_risk_ports:
                    severity = Severity.LOW
                    port_desc = f"port {from_port}"
                else:
                    severity = Severity.MEDIUM
                    port_desc = f"port {from_port}"

                # Create a finding
                headline = f"Security group '{sg['GroupId']}' allows public access on {port_desc}"
                description = (
                    f"The security group '{sg['GroupId']}' in region {region} allows inbound "
                    f"traffic from 0.0.0.0/0 on {port_desc} ({protocol}). "
                    f"This increases the attack surface and should be restricted."
                )

                # remediation = generate_ai_remediation(headline, description)

                findings.append(Finding(
                    finding_id=generate_finding_id("sec-vpc-001", sg["GroupId"], region),
                    resource_id=sg["GroupId"],
                    region=region,
                    pillar=Pillar.SECURITY,
                    severity=severity,
                    effort=Effort.LOW,
                    estimated_savings=0.0,
                    headline=headline,
                    detailed_description=description,
                    remediation_steps="	Restrict access to trusted IP ranges."
                ))

    return findings

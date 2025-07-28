import boto3
from src.infra_review_cli.core.checks.vpc import check_insecure_sg_rules


def fetch_insecure_default_sgs(region: str):
    ec2 = boto3.client("ec2", region_name=region)

    # Get all security groups named "default"
    # response = ec2.describe_security_groups(Filters=[
    #     {"Name": "group-name", "Values": ["default"]}
    # ])
    response = ec2.describe_security_groups()

    findings = []
    for sg in response["SecurityGroups"]:
        findings.extend(check_insecure_sg_rules(sg, region))

    return findings

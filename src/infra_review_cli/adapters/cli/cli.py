# # src/infra_review_cli/main.py
#
# import argparse
# import sys
# import os
# import tempfile
# import webbrowser
#
# from src.infra_review_cli.adapters.aws.ec2_adapter import fetch_cpu_data
# from src.infra_review_cli.core.formatters import format_as_text, format_as_json, format_as_html
#
#
# def run_interactive():
#     print("🛠 Welcome to Infra Review CLI (Interactive Mode)\n")
#
#     target = input("🔍 What would you like to check? (e.g., aws): ").strip().lower()
#     if target != "aws":
#         print("❌ Unsupported target. Only 'aws' is supported for now.")
#         return
#
#     region = input("🌍 AWS region to scan (default us-east-1): ").strip() or "us-east-1"
#
#     valid_formats = ["text", "json", "html"]
#     while True:
#         fmt = input("🖨️  Output format? (text / json / html): ").strip().lower() or "text"
#         if fmt in valid_formats:
#             break
#         print("❌ Invalid format. Please enter 'text', 'json', or 'html'.")
#
#     output = input("📁 Output file name (leave blank to print to console): ").strip()
#
#     if target == "aws":
#         findings = fetch_cpu_data(region=region)
#
#         if not findings:
#             content = "✅ No underutilized EC2 instances found."
#         else:
#             if fmt == "json":
#                 content = format_as_json(findings)
#             elif fmt == "html":
#                 content = format_as_html(findings)
#             else:
#                 content = format_as_text(findings)
#
#         if output:
#             with open(output, "w", encoding="utf-8") as f:
#                 f.write(content)
#             print(f"\n✅ Report saved to {output}")
#             if fmt == "html":
#                 try:
#                     webbrowser.open('file://' + os.path.realpath(output))
#                 except Exception:
#                     print("🌐 Could not open the file in a browser.")
#         else:
#             print("\n" + content)
#
#     else:
#         print("❌ Unsupported target for now. Try 'aws'.")
#
#
# def main():
#     # Check if no arguments were passed (interactive mode)
#     if len(sys.argv) == 1:
#         return run_interactive()
#
#     parser = argparse.ArgumentParser(description=" Infra Review CLI Tool")
#     subparsers = parser.add_subparsers(dest="command")
#
#     # Subcommand: check
#     check_parser = subparsers.add_parser("check", help="Run infrastructure checks")
#     check_parser.add_argument("target", choices=["aws", "logs", "all"], help="What to check")
#
#     check_parser.add_argument(
#         "--format",
#         choices=["text", "json", "html"],
#         default="text",
#         help="The output format, could be 'text', 'json', or 'html'. Default is 'text'."
#     )
#
#     check_parser.add_argument(
#         "--region",
#         default="us-east-1",
#         help="AWS region to check (default: us-east-1)."
#     )
#
#     check_parser.add_argument(
#         "--output",
#         help="File path to save the report (optional). If not set, output is printed to the console."
#     )
#
#     args = parser.parse_args()
#
#     if args.command == "check" and args.target == "aws":
#         findings = fetch_cpu_data(region=args.region)
#
#         if not findings:
#             output = "✅ No underutilized EC2 instances found."
#         else:
#             # Choose formatter based on --format
#             if args.format == "json":
#                 output = format_as_json(findings)
#             elif args.format == "html":
#                 output = format_as_html(findings)
#             else:
#                 output = format_as_text(findings)
#
#         if args.output:
#             with open(args.output, "w", encoding="utf-8") as f:
#                 f.write(output)
#             print(f"✅ Report saved to {args.output}")
#             if args.format == "html":
#                 try:
#                     webbrowser.open('file://' + os.path.realpath(args.output))
#                 except Exception:
#                     print("🌐 Could not open the file in a browser.")
#                     return None
#             return None
#         else:
#             print(output)
#             return None
#     else:
#         parser.print_help()
#         return None
#
#
# if __name__ == "__main__":
#     main()

# src/infra_review_cli/main.py


"""
Infrastructure Review CLI - Main Entry Point
"""
# src/infra_review_cli/main.py

import os
import sys
import webbrowser
import questionary
from pathlib import Path

from src.infra_review_cli.adapters.aws.ec2_adapter import fetch_cpu_data, fetch_unassociated_eips
from src.infra_review_cli.adapters.aws.ebs_adapter import fetch_unattached_ebs
from src.infra_review_cli.adapters.aws.ecs_adapter import fetch_ecs_task_def_drift
from src.infra_review_cli.adapters.aws.s3_adapter import fetch_s3_public_info
from src.infra_review_cli.adapters.aws.elb_adapter import fetch_elb_usage
from src.infra_review_cli.adapters.aws.vpc_adapter import fetch_insecure_default_sgs
from src.infra_review_cli.core.formatters import format_as_text, format_as_json, format_as_html
from src.infra_review_cli.adapters.report.summary import display_summary, generate_filename

# -----------------------
# Step 1: User Inputs
# -----------------------
def get_user_inputs():
    print("🛠️  Welcome to Infra Review CLI\n")

    # 1. Select AWS service
    service = questionary.select(
        "⚙️  Which AWS service?",
        choices=["ec2", "s3", "elb", "ecs","vpc", "all"],
        default="all"
    ).ask()

    # 2. Thresholds (only for ec2 or all)
    older_than = 30
    threshold = 20.0

    if service in ["ec2", "all"]:
        older_than_input = questionary.text("📆 EBS volume age threshold (days)", default="30").ask()
        try:
            older_than = int(older_than_input)
        except (ValueError, TypeError):
            print("❌ Invalid number. Using default of 30 days.")

        threshold_input = questionary.text("📉 CPU usage % threshold for underutilization", default="20").ask()
        try:
            threshold = float(threshold_input)
        except (ValueError, TypeError):
            print("❌ Invalid number. Using default of 20%.")

    # 3. AWS Region
    region = questionary.text("🌍 AWS region", default="us-east-1").ask()

    # 4. Output format
    fmt = questionary.select(
        "🖨️  Output format?",
        choices=["text", "json", "html"],
        default="text"
    ).ask()

    # 5. Output file
    default_file = generate_filename(fmt) if fmt != "text" else ""
    output_file = questionary.text("📁 Output file (leave blank for console)", default=default_file).ask()

    return service, older_than, threshold, region, fmt, output_file

# -----------------------
# Step 2: Run Checks
# -----------------------
def run_checks(service, region, older_than, threshold):
    print(f"\n⏳ Running checks in {region}...\n")
    findings = []

    if service in ["ec2", "all"]:
        print("🔍 Fetching EC2 data...")
        ec2_findings = fetch_cpu_data(region=region, threshold=threshold)
        ebs_findings = fetch_unattached_ebs(region=region, min_age_days=older_than)
        elasticip_findings= fetch_unassociated_eips(region=region)

        if ec2_findings:
            print(f"🔍 Found {len(ec2_findings)} underutilized EC2 instances.")
            findings.extend(ec2_findings)
        if ebs_findings:
            print(f"🔍 Found {len(ebs_findings)} unattached EBS volumes.")
            findings.extend(ebs_findings)
        if elasticip_findings:
            print(f"🔍 Found {len(elasticip_findings)} unassociated Elastic IPs.")
            findings.extend(elasticip_findings)

    if service in ["s3", "all"]:
        print("🔍 Checking public S3 buckets...")
        findings.extend(fetch_s3_public_info(region=region))

    if service in ["elb", "all"]:
        print("🔍 Checking unused Load Balancers...")
        findings.extend(fetch_elb_usage(region=region))

    if service in ["ecs", "all"]:
        print("🔍 Checking ECS task definition drift...")
        findings.extend(fetch_ecs_task_def_drift(region=region))

    if service in ["vpc", "all"]:
        print("🔍 Checking VPC  security groups...")
        findings.extend(fetch_insecure_default_sgs(region=region))

    return findings

# -----------------------
# Step 3: Output Results
# -----------------------
def output_results(findings, fmt, output_file):
    if not findings:
        content = "✅ No findings found."
    else:
        display_summary(findings)

        if fmt == "json":
            content = format_as_json(findings)
        elif fmt == "html":
            logo_data_uri = "https://wealth.ic.africa/img/logo.png"

            content = format_as_html(findings, logo_url=logo_data_uri)
        else:
            content = format_as_text(findings)

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Report saved to {output_file}")

            if fmt == "html":
                webbrowser.open('file://' + os.path.abspath(output_file))
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            print("\n" + content)
    else:
        print("\n" + content)

# -----------------------
# Entry Point
# -----------------------
def main():
    try:
        service, older_than, threshold, region, fmt, output_file = get_user_inputs()

        if any(x is None for x in [service, region, fmt]):
            print("\n⚠️  Operation cancelled.")
            return

        findings = run_checks(service, region, older_than, threshold)
        output_results(findings, fmt, output_file)

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

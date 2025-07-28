# src/infra_review_cli/main.py

import argparse

def check_command(target):
    if target == "aws":
        print("🔍 Checking AWS infrastructure...")
    elif target == "k8s":
        print("🔍 Checking Kubernetes infrastructure...")
    elif target == "logs":
        print("🔍 Checking auditing logs...")
    elif target == "all":
        print("🔍 Checking everything (AWS, K8s, and more)...")
    else:
        print(f"❌ Unknown target for check: {target}")

def audit_command(target):
    if target == "logs":
        print("🔒 Auditing log access...")
    elif target == "permissions":
        print("🔒 Auditing IAM permissions...")
    else:
        print(f"❌ Unknown audit target: {target}")

def report_command(target):
    if target == "summary":
        print("🧾 Generating summary report...")
    elif target == "detail":
        print("🧾 Generating detailed report...")
    else:
        print(f"❌ Unknown report type: {target}")

def main():
    parser = argparse.ArgumentParser(description="🛠 Infra Review CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: check
    check_parser = subparsers.add_parser("check", help="Run infrastructure checks")
    check_parser.add_argument("target", help="What to check (aws, k8s, logs, all)")

    # Subcommand: audit
    audit_parser = subparsers.add_parser("audit", help="Run audit checks")
    audit_parser.add_argument("target", help="What to audit (logs, permissions)")

    # Subcommand: report
    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_parser.add_argument("target", help="Type of report (summary, detail)")

    args = parser.parse_args()

    if args.command == "check":
        check_command(args.target)
    elif args.command == "audit":
        audit_command(args.target)
    elif args.command == "report":
        report_command(args.target)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

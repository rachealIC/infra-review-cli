# src/infra_review_cli/cli.py
"""
Modern CLI implementation using click and rich.
Supports both interactive prompts and flag-based automation.
"""

import os
import sys
import webbrowser
from typing import Optional

import click
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.theme import Theme

from .adapters.provider_registry import get_provider, list_providers
from .utils.formatters import format_as_text, format_as_json, format_as_html
from .utils.utility import generate_filename
from .core.models import ScanResult, Pillar


# Custom theme for brand alignment
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "pillar": "bold blue",
    "severity.critical": "bold white on red",
    "severity.high": "bold red",
    "severity.medium": "bold yellow",
    "severity.low": "dim white",
})

console = Console(theme=custom_theme)


def display_rich_summary(result: ScanResult):
    """Prints a beautiful summary table to the console."""
    console.print("\n")
    console.print(Panel(
        f"[bold white]Scan Complete for Account:[/][bold cyan] {result.account_id}[/] [dim]({result.region})[/]\n"
        f"[bold white]Overall Health Score:[/] [bold {result.overall_score >= 70 and 'green' or 'red'}]{result.overall_score}/100[/]",
        title="[bold blue]Infra Review Summary[/]",
        expand=False,
    ))

    table = Table(title="Pillar Health Scores", box=None, padding=(0, 2))
    table.add_column("Pillar", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Findings", justify="right")

    for name, ps in result.pillar_scores.items():
        status_color = "green" if ps.score >= 75 else "yellow" if ps.score >= 50 else "red"
        table.add_row(
            name,
            f"{ps.score}/100",
            f"[{status_color}]{ps.emoji} {ps.label}[/]",
            str(ps.findings_count)
        )
    
    console.print(table)
    console.print(f"\n[bold green]💰 Total Estimated Monthly Savings: ${result.total_savings:,.2f}[/]")
    
    if result.executive_summary:
        console.print(Panel(result.executive_summary, title="[bold cyan]AI Executive Summary[/]", border_style="cyan"))


@click.group()
def cli():
    """🛠 Infra Review CLI - Secure & Optimized Infrastructure Scanner."""
    pass


@cli.command()
@click.argument("provider", type=click.Choice(list_providers()), default="aws")
@click.option("--region", default="us-east-1", help="AWS region or Provider-specific region ID.")
@click.option("--format", "fmt", type=click.Choice(["text", "json", "html"]), default="text", help="Output format.")
@click.option("--output", "-o", help="Save report to this file.")
@click.option("--pillar", "-p", multiple=True, help="Filter by pillar (e.g., Security, Cost Optimization).")
@click.option("--severity", "-s", multiple=True, help="Filter by severity (e.g., Critical, High).")
@click.option("--dry-run", is_flag=True, help="Show which checks would run without executing them.")
@click.option("--interactive", "-i", is_flag=True, help="Run in interactive prompt mode.")


def check(provider, region, fmt, output, pillar, severity, dry_run, interactive):
    """Run infrastructure security and cost optimization checks."""
    
    if interactive or (not interactive and len(sys.argv) == 2):
        # Fallback to interactive mode if no options provided or explicitly requested
        provider, region, fmt, output, pillar, severity = run_interactive_prompts()
    
    provider_cls = get_provider(provider)
    scanner = provider_cls(region=region)

    if not scanner.validate_credentials():
        console.print(f"[error]Error:[/] Invalid or missing credentials for {provider.upper()}.")
        console.print("[dim]Please ensure your environment variables or local config files are set up properly.[/]")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        def progress_update(label, done, total):
            if label not in [t.description for t in progress.tasks]:
                progress.add_task(label, total=total)
            for task in progress.tasks:
                if task.description == label:
                    progress.update(task.id, completed=done)

        scan_result = scanner.run_scan(
            pillars=list(pillar) if pillar else None,
            severity_filter=list(severity) if severity else None,
            dry_run=dry_run,
            progress_callback=progress_update if not dry_run else None
        )

    if dry_run:
        console.print("[info]Dry run complete. No actual cloud calls were made.[/]")
        return

    # Handle Output
    if fmt == "json":
        content = format_as_json(scan_result.findings)
    elif fmt == "html":
        content = format_as_html(scan_result)  # Passing the whole ScanResult now!
    else:
        content = format_as_text(scan_result.findings)
        display_rich_summary(scan_result)

    if fmt == "html" and not output:
        output = generate_filename("html")

    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            console.print(f"\n[success]✅ Report saved to {output}[/]")
            if fmt == "html":
                webbrowser.open('file://' + os.path.abspath(output))
        except Exception as e:
            console.print(f"[error]Error saving file:[/] {e}")
    elif fmt != "text":
        # Print non-text formats to console if no output file
        console.print(content)


def run_interactive_prompts():
    """Wraps questionary prompts for interactive mode."""
    console.print(Panel.fit("🛠 [bold white]Welcome to Infra Review CLI[/]", border_style="blue"))
    
    provider = questionary.select(
        "Select Cloud Provider:",
        choices=list_providers(),
        default="aws"
    ).ask()
    
    region = questionary.text("Enter Region:", default="us-east-1").ask()
    
    fmt = questionary.select(
        "Output format?",
        choices=["text", "json", "html"],
        default="text"
    ).ask()
    
    output = questionary.text("Output file (leave blank for console):").ask()
    
    # Optional filtering
    filter_choice = questionary.confirm("Apply pillar/severity filters?", default=False).ask()
    pillars = []
    severities = []
    
    if filter_choice:
        pillars = questionary.checkbox(
            "Select Pillars to scan:",
            choices=[p.value for p in Pillar]
        ).ask()
        severities = questionary.checkbox(
            "Filter by Severity:",
            choices=["Critical", "High", "Medium", "Low"]
        ).ask()
        
    return provider, region, fmt, output, pillars, severities


def main():
    cli()


if __name__ == "__main__":
    main()
